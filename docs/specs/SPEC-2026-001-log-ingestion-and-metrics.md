# SPEC-2026-001: Log Ingestion and Metrics

> ⚠️ SPEC RETROATIVA — Reconstruída em 2026-05-16 a partir do código-fonte, ADRs e histórico git.
> Revisada e validada por Valdomiro Souza.

## Metadata
- **ID:** SPEC-2026-001
- **Status:** Approved
- **Author:** Valdomiro Souza
- **Reviewers:** Valdomiro Souza (Tech Lead)
- **Created:** 2026-01-01 (estimado) — Formalizado: 2026-05-16
- **Version:** 1.0.0
- **AI-assisted:** Yes — Claude Sonnet 4.6 / Prompt ID: PROMPT_VERSION 1.0.0

## Context and Problem

O sistema de Incident Response precisa de uma fonte de Golden Signals (latência, erros,
tráfego, saturação) derivada de logs estruturados do HAProxy. Sem essa camada, o Incident
Response Agent não tem métricas para acionar análise LLM. O Redis foi escolhido como store
de métricas por sua latência sub-milissegundo e TTL nativo para dados de séries temporais leves
(ADR-2026-0003). O serviço roda na porta :8000.

## Scope
### Includes
- Ingestão de logs HAProxy via `POST /logs`
- Cálculo de métricas derivadas: error rate 4xx/5xx, latência P50/P95/P99, RPS por minuto, saturação Redis
- Endpoints de consulta de métricas: `/metrics/overview`, `/metrics/response-times`, `/metrics/saturation`, `/metrics/rps`, `/metrics/backends`
- SLO endpoint: `GET /metrics/slo-status`
- Prometheus scrape: `GET /prometheus/metrics` (autenticado)
- Observabilidade: structured logs JSON, OpenTelemetry traces, Prometheus metrics
- Segurança: API key auth (HMAC), security headers, rate limiting, PII anonymization

### Out of Scope
- Alerting direto (responsabilidade do Prometheus/AlertManager)
- Persistência histórica de longo prazo (fora do escopo Redis)
- Ingestão de logs de outras fontes além de HAProxy

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| RF-01 | `POST /logs` aceita log HAProxy (HaproxyLog model) e persiste métricas no Redis | Must Have | Status 202; métricas incrementadas no Redis |
| RF-02 | `GET /metrics/overview` retorna total de requests, erros 4xx/5xx e error rates | Must Have | Valores consistentes com logs ingeridos |
| RF-03 | `GET /metrics/response-times` retorna P50/P95/P99 em ms | Must Have | Percentis calculados via Redis sorted set |
| RF-04 | `GET /metrics/saturation` retorna uso de memória Redis e conexões | Must Have | Dados diretos do Redis INFO |
| RF-05 | `GET /metrics/rps` retorna RPS por minuto na janela de 60 min | Must Have | Bucket de 1 minuto; RPS atual calculado |
| RF-06 | `GET /metrics/backends` retorna distribuição de requests por backend | Must Have | Contadores por backend do Redis |
| RF-07 | `GET /metrics/slo-status` retorna SloStatusReport com error budget | Must Have | SLOs: availability 99.5%, latency_p95 99%, latency_p99 99.9% |
| RF-08 | `GET /health` retorna status do serviço e conectividade Redis | Must Have | Status 200 quando healthy |
| RF-09 | Endpoint `/prometheus/metrics` expõe métricas Prometheus autenticadas | Should Have | Requer `X-Prometheus-Key` header |

## Non-Functional Requirements

| ID | Category | Requirement | Metric |
|----|----------|-------------|--------|
| RNF-01 | Performance | p99 latência de ingestão < 50ms | Prometheus histogram `http_request_duration_seconds` |
| RNF-02 | Availability | SLO 99.5% (taxa 5xx ≤ 0.5%) | SLI medido via `/metrics/slo-status` |
| RNF-03 | Latency | P95 ≤ 500ms | SLI medido continuamente |
| RNF-04 | Security | Zero findings OWASP Top 10 (SAST + DAST) | CI bloqueante |
| RNF-05 | Coverage | ≥ 85% branch coverage | pyproject.toml `--cov-fail-under=85` |
| RNF-06 | Privacy | PII (IPs, CPF, email) anonimizado antes de logging | `pii.py` L1/L2/L3 patterns |

## Architecture

```
HAProxy logs
    │
    ▼ POST /logs
[Log-Ingestion-and-Metrics :8000]
    │  FastAPI + fakeredis (tests) / Redis 7 (prod)
    │
    ├── ingestion.py ──────── persiste métricas no Redis
    ├── pii.py ─────────────── anonimiza PII antes de log
    ├── metrics_registry.py ── Prometheus counters/histograms
    ├── slo.py ─────────────── calcula error budget
    └── telemetry.py ───────── OTel traces via OTLP
```

### Back-of-Envelope Summary (NALSD)
- **Carga acadêmica:** carga simulada via Locust (load-tests/locustfile.py)
- **Peak RPS estimado:** 100 req/s (dissertação — single node Docker Compose)
- **Latência budget p99:** ingestão < 50ms; Redis ZADD/INCR: ~1ms local; FastAPI overhead: ~5ms
- **Storage Redis:** 50k logs × 200 bytes = ~10 MB/sessão; TTL implícito via contadores
- **Instâncias:** 1 instância (+ Redis replicado em prod) — N+1 com healthcheck

ADR relacionados: ADR-2026-0001 (microservices), ADR-2026-0003 (Redis), ADR-2026-0009 (auth)

## Observability
- **Logs:** JSON estruturado via `logging_config.py`; campos: `timestamp`, `level`, `service`, `version`, `trace_id`, `span_id`, `message`; PII anonimizado via `pii.py`
- **Metrics:** `http_requests_total`, `http_request_duration_seconds`, `error_budget_remaining_pct`, `redis_memory_usage_bytes` (via `metrics_registry.py`)
- **Traces:** OpenTelemetry com FastAPIInstrumentor + RedisInstrumentor; exportado via OTLP; propagação W3C TraceContext
- **SLI:** `error_rate_5xx_pct` ≤ 0.5%; `p95_ms` ≤ 500ms; `p99_ms` ≤ 1000ms
- **SLO:** availability 99.5%; latency_p95 99.0%; latency_p99 99.9%

## Security
- PII involved: Yes — classificação L3 (IPs em logs HAProxy), L2 (paths com dados pessoais)
- Anonymization: `pii.py` com regex patterns para CPF, email, phone, IP, hostname
- Credentials: API_KEY via variável de ambiente (sem vault em dev; vault-ready para prod)
- Communication: TLS 1.3 (via reverse proxy/API Gateway em prod)
- Threat model: `/docs/security/threat-model.md` — STRIDE aplicado; DoS via rate limiting
- OWASP review: A01 (HMAC API key), A02 (sem hardcoded secrets), A05 (security headers), A07 (structured logging sem stack trace para cliente)
- DPIA required: No — sem dados pessoais de usuários finais; logs de infra apenas

## Dependencies
Referência: `docs/dependency-manifest-log-ingestion.yaml`

Runtime principais: `fastapi==0.115.12`, `redis==5.2.1`, `prometheus-fastapi-instrumentator==7.1.0`,
`opentelemetry-sdk`, `pydantic==2.11.4`, `pydantic-settings`

Infra: Redis 7 (:6379), Prometheus (:9090)

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Redis OOM sob carga alta | Alta — perda de métricas | Média | `maxmemory-policy allkeys-lru`; alerta Prometheus em 80% uso |
| P99 acima de SLO em pico | Média — SLO breach | Baixa | Circuit breaker no IRA; rate limiting 429 |
| PII vazado em logs | Alta — LGPD | Baixa | `pii.py` anonimização; testes de regressão `test_pii.py` |
| Ingestão de log malicioso | Média — pollution | Baixa | Pydantic v2 validation; `max_length` em todos os fields |

## Approval
| Role | Name | Date | Status |
|------|------|------|--------|
| Tech Lead | Valdomiro Souza | 2026-05-16 | Approved (retroativo) |
| Security | Valdomiro Souza | 2026-05-16 | Approved (retroativo) |
| Architect | Valdomiro Souza | 2026-05-16 | Approved (retroativo) |
