from fastapi.testclient import TestClient

from app.core.config import Settings

BODY = {"messages": [{"role": "user", "content": "Hi"}]}


def test_auth_disabled_allows_anonymous(client: TestClient) -> None:
    assert client.post("/api/chat/stream", json=BODY).status_code == 200


def test_auth_enabled_requires_token(client: TestClient, settings: Settings) -> None:
    settings.auth_enabled = True
    response = client.post("/api/chat/stream", json=BODY)
    assert response.status_code == 401


def test_auth_enabled_accepts_bearer_token(client: TestClient, settings: Settings) -> None:
    settings.auth_enabled = True
    response = client.post(
        "/api/chat/stream", json=BODY, headers={"Authorization": "Bearer dummy-token"}
    )
    assert response.status_code == 200
