"""
Tool registry — maps tool names to LangChain tool objects.
"""
from __future__ import annotations

from typing import Dict, List
from langchain_core.tools import BaseTool

from backend.runtime.tools.web_search import web_search
from backend.runtime.tools.calculator import calculator
from backend.runtime.tools.datetime_tool import get_current_datetime
from backend.runtime.tools.agent_messenger import send_message_to_agent

TOOL_REGISTRY: Dict[str, BaseTool] = {
    "web_search": web_search,
    "calculator": calculator,
    "get_current_datetime": get_current_datetime,
    "send_message_to_agent": send_message_to_agent,
}


def get_tools(tool_names: List[str]) -> List[BaseTool]:
    """Return tool objects for the given list of tool names."""
    return [TOOL_REGISTRY[name] for name in tool_names if name in TOOL_REGISTRY]


def list_available_tools() -> List[Dict]:
    """Return metadata about all available tools."""
    result = []
    for name, tool in TOOL_REGISTRY.items():
        result.append({
            "name": name,
            "description": tool.description,
        })
    return result
