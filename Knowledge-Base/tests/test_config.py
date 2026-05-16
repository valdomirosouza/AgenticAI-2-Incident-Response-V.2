"""Testes para validações de configuração em produção."""

import pytest
from pydantic import ValidationError


def test_production_requires_api_key():
    from app.config import Settings
    with pytest.raises(ValidationError, match="API_KEY"):
        Settings(app_env="production", api_key="", enable_docs=False)


def test_production_requires_docs_disabled():
    from app.config import Settings
    with pytest.raises(ValidationError, match="enable_docs"):
        Settings(app_env="production", api_key="secret", enable_docs=True)


def test_staging_requires_api_key():
    from app.config import Settings

    with pytest.raises(ValidationError, match="API_KEY"):
        Settings(app_env="staging", api_key="")


def test_staging_with_api_key_passes():
    from app.config import Settings

    s = Settings(app_env="staging", api_key="staging-key")
    assert s.api_key == "staging-key"


def test_development_allows_no_api_key():
    from app.config import Settings
    s = Settings(app_env="development", api_key="", enable_docs=True)
    assert s.app_env == "development"


def test_default_min_similarity_score():
    from app.config import Settings
    s = Settings()
    assert s.min_similarity_score == 0.30
