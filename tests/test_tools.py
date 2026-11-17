"""Offline tests: validation, call building (mocked chain), Hub serialisation."""

import inspect
import json
from unittest.mock import MagicMock

import pytest
from eth_utils import keccak
from smolagents import Tool

from smolagents_spraay import (
    SpraayBatchSendEthTool,
    SpraayBatchSendEthVariableTool,
    SpraayBatchSendTokenTool,
    get_spraay_tools,
)

A1 = "0x742D35CC6634C0532925a3B844Bc9E7595F2bD18"
A2 = "0x53d284357ec70cE289D6D64134DfAc8E511c8a3D"
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
CLASSES = [SpraayBatchSendEthTool, SpraayBatchSendTokenTool, SpraayBatchSendEthVariableTool]
SHARED_ATTRS = [
    "SPRAAY_CONTRACT",
    "BASE_CHAIN_ID",
    "FALLBACK_FEE_BPS",
    "MAX_FEE_BPS",
    "MAX_RECIPIENTS",
    "SPRAAY_ABI_JSON",
    "ERC20_ABI_JSON",
    "ZERO_ADDRESS",
    "DEFAULT_RPC",
    "RECEIPT_TIMEOUT",
]
SHARED_METHODS = ["_check_recipients", "_to_units", "_connect", "_fee", "_send"]

# 4-byte selectors of the deployed SprayContract functions (confirmed in bytecode by tests/test_live.py).
EXPECTED_SELECTORS = {"sprayETH": "970aa1f2", "sprayToken": "fb83b683", "sprayEqual": "fdee1820", "feeBps": "24a9d853"}


def _sig(entry):
    def t(i):
        if i["type"].startswith("tuple"):
            return "(" + ",".join(t(c) for c in i["components"]) + ")" + i["type"][5:]
        return i["type"]

    return f"{entry['name']}({','.join(t(i) for i in entry['inputs'])})"


def fake_chain(tool, monkeypatch, fee_bps=30, allowance=0, decimals=6):
    """Replace _connect/_send with recorders. Returns (contract, sends)."""
    w3 = MagicMock()
    w3.from_wei.side_effect = lambda v, unit: v / 10**18
    account = MagicMock()
    account.address = "0x000000000000000000000000000000000000dEaD"
    contract = MagicMock()
    contract.address = tool.SPRAAY_CONTRACT
    contract.functions.feeBps.return_value.call.return_value = fee_bps
    token = MagicMock()
    token.address = USDC
    token.functions.decimals.return_value.call.return_value = decimals
    token.functions.allowance.return_value.call.return_value = allowance
    w3.eth.contract.return_value = token
    sends = []

    def _send(w3_, account_, call, value=0):
        sends.append((call, value))
        return "0x" + "ab" * 32, True

    monkeypatch.setattr(tool, "_connect", lambda: (w3, account, contract))
    monkeypatch.setattr(tool, "_send", _send)
    return contract, token, sends


def test_abi_selectors_match_deployed_contract():
    for cls in CLASSES:
        got = {e["name"]: keccak(text=_sig(e))[:4].hex() for e in json.loads(cls.SPRAAY_ABI_JSON)}
        assert got == EXPECTED_SELECTORS


def test_shared_code_is_identical_across_tools():
    base = CLASSES[0]
    for cls in CLASSES[1:]:
        for attr in SHARED_ATTRS:
            assert getattr(cls, attr) == getattr(base, attr), attr
        for m in SHARED_METHODS:
            assert inspect.getsource(getattr(cls, m)) == inspect.getsource(getattr(base, m)), m


def test_names_match_the_original_pr():
    assert [t.name for t in get_spraay_tools()] == [
        "spraay_batch_send_eth",
        "spraay_batch_send_token",
        "spraay_batch_send_eth_variable",
    ]


@pytest.mark.parametrize("cls", CLASSES)
def test_hub_serialisation_round_trip(cls):
    d = cls().to_dict()  # raises if the class is not self-contained
    assert "web3" in d["requirements"] and "smolagents" in d["requirements"]
    rebuilt = Tool.from_dict(d)
    assert rebuilt.name == cls.name and rebuilt.inputs == cls.inputs
    assert rebuilt.SPRAAY_ABI_JSON == cls.SPRAAY_ABI_JSON
    # the rebuilt (Hub-loaded) code actually runs
    with pytest.raises(ValueError, match="Invalid address"):
        rebuilt._check_recipients(["0x123"])
    assert rebuilt._to_units("1.5", 6) == 1_500_000


def test_validation_errors_need_no_network(monkeypatch):
    monkeypatch.delenv("SPRAAY_PRIVATE_KEY", raising=False)
    eth, tok, var = get_spraay_tools()
    assert eth([A1] * 201, "0.001") == "Error: Maximum 200 recipients per transaction."
    assert eth([], "0.001").startswith("Error: Recipients must be a non-empty list")
    assert eth(["0x123"], "0.001") == "Error: Invalid address: 0x123"
    typo = "0x742d35Cc6634C0532925a3b844Bc9e7595f2bD18"  # mixed case, wrong checksum
    assert eth([typo], "0.001") == f"Error: Address has a bad checksum (possible typo): {typo}"
    assert eth([A1], "0").startswith("Error: Amount must be greater than 0")
    assert eth([A1], "-1").startswith("Error: Amount must be greater than 0")
    assert eth([A1], "abc") == "Error: Invalid amount: abc"
    assert eth([A1], "nan").startswith("Error: Amount must be greater than 0")
    assert eth([A1], "0.0000000000000000001") == "Error: Amount 0.0000000000000000001 has more than 18 decimal places."
    assert var([A1, A2], ["0.001"]) == "Error: Number of recipients must match number of amounts."
    assert tok("nope", [A1], "1") == "Error: Invalid token address: nope"
    assert eth([A1], "0.001") == "Error: Set the SPRAAY_PRIVATE_KEY environment variable."


def test_eth_equal_calls_sprayEqual_with_zero_address_and_fee(monkeypatch):
    tool = SpraayBatchSendEthTool()
    contract, _, sends = fake_chain(tool, monkeypatch)
    out = tool([A1, A2.lower()], "0.001")
    contract.functions.sprayEqual.assert_called_once_with(tool.ZERO_ADDRESS, [A1, A2], 10**15)
    total = 2 * 10**15
    assert sends == [(contract.functions.sprayEqual.return_value, total + total * 30 // 10000)]
    assert "Status: Success" in out and "https://basescan.org/tx/0x" in out and "Recipients: 2" in out


def test_eth_variable_calls_sprayETH_with_structs(monkeypatch):
    tool = SpraayBatchSendEthVariableTool()
    contract, _, sends = fake_chain(tool, monkeypatch, fee_bps=50)
    tool([A1, A2], ["0.001", "0.0025"])
    contract.functions.sprayETH.assert_called_once_with([(A1, 10**15), (A2, 25 * 10**14)])
    total = 35 * 10**14
    assert sends[0][1] == total + total * 50 // 10000


def test_fee_falls_back_when_live_read_is_out_of_range(monkeypatch):
    tool = SpraayBatchSendEthTool()
    _, _, sends = fake_chain(tool, monkeypatch, fee_bps=9999)
    tool([A1], "1")
    assert sends[0][1] == 10**18 + 10**18 * 30 // 10000


def test_token_approves_exactly_total_plus_fee_then_sprays(monkeypatch):
    tool = SpraayBatchSendTokenTool()
    contract, token, sends = fake_chain(tool, monkeypatch, allowance=0, decimals=6)
    out = tool(USDC, [A1, A2], "25.5")
    total = 2 * 25_500_000
    token.functions.approve.assert_called_once_with(tool.SPRAAY_CONTRACT, total + total * 30 // 10000)
    contract.functions.sprayEqual.assert_called_once_with(USDC, [A1, A2], 25_500_000)
    assert [s[0] for s in sends] == [token.functions.approve.return_value, contract.functions.sprayEqual.return_value]
    assert all(v == 0 for _, v in sends)
    assert "Approval tx:" in out


def test_token_skips_approval_when_allowance_is_enough(monkeypatch):
    tool = SpraayBatchSendTokenTool()
    _, token, sends = fake_chain(tool, monkeypatch, allowance=10**12)
    out = tool(USDC, [A1], "1")
    token.functions.approve.assert_not_called()
    assert len(sends) == 1 and "Approval tx:" not in out


def test_token_rejects_wrong_decimals_and_excess_precision(monkeypatch):
    tool = SpraayBatchSendTokenTool()
    _, _, sends = fake_chain(tool, monkeypatch, decimals=6)
    assert tool(USDC, [A1], "1", 18) == "Error: decimals=18 does not match the token's on-chain decimals (6)."
    assert tool(USDC, [A1], "1.0000001") == "Error: Amount 1.0000001 has more than 6 decimal places."
    assert sends == []


def test_token_stops_if_approval_fails(monkeypatch):
    tool = SpraayBatchSendTokenTool()
    contract, _, _ = fake_chain(tool, monkeypatch)
    monkeypatch.setattr(tool, "_send", lambda *a, **k: ("0x" + "cd" * 32, False))
    assert tool(USDC, [A1], "1").startswith("Error: Token approval failed")
    contract.functions.sprayEqual.assert_not_called()
