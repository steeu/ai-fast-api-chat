from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.config import Settings, get_settings

# auto_error=False: get_current_user decides (via AUTH_ENABLED) if a missing token is an error
bearer_scheme = HTTPBearer(auto_error=False)

# Roles of the project the token was issued for: {"chat-user": {"<org id>": "<org domain>"}}
ROLES_CLAIM = "urn:zitadel:iam:org:project:roles"


class User(BaseModel):
    id: str
    roles: frozenset[str] = frozenset()
    is_anonymous: bool = False


ANONYMOUS_USER = User(id="anonymous", is_anonymous=True)


@lru_cache
def _cached_jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    # Cached so the public keys are fetched once and reused; unknown key ids trigger a refetch
    return jwt.PyJWKClient(jwks_url, cache_keys=True)


def get_jwks_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> jwt.PyJWKClient | None:
    if not settings.auth_enabled:
        return None
    return _cached_jwks_client(f"{settings.zitadel_issuer}/oauth/v2/keys")


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _roles(claims: dict[str, Any], project_id: str) -> frozenset[str]:
    # Zitadel asserts the roles generically and per project; accept either
    project_roles = claims.get(f"urn:zitadel:iam:org:project:{project_id}:roles", {})
    return frozenset({*claims.get(ROLES_CLAIM, {}), *project_roles})


def get_current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    jwks_client: Annotated[jwt.PyJWKClient | None, Depends(get_jwks_client)],
) -> User:
    if not settings.auth_enabled:
        return ANONYMOUS_USER
    if jwks_client is None:
        # Fail closed: auth is on, so never fall back to anonymous
        raise RuntimeError("JWKS client missing although auth is enabled.")

    if credentials is None:
        raise _unauthorized("Not authenticated")

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(credentials.credentials)
        claims = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.zitadel_project_id,
            issuer=settings.zitadel_issuer,
            options={"require": ["exp", "iss", "aud", "sub"]},
            leeway=30,
        )
    except jwt.PyJWKClientConnectionError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="Login service unreachable."
        ) from exc
    except jwt.PyJWTError as exc:
        # Never log or return the token itself
        raise _unauthorized("Invalid or expired token") from exc

    user = User(id=claims["sub"], roles=_roles(claims, settings.zitadel_project_id or ""))
    if settings.auth_required_role not in user.roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Missing required role.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
