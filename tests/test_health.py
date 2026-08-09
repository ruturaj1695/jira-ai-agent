from fastapi.testclient import TestClient

from rtb_jira_ai_agent.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_runtime_status() -> None:
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    assert response.json()["llm_provider"] == "ollama"


def test_query_uses_demo_data_without_external_credentials() -> None:
    response = client.post(
        "/api/v1/query",
        json={"conversation_id": "test", "query": "What are blockers in current sprint?"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "blockers"
    assert payload["metadata"]["issue_count"] >= 1
    assert "blocker" in payload["answer"].lower()
