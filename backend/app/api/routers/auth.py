from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthConfig(BaseModel):
    enabled: bool
    issuer: str | None
    client_id: str | None
    project_id: str | None


@router.get("/config")
async def auth_config(settings: Annotated[Settings, Depends(get_settings)]) -> AuthConfig:
    """Public login settings for the frontend, so one image works in every environment."""
    if not settings.auth_enabled:
        return AuthConfig(enabled=False, issuer=None, client_id=None, project_id=None)
    return AuthConfig(
        enabled=True,
        issuer=settings.zitadel_issuer,
        client_id=settings.zitadel_client_id,
        project_id=settings.zitadel_project_id,
    )
