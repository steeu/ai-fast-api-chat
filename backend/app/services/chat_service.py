from collections.abc import AsyncIterator

from app.core.pricing import ModelPrice, estimate_cost
from app.providers.base import LLMProvider
from app.schemas.chat import ChatMessage, Usage, UsageReport


class ChatService:
    """Business logic for the chat. Knows nothing about HTTP or a specific LLM provider."""

    def __init__(
        self,
        provider: LLMProvider,
        system_prompt: str,
        prices: dict[str, ModelPrice],
        usd_to_chf: float,
    ) -> None:
        self.provider = provider
        self.system_prompt = system_prompt
        self.prices = prices
        self.usd_to_chf = usd_to_chf

    async def stream_reply(self, messages: list[ChatMessage]) -> AsyncIterator[str | UsageReport]:
        if messages[-1].role != "user":
            raise ValueError("The last message must come from the user.")
        async for item in self.provider.stream(messages, self.system_prompt):
            if isinstance(item, Usage):
                yield self._report(item)
            else:
                yield item

    def _report(self, usage: Usage) -> UsageReport:
        # Cost is computed here, not in the provider, so it works the same for every provider
        cost_usd = estimate_cost(
            self.prices,
            usage.model,
            input_tokens=usage.input_tokens,
            cached_tokens=usage.cached_tokens,
            output_tokens=usage.output_tokens,
        )
        cost_chf = None if cost_usd is None else cost_usd * self.usd_to_chf
        return UsageReport(**usage.model_dump(), cost_chf=cost_chf)
