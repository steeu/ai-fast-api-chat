from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20_000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=100)


class Usage(BaseModel):
    """Token usage of one answer as reported by the provider."""

    model: str
    input_tokens: int
    cached_tokens: int = 0
    # Reasoning tokens are part of output_tokens (billed as output, not visible in the text)
    output_tokens: int
    reasoning_tokens: int = 0


class UsageReport(Usage):
    # None if the model has no known price
    cost_usd: float | None
