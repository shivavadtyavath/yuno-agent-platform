"""
Tests for workflow creation and execution.
"""
import pytest
from fastapi.testclient import TestClient

from backend.core.database import get_db
from backend.main import app

client = TestClient(app, raise_server_exceptions=False)

SAMPLE_GRAPH = {
    "nodes": [
        {
            "id": "node1",
            "type": "agent",
            "position": {"x": 100, "y": 100},
            "data": {
                "label": "Test Agent",
                "agentId": "",
                "isStart": True,
            },
        }
    ],
    "edges": [],
}


def test_create_workflow():
    response = client.post("/api/v1/workflows/", json={
        "name": "Test Workflow",
        "description": "A test workflow",
        "graph": SAMPLE_GRAPH,
    })
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == "Test Workflow"
    assert "id" in data


def test_list_workflows():
    client.post("/api/v1/workflows/", json={"name": "WF 1", "graph": {}})
    client.post("/api/v1/workflows/", json={"name": "WF 2", "graph": {}})

    response = client.get("/api/v1/workflows/")
    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_get_workflow():
    create_resp = client.post("/api/v1/workflows/", json={
        "name": "Fetch Workflow",
        "graph": {},
    })
    assert create_resp.status_code == 201
    wf_id = create_resp.json()["id"]

    response = client.get(f"/api/v1/workflows/{wf_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Fetch Workflow"


def test_update_workflow():
    create_resp = client.post("/api/v1/workflows/", json={
        "name": "Old WF",
        "graph": {},
    })
    assert create_resp.status_code == 201
    wf_id = create_resp.json()["id"]

    response = client.put(f"/api/v1/workflows/{wf_id}", json={"name": "Updated WF"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated WF"


def test_delete_workflow():
    create_resp = client.post("/api/v1/workflows/", json={
        "name": "Delete WF",
        "graph": {},
    })
    assert create_resp.status_code == 201
    wf_id = create_resp.json()["id"]

    response = client.delete(f"/api/v1/workflows/{wf_id}")
    assert response.status_code == 204

    get_resp = client.get(f"/api/v1/workflows/{wf_id}")
    assert get_resp.status_code == 404


def test_list_templates():
    response = client.get("/api/v1/workflows/templates")
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) >= 2
    names = [t["name"] for t in templates]
    assert "Customer Support Triage" in names
    assert "Research & Summarize" in names


def test_workflow_not_found():
    response = client.get("/api/v1/workflows/nonexistent-xyz")
    assert response.status_code == 404
