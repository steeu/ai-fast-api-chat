import json

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.core.config import Settings


def parse_sse(body: str) -> list[tuple[str, object]]:
    """Turn an SSE body into a list of (event, json-decoded data)."""
    events = []
    for block in body.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        events.append((fields.get("event", "message"), json.loads(fields.get("data", "null"))))
    return events


def test_stream_returns_tokens_then_done(client: TestClient) -> None:
    response = client.post(
        "/api/chat/stream", json={"messages": [{"role": "user", "content": "Hallo Welt"}]}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = parse_sse(response.text)
    tokens = [data for event, data in events if event == "token"]
    assert "".join(tokens).strip() == "Echo: Hallo Welt"
    assert events[-1][0] == "done"


def test_usage_event_comes_before_done(client: TestClient) -> None:
    response = client.post(
        "/api/chat/stream", json={"messages": [{"role": "user", "content": "Hallo Welt"}]}
    )
    events = parse_sse(response.text)

    assert [event for event, _ in events[-2:]] == ["usage", "done"]
    usage = events[-2][1]
    assert usage["model"] == "fake"
    assert usage["output_tokens"] == 3
    # The fake model has no price, so no cost is claimed
    assert usage["cost_usd"] is None


def test_last_message_must_be_from_user(client: TestClient) -> None:
    response = client.post(
        "/api/chat/stream", json={"messages": [{"role": "assistant", "content": "Hi"}]}
    )
    events = parse_sse(response.text)
    assert events[-1][0] == "error"


def test_empty_messages_rejected(client: TestClient) -> None:
    response = client.post("/api/chat/stream", json={"messages": []})
    assert response.status_code == 422


def test_missing_api_key_returns_503(
    client: TestClient, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.llm_provider = "openai"
    settings.openai_api_key = None
    # Use the real provider factory instead of the FakeProvider override
    client.app.dependency_overrides.pop(deps.get_llm_provider)
    monkeypatch.setattr(deps, "get_settings", lambda: settings)
    deps._cached_provider.cache_clear()

    response = client.post(
        "/api/chat/stream", json={"messages": [{"role": "user", "content": "Hi"}]}
    )

    deps._cached_provider.cache_clear()
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]
