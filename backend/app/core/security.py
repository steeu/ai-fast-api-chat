from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.config import Settings, get_settings

# auto_error=False: get_current_user decides (via AUTH_ENABLED) if a missing token is an error
bearer_scheme = HTTPBearer(auto_error=False)


class User(BaseModel):
    id: str
    is_anonymous: bool = False


ANONYMOUS_USER = User(id="anonymous", is_anonymous=True)


def get_current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if not settings.auth_enabled:
        return ANONYMOUS_USER

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # TODO: Validate the JWT here (signature via JWKS, exp, aud, iss) and
    # read the user id from the "sub" claim, e.g. with PyJWT:
    #   claims = jwt.decode(credentials.credentials, key, algorithms=["RS256"], audience=...)
    #   return User(id=claims["sub"])
    return User(id="token-user")


CurrentUser = Annotated[User, Depends(get_current_user)]
