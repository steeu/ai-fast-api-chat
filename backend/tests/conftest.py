import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_llm_provider
from app.core.config import Settings, get_settings
from app.main import create_app
from app.providers.fake_provider import FakeProvider


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, llm_provider="fake", auth_enabled=False)


@pytest.fixture
def client(settings: Settings) -> TestClient:
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_llm_provider] = lambda: FakeProvider(delay=0)
    return TestClient(app)
