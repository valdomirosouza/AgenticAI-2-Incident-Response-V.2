# ADR Examples — Filled

## Example 1 — New Decision (PostgreSQL)

```markdown
# ADR-0001: Use PostgreSQL as Primary Database

## Metadata
| Field | Value |
|-------|-------|
| ID | ADR-2022-0001 |
| Status | Accepted |
| Area | Data |
| Author | @joao.silva |
| Approved | 2022-03-10 |
| AI-assisted | No |

## 1. Context and Problem
The payment service requires a relational database for ACID transactional
consistency on financial operations. Evaluated in March 2022 with requirements:
ACID mandatory, JSON support for flexible metadata, team prior expertise,
managed service available on AWS.

**Driving forces:** ACID mandatory | Team SQL expertise | Moderate budget

## 2. Decision
Adopt PostgreSQL 14+ as primary database for payment-service, hosted as
Amazon RDS Multi-AZ in us-east-1.

**Scope:** Applies to payment-service primary datastore. Does not apply to
analytics read models (separate decision).

## 3. Alternatives Considered
| Alternative | Pros | Cons | Reason for Rejection |
|-------------|------|------|---------------------|
| **PostgreSQL** | ACID, JSON, open-source, team expertise | — | Chosen |
| MySQL | Widely known | Weaker JSON, complex replication | Inferior JSON support |
| MongoDB | Schema flexibility | No full ACID until v4 | ACID mandatory |
| Aurora PostgreSQL | Managed performance | 30% higher cost, more vendor lock-in | Budget |

## 4. Consequences
### Positive
- ACID guarantees integrity of financial transactions
- Zero learning curve — team already knows the technology

### Negative / Trade-offs
- Schema migrations require care (expand-contract — see ADR-0008)
- Horizontal sharding requires additional solution if volume exceeds 10TB

### Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Volume exceeds single instance capacity | Low (5 years) | High | Read replicas + review ADR at 5TB |

## 5. Future Review Criteria
- [ ] Data volume exceeds 5TB
- [ ] RDS PostgreSQL version reaches EOL
- [ ] Multi-region active-active requirement emerges

## 8. Approval
| Role | Name | Date | Decision |
|------|------|------|---------|
| Tech Lead | Maria Santos | 2022-03-10 | ✅ Approve |
| Architect | Carlos Lima | 2022-03-10 | ✅ Approve |
```

---

## Example 2 — Revision Superseding Previous ADR

```markdown
# ADR-0019: Use Centralized Redis for Cache (supersedes ADR-0003)

## Metadata
| Field | Value |
|-------|-------|
| ID | ADR-2023-0019 |
| Status | Accepted |
| Area | Data |
| Supersedes | ADR-0003 (local in-memory cache) |
| Approved | 2023-07-18 |
| AI-assisted | Yes — Claude Sonnet, trade-off analysis, reviewed by @ana.costa |

## 1. Context and Problem
ADR-0003 chose local in-memory (in-process) cache for user sessions.
With growth to 8 service instances, each instance has isolated cache, causing:
inconsistency between instances (user authenticated on pod A not recognized
on pod B), impossible coordinated invalidation, and inconsistent rate limiting
across pods.

**Driving forces:** Cache consistency across instances | Coordinated invalidation |
Centralized rate limiting | Acceptable +2ms latency cost

## 2. Decision
Replace local in-memory cache with Redis 7.x managed (ElastiCache),
shared across all service instances.

**Scope:** Applies to session cache and rate limiting in payment-service.
Does not apply to computation caches local to a single request lifecycle.

## 3. Alternatives Considered
| Alternative | Pros | Cons | Reason for Rejection |
|-------------|------|------|---------------------|
| **Redis centralized** | Consistency, invalidation, rate limiting | +2ms latency, new dependency | Chosen |
| Keep local cache | Zero additional latency | Inconsistency grows with scale | Problem not solved |
| Memcached | Simple, fast | No persistence, no advanced structures | Redis more complete |
| DynamoDB DAX | Managed, low latency | AWS lock-in, high cost | Portability and cost |

## 4. Consequences
### Positive
- Consistent cache across all instances
- Coordinated invalidation (e.g., logout invalidates session on all pods)
- Fair centralized rate limiting

### Negative / Trade-offs
- +2ms latency on cache operations (acceptable given 200ms p99 SLO)
- New dependency: Redis failure impacts authentication → circuit breaker mandatory

### Tech Debt Introduced
- DEBT-2023-041: Remove local cache code (estimate: 2 days)

## 5. Future Review Criteria
- [ ] Redis latency consistently exceeds 10ms
- [ ] ElastiCache cost exceeds 15% of total infra cost
- [ ] Per-region cache requirement emerges (consider Redis Cluster)

## 7. AI Assistance
| Field | Value |
|-------|-------|
| AI used | Claude Sonnet 4.6 |
| AI role | Trade-off analysis between alternatives, risk identification |
| Output reviewed by | @ana.costa |
| Final decision made by | Ana Costa (Tech Lead) |

## 8. Approval
| Role | Name | Date | Decision |
|------|------|------|---------|
| Tech Lead | Ana Costa | 2023-07-18 | ✅ Approve |
| SecOps | Pedro Ramos | 2023-07-19 | ✅ Approve (TLS in transit validated) |
```
