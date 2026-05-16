# Log-Ingestion-and-Metrics

> Serviço de ingestão de logs HAProxy e cálculo de Golden Signals em tempo real.
> Porta: **:8000** | Stack: FastAPI + Redis 7

## Quick Start

```bash
cd Log-Ingestion-and-Metrics
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
# Configure: cp ../.env.example ../.env && edite as variáveis
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Ou com toda a stack via Docker:
```bash
cd ..
docker compose up -d --wait
```

## Architecture

```
POST /logs ──► ingestion.py ──► Redis (counters + sorted sets)
                   │
                   └── pii.py (anonymização L1/L2/L3)

GET /metrics/* ──► routers/metrics.py ──► Redis ──► cálculo de percentis
GET /metrics/slo-status ──────────────── slo.py ──► error budget
GET /prometheus/metrics ─────────────── prometheus-fastapi-instrumentator
```

Referência completa: [SPEC-2026-001](../docs/specs/SPEC-2026-001-log-ingestion-and-metrics.md)
ADRs: [ADR-0001](../docs/adr/active/ADR-2026-0001-microservices-three-fastapi-services.md), [ADR-0003](../docs/adr/active/ADR-2026-0003-redis-as-golden-signals-store.md)

## Configuration

Todas as variáveis via `.env` (copie de `../.env.example`):

| Variável | Padrão | Obrigatória em Prod |
|----------|--------|---------------------|
| `APP_ENV` | `development` | Sim |
| `REDIS_URL` | `redis://redis:6379` | Sim |
| `REDIS_PASSWORD` | vazio | Sim |
| `PROMETHEUS_API_KEY` | vazio | Sim |
| `API_KEY` | vazio | Sim |
| `ALLOWED_ORIGINS` | `http://localhost:3000,...` | Sim |
| `OTLP_ENDPOINT` | vazio | Não |

## API

| Endpoint | Método | Auth | Descrição |
|----------|--------|------|-----------|
| `/logs` | POST | API Key | Ingestão de log HAProxy |
| `/metrics/overview` | GET | — | Totais de requests e error rates |
| `/metrics/response-times` | GET | — | P50/P95/P99 em ms |
| `/metrics/saturation` | GET | — | Uso de memória Redis |
| `/metrics/rps` | GET | — | RPS por minuto (janela 60 min) |
| `/metrics/backends` | GET | — | Distribuição por backend |
| `/metrics/slo-status` | GET | — | SloStatusReport com error budget |
| `/prometheus/metrics` | GET | Prometheus Key | Scrape Prometheus |
| `/health` | GET | — | Liveness + conectividade Redis |

OpenAPI spec (em runtime dev): `http://localhost:8000/docs`
Referência estática: [docs/api/openapi-log-ingestion.yaml](../docs/api/openapi-log-ingestion.yaml)

## Observability

- **Logs:** JSON estruturado; `trace_id` + `span_id` em todos os logs
- **Metrics:** Prometheus em `/prometheus/metrics`; dashboard: [golden-signals.json](../infra/grafana/dashboards/golden-signals.json)
- **Traces:** OpenTelemetry; exportado via `OTLP_ENDPOINT`
- **Alertas:** [infra/prometheus/alerts.yaml](../infra/prometheus/alerts.yaml)
- **Runbook de latência:** [docs/runbooks/high-latency.md](../docs/runbooks/high-latency.md)
- **Runbook Redis:** [docs/runbooks/redis-memory.md](../docs/runbooks/redis-memory.md)

## Dependencies

[docs/dependency-manifest-log-ingestion.yaml](../docs/dependency-manifest-log-ingestion.yaml)

## SLO

[slo/slo.yaml](../slo/slo.yaml)

| SLO | Target | Threshold |
|-----|--------|-----------|
| availability | 99.5% | 5xx rate ≤ 0.5% |
| latency_p95 | 99.0% | P95 ≤ 500ms |
| latency_p99 | 99.9% | P99 ≤ 1000ms |

## On-call and Incidents

Escalação: Slack `#sre-alerts` → on-call via PagerDuty
Severidades: [docs/runbooks/](../docs/runbooks/) | Postmortems: [docs/post-mortems/](../docs/post-mortems/)

## Contributing

```bash
# Testes unitários (sem Docker)
.venv/bin/pytest tests/ -q --tb=short

# Testes E2E (requerem Docker daemon)
.venv/bin/pytest tests/test_e2e_redis.py -m e2e

# Cobertura completa (≥85% obrigatório)
.venv/bin/pytest --cov=app --cov-report=term-missing
```

## Changelog

[CHANGELOG.md](CHANGELOG.md)
