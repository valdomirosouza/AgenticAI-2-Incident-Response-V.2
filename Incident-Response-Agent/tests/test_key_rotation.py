"""
Testes para rotação de API Keys — S4-07 (SDD §7.1 A07:2021).

Cobre:
  - parse_keys: single, múltiplas, vazia, espaços
  - KeyManager (funções puras): validação, hash, geração
  - Rotação em memória: add_rotated_key, revoke_extra_keys, has_any_keys
  - /admin/rotate-key: sucesso, sem ADMIN_KEY, chave admin errada
  - /admin/revoke-legacy: remove extras, mantém env
  - /admin/key-status: lista hashes, nunca valores reais
  - Multi-key auth: cliente antigo e novo ambos aceitos durante rotação
"""
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.key_manager import (
    add_rotated_key,
    generate_key,
    has_any_keys,
    hash_key,
    is_valid,
    key_status,
    parse_keys,
    reset_for_testing,
    revoke_extra_keys,
)

# Apenas testes async recebem a marca individualmente (evita warnings em sync)


# ── Fixture: limpa chaves em memória entre testes ─────────────────────────────

@pytest.fixture(autouse=True)
def clean_extra_keys():
    reset_for_testing()
    yield
    reset_for_testing()


# ── Helpers de cliente ─────────────────────────────────────────────────────────

def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ── parse_keys ─────────────────────────────────────────────────────────────────

def test_parse_keys_single():
    assert parse_keys("abc123") == ["abc123"]


def test_parse_keys_multiple():
    assert parse_keys("key1,key2,key3") == ["key1", "key2", "key3"]


def test_parse_keys_strips_whitespace():
    assert parse_keys("  key1 , key2  ") == ["key1", "key2"]


def test_parse_keys_empty_string():
    assert parse_keys("") == []


def test_parse_keys_only_commas():
    assert parse_keys(",,,") == []


# ── generate_key / hash_key ───────────────────────────────────────────────────

def test_generate_key_is_unique():
    k1 = generate_key()
    k2 = generate_key()
    assert k1 != k2


def test_generate_key_has_minimum_length():
    assert len(generate_key()) >= 32


def test_hash_key_is_8_chars():
    assert len(hash_key("any-key")) == 8


def test_hash_key_does_not_contain_original():
    key = "super-secret"
    assert key not in hash_key(key)


def test_hash_key_is_deterministic():
    assert hash_key("key") == hash_key("key")


# ── is_valid ──────────────────────────────────────────────────────────────────

def test_is_valid_correct_single_key():
    assert is_valid("mykey", "mykey") is True


def test_is_valid_wrong_key():
    assert is_valid("wrong", "mykey") is False


def test_is_valid_accepts_any_env_key():
    assert is_valid("key2", "key1,key2,key3") is True


def test_is_valid_rejects_key_not_in_list():
    assert is_valid("key4", "key1,key2,key3") is False


def test_is_valid_with_extra_key_in_memory():
    rotated = generate_key()
    add_rotated_key(rotated)
    assert is_valid(rotated, "") is True  # env vazio, mas extra key existe


def test_is_valid_rejects_after_revoke():
    rotated = generate_key()
    add_rotated_key(rotated)
    revoke_extra_keys()
    assert is_valid(rotated, "") is False


# ── has_any_keys ──────────────────────────────────────────────────────────────

def test_has_any_keys_false_when_empty():
    assert has_any_keys("") is False


def test_has_any_keys_true_with_env_key():
    assert has_any_keys("somekey") is True


def test_has_any_keys_true_with_only_extra_keys():
    add_rotated_key(generate_key())
    assert has_any_keys("") is True


# ── key_status ────────────────────────────────────────────────────────────────

def test_key_status_env_key_labeled_correctly():
    statuses = key_status("mykey")
    assert len(statuses) == 1
    assert statuses[0]["label"] == "env"
    assert "mykey" not in statuses[0]["hash"]  # nunca expõe o valor


def test_key_status_includes_rotated_keys():
    add_rotated_key("rotatedkey123")
    statuses = key_status("envkey")
    labels = [s["label"] for s in statuses]
    assert "env" in labels
    assert "rotated" in labels


def test_key_status_empty_when_no_keys():
    assert key_status("") == []


# ── /admin/rotate-key ─────────────────────────────────────────────────────────

async def test_rotate_key_requires_admin_key():
    async with _client() as c:
        with patch("app.config.settings.admin_key", "admin-secret"):
            resp = await c.post("/admin/rotate-key")
            assert resp.status_code == 401


async def test_rotate_key_wrong_admin_key_returns_401():
    async with _client() as c:
        with patch("app.config.settings.admin_key", "admin-secret"):
            resp = await c.post("/admin/rotate-key", headers={"X-API-Key": "wrong"})
            assert resp.status_code == 401


async def test_rotate_key_success():
    async with _client() as c:
        with patch("app.config.settings.admin_key", "admin-secret"):
            resp = await c.post("/admin/rotate-key", headers={"X-API-Key": "admin-secret"})
    assert resp.status_code == 200
    data = resp.json()
    assert "new_key" in data
    assert len(data["new_key"]) >= 32
    assert data["active_keys_count"] >= 1
    assert "rotated_at" in data


async def test_rotate_key_not_configured_returns_503():
    async with _client() as c:
        with patch("app.config.settings.admin_key", ""):
            resp = await c.post("/admin/rotate-key", headers={"X-API-Key": "anything"})
            assert resp.status_code == 503


async def test_rotated_key_is_immediately_usable_for_api():
    # Gera nova chave via /admin/rotate-key e usa para chamar /analyze
    async with _client() as c:
        with patch("app.config.settings.admin_key", "admin-secret"), \
             patch("app.config.settings.api_key", "old-key"):
            resp = await c.post("/admin/rotate-key", headers={"X-API-Key": "admin-secret"})
            new_key = resp.json()["new_key"]

        # Nova chave aceita mesmo sem alterar o env var
        with patch("app.config.settings.api_key", "old-key"), \
             patch("app.routers.analyze.run_analysis") as mock_run:
            from unittest.mock import AsyncMock
            from tests.conftest import OK_REPORT
            mock_run.return_value = OK_REPORT
            resp2 = await c.post("/analyze", headers={"X-API-Key": new_key})
            assert resp2.status_code == 200


async def test_old_key_still_valid_during_rotation():
    # Rotação não invalida a chave antiga imediatamente
    async with _client() as c:
        with patch("app.config.settings.admin_key", "admin-secret"), \
             patch("app.config.settings.api_key", "old-key"):
            await c.post("/admin/rotate-key", headers={"X-API-Key": "admin-secret"})

        with patch("app.config.settings.api_key", "old-key"), \
             patch("app.routers.analyze.run_analysis") as mock_run:
            from unittest.mock import AsyncMock
            from tests.conftest import OK_REPORT
            mock_run.return_value = OK_REPORT
            resp = await c.post("/analyze", headers={"X-API-Key": "old-key"})
            assert resp.status_code == 200


# ── /admin/revoke-legacy ──────────────────────────────────────────────────────

async def test_revoke_legacy_removes_rotated_keys():
    add_rotated_key(generate_key())
    add_rotated_key(generate_key())
    async with _client() as c:
        with patch("app.config.settings.admin_key", "admin-secret"), \
             patch("app.config.settings.api_key", "env-key"):
            resp = await c.post("/admin/revoke-legacy", headers={"X-API-Key": "admin-secret"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["revoked_extra_keys"] == 2


async def test_revoke_legacy_keeps_env_key():
    add_rotated_key(generate_key())
    async with _client() as c:
        with patch("app.config.settings.admin_key", "admin-secret"), \
             patch("app.config.settings.api_key", "env-key"):
            resp = await c.post("/admin/revoke-legacy", headers={"X-API-Key": "admin-secret"})
    assert resp.json()["active_keys_count"] == 1  # só a env key


# ── /admin/key-status ─────────────────────────────────────────────────────────

async def test_key_status_endpoint_requires_admin_key():
    async with _client() as c:
        with patch("app.config.settings.admin_key", "admin-secret"):
            resp = await c.get("/admin/key-status")
            assert resp.status_code == 401


async def test_key_status_endpoint_returns_hashes():
    async with _client() as c:
        with patch("app.config.settings.admin_key", "admin-secret"), \
             patch("app.config.settings.api_key", "my-env-key"):
            resp = await c.get("/admin/key-status", headers={"X-API-Key": "admin-secret"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["active_keys_count"] == 1
    assert data["keys"][0]["label"] == "env"
    assert "my-env-key" not in str(data)  # nunca expõe o valor real


async def test_key_status_includes_rotated_after_rotation():
    add_rotated_key("rotated-key-xyz")
    async with _client() as c:
        with patch("app.config.settings.admin_key", "admin-secret"), \
             patch("app.config.settings.api_key", "env-key"):
            resp = await c.get("/admin/key-status", headers={"X-API-Key": "admin-secret"})
    data = resp.json()
    assert data["active_keys_count"] == 2
    labels = [k["label"] for k in data["keys"]]
    assert "env" in labels
    assert "rotated" in labels
