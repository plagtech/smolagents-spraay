"""Run a CodeAgent with the Spraay batch payment tools.

Requires SPRAAY_PRIVATE_KEY (a funded Base wallet) and Hugging Face inference access.
This sends a real transaction.
"""

import sys

from smolagents import CodeAgent, InferenceClientModel

from smolagents_spraay import get_spraay_tools

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('usage: python examples/agent.py "Send 0.001 ETH to each of 0x... and 0x... on Base"')
    agent = CodeAgent(tools=get_spraay_tools(), model=InferenceClientModel())
    print(agent.run(sys.argv[1]))
