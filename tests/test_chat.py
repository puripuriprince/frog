import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "frog" in response.json()["service"]


def test_chat_completions_simple():
    """Test simple chat completion without workflow."""
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-frog_test"},
        json={
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Hello"}]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert len(data["choices"]) > 0
    assert "message" in data["choices"][0]


def test_chat_completions_streaming():
    """Test streaming chat completion."""
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-frog_test"},
        json={
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": True
        }
    )
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]


def test_chat_completions_with_workflow():
    """Test chat completion with workflow."""
    workflow = {
        "id": "test_workflow",
        "name": "Test Workflow",
        "nodes": [
            {
                "id": "search",
                "tool": {
                    "type": "browser.search",
                    "parameters": {"query": "test query"}
                },
                "depends_on": []
            }
        ]
    }
    
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-frog_test"},
        json={
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Search for something"}],
            "workflow": workflow
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data


def test_unauthorized_request():
    """Test request without API key."""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Hello"}]
        }
    )
    assert response.status_code == 401


def test_invalid_api_key():
    """Test request with invalid API key."""
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer invalid_key"},
        json={
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Hello"}]
        }
    )
    assert response.status_code == 401


def test_list_models():
    """Test models endpoint."""
    response = client.get(
        "/v1/models",
        headers={"Authorization": "Bearer sk-frog_test"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) > 0 