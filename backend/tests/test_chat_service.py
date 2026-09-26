import asyncio
from collections.abc import AsyncIterator

import pytest

from app.core.pricing import ModelPrice
from app.schemas.chat import ChatMessage, Usage, UsageReport
from app.services.chat_service import ChatService


class PricedProvider:
    """Reports a fixed usage for a model with a known price."""

    async def stream(
        self, messages: list[ChatMessage], system_prompt: str
    ) -> AsyncIterator[str | Usage]:
        yield Usage(model="priced", input_tokens=1_000, output_tokens=500)


def test_cost_is_converted_to_chf() -> None:
    prices = {"priced": ModelPrice(input=5.0, cached_input=0.5, output=30.0)}
    service = ChatService(PricedProvider(), "", prices=prices, usd_to_chf=0.8)

    async def collect() -> list[str | UsageReport]:
        messages = [ChatMessage(role="user", content="Hi")]
        return [item async for item in service.stream_reply(messages)]

    [report] = asyncio.run(collect())

    assert isinstance(report, UsageReport)
    # 1'000 input + 500 output tokens = 0.02 USD
    assert report.cost_chf == pytest.approx(0.02 * 0.8)
