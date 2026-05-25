"""
Tests for message delivery, execution tracking, tools, and event bus.
"""
import asyncio
import pytest
from fastapi.testclient import TestClient

from backend.core.database import get_db
from backend.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_execution_stats_empty():
    response = client.get("/api/v1/executions/stats/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_agents" in data
    assert "total_executions" in data
    assert "total_tokens_used" in data
    assert data["total_agents"] == 0
    assert data["total_executions"] == 0


def test_list_executions_empty():
    response = client.get("/api/v1/executions/")
    assert response.status_code == 200
    assert response.json() == []


def test_execution_not_found():
    response = client.get("/api/v1/executions/nonexistent-id-xyz")
    assert response.status_code == 404


def test_calculator_tool():
    """Calculator tool works correctly."""
    from backend.runtime.tools.calculator import calculator
    result = calculator.invoke({"expression": "2 + 2"})
    assert "4" in result

    result = calculator.invoke({"expression": "100 * 1.08"})
    assert "108" in result

    result = calculator.invoke({"expression": "10 / 0"})
    assert "zero" in result.lower()


def test_datetime_tool():
    """Datetime tool returns a valid date string."""
    from backend.runtime.tools.datetime_tool import get_current_datetime
    result = get_current_datetime.invoke({"timezone_name": "UTC"})
    assert "UTC" in result
    # Should contain a 4-digit year
    import re
    assert re.search(r'\d{4}', result)


def test_event_bus_emit():
    """Event bus stores emitted events."""
    from backend.core.events import bus, Event

    event = Event(
        type="test_event",
        payload={"message": "hello"},
        execution_id="test-exec-123",
    )

    # Use asyncio.run for Python 3.12 compatibility
    asyncio.run(bus.emit(event))

    history = bus.get_history(limit=50)
    assert any(e["type"] == "test_event" for e in history)


def test_monitor_history_endpoint():
    response = client.get("/api/v1/monitor/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "agents_loaded" in data
    assert "version" in data


def test_memory_add_and_search():
    """Memory system stores and retrieves messages."""
    from backend.runtime.memory import AgentMemory
    mem = AgentMemory("test-agent-001", window_size=5, persist_dir="./test_memory")
    mem.clear()  # start fresh

    mem.add_message("human", "What is the capital of France?", "msg-1")
    mem.add_message("assistant", "The capital of France is Paris.", "msg-2")

    recent = mem.get_recent_messages()
    assert len(recent) == 2
    assert recent[0]["role"] == "human"

    results = mem.search_memory("France capital")
    assert len(results) >= 1
    assert any("France" in r or "Paris" in r for r in results)

    mem.clear()


def test_tools_registry():
    """All expected tools are registered."""
    from backend.runtime.tools import list_available_tools, TOOL_REGISTRY
    tools = list_available_tools()
    names = [t["name"] for t in tools]
    assert "web_search" in names
    assert "calculator" in names
    assert "get_current_datetime" in names
    assert "send_message_to_agent" in names
    assert len(TOOL_REGISTRY) >= 4
