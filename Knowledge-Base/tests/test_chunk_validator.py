"""Testes unitários síncronos para chunk_validator (sem mocks)."""

import pytest
from app.services.chunk_validator import validate_chunk_size, detect_blameful_language, MAX_CHUNK_SIZE


# ─── validate_chunk_size ──────────────────────────────────────────────────────

def test_validate_chunk_size_ok():
    validate_chunk_size("a" * 100)  # Não deve levantar


def test_validate_chunk_size_exact_limit():
    validate_chunk_size("x" * MAX_CHUNK_SIZE)  # Exatamente no limite — ok


def test_validate_chunk_size_exceeds_limit():
    with pytest.raises(ValueError, match="Content too large"):
        validate_chunk_size("x" * (MAX_CHUNK_SIZE + 1))


def test_validate_chunk_size_reports_actual_length():
    content = "y" * (MAX_CHUNK_SIZE + 50)
    with pytest.raises(ValueError, match=str(len(content))):
        validate_chunk_size(content)


# ─── detect_blameful_language ─────────────────────────────────────────────────

def test_detect_blameful_clean_text():
    result = detect_blameful_language("Redis OOM due to missing TTL configuration.")
    assert result == []


def test_detect_blameful_portuguese_culpa():
    result = detect_blameful_language("A culpa foi do time de operações.")
    assert len(result) == 1


def test_detect_blameful_portuguese_negligencia():
    result = detect_blameful_language("Houve negligência no processo de deploy.")
    assert len(result) == 1


def test_detect_blameful_english_blame():
    result = detect_blameful_language("We must place blame on the on-call engineer.")
    assert len(result) == 1


def test_detect_blameful_english_negligence():
    result = detect_blameful_language("This was pure negligence from the team.")
    assert len(result) == 1


def test_detect_blameful_case_insensitive():
    result = detect_blameful_language("The FAULT lies with the developer.")
    assert len(result) == 1


def test_detect_blameful_human_error():
    result = detect_blameful_language("Root cause: human error in config change.")
    assert len(result) == 1


def test_detect_blameful_multiple_patterns():
    result = detect_blameful_language("culpa e negligence ambos presentes.")
    assert len(result) >= 2


def test_detect_blameful_returns_strings():
    result = detect_blameful_language("erro humano identificado.")
    assert all(isinstance(w, str) for w in result)
