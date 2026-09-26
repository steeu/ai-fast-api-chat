import re

from pydantic import BaseModel, Field


class ModelPrice(BaseModel):
    """Prices in USD per 1 million tokens."""

    input: float = Field(ge=0)
    cached_input: float = Field(ge=0)
    output: float = Field(ge=0)


# Defaults, can be overridden or extended via LLM_PRICES in .env (prices change over time)
DEFAULT_PRICES: dict[str, ModelPrice] = {
    "gpt-5.5": ModelPrice(input=5.00, cached_input=0.50, output=30.00),
}

# Snapshot names like "gpt-5.5-2026-04-23" are billed like their base model
_SNAPSHOT_SUFFIX = re.compile(r"-\d{4}-\d{2}-\d{2}$")


def find_price(model: str, prices: dict[str, ModelPrice]) -> ModelPrice | None:
    return prices.get(model) or prices.get(_SNAPSHOT_SUFFIX.sub("", model))


def estimate_cost(
    prices: dict[str, ModelPrice],
    model: str,
    input_tokens: int,
    cached_tokens: int,
    output_tokens: int,
) -> float | None:
    """Estimated cost in USD, or None for an unknown model (better no number than a wrong one).

    Reasoning tokens are already included in output_tokens. Surcharges for very long prompts
    or data residency are ignored, so this stays an estimate.
    """
    price = find_price(model, prices)
    if price is None:
        return None
    uncached = input_tokens - cached_tokens
    return (
        uncached * price.input + cached_tokens * price.cached_input + output_tokens * price.output
    ) / 1_000_000
