"""
Tests for Agent CRUD operations.
"""
import pytest
from fastapi.testclient import TestClient

from backend.core.database import get_db
from backend.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_create_agent():
    response = client.post("/api/v1/agents/", json={
        "name": "Test Agent",
        "role": "Test Role",
        "system_prompt": "You are a test agent.",
        "model": "gpt-4o-mini",
        "tools": ["calculator"],
    })
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == "Test Agent"
    assert data["role"] == "Test Role"
    assert "id" in data


def test_list_agents():
    client.post("/api/v1/agents/", json={"name": "Agent A", "role": "Role A"})
    client.post("/api/v1/agents/", json={"name": "Agent B", "role": "Role B"})

    response = client.get("/api/v1/agents/")
    assert response.status_code == 200
    agents = response.json()
    assert len(agents) >= 2


def test_get_agent():
    create_resp = client.post("/api/v1/agents/", json={
        "name": "Fetch Me",
        "role": "Fetchable",
    })
    assert create_resp.status_code == 201
    agent_id = create_resp.json()["id"]

    response = client.get(f"/api/v1/agents/{agent_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Fetch Me"


def test_update_agent():
    create_resp = client.post("/api/v1/agents/", json={
        "name": "Old Name",
        "role": "Old Role",
    })
    assert create_resp.status_code == 201
    agent_id = create_resp.json()["id"]

    response = client.put(f"/api/v1/agents/{agent_id}", json={"name": "New Name"})
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_delete_agent():
    create_resp = client.post("/api/v1/agents/", json={
        "name": "Delete Me",
        "role": "Deletable",
    })
    assert create_resp.status_code == 201
    agent_id = create_resp.json()["id"]

    response = client.delete(f"/api/v1/agents/{agent_id}")
    assert response.status_code == 204

    get_resp = client.get(f"/api/v1/agents/{agent_id}")
    assert get_resp.status_code == 404


def test_get_available_tools():
    response = client.get("/api/v1/agents/tools")
    assert response.status_code == 200
    tools = response.json()
    tool_names = [t["name"] for t in tools]
    assert "calculator" in tool_names
    assert "web_search" in tool_names
    assert "get_current_datetime" in tool_names


def test_agent_not_found():
    response = client.get("/api/v1/agents/nonexistent-id-xyz")
    assert response.status_code == 404
