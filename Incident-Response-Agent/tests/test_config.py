"""Testes para validações de configuração (OWASP A01/A05 — SDD §5)."""

import pytest
from pydantic import ValidationError


def test_production_requires_api_key():
    from app.config import Settings

    with pytest.raises(ValidationError, match="API_KEY"):
        Settings(app_env="production", api_key="", anthropic_api_key="sk-x", enable_docs=False)


def test_staging_requires_api_key():
    from app.config import Settings

    with pytest.raises(ValidationError, match="API_KEY"):
        Settings(app_env="staging", api_key="")


def test_production_requires_anthropic_key():
    from app.config import Settings

    with pytest.raises(ValidationError, match="ANTHROPIC_API_KEY"):
        Settings(app_env="production", api_key="secret", anthropic_api_key="", enable_docs=False)


def test_production_requires_docs_disabled():
    from app.config import Settings

    with pytest.raises(ValidationError, match="enable_docs"):
        Settings(app_env="production", api_key="secret", anthropic_api_key="sk-x", enable_docs=True)


def test_development_allows_no_api_key():
    from app.config import Settings

    s = Settings(app_env="development", api_key="", enable_docs=True)
    assert s.app_env == "development"


def test_staging_with_api_key_passes():
    from app.config import Settings

    s = Settings(app_env="staging", api_key="staging-key")
    assert s.api_key == "staging-key"
