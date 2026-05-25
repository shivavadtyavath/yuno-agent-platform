"""
Agent-to-agent messaging tool.
Allows one agent to send a task/message to another agent and get a response.
This is what enables multi-agent collaboration.
"""
from __future__ import annotations

import logging
from typing import Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# This will be injected at runtime by the engine
_engine_ref = None


def set_engine(engine) -> None:
    global _engine_ref
    _engine_ref = engine


@tool
def send_message_to_agent(agent_name: str, message: str, execution_id: Optional[str] = None) -> str:
    """
    Send a message or task to another agent and get their response.
    Use this to delegate subtasks to specialized agents.

    Args:
        agent_name: The name of the target agent to send the message to.
        message: The message or task to send to the agent.
        execution_id: Optional execution context ID.

    Returns:
        The response from the target agent.
    """
    if _engine_ref is None:
        return "Agent messaging is not available (engine not initialized)."

    try:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # A loop is already running in this thread, run in a separate thread context
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    _engine_ref.invoke_agent_by_name(agent_name, message, execution_id)
                )
                result = future.result(timeout=60)
        except RuntimeError:
            # No running loop in this background thread (standard for run_in_executor)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    _engine_ref.invoke_agent_by_name(agent_name, message, execution_id)
                )
            finally:
                loop.close()
        return result
    except Exception as e:
        logger.error("Agent messaging failed: %s", e)
        return f"Failed to reach agent '{agent_name}': {str(e)}"
