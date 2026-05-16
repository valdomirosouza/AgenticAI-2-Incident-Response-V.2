---
name: observability-engineering
description: Implements production observability using the three pillars (logs, metrics, traces), defines and monitors SLI/SLO/SLA, and instruments services with OpenTelemetry. Use when adding observability to a service, defining SLOs, configuring alerts, designing dashboards, or setting up telemetry pipelines. Also use when asked about Golden Signals, error budgets, structured logging, trace context propagation, or OTel configuration.
---

# Observability Engineering

## Contents
- Golden Signals (mandatory for every service)
- Structured logging standard
- Metrics conventions
- Distributed tracing (OpenTelemetry)
- SLI / SLO / SLA definitions and templates → [sli-slo-templates.md](sli-slo-templates.md)
- Telemetry stack reference
- Instrumentation code patterns → [instrumentation-guide.md](instrumentation-guide.md)

---

## Golden Signals — Mandatory for Every Service

| Signal | Definition | Example metric | Base alert |
|--------|-----------|---------------|------------|
| **Errors** | Rate of failed requests (4xx/5xx) | `http_requests_total{status=~"5.."}` | > 1% for 5 min |
| **Latency** | Response time — always track p50/p95/p99 | `http_request_duration_seconds` | p99 > SLO threshold |
| **Traffic** | Request/operation volume per second | `http_requests_total` | Anomaly by std deviation |
| **Saturation** | Resource utilization (CPU, mem, disk, queue) | `container_cpu_usage_seconds_total` | > 80% for 10 min |

---

## Structured Log Standard

Every log entry MUST contain:

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "ERROR",
  "service": "payment-service",
  "version": "1.4.2",
  "environment": "production",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "message": "Payment processing failed",
  "http": { "method": "POST", "path": "/v1/payments", "status_code": 504, "duration_ms": 3001 }
}
```

**Required fields:** `timestamp` (ISO 8601 UTC), `level`, `service`, `version`, `trace_id`, `span_id`, `environment`

**Forbidden in logs:** passwords, tokens, API keys, CPF, card numbers, raw request bodies with PII

---

## Metrics Naming Convention

```
[namespace]_[subsystem]_[metric]_[unit]

# Examples:
http_server_requests_total{method, path, status}       # Counter
http_server_request_duration_seconds{method, path}     # Histogram
db_connections_active{pool, database}                  # Gauge
queue_messages_pending{queue_name, consumer_group}     # Gauge
```

**Label rules:**
- High-cardinality labels are forbidden (`user_id`, IP, UUID)
- Labels must be stable and pre-defined in spec
- Max 10 labels per metric

---

## Distributed Tracing — OpenTelemetry Standard

```yaml
standard: OpenTelemetry (OTel)
propagation: W3C TraceContext + Baggage

required_spans:
  - All incoming HTTP requests
  - All outgoing calls (external services, DB, queues)
  - Critical business logic operations

required_attributes:
  - service.name, service.version, deployment.environment
  - http.method, http.url, http.status_code
  - db.system, db.statement (sanitized — no PII)
  - error (boolean + error.message when applicable)

sampling:
  production: tail-based — 10% normal, 100% errors
  staging: 100%
```

For code examples → [instrumentation-guide.md](instrumentation-guide.md)

---

## SLI / SLO / SLA

| Term | Definition | Owner |
|------|-----------|-------|
| SLI | Quantitative measure of service behavior | Engineering |
| SLO | Internal reliability target | Engineering + Product |
| SLA | Contractual commitment to customer | Business + Legal |
| Error Budget | `1 - SLO target` — allowed margin of failure | Engineering |

**Key rule:** Internal SLO must be stricter than external SLA (buffer of safety).
Example: SLA = 99.5% → SLO = 99.9%

For `slo.yaml` template and alert configuration → [sli-slo-templates.md](sli-slo-templates.md)

---

## Telemetry Stack Reference

| Layer | Options |
|-------|---------|
| Collection | OpenTelemetry Collector, Fluent Bit |
| Logs storage | Loki, Elasticsearch, OpenSearch |
| Metrics storage | Prometheus + Thanos (long-term) |
| Traces storage | Tempo, Jaeger, Zipkin |
| Visualization | Grafana, Kibana |
| Alerting | AlertManager → PagerDuty / OpsGenie |
| AIOps | Grafana ML, Dynatrace Davis (anomaly detection) |
