"""
Audit log separado para eventos de segurança — nunca misturar com logs operacionais.
Referência: SDD §9.9.1 / Building Secure and Reliable Systems, Cap. 15.
"""

import hashlib
import logging
from datetime import datetime, timezone

_audit = logging.getLogger("audit")


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def log_analysis_requested(request_id: str, api_key: str, client_ip: str) -> None:
    _audit.info(
        "ANALYSIS_REQUESTED",
        extra={
            "event": "analysis_requested",
            "request_id": request_id,
            "api_key_hash": _hash_key(api_key) if api_key else "none",
            "client_ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


def log_auth_failure(request_id: str, client_ip: str, reason: str) -> None:
    _audit.warning(
        "AUTH_FAILURE",
        extra={
            "event": "auth_failure",
            "request_id": request_id,
            "client_ip": client_ip,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
