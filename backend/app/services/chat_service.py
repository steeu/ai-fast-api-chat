from collections.abc import AsyncIterator

from app.providers.base import LLMProvider
from app.schemas.chat import ChatMessage


class ChatService:
    """Business logic for the chat. Knows nothing about HTTP or a specific LLM provider."""

    def __init__(self, provider: LLMProvider, system_prompt: str) -> None:
        self.provider = provider
        self.system_prompt = system_prompt

    async def stream_reply(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        if messages[-1].role != "user":
            raise ValueError("The last message must come from the user.")
        async for delta in self.provider.stream(messages, self.system_prompt):
            yield delta
