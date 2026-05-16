---
name: managing-adrs
description: Creates, maintains, and retrieves Architecture Decision Records (ADRs) — the permanent, immutable record of architectural reasoning. Covers writing new ADRs, recovering historical decisions (archaeology), managing ADR lifecycle states, and integrating ADRs into the SDD workflow. Use when making an architectural decision, reviewing whether a decision needs an ADR, recovering past decisions from git history or wikis, updating an ADR's status, conducting quarterly ADR reviews, or referencing past decisions during spec or PRR reviews.
---

# Managing ADRs

## Core rule
ADRs are **immutable after acceptance**. Never edit an accepted ADR — create a new one that supersedes it. Never delete ADRs (not even rejected ones).

## Contents
- What requires an ADR
- Repository structure and index
- ADR lifecycle (states and transitions)
- Recovering historical ADRs (archaeology)
- Mandatory inventory checklist
- ADR template → [adr-template.md](adr-template.md)
- Filled examples → [adr-examples.md](adr-examples.md)
- Integration with SDD cycle

---

## What Requires an ADR

**Requires an ADR:**
- Database / message broker choice
- Authentication / authorization strategy
- Sync vs async communication; REST vs gRPC vs GraphQL
- Deployment strategy (canary, blue-green, feature flags)
- CAP theorem tradeoff (consistency vs availability)
- Service boundaries and domain limits
- Primary framework or runtime adoption
- Data or schema migration strategy
- Security decision with systemic impact
- Revision or reversal of a previous ADR

**Does NOT require an ADR:**
- Minor utility library choice
- Variable naming conventions (handled by linter)
- Bugfix without architectural impact
- Internal refactoring without contract change

---

## Repository Structure

```
/docs/adr/
  README.md           ← Navigable index of all ADRs
  /active/            ← ADRs in effect
  /superseded/        ← Replaced ADRs (never delete)
  /proposed/          ← ADRs under review
  /deprecated/        ← ADRs whose context no longer exists
```

**README.md** must be kept current and include:
- Table of active ADRs (ID, title, area, date, author)
- Table of superseded ADRs with link to successor
- Thematic filters (security, data, communication, observability, infra)

---

## ADR Lifecycle

| Status | Meaning | Editable? |
|--------|---------|-----------|
| Draft | In progress — not submitted for review | Yes |
| Proposed | Submitted for team review | Comments only |
| Accepted | Approved — current decision | **Never** |
| Rejected | Evaluated and not adopted — preserve with reasons | **Never** |
| Superseded | Replaced by a newer ADR | **Never** |
| Deprecated | Context that motivated it no longer exists | **Never** |

**Superseding an ADR:**
1. Create new ADR (Draft) documenting the revised decision
2. Reference the old ADR explicitly
3. Follow normal approval process
4. After new ADR is Accepted: mark old one Superseded with link to new
5. Move old ADR to `/superseded/` — never delete

---

## ADR Archaeology — Recovering Historical Decisions

For systems without existing ADRs, recover past decisions before writing new ones.

**Sources to consult:**
```
□ git log --all (commit messages with implicit decisions)
□ Old Pull Requests (design discussions in comments)
□ Closed issues with "architecture" or "design" labels
□ Wikis, Confluence, Notion — existing informal documentation
□ Slack/Teams: search "we decided", "we chose", "we'll use"
□ Interviews with long-tenured team members
□ The code itself (reveals what was chosen)
```

**Retroactive ADR marker:**
```markdown
> ⚠️ RETROACTIVE ADR — This decision was made on [estimated date] but
> was not formally documented at the time. Reconstructed on [date]
> from [source: git log / PR #NNN / wiki / interview with @name].
> Reviewed and validated by [name] on [date].
```

**Minimum ADR inventory checklist** — every mature production system must have ADRs covering:

```
Data & Storage:
  □ Why this database? (SQL vs NoSQL, specific engine)
  □ ORM vs raw SQL decision
  □ Backup and recovery strategy

Communication:
  □ Sync vs async for critical operations
  □ REST vs gRPC vs GraphQL
  □ Messaging protocol (Kafka, RabbitMQ, SQS)
  □ API versioning strategy

Security:
  □ Authentication and authorization strategy
  □ Session and token management
  □ Encryption strategy for sensitive data
  □ Inter-service trust model (mTLS, JWT, API Key)

Architecture:
  □ Domain boundaries and bounded contexts
  □ Deployment strategy (canary, blue-green)
  □ Monolith vs microservices decision
  □ Cache strategy
  □ Primary framework decision

Observability:
  □ Observability stack (Prometheus, Grafana, OTel)
  □ Trace sampling strategy

Infrastructure:
  □ Cloud provider choice
  □ Containerization and orchestration
  □ IaC tool (Terraform, Pulumi, CDK)
```

---

## Quarterly ADR Review

**Agenda (1h, quarterly):**

1. **Scan active ADRs (20 min):** For each, ask: Is the premise still valid? Is the technology still supported and secure? Did a CVE, EOL, or ecosystem change occur?

2. **Triage review candidates (15 min):** ADRs > 2 years old with active technology; ADRs with associated tech debt; ADRs whose context changed.

3. **Identify undocumented decisions (10 min):** Did the team make significant decisions this quarter without an ADR? Are there approved specs with architectural decisions missing an ADR?

4. **Actions (15 min):** Assign owners and deadlines for new/revision ADRs.

---

## ADR Template

Full template with all 8 sections → [adr-template.md](adr-template.md)

Filled examples (new decision + superseding revision) → [adr-examples.md](adr-examples.md)

**Required sections for ADR approval:**
1. Metadata (ID, status, area, AI assistance flag)
2. Context and Problem (with explicit forces and constraints)
3. Decision (clear affirmative statement + application scope)
4. Alternatives Considered (including "do nothing")
5. Consequences (positive, negative/trade-offs, risk table)
6. Future Review Criteria (conditions that make this ADR obsolete)
7. References
8. Approval signatures
