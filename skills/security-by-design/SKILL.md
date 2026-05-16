---
name: security-by-design
description: Embeds security as a structural property of systems from the spec phase — covering threat modeling (STRIDE/LINDDUN), Secure by Default, Defense in Depth, Privacy by Design (LGPD/GDPR), and Attack Surface Reduction. Use when reviewing or writing a spec for security completeness, performing threat modeling, designing access control, evaluating privacy impact (DPIA), or verifying that a system follows Security by Design principles. Also use when asked about fail-safe defaults, blast radius, CSP headers, or DPIA.
---

# Security by Design

Security is a structural property — not a layer added after coding. This skill governs the security architecture phase that precedes DevSecOps tooling.

## Contents
- Secure SDLC: security gates per development phase
- Threat Modeling (STRIDE) → [threat-modeling.md](threat-modeling.md)
- Secure by Default (fail-safe, deny-all, HTTP headers)
- Defense in Depth (8-layer model)
- Privacy by Design + DPIA → [privacy-by-design.md](privacy-by-design.md)
- Attack Surface Reduction
- Spec approval checklist

---

## Secure SDLC — Gates per Phase

| Phase | Security activity | Artifact |
|-------|------------------|---------|
| Spec Draft | Threat modeling, PII classification | Security section in spec |
| Tech Review | Threat model + controls validated | Spec with security sign-off |
| Implementation | Secure coding, SAST pre-commit, no hardcoded secrets | Code with traceability header |
| Harness / Tests | Authorization tests, negative tests | Security tests in harness |
| CI/CD | SAST, SCA, secret scan, container scan | Security report in PR |
| Staging | DAST, TLS/mTLS validation | DAST report |
| Production | Artifact signature verified, SBOM validated | Signed deploy evidence |
| Operations | Anomaly monitoring, log review, SIEM | Monthly security reports |
| Deprecation | Credential revocation, data sanitization | Decommission checklist |

---

## Secure by Default

**Fail-safe principle:** On failure, deny access — never permit by omission.

```
Examples:
  Auth middleware fails?    → HTTP 500, NOT bypass
  Vault unavailable?        → Service does NOT start (no hardcoded fallback)
  Feature flag unavailable? → Feature OFF, not ON
  Circuit breaker open?     → Return error, do NOT retry infinitely
```

**Deny-all defaults:**
- Kubernetes NetworkPolicy: deny-all ingress/egress by default; explicit allowlist
- Security Groups: deny-all; allow by specific port and source
- WAF: block mode for OWASP Core Rule Set
- All routes require explicit permission — no public routes by default

**Mandatory HTTP security headers:**
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Content-Security-Policy: [defined restrictive policy]
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: [restrict unused browser APIs]
```

**Cookies:** `Secure; HttpOnly; SameSite=Strict` (or Lax when required)

**CORS:** Explicit origin allowlist — never wildcard (`*`) in production

---

## Defense in Depth — 8 Layers

```
Layer 8: People & Process    → Training, blameless postmortem, threat intel
Layer 7: Data                → Encryption at rest, PII anonymization, DLP, retention/purge
Layer 6: Application         → Input validation, authn/authz, SAST, DAST, SCA
Layer 5: Identity            → MFA, RBAC, JIT access, session management, Zero Trust
Layer 4: Endpoint/Workload   → Container hardening, EDR, Falco, admission controllers
Layer 3: Network             → mTLS, NetworkPolicy, WAF, API Gateway, egress filtering
Layer 2: Perimeter           → Firewall, VPC, Security Groups, ZTNA
Layer 1: Physical/Cloud      → Cloud provider shared responsibility model
```

**Design rule:** For every critical security control, ask:
- "What happens if this control fails?"
- "Is there an independent control that still protects?"
- "Is the failure of this control detectable and alerted?"

---

## Threat Modeling

Mandatory for: services with L1/L2 data, external API exposure, architectural changes.

**STRIDE quick reference:**

| Threat | Control |
|--------|---------|
| Spoofing | Strong authentication (OAuth 2.0/OIDC, mTLS) |
| Tampering | TLS 1.3, digital signatures, checksums |
| Repudiation | Immutable and audited logging (SIEM) |
| Information Disclosure | Encryption, PII masking, RBAC |
| Denial of Service | Rate limiting, circuit breaker, auto-scaling |
| Elevation of Privilege | Least Privilege, per-operation authorization |

Full process, DFD template, and LINDDUN for privacy → [threat-modeling.md](threat-modeling.md)

---

## Attack Surface Reduction

| Area | Key rules |
|------|-----------|
| Code | Remove unused dependencies; disable beta features in production |
| Network | Expose only necessary ports; egress allowlist for external calls |
| API | Version and deprecate old endpoints; no bulk endpoints without auth + rate limiting |
| Dependencies | Audit each new dependency; no open version ranges in production |
| Infrastructure | Remove unused cloud resources; monthly IAM permission audit |

---

## Security by Design — Spec Approval Checklist

Before approving any spec with new service, data access, or architecture change:

```markdown
### Threat Modeling
- [ ] STRIDE applied to main components
- [ ] DFD with trust boundaries documented
- [ ] High-risk threats have mapped controls
- [ ] LINDDUN applied if PII involved (or DPIA initiated)
- [ ] Residual risks accepted and documented

### Secure by Default
- [ ] System initial state is maximally restrictive
- [ ] Fail-safe defined for each critical failure point
- [ ] Security HTTP headers configured
- [ ] Debug/admin interfaces disabled in production
- [ ] Timeouts defined for all integrations

### Defense in Depth
- [ ] For each critical control: independent backup control exists?
- [ ] Control failure is detectable and alerted?
- [ ] No single point of security failure

### Privacy by Design
- [ ] Data collected is minimal for the purpose
- [ ] Legal basis (LGPD/GDPR) identified for each data type
- [ ] Retention policy defined
- [ ] Data subject rights implemented (DSAR, erasure, portability)
- [ ] DPIA completed if applicable

### Approval
| Reviewer | Role | Date | Status |
|----------|------|------|--------|
| | Engineer | | |
| | SecOps | | |
| | DPO (if L1/L2 PII) | | |
```
