"""
Admin endpoints para rotação de API Keys — S4-07 (SDD §7.1 A07:2021).

Todos os endpoints requerem o header X-API-Key com o valor de ADMIN_KEY
(variável de ambiente separada de API_KEY — princípio de menor privilégio).

Endpoints:
  POST /admin/rotate-key   — gera nova chave ativa, retorna uma única vez
  POST /admin/revoke-legacy — remove chaves rotacionadas em memória
  GET  /admin/key-status   — lista chaves ativas (hashes, nunca valores)
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import require_admin_key
from app.config import settings
from app.key_manager import add_rotated_key, generate_key, key_status, revoke_extra_keys

router = APIRouter(prefix="/admin", tags=["admin"])


class RotateKeyResponse(BaseModel):
    new_key: str          # visível apenas nesta resposta
    message: str
    active_keys_count: int
    rotated_at: datetime


class KeyStatusResponse(BaseModel):
    active_keys_count: int
    keys: list[dict]      # hashes + labels; nunca os valores reais


@router.post("/rotate-key", response_model=RotateKeyResponse,
             dependencies=[Depends(require_admin_key)])
async def rotate_key() -> RotateKeyResponse:
    """
    Gera nova chave criptograficamente segura (256 bits) e a torna ativa
    imediatamente. A chave antiga permanece válida até revoke-legacy ou restart.
    Copie new_key e persista em API_KEY no .env para sobreviver a restarts.
    """
    new_key = generate_key()
    add_rotated_key(new_key)
    statuses = key_status(settings.api_key)
    return RotateKeyResponse(
        new_key=new_key,
        message=(
            "Nova chave gerada e ativa. "
            "Atualize API_KEY no .env e reinicie o serviço para persistir."
        ),
        active_keys_count=len(statuses),
        rotated_at=datetime.now(timezone.utc),
    )


@router.post("/revoke-legacy", dependencies=[Depends(require_admin_key)])
async def revoke_legacy() -> dict:
    """Remove chaves rotacionadas em memória; mantém apenas as chaves do env var."""
    removed = revoke_extra_keys()
    statuses = key_status(settings.api_key)
    return {"revoked_extra_keys": removed, "active_keys_count": len(statuses)}


@router.get("/key-status", response_model=KeyStatusResponse,
            dependencies=[Depends(require_admin_key)])
async def get_key_status() -> KeyStatusResponse:
    """Lista todas as chaves ativas com label e hash (nunca o valor real)."""
    statuses = key_status(settings.api_key)
    return KeyStatusResponse(active_keys_count=len(statuses), keys=statuses)
