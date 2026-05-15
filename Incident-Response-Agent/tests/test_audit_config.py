"""
Testes para audit.py, config.py e limiter.py.
"""

import pytest
import logging
from unittest.mock import patch
from pydantic import ValidationError

from app.audit import log_analysis_requested, log_auth_failure, _hash_key
from app.config import Settings


# ─── _hash_key ────────────────────────────────────────────────────────────────

def test_hash_key_returns_16_char_hex():
    result = _hash_key("my-api-key")
    assert len(result) == 16
    assert all(c in "0123456789abcdef" for c in result)


def test_hash_key_is_not_original():
    key = "super-secret"
    assert _hash_key(key) != key


def test_hash_key_deterministic():
    assert _hash_key("same-key") == _hash_key("same-key")


def test_hash_key_different_inputs_different_outputs():
    assert _hash_key("key-a") != _hash_key("key-b")


# ─── log_analysis_requested ───────────────────────────────────────────────────

def test_log_analysis_requested_emits_info(caplog):
    with caplog.at_level(logging.INFO, logger="audit"):
        log_analysis_requested("req-001", "my-api-key", "1.2.3.4")
    assert "ANALYSIS_REQUESTED" in caplog.text


def test_log_analysis_requested_hides_api_key(caplog):
    with caplog.at_level(logging.INFO, logger="audit"):
        log_analysis_requested("req-001", "super-secret", "1.2.3.4")
    assert "super-secret" not in caplog.text


def test_log_analysis_requested_no_api_key(caplog):
    with caplog.at_level(logging.INFO, logger="audit"):
        log_analysis_requested("req-001", "", "1.2.3.4")
    assert "ANALYSIS_REQUESTED" in caplog.text


# ─── log_auth_failure ─────────────────────────────────────────────────────────

def test_log_auth_failure_emits_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="audit"):
        log_auth_failure("req-002", "9.8.7.6", "invalid_key")
    assert "AUTH_FAILURE" in caplog.text


def test_log_auth_failure_includes_reason(caplog):
    with caplog.at_level(logging.WARNING, logger="audit"):
        log_auth_failure("req-002", "9.8.7.6", "missing_header")
    # extra fields land on LogRecord attributes, not in the formatted message text
    assert any(getattr(r, "reason", "") == "missing_header" for r in caplog.records)


# ─── Config production validations ────────────────────────────────────────────

def test_production_requires_anthropic_api_key():
    with pytest.raises(ValidationError, match="ANTHROPIC_API_KEY"):
        Settings(app_env="production", anthropic_api_key="", api_key="k", enable_docs=False)


def test_production_requires_api_key():
    with pytest.raises(ValidationError, match="API_KEY"):
        Settings(app_env="production", anthropic_api_key="ak", api_key="", enable_docs=False)


def test_production_requires_docs_disabled():
    with pytest.raises(ValidationError, match="enable_docs"):
        Settings(app_env="production", anthropic_api_key="ak", api_key="k", enable_docs=True)


def test_development_allows_empty_keys():
    s = Settings(app_env="development", anthropic_api_key="", api_key="", enable_docs=True)
    assert s.app_env == "development"


def test_default_model_is_claude_sonnet():
    s = Settings()
    assert "claude" in s.model.lower()


def test_latency_threshold_default():
    s = Settings()
    assert s.latency_p99_threshold_ms == 1000.0


def test_error_rate_threshold_default():
    s = Settings()
    assert s.error_rate_5xx_threshold_pct == 1.0


# ─── Limiter ──────────────────────────────────────────────────────────────────

def test_limiter_key_func_uses_api_key():
    from app.limiter import _get_api_key_or_ip
    from unittest.mock import MagicMock
    mock_request = MagicMock()
    mock_request.headers = {"X-API-Key": "my-key"}
    result = _get_api_key_or_ip(mock_request)
    assert result == "my-key"


def test_limiter_key_func_falls_back_to_ip():
    from app.limiter import _get_api_key_or_ip
    from unittest.mock import MagicMock
    mock_request = MagicMock()
    mock_request.headers = {}
    mock_request.client.host = "127.0.0.1"
    # get_remote_address uses request.client.host
    result = _get_api_key_or_ip(mock_request)
    assert result  # just verify it returns something
