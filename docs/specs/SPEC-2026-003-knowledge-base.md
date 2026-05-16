# SPEC-2026-003: Knowledge Base

> ⚠️ SPEC RETROATIVA — Reconstruída em 2026-05-16 a partir do código-fonte, ADRs e histórico git.
> Revisada e validada por Valdomiro Souza.

## Metadata
- **ID:** SPEC-2026-003
- **Status:** Approved
- **Author:** Valdomiro Souza
- **Reviewers:** Valdomiro Souza (Tech Lead)
- **Created:** 2026-01-01 (estimado) — Formalizado: 2026-05-16
- **Version:** 1.0.0
- **AI-assisted:** Yes — Claude Sonnet 4.6 / Prompt ID: PROMPT_VERSION 1.0.0

## Context and Problem

O IRA precisa enriquecer suas recomendações com histórico de incidentes passados — runbooks,
postmortems, playbooks. Uma vector database permite recuperação semântica (por similaridade)
em vez de busca exata. Qdrant foi escolhido (ADR-2026-0004) por sua API REST simples, suporte
a Docker nativo e score_threshold nativo (mitigação LLM08:2025). O modelo de embeddings
all-MiniLM-L6-v2 (ADR-2026-0008) foi escolhido por ser leve (22 MB), rápido e gratuito.
O serviço roda na porta :8002.

## Scope
### Includes
- `POST /kb/ingest` — ingere chunk de conhecimento (runbook, postmortem, playbook) no Qdrant
- `POST /kb/search` — busca semântica por similaridade coseno com score_threshold=0.70
- Embeddings via `all-MiniLM-L6-v2` (sentence-transformers, vector size 384)
- Validação de chunk: tamanho máximo, detecção de linguagem blameful
- `GET /health` — status do serviço e conectividade Qdrant
- Criação automática de coleção Qdrant no startup
- Segurança: API key auth em `/kb/ingest`; `/kb/search` público (dados de infra, não PII)

### Out of Scope
- UI de gerenciamento de conhecimento
- Atualização/deleção de chunks individuais (append-only por design)
- Autenticação em `/kb/search` (conhecimento de infra, sem PII)
- Fine-tuning do modelo de embeddings

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| RF-01 | `POST /kb/ingest` aceita `{content, incident_id, metadata}`, gera embedding e persiste no Qdrant | Must Have | Status 201; `chunk_id` UUID retornado |
| RF-02 | `POST /kb/search` aceita `{query, limit}` e retorna até 10 chunks com score ≥ 0.70 | Must Have | Chunks ordenados por similaridade; sem resultados abaixo do threshold |
| RF-03 | Score threshold 0.70 aplicado em todas as buscas (LLM08:2025 — evita contexto irrelevante) | Must Have | `min_similarity_score=0.70` em `config.py`; configurável por env var |
| RF-04 | `validate_chunk_size` rejeita chunks acima do limite (evita embedding degradado) | Should Have | 422 para chunks muito grandes |
| RF-05 | `detect_blameful_language` detecta e loga linguagem de culpa (cultura blameless) | Should Have | Warning logado; chunk ingerido com aviso |
| RF-06 | Coleção Qdrant criada automaticamente no startup se não existir | Must Have | `ensure_collection()` no lifespan |
| RF-07 | `GET /health` retorna status Qdrant (conexão, coleção existente) | Must Have | Status 200 healthy / 503 degraded |
| RF-08 | `/kb/ingest` requer API key via `X-API-Key` header | Must Have | 401 sem key |

## Non-Functional Requirements

| ID | Category | Requirement | Metric |
|----|----------|-------------|--------|
| RNF-01 | Performance | Embedding + search p99 < 200ms | Latência medida em testes de integração |
| RNF-02 | Reliability | Coleção recriada automaticamente se inexistente | `ensure_collection()` idempotente |
| RNF-03 | Quality | Score threshold 0.70 garante relevância semântica | Sem resultados irrelevantes no benchmark |
| RNF-04 | CI | sentence-transformers/torch (~800 MB) mockados em CI | `requirements-test.txt` sem ML packages |
| RNF-05 | Coverage | ≥ 85% branch coverage | `--cov-fail-under=85` |
| RNF-06 | Security | Sem PII em chunks (dados de infra apenas) | Checklist de revisão de conteúdo na ingestão |

## Architecture

```
IRA ou operador
    │
    ├── POST /kb/ingest ──── API key auth
    │   └── EmbeddingService.encode(content) ── all-MiniLM-L6-v2
    │       └── QdrantService.upsert(chunk_id, vector, payload)
    │
    └── POST /kb/search ──── público
        └── EmbeddingService.encode(query)
            └── QdrantService.search(vector, score_threshold=0.70)
                └── retorna [{"content": ..., "incident_id": ..., "score": ...}]

[Knowledge-Base :8002]
    ├── embedding_service.py ── all-MiniLM-L6-v2 (384-dim vectors)
    ├── qdrant_service.py ───── AsyncQdrantClient, cosine distance
    └── chunk_validator.py ──── tamanho + blameful language check
```

### Back-of-Envelope Summary (NALSD)
- **Carga estimada:** ~5 buscas/análise (1 por specialist) × 10 análises/hora = 50 buscas/hora
- **Latência budget:** embedding ~10ms (CPU local) + Qdrant search ~5ms = ~15ms total
- **Storage Qdrant:** 1000 chunks × 384 floats × 4 bytes = ~1.5 MB vectors; payloads ~500 KB
- **Instâncias:** 1 (single-node Qdrant em Docker; escalável horizontalmente se necessário)
- **Modelo:** 22 MB RAM para all-MiniLM-L6-v2; sem GPU necessária

ADRs: ADR-0001, ADR-0004, ADR-0008, ADR-0009, ADR-0013

## Observability
- **Logs:** JSON estruturado; `chunk_id` e `incident_id` em cada ingestão; blameful language warnings
- **Metrics:** `http_requests_total`, `http_request_duration_seconds` (via Instrumentator)
- **Traces:** middleware de request logging; sem OTel explícito (v1 — roadmap para v2)
- **SLI:** disponibilidade do `/health` endpoint; erro de conexão Qdrant → 503
- **SLO:** disponibilidade 99.5% (herdado do SLO geral do sistema)

## Security
- PII involved: No — apenas runbooks, postmortems e playbooks de infra
- Anonymization: N/A — sem dados pessoais
- Credentials: `API_KEY`, `QDRANT_API_KEY` via env vars
- Communication: TLS com Qdrant Cloud (se remoto); local Docker sem TLS
- Threat model: ADR-0013 (inter-service trust); `/kb/search` público (dados de infra, sem PII)
- OWASP review: A01 (auth em /ingest), A03 (Pydantic validation em inputs), A09 (structured logs)
- DPIA required: No

## Dependencies
Referência: `docs/dependency-manifest-kb.yaml`

Runtime principais: `fastapi`, `qdrant-client`, `pydantic==2.11.4`, `sentence-transformers` (prod),
`torch` (prod — ~800 MB, mockado em CI)

Infra: Qdrant (:6333)

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Qdrant indisponível | Alta — KB inacessível | Baixa | Circuit breaker no IRA; `search_kb()` com fallback |
| Score threshold muito alto (sem resultados) | Média — recomendações sem histórico | Média | 0.70 configurável via env var `MIN_SIMILARITY_SCORE` |
| Chunk com conteúdo blameful ingerido | Baixa — cultura organizacional | Média | `detect_blameful_language()` + warning log |
| sentence-transformers OOM em prod | Média — crash do serviço | Baixa | Modelo leve 22MB; monitorar `container_memory_usage_bytes` |

## Approval
| Role | Name | Date | Status |
|------|------|------|--------|
| Tech Lead | Valdomiro Souza | 2026-05-16 | Approved (retroativo) |
| Security | Valdomiro Souza | 2026-05-16 | Approved (retroativo) |
| Architect | Valdomiro Souza | 2026-05-16 | Approved (retroativo) |
