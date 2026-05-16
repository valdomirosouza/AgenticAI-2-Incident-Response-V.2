# Changelog — Log-Ingestion-and-Metrics

## [1.3.0] — 2026-05-16
### Added
- `README.md` — documentação completa do serviço

## [1.2.0] — 2026-05 (estimado)
### Added
- Prometheus auth: `X-Prometheus-Key` obrigatório em staging/production (A05)
- PII anonimização L1/L2/L3 em `pii.py` (CPF, email, IP, hostname)

## [1.1.0] — 2026-04 (estimado)
### Added
- `GET /metrics/slo-status` — SloStatusReport com error budget
- OpenTelemetry traces: FastAPIInstrumentor + RedisInstrumentor
- `error_budget_remaining_pct` Gauge no Prometheus
- Alertas Prometheus: SLO availability, latency_p95, latency_p99

## [1.0.0] — 2026-01 (estimado)
### Added
- `POST /logs` — ingestão de logs HAProxy
- `GET /metrics/overview`, `/response-times`, `/saturation`, `/rps`, `/backends`
- `GET /health`
- Redis 7 como store de métricas (ADR-2026-0003)
- JSON structured logging com trace_id + span_id
- Pydantic v2 validation em todos os endpoints
- Security headers middleware
- Docker container non-root (appuser)
