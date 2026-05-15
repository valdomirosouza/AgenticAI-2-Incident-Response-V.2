"""
Gerenciamento de API Keys com suporte a rotação — S4-07 (SDD §7.1 A07:2021).

Suporta múltiplas chaves ativas simultaneamente:
  - Chaves de ambiente: lidas do API_KEY env var (separadas por vírgula)
  - Chaves rotacionadas: geradas em runtime via POST /admin/rotate-key

Chaves em memória não são persistidas — ao reiniciar o serviço, apenas as
chaves do env var estarão ativas. Para persistência, atualize API_KEY no .env.
"""
import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Chaves geradas via rotação em runtime (complementam as do env var).
_extra_keys: dict[str, datetime] = {}


def parse_keys(raw: str) -> list[str]:
    """Analisa lista de chaves separadas por vírgula do env var."""
    return [k.strip() for k in raw.split(",") if k.strip()]


def generate_key() -> str:
    """Gera chave criptograficamente segura — 256 bits via URL-safe base64."""
    return secrets.token_urlsafe(32)


def hash_key(key: str) -> str:
    """SHA-256 truncado a 8 chars — para logs de auditoria, nunca o valor real."""
    return hashlib.sha256(key.encode()).hexdigest()[:8]


def add_rotated_key(key: str) -> None:
    """Registra chave gerada por rotação no store em memória."""
    _extra_keys[key] = datetime.now(timezone.utc)
    logger.info(
        "API key added via rotation — total extra keys: %d",
        len(_extra_keys),
        extra={"key_hash": hash_key(key)},
    )


def revoke_extra_keys() -> int:
    """Remove todas as chaves rotacionadas em memória; mantém apenas as do env."""
    count = len(_extra_keys)
    _extra_keys.clear()
    if count:
        logger.info("Revoked %d rotated API key(s)", count)
    return count


def has_any_keys(env_key_raw: str) -> bool:
    """True se ao menos uma chave está ativa (env ou memória)."""
    return bool(parse_keys(env_key_raw) or _extra_keys)


def is_valid(candidate: str, env_key_raw: str) -> bool:
    """
    Valida candidate contra todas as chaves ativas.
    Usa hmac.compare_digest em cada chave para prevenir timing attacks.
    """
    all_keys = parse_keys(env_key_raw) + list(_extra_keys.keys())
    return any(
        hmac.compare_digest(candidate.encode(), k.encode())
        for k in all_keys
    )


def key_status(env_key_raw: str) -> list[dict]:
    """Estado das chaves ativas — retorna hashes e labels, nunca os valores."""
    result = []
    for k in parse_keys(env_key_raw):
        result.append({"label": "env", "hash": hash_key(k), "created_at": None})
    for k, created_at in _extra_keys.items():
        result.append({
            "label": "rotated",
            "hash": hash_key(k),
            "created_at": created_at.isoformat(),
        })
    return result


def reset_for_testing() -> None:
    """Limpa chaves em memória. Apenas para testes."""
    _extra_keys.clear()
