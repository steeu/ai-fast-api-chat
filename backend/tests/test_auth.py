import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import get_jwks_client

BODY = {"messages": [{"role": "user", "content": "Hi"}]}
ISSUER = "https://test.zitadel.cloud"
PROJECT_ID = "project-123"

PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class FakeJWKSClient:
    """Stands in for Zitadel's key endpoint and always returns our test public key."""

    def get_signing_key_from_jwt(self, token: str) -> SimpleNamespace:
        return SimpleNamespace(key=PRIVATE_KEY.public_key())


def make_token(
    key: Any = PRIVATE_KEY, roles: tuple[str, ...] = ("chat-user",), **claims: Any
) -> str:
    now = int(time.time())
    payload = {
        "iss": ISSUER,
        "aud": [PROJECT_ID, "client-456"],
        "sub": "user-1",
        "iat": now,
        "exp": now + 3600,
        "urn:zitadel:iam:org:project:roles": {role: {"org-1": "example.ch"} for role in roles},
        **claims,
    }
    return jwt.encode(payload, key, algorithm="RS256")


@pytest.fixture
def auth_client(client: TestClient, settings: Settings) -> TestClient:
    settings.auth_enabled = True
    settings.zitadel_issuer = ISSUER
    settings.zitadel_client_id = "client-456"
    settings.zitadel_project_id = PROJECT_ID
    client.app.dependency_overrides[get_jwks_client] = FakeJWKSClient
    return client


def post(client: TestClient, token: str | None = None) -> int:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post("/api/chat/stream", json=BODY, headers=headers).status_code


def test_auth_disabled_allows_anonymous(client: TestClient) -> None:
    assert post(client) == 200


def test_auth_enabled_requires_token(auth_client: TestClient) -> None:
    assert post(auth_client) == 401


def test_valid_token_with_role_is_accepted(auth_client: TestClient) -> None:
    assert post(auth_client, make_token()) == 200


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(make_token(exp=int(time.time()) - 3600), id="expired"),
        pytest.param(make_token(aud="other-project"), id="wrong-audience"),
        pytest.param(make_token(iss="https://evil.example"), id="wrong-issuer"),
        pytest.param(make_token(key=OTHER_KEY), id="wrong-signature"),
        pytest.param("not-a-jwt", id="garbage"),
    ],
)
def test_invalid_token_is_rejected(auth_client: TestClient, token: str) -> None:
    assert post(auth_client, token) == 401


def test_token_without_role_is_forbidden(auth_client: TestClient) -> None:
    assert post(auth_client, make_token(roles=())) == 403


def test_project_specific_roles_claim_is_accepted(auth_client: TestClient) -> None:
    token = make_token(
        roles=(), **{f"urn:zitadel:iam:org:project:{PROJECT_ID}:roles": {"chat-user": {}}}
    )
    assert post(auth_client, token) == 200


def test_auth_config_is_public(auth_client: TestClient) -> None:
    response = auth_client.get("/api/auth/config")
    assert response.status_code == 200
    assert response.json() == {
        "enabled": True,
        "issuer": ISSUER,
        "client_id": "client-456",
        "project_id": PROJECT_ID,
    }


def test_auth_config_hides_values_when_disabled(client: TestClient) -> None:
    assert client.get("/api/auth/config").json()["enabled"] is False


def test_auth_enabled_without_zitadel_settings_fails_at_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ZITADEL_ISSUER", raising=False)
    with pytest.raises(ValueError, match="ZITADEL_ISSUER"):
        Settings(_env_file=None, auth_enabled=True)


def test_env_file_wins_over_environment_variables(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("ZITADEL_ISSUER=https://from-env-file.zitadel.cloud\n")
    monkeypatch.setenv("ZITADEL_ISSUER", "https://from-shell.zitadel.cloud")
    monkeypatch.setenv("ZITADEL_CLIENT_ID", "client-from-shell")

    settings = Settings(_env_file=env_file)

    assert settings.zitadel_issuer == "https://from-env-file.zitadel.cloud"
    # Values missing in .env still come from the environment (Docker --env-file)
    assert settings.zitadel_client_id == "client-from-shell"


def test_unreachable_key_endpoint_returns_503(auth_client: TestClient) -> None:
    class UnreachableJWKSClient:
        def get_signing_key_from_jwt(self, token: str) -> None:
            raise jwt.PyJWKClientConnectionError("timeout")

    auth_client.app.dependency_overrides[get_jwks_client] = UnreachableJWKSClient
    assert post(auth_client, make_token()) == 503
