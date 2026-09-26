from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.schemas.chat import ChatMessage, Usage


class OpenAIProvider:
    def __init__(self, api_key: str | None, model: str, temperature: float | None = None) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature

    async def stream(
        self, messages: list[ChatMessage], system_prompt: str
    ) -> AsyncIterator[str | Usage]:
        # Only send temperature when configured, so models that reject it keep working
        extra = {} if self.temperature is None else {"temperature": self.temperature}
        stream = await self.client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=[{"role": m.role, "content": m.content} for m in messages],
            stream=True,
            **extra,
        )
        async for event in stream:
            if event.type == "response.output_text.delta":
                yield event.delta
            elif event.type in ("response.completed", "response.incomplete"):
                # Final event; incomplete (e.g. max tokens reached) is billed as well
                if usage := event.response.usage:
                    yield Usage(
                        model=event.response.model,
                        input_tokens=usage.input_tokens,
                        cached_tokens=usage.input_tokens_details.cached_tokens,
                        output_tokens=usage.output_tokens,
                        reasoning_tokens=usage.output_tokens_details.reasoning_tokens,
                    )
            elif event.type in ("response.failed", "error"):
                raise RuntimeError(f"OpenAI stream failed: {event.type}")
