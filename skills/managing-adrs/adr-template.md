# ADR Template

```markdown
# ADR-[NNNN]: [Concise Decision Title]
> Title must be an affirmative statement describing the decision, not the problem.
> Good: "Use PostgreSQL as primary database"
> Bad: "Database decision"

---

## Metadata
| Field | Value |
|-------|-------|
| **ID** | ADR-YYYY-NNNN |
| **Status** | Draft → Proposed → Accepted |
| **Area** | Data / Communication / Security / Architecture / Observability / Infra / Deploy |
| **Author** | [name + @handle] |
| **Reviewers** | [list] |
| **Created** | YYYY-MM-DD |
| **Approved** | YYYY-MM-DD |
| **Supersedes** | ADR-NNNN (if this replaces another) |
| **Superseded by** | — (filled when this is replaced) |
| **Related spec** | SPEC-YYYY-NNN |
| **AI-assisted** | Yes / No — [model, version, AI role] |

---

## 1. Context and Problem *
> Current state, technical and business context, driving forces.
> Be specific — numbers over generalizations.

**Driving forces:**
- [force 1: e.g., latency < 100ms at p99]
- [force 2: e.g., team without expertise in X]

**Constraints:**
- [constraint 1]

---

## 2. Decision *
> Clear, direct statement. Active voice: "We will adopt X because Y."

**Decision:** [clear, direct statement]

**Scope:**
- Applies to: [components / teams / contexts]
- Does not apply to: [explicit exceptions]

---

## 3. Alternatives Considered *
| Alternative | Pros | Cons | Reason for Rejection |
|-------------|------|------|--------------------|
| **[Option A — chosen]** | [pros] | [cons] | — (chosen) |
| [Option B] | [pros] | [cons] | [why not] |
| "Do nothing" | [pros] | [cons] | [why not] |

> "Do nothing" must always be an explicit alternative.

---

## 4. Consequences *

### Positive
- [benefit 1]

### Negative / Trade-offs
- [trade-off 1]

### Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|

### Tech Debt Introduced
- [DEBT-NNNN created]: [description] — or "None"

---

## 5. Future Review Criteria *
This ADR should be revisited if:
- [ ] [condition 1: e.g., throughput exceeds 500k req/s]
- [ ] [condition 2: e.g., technology X reaches EOL]
- [ ] After 2 years without review (default minimum)

---

## 6. References
- [Official documentation link]
- [Benchmark or PoC link]
- [PR or issue discussion link]

---

## 7. AI Assistance (when applicable)
| Field | Value |
|-------|-------|
| **AI used** | [model and version] |
| **AI role** | [e.g., alternatives analysis, trade-off analysis] |
| **Output reviewed by** | [engineer name] |
| **Final decision made by** | [name — always human] |

---

## 8. Approval *
| Role | Name | Date | Decision |
|------|------|------|---------|
| Author | | | Proposes |
| Tech Lead | | | ☐ Approve ☐ Reject ☐ Request revision |
| Architect (systemic impact) | | | ☐ Approve ☐ Reject |
| SecOps (security impact) | | | ☐ Approve ☐ Reject |
| DPO (personal data impact) | | | ☐ Approve ☐ Reject |
```
