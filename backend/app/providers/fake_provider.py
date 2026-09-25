import asyncio
from collections.abc import AsyncIterator

from app.schemas.chat import ChatMessage


class FakeProvider:
    """Echoes the last user message word by word. For tests and development without API key."""

    def __init__(self, delay: float = 0.05) -> None:
        self.delay = delay

    async def stream(self, messages: list[ChatMessage], system_prompt: str) -> AsyncIterator[str]:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        for word in f"Echo: {last_user}".split(" "):
            if self.delay:
                await asyncio.sleep(self.delay)
            yield word + " "
