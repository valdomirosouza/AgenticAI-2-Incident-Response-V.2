# OWASP Top 10 Controls

| ID | Vulnerability | Required Control |
|----|--------------|-----------------|
| A01 | Broken Access Control | RBAC + automated authorization tests on every endpoint |
| A02 | Cryptographic Failures | TLS 1.3, AES-256, key rotation via KMS |
| A03 | Injection | Parameterized queries, input validation, ORM |
| A04 | Insecure Design | Threat modeling in spec, Security PRR gate |
| A05 | Security Misconfiguration | IaC with Checkov, hardening guides, Secure by Default |
| A06 | Vulnerable Components | SCA in CI (Snyk/OWASP DC), SBOM, CVE SLA |
| A07 | Auth & Identity Failures | MFA, OAuth 2.0/OIDC, token rotation, session revocation |
| A08 | Data Integrity Failures | Artifact signing (Cosign/Sigstore), SBOM, SLSA |
| A09 | Logging & Monitoring Failures | Structured logging mandatory, SIEM, alert on missing logs |
| A10 | SSRF | URL allowlist for external calls, egress filtering |

## OWASP ASVS Level Mapping

| ASVS Level | When to apply |
|-----------|---------------|
| L1 | All applications — minimum bar |
| L2 | Applications handling sensitive data (L1/L2 PII) |
| L3 | Critical systems — financial, healthcare, regulatory |
