from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.schemas.chat import ChatMessage


class OpenAIProvider:
    def __init__(self, api_key: str | None, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def stream(self, messages: list[ChatMessage], system_prompt: str) -> AsyncIterator[str]:
        stream = await self.client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=[{"role": m.role, "content": m.content} for m in messages],
            stream=True,
        )
        async for event in stream:
            if event.type == "response.output_text.delta":
                yield event.delta
            elif event.type in ("response.failed", "error"):
                raise RuntimeError(f"OpenAI stream failed: {event.type}")
