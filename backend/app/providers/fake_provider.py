import asyncio
from collections.abc import AsyncIterator

from app.schemas.chat import ChatMessage, Usage


class FakeProvider:
    """Echoes the last user message word by word. For tests and development without API key."""

    def __init__(self, delay: float = 0.05) -> None:
        self.delay = delay

    async def stream(
        self, messages: list[ChatMessage], system_prompt: str
    ) -> AsyncIterator[str | Usage]:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        words = f"Echo: {last_user}".split(" ")
        for word in words:
            if self.delay:
                await asyncio.sleep(self.delay)
            yield word + " "
        # Rough estimate: one token per word
        prompt = [system_prompt, *(m.content for m in messages)]
        yield Usage(
            model="fake",
            input_tokens=sum(len(text.split()) for text in prompt),
            output_tokens=len(words),
        )
