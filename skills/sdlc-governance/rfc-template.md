# RFC Template — Request for Change

```markdown
# RFC-[NNN]: [Change Title]

## Metadata
- **ID:** RFC-YYYY-NNN
- **Type:** Standard | Normal | Emergency
- **Requestor:** [name + team]
- **Requested date:** YYYY-MM-DD
- **Execution window:** YYYY-MM-DD HH:MM → HH:MM (timezone)
- **Related spec:** SPEC-YYYY-NNN (if applicable)
- **Related incident:** INC-NNN (if Emergency)

## Change Description
> What will be changed, in which environment, in which component.

## Motivation
> Why is this change necessary now?

## Expected Impact
- **Affected systems:** [list]
- **Users affected during window:** [estimate]
- **Expected downtime:** Yes/No — [estimated duration]
- **SLO impact:** [% of error budget consumed if downtime occurs]

## Execution Plan
| Step | Action | Owner | Estimated Duration |
|------|--------|-------|-------------------|
| 1 | | | |
| 2 | | | |

## Rollback Plan
> Exact steps to revert the change. Must be tested before the window.
- Rollback trigger: [condition that activates rollback]
- Max time before rollback: [X minutes]
- Rollback command/procedure: [exact and verified]

## Pre-Change Tests
- [ ] Executed in staging with representative data
- [ ] Rollback plan tested
- [ ] Monitoring configured for the window

## Approval
| Role | Name | Date | Decision |
|------|------|------|---------|
| Requestor | | | Proposes |
| Tech Lead | | | Approve / Reject |
| SecOps (if security impact) | | | Approve / Reject |
| CAB | | | Approve / Reject |
```

---

## CAB Governance

```yaml
composition:
  - Engineering Manager (chair)
  - Tech Lead representative per domain
  - SecOps (permanent)
  - SRE (permanent)
  - DBA (when DB changes)
  - Business representative (when customer impact)

cadence:
  regular_meeting: "Weekly — every Monday 14:00"
  emergency_rfcs: "Async via #cab-emergency channel — approval within 2h"

approval_criteria:
  approve: "Risk assessed, rollback plan tested, adequate window"
  reject: "Risk not assessed, no rollback, inadequate window"
  defer: "Valid change but wrong window or incomplete impact mapping"
```
