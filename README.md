# smolagents-spraay

Spraay batch payment tools for [smolagents](https://github.com/huggingface/smolagents). An agent can pay up to 200 recipients in a single transaction on Base through the [Spraay](https://spraay.app) batch contract.

| Tool | What it does | Contract function |
| --- | --- | --- |
| `spraay_batch_send_eth` | Same ETH amount to every recipient | `sprayEqual` (token = zero address) |
| `spraay_batch_send_token` | Same ERC-20 amount (e.g. USDC) to every recipient | `sprayEqual` |
| `spraay_batch_send_eth_variable` | A different ETH amount per recipient | `sprayETH` |

Contract: `0x1646452F98E36A3c9Cfc3eDD8868221E207B5eEC` on Base mainnet (chain 8453).

> **These tools move real funds.** They sign transactions with the private key in `SPRAAY_PRIVATE_KEY`. Use a dedicated wallet that holds only what you are willing to let an agent spend, and review what your agent is asked to do.

## Install

```bash
pip install smolagents-spraay
```

## Use

```python
from smolagents import CodeAgent, InferenceClientModel
from smolagents_spraay import get_spraay_tools

agent = CodeAgent(tools=get_spraay_tools(), model=InferenceClientModel())
agent.run("Send 0.001 ETH to each of these addresses on Base: 0x..., 0x...")
```

Or call a tool directly:

```python
from smolagents_spraay import SpraayBatchSendTokenTool

send = SpraayBatchSendTokenTool()
print(
    send(
        token_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC on Base
        recipients=["0x...", "0x..."],
        amount_each="25.5",
    )
)
```

## Configuration

| Variable | Required | Meaning |
| --- | --- | --- |
| `SPRAAY_PRIVATE_KEY` | yes | Private key of the paying wallet |
| `SPRAAY_RPC_URL` | no | Base RPC endpoint. Default: `https://mainnet.base.org` |

## Behaviour

- **Fee.** The protocol fee is read live from the contract's `feeBps()` (currently 30 = 0.3%) and added on top of the total. ETH tools send `total + fee` as value; the token tool needs an allowance of `total + fee`.
- **Approvals are exact.** If the token allowance is too low, the tool approves exactly `total + fee`, waits for that transaction to succeed, then sends the batch. It never sets an unlimited allowance.
- **Token decimals** are read from the token contract. If you pass `decimals` and it disagrees with the chain, the tool refuses.
- **Amounts are decimal strings** and are converted exactly. An amount with more decimal places than the asset supports is rejected, not rounded.
- **Checks before sending.** At most 200 recipients, every address validated (a mixed-case address with a wrong checksum is rejected as a likely typo), the RPC must report chain 8453, and gas is estimated before signing, so a batch that would revert fails before anything is broadcast.
- **Return value.** A status line with the Basescan link on success, or `Error: ...`.

## Tests

```bash
pip install -e ".[dev]"
pytest              # offline: validation, call building, Hub serialisation
pytest -m live      # read-only checks against Base mainnet; no key, nothing is sent
```

The live suite confirms that every function in the bundled ABI exists in the deployed bytecode, and simulates the batch calls with `eth_call`.

## Hugging Face Hub

Each tool class is self-contained, so it can be shared with `Tool.push_to_hub` and loaded with `load_tool`:

```bash
python scripts/push_to_hub.py --namespace <your-hf-username-or-org>
```

```python
from smolagents import load_tool

send_eth = load_tool("<namespace>/spraay-batch-send-eth", trust_remote_code=True)
```

The script creates each Space as a static Space, which works on a free Hugging Face account, so the Spaces show a short info page instead of a Gradio demo. `load_tool` only needs `tool.py` and is unaffected.

Do not add a private key as a secret on the public Spaces this creates.

## Development

`src/smolagents_spraay/tools.py` is generated. Hub tools must be self-contained classes, so the shared constants and helpers are stamped into each class from one template. Edit `gen_tools.py`, then run `python gen_tools.py`.

## License

Apache-2.0
