# Knowledge-Base

> Vector database de runbooks, postmortems e playbooks para enriquecer análises de incidentes.
> Porta: **:8002** | Stack: FastAPI + Qdrant + all-MiniLM-L6-v2

## Quick Start

```bash
cd Knowledge-Base

# Runtime completo (com sentence-transformers ~800 MB)
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Apenas testes/CI (sem ML packages)
.venv/bin/pip install -r requirements-test.txt

.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

Ou com toda a stack via Docker:
```bash
cd ..
docker compose up -d --wait
```

## Architecture

```
POST /kb/ingest ──► EmbeddingService.encode(content)  ── all-MiniLM-L6-v2 (384-dim)
                        └──► QdrantService.upsert(uuid, vector, payload)
                                   └──► Qdrant :6333

POST /kb/search ──► EmbeddingService.encode(query)
                        └──► QdrantService.search(vector, score_threshold=0.70)
                                   └──► retorna chunks relevantes
```

Referência completa: [SPEC-2026-003](../docs/specs/SPEC-2026-003-knowledge-base.md)
ADRs: [ADR-0004](../docs/adr/active/ADR-2026-0004-qdrant-as-vector-database.md) (Qdrant), [ADR-0008](../docs/adr/active/ADR-2026-0008-all-minilm-l6-v2-embedding-model.md) (embeddings)

## Configuration

| Variável | Padrão | Obrigatória em Prod |
|----------|--------|---------------------|
| `QDRANT_URL` | `http://qdrant:6333` | Sim |
| `QDRANT_API_KEY` | vazio | Sim |
| `API_KEY` | vazio | Sim |
| `MIN_SIMILARITY_SCORE` | `0.70` | Não |
| `QDRANT_COLLECTION` | `incident_knowledge` | Não |

## API

| Endpoint | Método | Auth | Descrição |
|----------|--------|------|-----------|
| `/kb/ingest` | POST | API Key | Ingere chunk (runbook, postmortem, playbook) |
| `/kb/search` | POST | — | Busca semântica (score ≥ 0.70) |
| `/health` | GET | — | Liveness + conectividade Qdrant |

**Score threshold:** 0.70 (configurável via `MIN_SIMILARITY_SCORE`) — mitiga LLM08:2025

## Ingestão de Conhecimento

```bash
# Ingere um postmortem
curl -X POST http://localhost:8002/kb/ingest \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Redis OOM causou degradação: aumentar maxmemory para 2GB...",
    "incident_id": "INC-001",
    "metadata": {"type": "postmortem", "severity": "sev2"}
  }'

# Busca semântica
curl -X POST http://localhost:8002/kb/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Redis memory exhaustion", "limit": 3}'
```

## CI — Sem ML packages

Em CI, `sentence-transformers` e `torch` (~800 MB) são mockados via `sys.modules` stub
em `tests/conftest.py`. Use `requirements-test.txt` para instalação em CI.

## Dependencies

[docs/dependency-manifest-kb.yaml](../docs/dependency-manifest-kb.yaml)

## Contributing

```bash
# Testes unitários (sem Docker, sem Qdrant)
.venv/bin/pip install -r requirements-test.txt
.venv/bin/pytest tests/ -q --tb=short

# Testes E2E (requerem Docker daemon + Qdrant)
.venv/bin/pytest tests/test_e2e_qdrant.py -m e2e

# Cobertura completa (≥85% obrigatório)
.venv/bin/pytest --cov=app --cov-report=term-missing
```

## Changelog

[CHANGELOG.md](CHANGELOG.md)
