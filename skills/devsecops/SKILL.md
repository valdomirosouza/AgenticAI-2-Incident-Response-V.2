---
name: devsecops
description: Integrates security into CI/CD pipelines using SAST, DAST, SCA, container scanning, and OWASP controls. Implements PII protection, data anonymization, and secure coding practices. Use when configuring security tooling in pipelines, reviewing code for security vulnerabilities, implementing OWASP Top 10 controls, handling PII data, anonymizing sensitive content, or assessing compliance with LGPD, GDPR, or PCI-DSS requirements.
---

# DevSecOps

## Contents
- CI/CD security gates (mandatory)
- SAST tooling by language
- DAST configuration
- OWASP Top 10 controls → [owasp-controls.md](owasp-controls.md)
- Secure coding checklist
- PII classification and anonymization → [pii-anonymization.md](pii-anonymization.md)

---

## CI/CD Security Gates — All Blocking

| Gate | Tool | Blocks on |
|------|------|-----------|
| Secret detection | gitleaks, truffleHog | Any secret found |
| SAST | Semgrep, SonarQube | CRITICAL or HIGH findings |
| SCA (dependencies) | OWASP Dependency Check, Snyk | Known CVE CRITICAL/HIGH |
| Container scan | Trivy, Grype | Critical CVEs in base image |
| IaC scan | Checkov, tfsec | CRITICAL misconfigurations |
| License check | FOSSA | Incompatible licenses |
| DAST | OWASP ZAP | OWASP Top 10 HIGH/CRITICAL (staging) |
| SBOM | Syft / CycloneDX | Missing or unsigned SBOM |

---

## SAST — Tools by Language

| Language | Primary | Secondary |
|----------|---------|-----------|
| Python | Semgrep + Bandit | PyLint security rules |
| JavaScript/TypeScript | Semgrep + ESLint security | njsscan |
| Go | Semgrep + gosec | staticcheck |
| Java | SonarQube + SpotBugs | Checkmarx |
| Terraform/IaC | Checkov + tfsec | Terrascan |
| Kubernetes YAML | Kubesec + Polaris | OPA/Gatekeeper |
| Dockerfile | Hadolint + Trivy | Dockle |

---

## DAST — Configuration

```yaml
tool: OWASP ZAP
target: https://staging.[service].internal

scan_types:
  baseline_scan: "Passive — every PR"
  full_scan:     "Active — every release"
  api_scan:      "OpenAPI spec imported — focus on endpoints"

blocking_findings:
  - OWASP Top 10 (A01–A10) with severity HIGH/CRITICAL

reports:
  formats: [HTML, JSON, XML]
  retention: 90 days
```

---

## Secure Coding Checklist

### Input / Output
- [ ] Input validation on all entry points (API, forms, queues) — type, size, format
- [ ] Output encoding before rendering user data
- [ ] Parameterized queries — never string interpolation in SQL
- [ ] Errors do not expose stack traces or internal data to clients

### Authentication / Authorization
- [ ] Authorization check on every operation (not just the route)
- [ ] JWT tokens: access 15min, refresh 7d, signature RS256 or ES256
- [ ] Sessions invalidated on logout
- [ ] No tokens in URLs or logs

### Resilience / Availability
- [ ] Retry with exponential backoff and circuit breaker on external calls
- [ ] Rate limiting on all public endpoints
- [ ] Resource limits on all containers

### Infrastructure
- [ ] Base images: distroless or alpine minimal (no shell in production)
- [ ] Containers running as non-root
- [ ] Read-only filesystem where possible
- [ ] All secrets via vault — no plaintext environment variables

---

## PII Classification

| Level | Type | Examples | Minimum control |
|-------|------|---------|-----------------|
| L1 — Critical | Financial, health | Card number, medical record | Encrypted at rest + transit, audited access |
| L2 — Sensitive | Personal identifiers | CPF, email, national ID | Encrypted, pseudonymization |
| L3 — Restricted | Behavioral | IP, access logs | Masking, limited retention |
| L4 — Public | Non-personal | Product name | Standard controls |

Full anonymization patterns → [pii-anonymization.md](pii-anonymization.md)
