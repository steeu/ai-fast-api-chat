import pytest

from app.core.config import Settings
from app.core.pricing import DEFAULT_PRICES, ModelPrice, estimate_cost

PRICES = {"gpt-5.5": ModelPrice(input=5.0, cached_input=0.5, output=30.0)}


def test_cost_from_input_and_output_tokens() -> None:
    cost = estimate_cost(PRICES, "gpt-5.5", input_tokens=1_000, cached_tokens=0, output_tokens=500)
    assert cost == pytest.approx(0.005 + 0.015)


def test_cached_tokens_use_cached_price() -> None:
    cost = estimate_cost(PRICES, "gpt-5.5", input_tokens=1_000, cached_tokens=800, output_tokens=0)
    assert cost == pytest.approx((200 * 5.0 + 800 * 0.5) / 1_000_000)


def test_snapshot_name_uses_base_model_price() -> None:
    cost = estimate_cost(
        PRICES, "gpt-5.5-2026-04-23", input_tokens=1_000, cached_tokens=0, output_tokens=0
    )
    assert cost == pytest.approx(0.005)


def test_unknown_model_has_no_cost() -> None:
    assert estimate_cost(PRICES, "gpt-5.5-mini", 1_000, 0, 500) is None


def test_prices_can_be_overridden_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PRICES", '{"my-model": {"input": 1, "cached_input": 0.1, "output": 2}}')
    prices = Settings(_env_file=None).model_prices

    assert prices["my-model"] == ModelPrice(input=1, cached_input=0.1, output=2)
    # Defaults stay available unless overridden
    assert prices["gpt-5.5"] == DEFAULT_PRICES["gpt-5.5"]
