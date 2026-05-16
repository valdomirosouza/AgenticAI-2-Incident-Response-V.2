"""
PIIAnonymizer — classificação L1-L4 e mascaramento de PII (LGPD Art. 46 / GDPR Art. 25).

Níveis de classificação (devsecops skill):
  L1_CRITICAL   — financeiro, saúde (cartão, CPF)
  L2_SENSITIVE  — identificadores pessoais (email, telefone)
  L3_RESTRICTED — comportamental / infraestrutura (IP, user-agent)
  L4_PUBLIC     — sem PII detectada

Uso:
    anonymizer = PIIAnonymizer()
    clean_text, matches = anonymizer.anonymize(raw_text)
    level = anonymizer.classify(raw_text)
"""

import re
from dataclasses import dataclass
from enum import Enum


class PIILevel(str, Enum):
    L1_CRITICAL = "L1_CRITICAL"
    L2_SENSITIVE = "L2_SENSITIVE"
    L3_RESTRICTED = "L3_RESTRICTED"
    L4_PUBLIC = "L4_PUBLIC"


@dataclass
class PIIMatch:
    level: PIILevel
    pattern_name: str
    original: str
    masked: str


_PATTERNS: list[tuple[PIILevel, str, re.Pattern, str]] = [
    # L1 — Critical: dados financeiros e de saúde
    (
        PIILevel.L1_CRITICAL,
        "credit_card",
        re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b"),
        "[CREDIT_CARD_REDACTED]",
    ),
    (
        PIILevel.L1_CRITICAL,
        "cpf",
        re.compile(r"\b\d{3}[.\-]?\d{3}[.\-]?\d{3}[-.]?\d{2}\b"),
        "[CPF_REDACTED]",
    ),
    (
        PIILevel.L1_CRITICAL,
        "cnpj",
        re.compile(r"\b\d{2}[.\-]?\d{3}[.\-]?\d{3}[/\-]?\d{4}[-.]?\d{2}\b"),
        "[CNPJ_REDACTED]",
    ),
    # L2 — Sensitive: identificadores pessoais
    (
        PIILevel.L2_SENSITIVE,
        "email",
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
        "[EMAIL_REDACTED]",
    ),
    (
        PIILevel.L2_SENSITIVE,
        "phone_br",
        re.compile(r"\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)(?:9\d{4}|\d{4})[-\s]?\d{4}\b"),
        "[PHONE_REDACTED]",
    ),
    # L3 — Restricted: comportamental / infraestrutura
    (
        PIILevel.L3_RESTRICTED,
        "ipv4",
        re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"),
        "[IP_REDACTED]",
    ),
    (
        PIILevel.L3_RESTRICTED,
        "ipv6",
        re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){3,7}[0-9a-fA-F]{1,4}\b"),
        "[IPV6_REDACTED]",
    ),
]

# Ordem de severidade para `classify` — maior nível vence
_LEVEL_ORDER = [PIILevel.L1_CRITICAL, PIILevel.L2_SENSITIVE, PIILevel.L3_RESTRICTED]


class PIIAnonymizer:
    """Detecta e mascara PII em texto livre seguindo classificação L1-L4 (LGPD/GDPR)."""

    def anonymize(self, text: str) -> tuple[str, list[PIIMatch]]:
        """Retorna (texto_anonimizado, lista_de_matches). Aplica L1 → L2 → L3 em sequência."""
        matches: list[PIIMatch] = []
        result = text

        for level, name, pattern, replacement in _PATTERNS:

            def _replace(m: re.Match, repl: str = replacement, lvl: PIILevel = level, n: str = name) -> str:
                matches.append(PIIMatch(level=lvl, pattern_name=n, original=m.group(), masked=repl))
                return repl

            result = pattern.sub(_replace, result)

        return result, matches

    def classify(self, text: str) -> PIILevel:
        """Retorna o nível mais alto de PII detectado no texto."""
        for level in _LEVEL_ORDER:
            for lvl, _, pattern, _ in _PATTERNS:
                if lvl == level and pattern.search(text):
                    return level
        return PIILevel.L4_PUBLIC


def anonymize_log_fields(entry: dict) -> dict:
    """Anonimiza campos string em um dict de log entry. Retorna novo dict sem modificar o original."""
    anonymizer = PIIAnonymizer()
    result: dict = {}
    for key, value in entry.items():
        if isinstance(value, str):
            cleaned, _ = anonymizer.anonymize(value)
            result[key] = cleaned
        elif isinstance(value, dict):
            result[key] = anonymize_log_fields(value)
        else:
            result[key] = value
    return result
