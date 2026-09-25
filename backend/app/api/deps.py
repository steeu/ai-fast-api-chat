from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.providers.base import LLMProvider
from app.providers.factory import ProviderConfigError, create_provider
from app.services.chat_service import ChatService


@lru_cache
def _cached_provider() -> LLMProvider:
    # Cached so the HTTP client of the provider is reused across requests
    return create_provider(get_settings())


def get_llm_provider() -> LLMProvider:
    try:
        return _cached_provider()
    except ProviderConfigError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


def get_chat_service(
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> ChatService:
    return ChatService(provider=provider, system_prompt=settings.system_prompt)


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
