from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_docs_disabled_by_default(client: TestClient) -> None:
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_api_docs_enabled_by_setting() -> None:
    client = TestClient(create_app(Settings(_env_file=None, api_docs_enabled=True)))
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
