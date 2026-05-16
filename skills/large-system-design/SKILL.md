---
name: large-system-design
description: Applies Google SRE NALSD methodology and principles from "Building Secure and Reliable Systems" to design scalable, reliable, and understandable distributed systems. Use when designing a new service or architecture, performing capacity planning, identifying system bottlenecks, reviewing resilience of an existing system, or preparing for the NALSD section of a PRR. Also use when asked about blast radius, cascading failures, load shedding, circuit breakers, or system evolvability.
---

# Large System Design — NALSD and Google SRE

Based on: Google SRE Book, SRE Workbook, and "Building Secure and Reliable Systems."

## Contents
- NALSD methodology (5 steps)
- Design for Understandability
- Resilience by Design (blast radius, circuit breaker)
- Overload Handling (load shedding, backpressure)
- Cascading Failure Prevention
- Design for Evolvability
- Templates and checklists → [nalsd-templates.md](nalsd-templates.md)
- Resilience patterns (code) → [resilience-patterns.md](resilience-patterns.md)

---

## The Four Fundamental NALSD Questions

Every design must answer these before PRR:

```
1. Does the design work?       → Logical correctness
2. Can it handle the load?     → Capacity under real traffic
3. Does it survive failures?   → Resilience and degradation modes
4. Can it evolve?              → Maintainability and extensibility
```

---

## NALSD in 5 Steps

**Step 1 — Napkin Design:** Simplest possible design. No optimizations. Something concrete to criticize.

**Step 2 — Back-of-Envelope:** Estimates are mandatory. Specs without numbers are abstractions — not NALSD.

```
Traffic:  DAU × requests/user/day / 86400 = avg RPS → × peak factor = peak RPS
Latency:  Sum of p99 latency per component ≤ SLO threshold
Storage:  records/day × record size × retention days = total
Capacity: peak RPS / throughput per instance = instances needed (+ N+2 redundancy)
```

Full template → [nalsd-templates.md](nalsd-templates.md)

**Step 3 — Identify Bottlenecks:** For each component: `max capacity vs peak demand`. Common bottlenecks and solutions → [nalsd-templates.md](nalsd-templates.md)

**Step 4 — Iterative Refinement:** Solve one bottleneck per iteration. Re-answer the four questions after each iteration. Document each iteration.

**Step 5 — Document Tradeoffs:** Every significant tradeoff (CAP, latency vs durability, complexity vs performance) gets an ADR. → See managing-adrs skill.

---

## Design for Understandability

A system that cannot be understood cannot be operated safely.

| Principle | Implementation |
|-----------|---------------|
| Explicit invariants | List properties that must ALWAYS be true. Add tests and alerts that verify them. |
| Explicit state machines | Any flow with > 2 states must have a documented state diagram |
| Cyclomatic complexity limits | Max 10 per function, max 50 per module. Enforced in CI. |
| Comment policy | Comment the WHY, not the WHAT. If you thought > 30s, document it. |

**Understandability PRR checklist:**
- [ ] Architecture diagram readable by engineer unfamiliar with the system
- [ ] State machines documented for all complex flows
- [ ] System invariants listed in spec
- [ ] Complexity within CI-enforced limits
- [ ] Runbook validated by engineer outside the team

---

## Resilience — Key Patterns

**Blast Radius Containment:**
- Bulkhead: separate thread/connection pools by operation type or tenant
- Cell-based architecture: independent cells for > 10M users or SLO > 99.99%
- Graceful degradation: define explicit fallback for every non-critical dependency

**Circuit Breaker States:** CLOSED → (failures ≥ threshold) → OPEN → (timeout) → HALF-OPEN → (probe success) → CLOSED

**Timeout Budget Rule:**
```
Total request timeout ≥ sum of all dependency timeouts + business logic margin
Never have a connection without a timeout configured.
```

Code patterns → [resilience-patterns.md](resilience-patterns.md)

---

## Overload Handling

**Priority-based load shedding:**
```
P1 (Critical): payment, authentication — never shed
P2 (High):     balance query, orders
P3 (Normal):   history, reports — shed at 80% capacity
P4 (Low):      analytics, recommendations — shed at 60% capacity
```

**Backpressure signals:**
- HTTP: `429 Too Many Requests` with `Retry-After` header
- gRPC: `RESOURCE_EXHAUSTED`
- Queues: consumer lag monitoring → producer throttling

---

## Cascading Failure Prevention

| Anti-pattern | Prevention |
|-------------|-----------|
| Retry storm | Exponential backoff + jitter (±25%), max 3 retries, retry budget |
| Thundering herd | Cache stampede lock, probabilistic early expiration, staggered TTL |
| Health propagation | Separate liveness (process alive) from readiness (can serve traffic) |
| Deadline loss | Propagate remaining deadline to all downstream calls |
| Retry after client gave up | Context cancellation propagation |

---

## Evolvability

- **API versioning:** Breaking changes in new version (`/v2/`). Add fields freely; never remove.
- **Feature flags:** All new features ship behind a flag. Flags have owners and expiry dates.
- **Schema evolution:** Expand-contract pattern for DB migrations. Schema Registry for events.
- **CVE SLA:** CRITICAL → 72h; HIGH → 7d; MEDIUM → 30d; LOW → next release.
- **SLO review:** Quarterly. Too easy to achieve → tighten target. Impossible → investigate root cause, don't loosen.
