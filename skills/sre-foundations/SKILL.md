---
name: sre-foundations
description: Applies Google SRE principles to production systems — Production Readiness Reviews, TOIL reduction, incident lifecycle, and blameless postmortems. Use when preparing a service for production, evaluating operational maturity, responding to incidents, or writing postmortems. Also use when someone asks about on-call, error budgets, SRE engagement, or reducing manual operational work.
---

# SRE Foundations

## Core principle
SRE treats operations as a software problem. Reliability is a feature. Every manual, repetitive task is a bug to eliminate.

## Contents
- **PRR (Production Readiness Review):** [prr-checklist.md](prr-checklist.md)
- **TOIL identification and elimination:** See below
- **Incident lifecycle and severities:** [incident-response.md](incident-response.md)
- **Blameless postmortem template:** [incident-response.md](incident-response.md)

---

## TOIL — Identification and Policy

Work is TOIL if it is: manual, repetitive, automatable, reactive, and has no enduring value.

| Metric | Target |
|--------|--------|
| Max TOIL as % of eng time | ≤ 50% |
| Sustainable target | ≤ 25% |
| Any task taking > Xh/week | Must have automation backlog item |

**Automation categories:**

| Category | Tools |
|----------|-------|
| Deployment | ArgoCD, Spinnaker, Harness CD |
| Scaling | HPA, VPA, KEDA |
| Remediation | Circuit breaker, auto-restart, auto-healing |
| Alerting | AlertManager, PagerDuty, OpsGenie |
| Incident | FireHydrant, Incident.io, PagerDuty Rundeck |

---

## Error Budget Policy

```
Error Budget = 1 - SLO target
Example: SLO 99.9% → Error Budget = 0.1% of time in the period

Budget < 50%  → Feature freeze; focus on reliability
Budget < 10%  → Deploy freeze (except hotfixes); incident review mandatory
Budget = 0    → Full deploy freeze; executive escalation; SLO review
```

---

## PRR Gate

Every service must pass PRR **before** production. See [prr-checklist.md](prr-checklist.md) for the full checklist.

PRR prerequisites (must complete first):
1. NALSD design validated (section 4.0 of main spec)
2. SLI/SLO defined and documented
3. Runbook written and reviewed by someone external to the team
4. Chaos experiments planned

---

## Incident Severity Matrix

| SEV | Criterion | Response SLA | Lead |
|-----|-----------|-------------|------|
| SEV-1 | Production down, massive user impact | < 5 min | Senior on-call + CTO |
| SEV-2 | Severe degradation, critical feature affected | < 15 min | On-call |
| SEV-3 | Partial degradation, workaround available | < 1h | Responsible team |
| SEV-4 | Minimal impact, no user effect | < 1 business day | Backlog |

Full incident lifecycle and postmortem template → [incident-response.md](incident-response.md)
