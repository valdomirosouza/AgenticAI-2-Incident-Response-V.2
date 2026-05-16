---
name: sdlc-governance
description: Manages the full software lifecycle beyond development — formal change control (RFC/CAB), technical debt tracking and prioritization, and service/API/dependency deprecation and end-of-life processes. Use when proposing a production change, reviewing a change request, managing a Change Advisory Board session, registering or prioritizing technical debt, planning a service deprecation, managing API sunset, or handling EOL of a runtime or library.
---

# SDLC Governance

## Contents
- Change Management (RFC/CAB) → [rfc-template.md](rfc-template.md)
- Technical Debt Management → [tech-debt-process.md](tech-debt-process.md)
- Deprecation and EOL lifecycle → [deprecation-process.md](deprecation-process.md)

---

## Change Management — Types and Flow

| Type | Definition | Approval | Examples |
|------|-----------|----------|---------|
| **Standard** | Pre-approved, low risk, documented procedure | Automated (pipeline) | Feature deploy via CI/CD, cert rotation, auto-scaling |
| **Normal** | Planned, risk assessed | CAB weekly | New integration, architecture change, major dependency upgrade |
| **Emergency** | Urgent fix for active incident | TL + SecOps async (< 2h) | Critical hotfix, emergency rollback, CRITICAL CVE patch |

**Change Freeze triggers:**
- Black Friday / commercial critical dates: -7d to +2d
- Fiscal year-end
- Error budget < 10% (auto-blocked by pipeline)
- Active SEV-1 incident

**CAB metrics:**
- Change success rate (no incident generated): target > 95%
- Emergency change rate: target < 5% (high % indicates weak process)

RFC template → [rfc-template.md](rfc-template.md)

---

## Technical Debt — Classification

| Type | Examples |
|------|---------|
| Architectural | SPOF not mitigated, tight domain coupling |
| Security | Unfixed CVE dependency, secret outside vault |
| Observability | Service without Golden Signals, trace without propagation |
| Reliability | No circuit breaker, no timeout, no fallback |
| Code | High complexity, no tests, dead code |
| Operational | Recurring manual process without automation ticket |
| Compliance | Deviation from this SDD standard |

**Severity and SLA:**

| Severity | Criterion | Resolution SLA | Accept risk? |
|----------|-----------|---------------|-------------|
| Critical | Security CVE or data loss risk | Current sprint | Forbidden |
| High | Caused or could have caused SEV-1/2 | Current quarter | VP Engineering |
| Medium | Reliability/maintainability degradation | Next two quarters | Engineering Manager |
| Low | Quality without operational impact | Backlog | Tech Lead |

**Budget rule:** Minimum 20% of engineering capacity dedicated to debt resolution each sprint.

Full registration process and metrics → [tech-debt-process.md](tech-debt-process.md)

---

## Deprecation / EOL — Policy by Type

| Type | Notice minimum | Sunset minimum | Exception |
|------|---------------|----------------|-----------|
| External APIs | 6 months | 3 months after deprecation | Critical CVE: 30 days |
| Internal APIs | 3 months | 1 month after deprecation | — |
| Libraries (EOL upstream) | When EOL announced | Before upstream EOL date | — |
| Service runtimes | 90 days before EOL | Before upstream EOL date | — |

**Rule:** Never operate in production with a runtime or dependency past its upstream EOL date.

**EOL tracking:** `eol-inventory.yaml` versioned per service, reviewed quarterly.

Full deprecation process, checklist, and templates → [deprecation-process.md](deprecation-process.md)
