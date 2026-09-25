from collections.abc import AsyncIterator
from typing import Protocol

from app.schemas.chat import ChatMessage


class LLMProvider(Protocol):
    """Common interface for all LLM providers (OpenAI, Anthropic, fake, ...)."""

    def stream(self, messages: list[ChatMessage], system_prompt: str) -> AsyncIterator[str]:
        """Yield the model's answer piece by piece as text deltas."""
        ...
