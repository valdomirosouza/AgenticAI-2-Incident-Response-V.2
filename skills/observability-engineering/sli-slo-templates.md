# SLI / SLO Templates

## Contents
- slo.yaml template
- SLO burn rate alert configuration
- Error budget policy

---

## slo.yaml Template

```yaml
# slo.yaml — versioned in the service repository
service: payment-service
version: "1.0"
owner: team-payments

slis:
  - name: availability
    description: Successful requests / total requests
    query: |
      sum(rate(http_requests_total{status!~"5.."}[5m]))
      /
      sum(rate(http_requests_total[5m]))
    good_events: "status != 5xx"
    total_events: "all requests"

  - name: latency
    description: Proportion of requests with latency < 200ms at p99
    query: |
      histogram_quantile(0.99, http_request_duration_seconds_bucket) < 0.2
    threshold_ms: 200
    percentile: p99

slos:
  - name: availability_slo
    sli: availability
    target: 99.9
    window: 30d
    error_budget_remaining_alert: 10  # Alert when < 10% budget remaining

  - name: latency_slo
    sli: latency
    target: 95.0  # 95% of requests < 200ms p99
    window: 30d

sla_reference:
  document: "contracts/sla-enterprise-v2.pdf"
  customer_commitment: 99.5%
  note: "Internal SLO (99.9%) is stricter than external SLA (99.5%) — safety buffer"
```

---

## SLO Burn Rate Alerts

Configure two alert windows to catch both fast and slow burns:

```yaml
# Fast burn: consuming budget quickly (urgent)
- alert: SLOFastBurn
  expr: |
    (
      error_rate_1h / (1 - slo_target)
    ) > 14.4
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Fast error budget burn — 1h rate consuming budget 14x faster than allowed"

# Slow burn: subtle degradation (important but not urgent)
- alert: SLOSlowBurn
  expr: |
    (
      error_rate_6h / (1 - slo_target)
    ) > 6
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Slow error budget burn — 6h rate consuming budget 6x faster than allowed"
```

---

## Error Budget Policy

| Budget remaining | Action |
|-----------------|--------|
| > 50% | Normal operations — feature work permitted |
| 25–50% | Monitor closely — reduce deployment frequency |
| 10–25% | Feature freeze — prioritize reliability work |
| < 10% | Deploy freeze (hotfixes only) — incident review mandatory |
| 0% | Full deploy freeze — executive escalation — SLO review |

**SLO Review Triggers:**
- Error budget exhausted twice in a quarter → review if SLO target is realistic
- Budget never consumed → review if SLO is too easy (misses real reliability signal)
- Quarterly review is mandatory regardless
