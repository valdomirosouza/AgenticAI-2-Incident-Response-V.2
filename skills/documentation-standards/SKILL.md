---
name: documentation-standards
description: Defines and maintains the documentation artifacts required for every service — dependency manifests, SBOM, API specs, changelogs, README, and the mandatory minimum documentation set. Use when creating or updating service documentation, writing a dependency manifest, generating or validating an SBOM, documenting a new API, writing or updating a README, or performing a documentation review as part of PRR. Also use when asked about requirements.txt standards, dependency tracking, or service documentation completeness.
---

# Documentation Standards

## Core principle
Documentation is a production artifact. Outdated documentation is worse than no documentation — it causes incidents.

## Contents
- Mandatory documentation set per service
- dependency-manifest.yaml (three-layer standard)
- SBOM generation
- API documentation standard
- README minimum structure
- Documentation review checklist (PRR)

---

## Mandatory Documentation per Service

| Document | Location | Update trigger |
|----------|----------|---------------|
| README.md | Repo root | Every release |
| dependency-manifest.yaml | /docs/ | Every dependency change |
| CHANGELOG.md | Repo root | Every release |
| API Spec (OpenAPI/AsyncAPI) | /docs/api/ | Every contract change |
| Runbook | /docs/runbook/ | Every new incident scenario |
| ADRs | /docs/adr/ | Every architectural decision |
| SLO definition (slo.yaml) | /slo/ | Quarterly or on target change |
| Threat Model | /docs/security/ | Every major release |
| eol-inventory.yaml | /docs/ | Quarterly |
| SBOM | /docs/ or registry | Every build (auto-generated) |

---

## dependency-manifest.yaml — Three-Layer Standard

**Layer 1:** Language-native lockfile (pinned versions — no ranges)
```
# Python: requirements.txt
fastapi==0.109.0
uvicorn==0.27.0
opentelemetry-sdk==1.22.0
```

**Layer 2:** Enriched manifest

```yaml
# dependency-manifest.yaml
service: payment-service
version: "1.4.2"
last_updated: "2024-01-15"
owner: team-payments

runtime_dependencies:
  - name: fastapi
    version: "0.109.0"
    purpose: "REST API web framework"
    license: MIT
    cve_status: clean        # Updated by CI
    end_of_life: null

  - name: stripe-python
    version: "7.8.0"
    purpose: "Payment gateway integration"
    license: MIT
    external_service: true
    data_classification: L1_CRITICAL
    dpa_reference: "legal/dpa/stripe-2024.pdf"

infra_dependencies:
  - name: PostgreSQL
    version: "15.4"
    purpose: "Primary database"
    managed: true            # RDS
    backup_policy: "daily, 30d retention"

ai_dependencies:
  - name: Anthropic API
    model: "claude-sonnet-4-6"
    purpose: "Transaction categorization suggestions"
    data_sent: "transaction_description (anonymized)"
    dpa_reference: "legal/dpa/anthropic-2024.pdf"
    pii_sent: false

third_party_services:
  - name: PagerDuty
    purpose: "Alerting and on-call management"
    data_classification: L3_RESTRICTED
```

**Layer 3:** SBOM (auto-generated in CI)

```bash
# Generate SBOM with Syft
syft . -o cyclonedx-json > sbom.json

# Sign with Cosign and publish alongside artifact
cosign attach sbom --sbom sbom.json registry.example.com/service:tag
```

---

## API Documentation Standard

```yaml
api_documentation:
  format: OpenAPI 3.1 (REST) | AsyncAPI 2.6 (events/queues)
  location: /docs/api/
  versioning: One spec file per major version (openapi-v1.yaml, openapi-v2.yaml)

  required_per_endpoint:
    - summary and description
    - request/response schemas with examples
    - error codes with descriptions
    - authentication requirements
    - rate limiting information
    - deprecation notice (if deprecated)

  generated_from_code: preferred  # FastAPI, Spring Boot auto-generate
  manually_maintained: only when framework does not support generation
```

---

## README Minimum Structure

```markdown
# [Service Name]

> One-sentence description of what this service does.

## Quick Start
[Minimum steps to run locally]

## Architecture
[High-level diagram or link to ADR/spec]

## Configuration
[All environment variables — reference .env.example]

## API
[Link to OpenAPI spec or Swagger UI]

## Observability
[Links to dashboards, alerts, and runbook]

## Dependencies
[Link to dependency-manifest.yaml]

## SLO
[Link to slo.yaml with current targets]

## On-call and Incidents
[Escalation path + link to runbook]

## Contributing
[Link to CONTRIBUTING.md]

## Changelog
[Link to CHANGELOG.md]
```

---

## Documentation Review Checklist (PRR)

```markdown
### Documentation PRR Gate
- [ ] README.md reflects current state of the service
- [ ] dependency-manifest.yaml updated with all dependencies
- [ ] All dependency versions pinned (no open ranges)
- [ ] SBOM generated and signed
- [ ] API spec (OpenAPI/AsyncAPI) reflects current contract
- [ ] CHANGELOG updated for this release
- [ ] Runbook exists and was reviewed by someone outside the team
- [ ] ADR index updated (all architectural decisions documented)
- [ ] slo.yaml committed and SLO targets validated
- [ ] Threat model updated (if major release)
- [ ] eol-inventory.yaml reviewed (quarterly)
- [ ] .env.example reflects all current required variables
- [ ] No documentation references deprecated APIs or removed features
```
