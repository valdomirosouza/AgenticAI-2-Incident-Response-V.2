# Incident-Response-Agent

> Agente de IA para análise de incidentes usando Claude Sonnet 4.6 via Anthropic tool-use API.
> Padrão Human-on-the-Loop (HOTL) — recomenda, não executa.
> Porta: **:8001** | Stack: FastAPI + Anthropic SDK

## Quick Start

```bash
cd Incident-Response-Agent
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
# Configure: cp ../.env.example ../.env && preencha ANTHROPIC_API_KEY, API_KEY, ADMIN_KEY
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Ou com toda a stack via Docker:
```bash
cd ..
docker compose up -d --wait
```

## Architecture

```
POST /analyze ──► orchestrator.py
                     │
                     ├── asyncio.gather([4 specialists em paralelo])
                     │   ├── LatencyAgent ── tool-use → GET :8000/metrics/response-times
                     │   ├── ErrorsAgent ─── tool-use → GET :8000/metrics/overview
                     │   ├── SaturationAgent ─ tool-use → GET :8000/metrics/saturation
                     │   └── TrafficAgent ── tool-use → GET :8000/metrics/rps+backends
                     │
                     ├── _sanitize_finding_text() ── LLM01+LLM02: remove injection, redact IPs
                     ├── OrchestratorAgent ────────── síntese causal (root cause vs trigger)
                     │   └── search_kb() ─────────── enriquece com Knowledge-Base :8002
                     │
                     └── AnthropicCircuitBreaker ── fallback rule-based se API indisponível
```

Referência completa: [SPEC-2026-002](../docs/specs/SPEC-2026-002-incident-response-agent.md)
ADRs: ADR-0005 (Claude), ADR-0006 (HOTL), ADR-0007 (specialists), ADR-0010 (circuit breaker)

## Configuration

| Variável | Padrão | Obrigatória em Prod |
|----------|--------|---------------------|
| `ANTHROPIC_API_KEY` | vazio | **Sim** |
| `API_KEY` | vazio | Sim |
| `ADMIN_KEY` | vazio | Sim |
| `APP_ENV` | `development` | Sim |
| `METRICS_API_URL` | `http://localhost:8000` | Sim |
| `KB_API_URL` | `http://localhost:8002` | Sim |
| `KB_API_KEY` | vazio | Sim |
| `MODEL` | `claude-sonnet-4-6` | Não |
| `CB_FAILURE_THRESHOLD` | `3` | Não |
| `CB_RECOVERY_TIMEOUT_S` | `60` | Não |

> ⚠️ `enable_docs` é forçado `False` em produção pelo `@model_validator` em `config.py`.

## API

| Endpoint | Método | Auth | Descrição |
|----------|--------|------|-----------|
| `/analyze` | POST | API Key | Análise completa → IncidentReport |
| `/admin/circuit-breaker/status` | GET | Admin Key | Status do circuit breaker |
| `/admin/circuit-breaker/reset` | POST | Admin Key | Reset manual do circuit breaker |
| `/prometheus/metrics` | GET | Prometheus Key | Scrape Prometheus |
| `/health` | GET | — | Liveness check |

**Rate limit:** `POST /analyze` — 10 req/min por IP (SlowAPI)

OpenAPI spec (em runtime dev): `http://localhost:8001/docs`

## Observability

- **Logs:** JSON estruturado; `prompt_version` em cada análise; API keys apenas como SHA-256 (8 chars)
- **Metrics LLM:** `llm_call_duration_seconds`, `llm_calls_total{outcome}`, `llm_output_validation_failures_total`, `prompt_injection_sanitized_total`
- **Traces:** OTel por specialist + orchestrator; propagação W3C TraceContext
- **Alertas:** `LLMHighErrorRate` (>1% por 5 min), `LLMCircuitBreakerOpen`

## Prompts

Prompts versionados em [`prompts/v1/`](../prompts/v1/).
Mudanças seguem o mesmo processo de PR que código.
Versão atual: `PROMPT_VERSION = "1.0.0"` (logado em cada análise).

## Dependencies

[docs/dependency-manifest-ira.yaml](../docs/dependency-manifest-ira.yaml)

## On-call and Incidents

Circuit breaker aberto: `GET /admin/circuit-breaker/status` → `POST /admin/circuit-breaker/reset`
Postmortems: [docs/post-mortems/](../docs/post-mortems/)

## Contributing

```bash
# Testes unitários (sem Docker, sem Anthropic API)
.venv/bin/pytest tests/ -q --tb=short

# Cobertura completa (≥85% obrigatório)
.venv/bin/pytest --cov=app --cov-report=term-missing
```

## Changelog

[CHANGELOG.md](CHANGELOG.md)
