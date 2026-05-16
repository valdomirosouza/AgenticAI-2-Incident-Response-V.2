# Agent Skills — Enterprise Engineering Standards

> **AI-Assisted Development Standard — Enterprise Edition**
> A collection of expert agent skills covering SRE, DevSecOps, Security, Architecture, and Governance for enterprise-grade software engineering.

These skills encode hard-won engineering standards into structured, reusable knowledge that AI agents can discover and apply consistently across projects. Each skill is self-contained, follows the [Anthropic Agent Skills best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices), and is aligned with Google SRE, OWASP, LGPD/GDPR, and enterprise compliance frameworks.

---

## Skill Index

| Skill | Domain | Triggers |
|-------|--------|---------|
| [sre-foundations](#sre-foundations) | SRE | PRR, TOIL, incidents, postmortem, error budget |
| [observability-engineering](#observability-engineering) | Observability | Golden Signals, SLI/SLO, OTel, logs, metrics, traces |
| [large-system-design](#large-system-design) | Architecture | NALSD, capacity planning, resilience, cascading failures |
| [devsecops](#devsecops) | Security | SAST, DAST, OWASP, PII, CI/CD security gates |
| [security-by-design](#security-by-design) | Security | Threat modeling, STRIDE, Privacy by Design, DPIA |
| [ai-governance](#ai-governance) | Governance | AI ethics, responsibility, prompt security, LLM observability |
| [spec-driven-development](#spec-driven-development) | Process | SDD cycle, spec template, definition of done |
| [sdlc-governance](#sdlc-governance) | Process | RFC/CAB, tech debt, deprecation, EOL |
| [managing-adrs](#managing-adrs) | Architecture | ADR creation, lifecycle, archaeology, quarterly review |
| [credentials-and-secrets](#credentials-and-secrets) | Security | Vault, least privilege, .gitignore, JIT access |
| [cicd-pipeline](#cicd-pipeline) | DevOps | Pipeline stages, quality gates, canary, SBOM |
| [documentation-standards](#documentation-standards) | Documentation | dependency-manifest, SBOM, API spec, README, PRR docs |

---

## Skill Descriptions

### sre-foundations
**Domain:** Site Reliability Engineering
**Directory:** `sre-foundations/`

Applies Google SRE principles to production systems — Production Readiness Reviews (PRR), TOIL identification and reduction, incident lifecycle management, and blameless postmortems. Includes the complete PRR checklist, incident severity matrix, error budget policy, and runbook + postmortem templates.

**Reference files:**
- `prr-checklist.md` — Full PRR gate with all verification domains
- `incident-response.md` — Incident lifecycle, runbook template, blameless postmortem, MTTD/MTTR tracking

**Use when:** Preparing a service for production, evaluating operational maturity, responding to incidents, writing postmortems, or managing error budgets.

---

### observability-engineering
**Domain:** Observability
**Directory:** `observability-engineering/`

Implements production observability using the three pillars (logs, metrics, traces), the four Golden Signals, and OpenTelemetry standards. Defines and monitors SLI/SLO/SLA with error budget policies, and provides instrumentation code patterns for Python and Go.

**Reference files:**
- `sli-slo-templates.md` — `slo.yaml` template, burn rate alert config, error budget policy
- `instrumentation-guide.md` — OTel code patterns (Python/Go), Collector config, instrumentation rules

**Use when:** Adding observability to a service, defining SLOs, configuring alerts, designing dashboards, setting up telemetry pipelines, or asked about Golden Signals, error budgets, or OTel.

---

### large-system-design
**Domain:** Architecture / SRE
**Directory:** `large-system-design/`

Applies Google SRE NALSD methodology and principles from "Building Secure and Reliable Systems" to design scalable, reliable, and understandable distributed systems. Covers the full NALSD 5-step process, Design for Understandability, Resilience by Design, Overload Handling (load shedding, backpressure), Cascading Failure Prevention, and Design for Evolvability.

**Reference files:**
- `nalsd-templates.md` — Back-of-envelope template, bottleneck analysis, pre-PRR checklist
- `resilience-patterns.md` — Code implementations: retry/backoff, circuit breaker, Kubernetes probes, cache stampede prevention

**Use when:** Designing a new service or architecture, performing capacity planning, identifying bottlenecks, reviewing system resilience, or preparing for PRR. Also for blast radius analysis, circuit breakers, load shedding, or CAP theorem tradeoffs.

---

### devsecops
**Domain:** Security / DevOps
**Directory:** `devsecops/`

Integrates security into CI/CD pipelines using SAST, DAST, SCA, container scanning, and OWASP controls. Implements PII protection, data anonymization aligned with LGPD/GDPR, and secure coding practices across all layers of the stack.

**Reference files:**
- `owasp-controls.md` — OWASP Top 10 with required controls per vulnerability; ASVS level mapping
- `pii-anonymization.md` — Anonymization techniques by context, PIIAnonymizer code, synthetic data generation, data retention policy, LGPD/GDPR legal bases

**Use when:** Configuring security tooling in pipelines, reviewing code for vulnerabilities, implementing OWASP Top 10 controls, handling PII, anonymizing sensitive content, or assessing LGPD/GDPR/PCI-DSS compliance.

---

### security-by-design
**Domain:** Security Architecture
**Directory:** `security-by-design/`

Embeds security as a structural property of systems from the spec phase — not as a layer added post-implementation. Covers the Secure SDLC (security gates per development phase), Threat Modeling (STRIDE/LINDDUN), Secure by Default (fail-safe, deny-all, HTTP headers), Defense in Depth (8-layer model), Privacy by Design (LGPD Art. 46, GDPR Art. 25), and Attack Surface Reduction.

**Reference files:**
- `threat-modeling.md` — STRIDE template, LINDDUN privacy threat modeling, DPIA template
- `privacy-by-design.md` — 7 principles operationalized, data minimization code example, right-to-erasure checklist

**Use when:** Reviewing or writing a spec for security completeness, performing threat modeling, designing access control, evaluating privacy impact (DPIA), or verifying Security by Design compliance.

---

### ai-governance
**Domain:** AI Governance / Ethics
**Directory:** `ai-governance/`

Applies AI responsibility, ethics, and governance standards to systems that use or are built with artificial intelligence. Covers human accountability, AI risk classification (High/Medium/Low), ethical principles checklist (transparency, fairness, privacy, auditability), prompt security (injection prevention, versioning), and LLM observability. Aligned with EU AI Act requirements.

**Reference files:** *(All content in SKILL.md — concise single-file skill)*

**Use when:** Designing AI-assisted features, reviewing AI usage in systems, classifying AI risk level, implementing prompt versioning, auditing AI outputs, or assessing EU AI Act or organizational AI policy compliance.

---

### spec-driven-development
**Domain:** Engineering Process
**Directory:** `spec-driven-development/`

Applies the Spec-Driven Development (SDD) methodology — writing, reviewing, and approving formal specs before any code is written, by humans or AI. Covers the full SDD cycle, Definition of Done, responsible AI use in development, and the integration points with Change Management, Technical Debt, and Deprecation processes.

**Reference files:**
- `spec-template.md` — Complete spec template with all required sections including NALSD, observability, security, and approval workflow

**Use when:** Starting any new feature or service, structuring a technical proposal, reviewing a spec for completeness, integrating AI in development, or evaluating work readiness for implementation.

---

### sdlc-governance
**Domain:** Engineering Process / Governance
**Directory:** `sdlc-governance/`

Manages the full software lifecycle beyond development — formal change control (RFC/CAB), technical debt tracking and prioritization with severity SLAs, and service/API/dependency deprecation and end-of-life processes. Includes the CAB governance model and change freeze policy.

**Reference files:**
- `rfc-template.md` — RFC template + CAB governance (composition, cadence, approval criteria)
- `tech-debt-process.md` — DEBT registration template, severity policy, engineering budget rule, metrics
- `deprecation-process.md` — 4-phase deprecation process, Deprecation Notice template, decommission checklist, `eol-inventory.yaml` template

**Use when:** Proposing a production change, managing CAB sessions, registering technical debt, planning a service deprecation, managing API sunset, or handling EOL of a runtime or library.

---

### managing-adrs
**Domain:** Architecture Documentation
**Directory:** `managing-adrs/`

Creates, maintains, and retrieves Architecture Decision Records (ADRs) — the permanent, immutable record of architectural reasoning. Covers writing new ADRs, recovering historical decisions through archaeology (git, PRs, wikis, interviews), managing ADR lifecycle states (Draft → Proposed → Accepted → Superseded), quarterly review cadence, and integration with the SDD/PRR workflow.

**Reference files:**
- `adr-template.md` — Full 8-section ADR template with all required fields
- `adr-examples.md` — Two filled ADR examples: new decision (PostgreSQL choice) and revision superseding previous ADR (local cache → Redis)

**Use when:** Making an architectural decision, recovering past decisions from git history, updating ADR status, conducting quarterly ADR reviews, or referencing architectural decisions during spec or PRR reviews.

---

### credentials-and-secrets
**Domain:** Security / Infrastructure
**Directory:** `credentials-and-secrets/`

Enforces a zero-secrets-in-code policy through credential vault integration, least privilege access across all layers (cloud IAM, Kubernetes RBAC, databases, CI/CD pipelines, human access), pre-commit secret detection hooks, and `.gitignore` standards that prevent accidental exposure of secrets and PII.

**Reference files:**
- `least-privilege.md` — Per-layer policies (Cloud IAM, K8s RBAC, DB, CI/CD, JIT human access) with code examples and checklists
- `gitignore-template.md` — Enterprise `.gitignore` covering credentials, PII (LGPD/GDPR/PCI-DSS), security tool outputs, logs, AI context, local configs

**Use when:** Configuring vault integration, designing IAM/RBAC policies, setting up pre-commit hooks, auditing permissions, implementing JIT access, configuring CI/CD OIDC auth, or reviewing repository secret hygiene.

---

### cicd-pipeline
**Domain:** DevOps
**Directory:** `cicd-pipeline/`

Defines and validates CI/CD pipeline standards — mandatory stage sequence (validate → test → security → build → staging → production), all-blocking quality gates, branch strategy with protection rules, deployment strategies (canary, blue-green, feature flags), artifact signing (Cosign/SLSA), and SBOM generation.

**Reference files:** *(All content in SKILL.md — comprehensive single-file skill)*

**Use when:** Designing or reviewing a CI/CD pipeline, configuring quality gates, defining branch protection rules, setting up canary deployments, implementing SBOM generation, or integrating Change Management types (Standard/Normal/Emergency) into the pipeline.

---

### documentation-standards
**Domain:** Documentation
**Directory:** `documentation-standards/`

Defines and maintains the complete documentation artifact set required for every service — the three-layer dependency standard (`requirements.txt` + `dependency-manifest.yaml` + SBOM), API documentation (OpenAPI/AsyncAPI), README minimum structure, and the documentation review checklist for PRR.

**Reference files:** *(All content in SKILL.md — concise reference skill)*

**Use when:** Creating or updating service documentation, writing a dependency manifest, generating or validating a SBOM, documenting a new API, writing a README, or performing documentation review as part of PRR.

---

## Repository Structure

```
agent-skills/
├── README.md
├── sre-foundations/
│   ├── SKILL.md
│   ├── prr-checklist.md
│   └── incident-response.md
├── observability-engineering/
│   ├── SKILL.md
│   ├── sli-slo-templates.md
│   └── instrumentation-guide.md
├── large-system-design/
│   ├── SKILL.md
│   ├── nalsd-templates.md
│   └── resilience-patterns.md
├── devsecops/
│   ├── SKILL.md
│   ├── owasp-controls.md
│   └── pii-anonymization.md
├── security-by-design/
│   ├── SKILL.md
│   ├── threat-modeling.md
│   └── privacy-by-design.md
├── ai-governance/
│   └── SKILL.md
├── spec-driven-development/
│   ├── SKILL.md
│   └── spec-template.md
├── sdlc-governance/
│   ├── SKILL.md
│   ├── rfc-template.md
│   ├── tech-debt-process.md
│   └── deprecation-process.md
├── managing-adrs/
│   ├── SKILL.md
│   ├── adr-template.md
│   └── adr-examples.md
├── credentials-and-secrets/
│   ├── SKILL.md
│   ├── least-privilege.md
│   └── gitignore-template.md
├── cicd-pipeline/
│   └── SKILL.md
└── documentation-standards/
    └── SKILL.md
```

---

## Standards and Frameworks Referenced

| Framework | Skills |
|-----------|--------|
| Google SRE Book + SRE Workbook | sre-foundations, large-system-design, observability-engineering |
| Building Secure and Reliable Systems (Google) | large-system-design, security-by-design |
| OWASP Top 10 + ASVS | devsecops, security-by-design |
| LGPD (Lei 13.709) + GDPR (Art. 25, 46) | devsecops, security-by-design, credentials-and-secrets |
| EU AI Act | ai-governance |
| NIST CSF | security-by-design, credentials-and-secrets |
| SLSA (Supply-chain Levels for Software Artifacts) | cicd-pipeline |
| OpenTelemetry (OTel) | observability-engineering |
| ISO/IEC 27001 | security-by-design, credentials-and-secrets |
| PCI-DSS | devsecops, credentials-and-secrets |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-16 | Initial release — 12 expert skills covering full enterprise engineering lifecycle |

---

*Generated with AI assistance — Claude Sonnet 4.6 | Human review applied to all content.*
*Skills follow [Anthropic Agent Skills best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices).*
