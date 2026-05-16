# Incident Response — Lifecycle, Runbook Template, Postmortem

## Contents
- Incident lifecycle
- Runbook template
- Blameless postmortem template
- MTTD / MTTR tracking

---

## Incident Lifecycle

```
DETECT → TRIAGE → CONTAIN → RESOLVE → POSTMORTEM
  |          |        |          |           |
Alert    SEV level  Mitigate  Root cause  Blameless
fires    declared   impact    eliminated  analysis
```

**Declaration rule:** When in doubt, declare. It is always better to stand down a SEV than to miss one.

---

## Runbook Template

```markdown
# RUNBOOK: [Service] — [Scenario]

## Quick identification
- Alert: [exact alert name]
- Dashboard: [link]
- Logs: [link + query]

## Diagnose (< 5 minutes)
1. Check [metric X] on dashboard [Y]
2. Run: `kubectl get pods -n [namespace]`
3. Check logs: `kubectl logs -l app=[service] --tail=100`

## Contain
- [ ] Option A — Rollback: `[exact command]`
- [ ] Option B — Feature flag off: `[procedure]`
- [ ] Option C — Scale up: `[exact command]`

## Communicate
- Update status page: [link]
- Incident channel: #incidents
- Stakeholders: [list]

## Escalate
If unresolved in 30 min → escalate to [name/role]

## Resolve
- Confirm metrics returned to normal
- Close alert
- Open postmortem ticket

## Related incidents
- [Link to past postmortems]
```

---

## Blameless Postmortem Template

```markdown
# Postmortem: [Incident Title]

## Executive summary
- Date/Time: Start → End → Total MTTR
- Severity: SEV-[N]
- Impact: [users affected, revenue, SLO burn %]

## Timeline
| Time | Event |
|------|-------|
| HH:MM | Alert fired |
| HH:MM | On-call paged |
| HH:MM | Cause identified |
| HH:MM | Containment applied |
| HH:MM | Service restored |

## Root Cause Analysis (5 Whys)
Why did X happen? → Because Y → Because Z → ...

## What went well
- ...

## What can improve
- ...

## Action items
| Action | Owner | Deadline | Priority |
|--------|-------|----------|----------|
| Add alert for X | @person | YYYY-MM-DD | High |

## Incident metrics
- MTTD (Mean Time to Detect): X min
- MTTR (Mean Time to Recover): X min
- SLO burn: X%
- Error budget consumed: X%
```

---

## MTTD / MTTR Tracking

Track per incident and aggregate quarterly:

| Metric | Definition | Target |
|--------|-----------|--------|
| MTTD | Time from incident start to alert fire | Trending down |
| MTTR | Time from detection to full recovery | Trending down |
| Incident frequency | Count per month by SEV | Trending down |
| Repeat incidents | Same root cause recurring | = 0 |

If MTTD or MTTR is not trending down, the postmortem action items are not being executed.
