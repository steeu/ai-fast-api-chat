from app.core.config import Settings
from app.providers.base import LLMProvider
from app.providers.fake_provider import FakeProvider
from app.providers.openai_provider import OpenAIProvider


class ProviderConfigError(Exception):
    """The configured provider can't be used, e.g. because the API key is missing."""


def create_provider(settings: Settings) -> LLMProvider:
    match settings.llm_provider:
        case "openai":
            if not settings.openai_api_key:
                raise ProviderConfigError("OPENAI_API_KEY is not set.")
            return OpenAIProvider(
                api_key=settings.openai_api_key,
                model=settings.llm_model,
                temperature=settings.llm_temperature,
            )
        case "fake":
            return FakeProvider()
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
