# CLAUDE.md — AgenticAI-2-Incident-Response

Agentic AI Copilot para reduzir MTTD/MTTR em incidentes de TI.
Dissertação de Mestrado — PPGCA / Unisinos. Autor: Valdomiro Souza.

**Fonte da verdade:** `AgenticAI-Incident-Response.md` (SDD v1.7.0 — 133 KB).
Antes de propor qualquer decisão arquitetural ou de segurança, consulte o SDD.

---

## Arquitetura — 3 Microsserviços FastAPI

| Serviço                   | Porta | Stack                                    | Diretório                    |
| ------------------------- | ----- | ---------------------------------------- | ---------------------------- |
| Log-Ingestion-and-Metrics | :8000 | FastAPI + Redis 7                        | `Log-Ingestion-and-Metrics/` |
| Incident-Response-Agent   | :8001 | FastAPI + Anthropic SDK                  | `Incident-Response-Agent/`   |
| Knowledge-Base            | :8002 | FastAPI + Qdrant + sentence-transformers | `Knowledge-Base/`            |

Infraestrutura de suporte: Redis :6379, Qdrant :6333, Prometheus, Grafana.
Orquestração: `docker-compose.yml` na raiz.

---

## Modelo de IA

- Modelo: `claude-sonnet-4-6` (configurado em `Incident-Response-Agent/app/config.py`)
- Padrão: **Human-on-the-Loop (HOTL)** — agente analisa e recomenda; humano decide e executa.
- **Nunca implementar ações automáticas de remediação.** O sistema é um copiloto, não um executor autônomo.

---

## Comandos de Desenvolvimento

### Setup (uma vez por serviço)

```bash
cd <serviço>
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Knowledge-Base usa `requirements-test.txt` no CI (sem sentence-transformers/torch ~800 MB):

```bash
cd Knowledge-Base
.venv/bin/pip install -r requirements-test.txt   # CI / testes unitários
.venv/bin/pip install -r requirements.txt         # runtime completo
```

### Testes

```bash
# Testes unitários (todos os serviços — rápidos, sem Docker)
cd <serviço> && .venv/bin/pytest tests/ -q --tb=short

# Testes E2E (requerem Docker daemon ativo)
.venv/bin/pytest tests/test_e2e_redis.py   # Log-Ingestion
.venv/bin/pytest tests/test_e2e_qdrant.py  # Knowledge-Base

# Cobertura completa
.venv/bin/pytest --cov=app --cov-report=term-missing
```

Threshold mínimo de cobertura: **85%** (configurado em `pyproject.toml` de cada serviço).
Coberturas atuais: IRA 99.35% · Log-Ingestion 95.61% · KB 97.60%.

### Stack completa via Docker

```bash
docker compose up -d --wait          # sobe todos os serviços + Redis + Qdrant
docker compose logs -f <serviço>
docker compose down
```

---

## Convenções de Código

- **Python:** 3.12, async/await, Pydantic v2, `pydantic-settings` para configuração
- **Formatação:** `black` + `ruff`, line-length=110, target `py312`
- **Testes:** `pytest` com `asyncio_mode = "auto"`, `fakeredis` para Redis (sem conexão real nos unitários)
- **Mocks:** `sys.modules` stub para `sentence_transformers`/`torch` no KB (evita 800 MB no CI)
- **Cobertura:** `branch = true` em todos os serviços; omitir `app/telemetry.py`
- **Sem `assert` fora de testes** (Bandit B101 — skipped apenas em `tests/`)

---

## Estrutura de Cada Serviço

```
<servico>/
├── app/
│   ├── main.py           # FastAPI app, middlewares, routers
│   ├── config.py         # Pydantic Settings (@model_validator para prod)
│   ├── models/           # Pydantic models (ou models.py)
│   ├── routers/          # Endpoints FastAPI
│   └── middleware/       # RequestLogging, SecurityHeaders, RequestSizeLimit
├── tests/
│   ├── conftest.py       # Fixtures compartilhadas
│   └── test_*.py
├── Dockerfile            # python:3.12-slim-bookworm, USER appuser (nonroot)
├── requirements.txt
└── pyproject.toml        # pytest, coverage, ruff, black, mypy
```

---

## Segurança — Regras Invioláveis

1. **Nunca logar API keys** — usar apenas `hash_key()` (SHA-256 truncado, 8 chars)
2. **Sanitizar findings antes do prompt LLM** — `_sanitize_finding_text()` (MAX=500 chars, remove tags system/human/assistant)
3. **Validar output do Claude com Pydantic** — `OrchestratorResponse` antes de construir `IncidentReport`
4. **`hmac.compare_digest`** para comparação de API keys (timing-safe)
5. **`USER appuser`** em todos os Dockerfiles (nunca root)
6. **`enable_docs=False`** em produção (bloqueado por `@model_validator`)
7. **`score_threshold=0.70`** na busca Qdrant (LLM08:2025)

Referências: SDD §5 (SAST), §6 (DAST), §7 (OWASP Top 10 + OWASP LLM 2025).

---

## Variáveis de Ambiente

Copiar `.env.example` para `.env` na raiz. Variáveis críticas:

| Variável            | Serviço                 | Obrigatória em Prod |
| ------------------- | ----------------------- | ------------------- |
| `ANTHROPIC_API_KEY` | Incident-Response-Agent | Sim                 |
| `API_KEY`           | IRA + Knowledge-Base    | Sim                 |
| `ADMIN_KEY`         | Incident-Response-Agent | Sim                 |
| `REDIS_URL`         | Log-Ingestion           | Sim                 |
| `QDRANT_URL`        | Knowledge-Base          | Sim                 |

---

## CI/CD — Workflows GitHub Actions

| Workflow        | Trigger                   | O que faz                                         |
| --------------- | ------------------------- | ------------------------------------------------- |
| `ci.yml`        | push/PR → qualquer branch | pytest 3 serviços + docker build gate             |
| `sast.yml`      | push/PR → main/staging    | bandit + semgrep + pip-audit + checkov            |
| `dast.yml`      | push → main/staging       | Schemathesis fuzzing + OWASP ZAP baseline         |
| `sbom.yml`      | push/PR → main            | syft SBOM + grype CVE scan (bloqueia em CRITICAL) |
| `load-test.yml` | workflow_dispatch         | Locust + check_slos.py contra SLO thresholds      |

---

## SLOs Definidos (Log-Ingestion-and-Metrics)

| SLO          | Target | Threshold       |
| ------------ | ------ | --------------- |
| availability | 99.5%  | 5xx rate ≤ 0.5% |
| latency_p95  | 99.0%  | P95 ≤ 500 ms    |
| latency_p99  | 99.9%  | P99 ≤ 1000 ms   |

Endpoint: `GET /metrics/slo-status` — retorna `SloStatusReport` com error budget.

---

## Contexto Acadêmico

Cada decisão de implementação relevante deve ter justificativa rastreável à RSL documentada no SDD §10. Ao sugerir novas abordagens, indicar o princípio SRE (SDD §9) ou paper correspondente quando aplicável.
