# Technical Debt — Registration and Process

## DEBT Registration Template

```markdown
# DEBT-[NNN]: [Debt Title]

## Metadata
- **ID:** DEBT-YYYY-NNN
- **Type:** Architectural | Security | Observability | Reliability | Code | Operational | Compliance
- **Severity:** Critical | High | Medium | Low
- **Affected service:** [name]
- **Registered by:** [name] on [date]
- **Discovered via:** code review | incident | PRR | audit | SAST
- **Related spec:** SPEC-YYYY-NNN (if applicable)

## Description
> What is the debt? Current state and desired state.

## Impact
- **Operational risk:** [what can happen if not resolved]
- **Current maintenance cost:** [TOIL in hours/week, incident frequency]
- **Blockers:** [what this debt prevents]

## Resolution Criteria
> How will we know the debt is fully paid?
- [ ] [verifiable condition 1]
- [ ] [verifiable condition 2]

## Effort
- Story points / engineering days: [estimate]
- Dependencies: [other debts or changes required]

## Prioritization
- **Backlog priority:** P1 | P2 | P3 | Accepted Risk
- **Target deadline:** [sprint / quarter]
- **Accepted as risk by:** [name + date] (only if Accepted Risk)
```

## Debt Metrics (tracked quarterly)

| Metric | Definition | Target |
|--------|-----------|--------|
| Debt ratio | Debt SPs / total backlog SPs | Stable or decreasing |
| Debt age | Avg time from registration to resolution by severity | Critical < 2 weeks |
| Introduction rate | New debts per sprint | Below resolution rate |
| Resolution rate | Debts resolved per sprint | Above introduction rate |
| Critical/High backlog | Count of open Critical + High | = 0 |
