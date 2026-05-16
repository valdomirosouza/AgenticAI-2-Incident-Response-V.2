# Spec Template

```markdown
# SPEC-[ID]: [Component / Feature Name]

## Metadata
- **ID:** SPEC-YYYY-NNN
- **Status:** Draft | Review | Approved | Deprecated
- **Author:** [name]
- **Reviewers:** [list]
- **Created:** YYYY-MM-DD
- **Version:** 1.0.0
- **AI-assisted:** Yes/No — [model, version, prompt ID]

## Context and Problem
> Why does this exist? What problem does it solve?
> Be specific: "needs to scale" is not context; "processes 50k req/s and DB hits 80% CPU at peak" is.

## Scope
### Includes
- ...
### Out of Scope
- ...

## Functional Requirements
| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| RF-01 | ... | Must Have | ... |
| RF-02 | ... | Should Have | ... |

## Non-Functional Requirements
| ID | Category | Requirement | Metric |
|----|----------|-------------|--------|
| RNF-01 | Performance | p99 latency < 200ms | Prometheus + Grafana |
| RNF-02 | Availability | SLO 99.9% | SLI measured over 30d |
| RNF-03 | Security | No OWASP Top 10 findings | SAST + DAST |
| RNF-04 | Privacy | PII L1/L2 encrypted at field level | Security audit |

## Architecture
> Diagram, design decisions, ADRs referenced.
> Include NALSD back-of-envelope estimates (see large-system-design skill).

### Back-of-Envelope Summary
- Peak RPS: [N]
- p99 latency budget: [Xms] (breakdown per component)
- Storage: [X GB/day], [Y TB total]
- Instances needed: [N + 2 redundancy]

## Observability
- **Logs:** structured JSON; required fields: [trace_id, span_id, service, level, message, timestamp]
- **Metrics:** [list key metrics and labels]
- **Traces:** [required spans]
- **SLI:** [exact definition]
- **SLO:** [target + window]

## Security
- PII involved: Yes/No — classification: [L1/L2/L3/L4]
- Anonymization mechanism: [describe]
- Credentials: [vault used]
- Communication: mTLS / TLS 1.3
- Threat model: [reference to STRIDE analysis]
- OWASP review: [checklist referenced]
- DPIA required: Yes/No — [reference if yes]

## Dependencies
> Reference to `dependency-manifest.yaml` (see documentation-standards skill)

## Risks and Mitigations
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|

## Approval
| Role | Name | Date | Status |
|------|------|------|--------|
| Tech Lead | | | |
| Security | | | |
| Architect | | | |
| DPO (if PII L1/L2) | | | |
```
