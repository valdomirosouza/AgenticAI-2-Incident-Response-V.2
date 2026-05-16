---
name: spec-driven-development
description: Applies the Spec-Driven Development (SDD) methodology — writing, reviewing, and approving formal specs before any code is written, by humans or AI. Use when starting any new feature or service, structuring a technical proposal, reviewing a spec for completeness, integrating AI assistance into the development process, or evaluating whether a piece of work is ready to be implemented. Also use when asked about SDD workflow, spec templates, definition of done, or responsible AI use in development.
---

# Spec-Driven Development (SDD)

## Core rule
**No code without an approved spec.** This applies to human-written code and AI-generated code alike. The spec is the contract; the code is the implementation.

## Contents
- SDD cycle (with AI)
- Spec template → [spec-template.md](spec-template.md)
- Definition of Done
- AI use policy in SDD
- SDLC extensions: Change Management, Tech Debt, Deprecation/EOL

---

## SDD Cycle

```
[PROBLEM]
    ↓
[SPEC DRAFT]       ← AI suggests structure; human decides content
    ↓
[TECH REVIEW]      ← Tech Lead / Architect validates
    ↓
[SPEC APPROVED]    ← Locked source of truth
    ↓
[IMPLEMENTATION]   ← AI generates; human reviews and approves
    ↓
[HARNESS / TESTS]  ← Automated + AI-assisted validation
    ↓
[CI/CD PIPELINE] → [DEPLOY] → [OBSERVABILITY]
```

---

## Definition of Done

A work item is **Done** only when ALL are true:

- [ ] Spec approved by Tech Lead or Architect
- [ ] Unit, integration, and contract tests with ≥ 80% coverage
- [ ] CI/CD pipeline green (SAST + DAST + lint + build)
- [ ] Observability implemented (structured logs, metrics, traces)
- [ ] SLI/SLO defined and monitored
- [ ] Security review complete (no open CRITICAL/HIGH findings)
- [ ] Documentation updated (`dependency-manifest.yaml`, ADR, Runbook)
- [ ] All credentials in vault — zero hardcoded secrets
- [ ] AI Governance review (when AI is a system component)

---

## AI Use Policy in SDD

| Phase | AI Can | AI Cannot |
|-------|--------|-----------|
| Spec Draft | Suggest structure, fill boilerplate, identify gaps | Approve the spec |
| Implementation | Generate code, tests, documentation | Merge without human review |
| Security Review | Identify potential vulnerabilities | Classify final risk |
| Incident Response | Suggest diagnosis, runbook steps | Execute production actions without approval |

**Traceability rule:** All AI-generated artifacts must include the traceability header (see ai-governance skill).

---

## SDLC Extensions

SDD covers the development cycle. Three additional processes complete the full lifecycle:

### Change Management (RFC/CAB)
Every production change needs a formal Request for Change:
- **Standard:** Pre-approved, low risk → automated by pipeline
- **Normal:** Planned, risk assessed → CAB weekly review
- **Emergency:** Urgent (active incident) → simplified approval, async

RFC template and CAB governance → see `sdlc-governance` skill.

### Technical Debt
Any deviation from this standard that cannot be fixed in the current PR becomes a registered `DEBT-YYYY-NNN`:
- Severity CRITICAL/HIGH: must be resolved in current or next sprint
- Budget: minimum 20% of engineering capacity dedicated to debt resolution

### Deprecation / EOL
All services, APIs, and dependencies have a formal end-of-life cycle:
- External APIs: minimum 6 months notice before sunset
- Internal APIs: minimum 3 months notice
- Runtimes: upgrade before upstream EOL date

Full process → see `sdlc-governance` skill.

---

## Spec Template

Full template with all required sections → [spec-template.md](spec-template.md)

Minimum required sections for spec approval:
1. Metadata (ID, status, author, AI usage flag)
2. Context and Problem
3. Scope (includes / excludes)
4. Functional Requirements with acceptance criteria
5. Non-Functional Requirements (performance, availability, security)
6. Architecture with NALSD back-of-envelope
7. Observability (logs schema, metrics, SLI/SLO)
8. Security (STRIDE, PII, credentials, communication)
9. Dependencies (`dependency-manifest.yaml` reference)
10. Risks and Mitigations
11. Approval signatures
