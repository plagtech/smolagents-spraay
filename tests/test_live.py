"""Read-only checks against Base mainnet. No key needed, no transaction sent.

Run with:  pytest -m live
"""

import json
import os

import pytest
from eth_utils import keccak
from web3 import Web3
from web3.exceptions import ContractLogicError

from smolagents_spraay import SpraayBatchSendEthTool

pytestmark = pytest.mark.live
T = SpraayBatchSendEthTool
A1 = "0x742D35CC6634C0532925a3B844Bc9E7595F2bD18"
A2 = "0x53d284357ec70cE289D6D64134DfAc8E511c8a3D"
# Any address holding plenty of ETH on Base works as the simulated sender (WETH contract).
RICH = "0x4200000000000000000000000000000000000006"
OLD_PR_SIGNATURES = [
    "batchSendETH(address[],uint256)",
    "batchSendToken(address,address[],uint256)",
    "batchSendETHVariable(address[],uint256[])",
    "batchSendTokenVariable(address,address[],uint256[])",
]


def signature(entry):
    def t(i):
        if i["type"].startswith("tuple"):
            return "(" + ",".join(t(c) for c in i["components"]) + ")" + i["type"][5:]
        return i["type"]

    return f"{entry['name']}({','.join(t(i) for i in entry['inputs'])})"


@pytest.fixture(scope="module")
def w3():
    w3 = Web3(Web3.HTTPProvider(os.environ.get("SPRAAY_RPC_URL") or T.DEFAULT_RPC))
    assert w3.eth.chain_id == T.BASE_CHAIN_ID
    return w3


@pytest.fixture(scope="module")
def contract(w3):
    return w3.eth.contract(address=Web3.to_checksum_address(T.SPRAAY_CONTRACT), abi=json.loads(T.SPRAAY_ABI_JSON))


def test_every_abi_function_exists_in_deployed_bytecode(w3, contract):
    code = w3.eth.get_code(contract.address).hex()
    assert len(code) > 100
    for entry in json.loads(T.SPRAAY_ABI_JSON):
        assert keccak(text=signature(entry))[:4].hex() in code, entry["name"]


def test_function_names_from_the_closed_pr_are_not_deployed(w3, contract):
    code = w3.eth.get_code(contract.address).hex()
    for sig in OLD_PR_SIGNATURES:
        assert keccak(text=sig)[:4].hex() not in code, sig


def test_live_fee_is_readable_and_within_cap(contract):
    assert 0 <= contract.functions.feeBps().call() <= T.MAX_FEE_BPS


def test_equal_and_variable_eth_sprays_simulate_cleanly(w3, contract):
    fee_bps = contract.functions.feeBps().call()
    each = 10**12
    total = 2 * each
    value = total + total * fee_bps // 10000
    contract.functions.sprayEqual(T.ZERO_ADDRESS, [A1, A2], each).call({"from": RICH, "value": value})
    contract.functions.sprayETH([(A1, each), (A2, each)]).call({"from": RICH, "value": value})
    gas = contract.functions.sprayEqual(T.ZERO_ADDRESS, [A1, A2], each).estimate_gas({"from": RICH, "value": value})
    assert 21000 < gas < 500000


def test_underpaying_the_fee_reverts(contract):
    each = 10**12
    with pytest.raises(ContractLogicError):
        contract.functions.sprayEqual(T.ZERO_ADDRESS, [A1, A2], each).call({"from": RICH, "value": 2 * each})
