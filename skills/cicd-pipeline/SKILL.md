---
name: cicd-pipeline
description: Defines and validates CI/CD pipeline standards — stage sequencing, quality gates, branch strategy, deployment strategies (canary, blue-green), and artifact signing. Use when designing or reviewing a CI/CD pipeline, configuring quality gates, defining branch protection rules, setting up canary deployments, implementing SBOM generation, or ensuring a pipeline meets enterprise security and reliability standards.
---

# CI/CD Pipeline

## Contents
- Mandatory pipeline stages (in order)
- Quality gates — all blocking
- Branch strategy
- Deployment strategies
- Artifact integrity (signing + SBOM)

---

## Mandatory Pipeline Stages

```yaml
stages:
  - name: validate
    steps:
      - lint                      # Language-specific
      - type-check
      - dependency-audit          # Known vulnerability scan
      - secret-detection          # gitleaks / truffleHog
      - spec-compliance-check     # Validates AI traceability header

  - name: test
    steps:
      - unit-tests                # Coverage ≥ 80%
      - integration-tests
      - contract-tests            # Pact / OpenAPI
      - observability-validation  # Log schema, metric labels, trace propagation

  - name: security
    steps:
      - SAST                      # Semgrep / SonarQube / Checkmarx
      - SCA                       # OWASP Dependency Check / Snyk
      - container-scan            # Trivy / Grype
      - IaC-scan                  # Checkov / tfsec
      - license-check             # FOSSA / license-checker

  - name: build
    steps:
      - build-artifact
      - sign-artifact             # Cosign / Sigstore (SLSA)
      - generate-SBOM             # Syft / CycloneDX
      - push-to-registry

  - name: staging-deploy
    environment: staging
    steps:
      - deploy
      - smoke-tests
      - DAST                      # OWASP ZAP full scan
      - performance-baseline

  - name: production-deploy
    environment: production
    requires: [manual-approval, RFC-approved]
    strategy: canary              # 5% → 25% → 100%
    steps:
      - deploy
      - golden-signal-monitoring  # 15 min observation window
      - auto-rollback-if-slo-breach
```

---

## Quality Gates — All Blocking

| Gate | Criterion | Blocks |
|------|-----------|--------|
| Lint | Zero critical rule warnings | Yes |
| Tests | Coverage ≥ 80%, zero failures | Yes |
| SAST | Zero CRITICAL/HIGH findings | Yes |
| Secrets | Zero secrets detected | Yes |
| Container | Zero critical CVEs in base image | Yes |
| SBOM | Generated and signed | Yes |
| Human review | Minimum 1 reviewer | Yes |
| DAST | Zero OWASP Top 10 critical findings | Yes (staging) |
| Error budget | Budget > 10% | Yes (production) |
| RFC | RFC approved for Normal/Emergency changes | Yes (production) |

---

## Branch Strategy

```
main ──────────────────────────────────────── (production — full protection)
  └── release/YYYY-MM-DD ─────────────────── (staging)
        └── feature/SPEC-NNN-description ─── (development)
        └── fix/SPEC-NNN-description ──────── (bugfix)
        └── hotfix/SPEC-NNN-description ───── (hotfix — direct merge to main)
```

**Branch protection rules (main):**
- Require PR — no direct push
- Minimum 1 approved review
- All status checks passing
- No force-push
- Require linear history

---

## Deployment Strategies

**Canary (default for production):**
```
Step 1: 5% of traffic → new version
  └── Monitor Golden Signals for 15 min
Step 2: 25% → if SLO maintained
  └── Monitor for 15 min
Step 3: 100% → if SLO maintained
Auto-rollback: if error rate > SLO threshold at any step
```

**Blue-Green (for stateful services or DB migrations):**
```
1. Deploy new version (green) alongside current (blue)
2. Run smoke tests on green
3. Switch load balancer to green
4. Keep blue running for 30 min (fast rollback)
5. Decommission blue
```

**Feature flags (for all new features):**
- Deploy to 100% of instances with flag OFF
- Enable progressively per user segment / % of traffic
- Flag owner and expiry date required

---

## Artifact Integrity

```bash
# Generate SBOM
syft . -o cyclonedx-json > sbom.json

# Sign artifact with Cosign (SLSA provenance)
cosign sign --key cosign.key registry.example.com/service:sha256-...

# Verify on deploy
cosign verify --key cosign.pub registry.example.com/service:sha256-...
```

**SLSA target:** Level 3 (hermetic builds, signed provenance, auditable build process)

---

## Change Type Integration

```yaml
# Pipeline behavior per change type
standard_change:
  label: "standard-change"
  approval: Automatic if pipeline green and spec referenced
  restriction: Deploy only in defined windows (Mon-Thu, 10:00-17:00)

normal_change:
  label: "normal-change"
  approval: RFC approved by CAB required before merge
  block: Pipeline rejects deploy without RFC_ID in commit message

emergency_change:
  label: "emergency-change"
  approval: TL + SecOps async approval in #cab-emergency
  audit: Emergency RFC generated retroactively within 24h
  postmortem: Mandatory even if change successful
```
