# Copyright Plagtech
# SPDX-License-Identifier: Apache-2.0
"""Spraay batch payment tools for smolagents."""

from .tools import SpraayBatchSendEthTool, SpraayBatchSendEthVariableTool, SpraayBatchSendTokenTool

__version__ = "0.1.0"


def get_spraay_tools():
    """Return one instance of each Spraay tool, ready to pass to an agent."""
    return [SpraayBatchSendEthTool(), SpraayBatchSendTokenTool(), SpraayBatchSendEthVariableTool()]


__all__ = [
    "SpraayBatchSendEthTool",
    "SpraayBatchSendEthVariableTool",
    "SpraayBatchSendTokenTool",
    "get_spraay_tools",
]
