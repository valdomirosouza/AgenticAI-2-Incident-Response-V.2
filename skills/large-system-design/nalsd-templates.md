# NALSD Templates

## Back-of-Envelope Template

```markdown
## Back-of-Envelope — [Service Name]

### Traffic
- DAU: X
- Requests per user per day: Y
- Peak factor: 3x
- Avg RPS: (DAU × Y) / 86,400 = N req/s
- Peak RPS: N × 3 = M req/s

### Latency budget (SLO p99: Xms)
| Component | p50 | p99 |
|-----------|-----|-----|
| API Gateway | 5ms | 10ms |
| Business logic | 20ms | 40ms |
| Database query | 10ms | 30ms |
| External service | 50ms | 150ms |
| **Total** | **85ms** | **230ms** ⚠️ exceeds 200ms SLO

### Storage
- Record size: X KB
- Records per day: Y
- Daily storage: X × Y = Z GB/day
- Retention: N years → Z × 365 × N = Total TB

### Capacity
- Throughput per instance (benchmark): N req/s
- Instances at peak: M / N = P
- With N+2 redundancy: P + 2 instances minimum
- Auto-scaling range: P to P × 3
```

## Bottleneck Analysis — Common Cases

| Bottleneck | Signals | Solutions |
|-----------|---------|-----------|
| Database | Connection pool exhausted; query time growing with load; DB CPU > 70% at peak | Read replicas; PgBouncer; query optimization; Redis cache; CQRS |
| External service | Latency dominated by third-party; timeout rate growing | Cache responses; circuit breaker; async processing via queue |
| CPU-bound | CPU > 70% at normal load; latency grows linearly with RPS | Horizontal scaling; identify and optimize CPU-bound operations; caching |
| Memory | OOM kills; GC pauses increasing | Memory limit tuning; object pooling; streaming vs buffering |
| Network | High bandwidth costs; packet loss at peak | Compression; batching; CDN for static content |

## Tradeoffs ADR Template

```markdown
## Design Tradeoffs — [Service Name]

### Consistency vs Availability (CAP)
- Decision: [eventual consistency for X; strong for Y]
- Justification: [user tolerates X stale but not Y incorrect]
- Implication: [read replicas for X; writes always to primary for Y]
- ADR: ADR-NNN

### Latency vs Durability
- Decision: [synchronous DB commit before responding]
- Justification: [payment cannot be lost on restart]
- Implication: [+10ms latency; no fire-and-forget on transactions]
- ADR: ADR-NNN

### Complexity vs Performance
- Decision: [Redis session cache instead of stateless JWT]
- Justification: [immediate session revocation is security requirement]
- Implication: [Redis dependency; cache invalidation operations]
- ADR: ADR-NNN
```

## Pre-PRR Checklist — NALSD + Google SRE

### NALSD
- [ ] Napkin design documented in spec
- [ ] Back-of-envelope calculations completed (traffic, latency, storage, capacity)
- [ ] Bottlenecks identified and resolved iteratively (minimum 2 iterations)
- [ ] Tradeoffs documented in ADRs (CAP, latency vs durability)
- [ ] Infrastructure cost estimate calculated and approved

### Understandability
- [ ] System invariants listed
- [ ] State machines documented for complex flows
- [ ] Cyclomatic complexity within CI limits
- [ ] Runbook validated by external engineer

### Resilience
- [ ] Timeout configured for every external dependency
- [ ] Fallback documented for every non-critical dependency
- [ ] Circuit breaker configured for dependencies with SLO < 99.9%
- [ ] Blast radius analyzed: which users/features affected by component failure?
- [ ] Degraded mode documented and tested

### Overload
- [ ] Rate limiting configured per client/endpoint
- [ ] Concurrency limit calculated (from back-of-envelope) and configured
- [ ] Load shedding by priority defined
- [ ] Behavior under 2× expected load tested and documented

### Cascading Failures
- [ ] Retry with exponential backoff + jitter implemented
- [ ] Liveness and readiness probes separated and correct
- [ ] Deadline propagation implemented for chained calls
- [ ] Thundering herd prevention for shared caches

### Evolvability
- [ ] API versioned with compatibility contract defined
- [ ] Feature flags for all new functionality
- [ ] DB migrations backward-compatible (expand-contract)
- [ ] CVE patching SLA documented and applied
- [ ] Deprecation policy defined for endpoints and schemas
