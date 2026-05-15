"""
Validação de chunks antes da ingestão na KB (SDD §9.13.8).
Detecta linguagem blameful para preservar cultura de blameless postmortems.
"""

import re

MAX_CHUNK_SIZE = 5000

BLAMEFUL_PATTERNS = [
    r"\b(culpa|culpado|culpável|negligência|descuido|irresponsabilidade)\b",
    r"\b(blame|fault|negligence|careless|reckless)\b",
    r"\b(erro humano|human error)\b",
]


def validate_chunk_size(content: str) -> None:
    if len(content) > MAX_CHUNK_SIZE:
        raise ValueError(f"Content too large: {len(content)} chars (max {MAX_CHUNK_SIZE})")


def detect_blameful_language(content: str) -> list[str]:
    """Retorna lista de avisos para linguagem blameful encontrada."""
    warnings = []
    for pattern in BLAMEFUL_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            warnings.append(f"Possible blameful language: pattern '{pattern}'")
    return warnings
