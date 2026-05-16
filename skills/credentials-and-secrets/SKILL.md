---
name: credentials-and-secrets
description: Enforces zero-secrets-in-code policy through credential vault integration, least privilege access across all layers (cloud IAM, Kubernetes RBAC, databases, CI/CD), and .gitignore standards that prevent accidental secret exposure. Use when configuring vault integration, designing IAM policies or Kubernetes RBAC, setting up pre-commit hooks for secret detection, auditing access permissions, implementing Just-in-Time access, configuring CI/CD OIDC authentication, or reviewing a repository's secret hygiene.
---

# Credentials and Secrets

## Core rule
**Zero secrets in code.** Every credential — password, API key, token, certificate, connection string — lives exclusively in a credential vault. No exceptions.

## Contents
- What is forbidden in repositories
- Vault architecture and integration
- Correct vs incorrect credential access patterns
- Least privilege by layer → [least-privilege.md](least-privilege.md)
- .gitignore enterprise template → [gitignore-template.md](gitignore-template.md)
- Pre-commit hooks for secret detection

---

## Forbidden in Any Code Artifact or Repository

```
✗ Passwords in plain text
✗ Hardcoded API keys
✗ Access tokens
✗ Private certificates
✗ Connection strings with credentials
✗ Secrets in OS environment variables (without vault injection)
✗ Committed .env files with values
✗ Secrets in CI/CD environment variables (use OIDC + vault)
```

---

## Vault Architecture

```yaml
primary_vault: HashiCorp Vault | AWS Secrets Manager | Azure Key Vault | GCP Secret Manager

policies:
  access_by_service_account: true   # Each service has its own SA
  access_by_role: true              # RBAC in vault
  automatic_rotation:
    database_credentials: 24h
    api_keys: 90d
    certificates: 30d before expiry
  audit:
    log_all_access: true
    alert_on_anomaly: true
  lease_duration:
    production: 1h
    staging: 8h
    development: 24h

kubernetes_integration:
  method: Vault Agent Injector or External Secrets Operator
  no_plaintext_k8s_secrets: true

ci_integration:
  method: OIDC federation (no static credential in CI)
  example: "GitHub Actions OIDC → AWS IAM Role → Secrets Manager"
```

---

## Correct Credential Access Patterns

```python
# ✅ CORRECT: Access via vault SDK
import boto3, json

def get_database_credentials():
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId="prod/payment-service/db")
    return json.loads(response["SecretString"])

# ✅ CORRECT: Environment variable injected by Vault Agent
import os
DB_PASSWORD = os.environ["DB_PASSWORD"]  # Injected by Vault Agent, not hardcoded

# ❌ WRONG: Never do this
DB_PASSWORD = "my_password_here"
DB_PASSWORD = os.environ.get("DB_PASSWORD", "fallback_password")  # Dangerous fallback
```

---

## .env.example — Mandatory Pattern

Every ignored `.env` must have a versioned `.env.example` with all fields documented:

```bash
# .env.example — VERSIONED in repository
# INSTRUCTION: Copy to .env and fill with values from the vault
# NEVER commit a filled .env

DB_HOST=           # Get from Vault: prod/db/host
DB_PORT=5432
DB_PASSWORD=       # Get from Vault: prod/db/password [AUTO-ROTATION]

STRIPE_API_KEY=    # Get from Vault: prod/stripe/api_key

OTEL_SERVICE_NAME=payment-service
OTEL_DEPLOYMENT_ENVIRONMENT=  # development | staging | production
```

---

## Pre-commit Hooks — Secret Detection

```yaml
# .pre-commit-config.yaml — mandatory in every repository
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
        name: "Detect secrets before commit"

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ["--baseline", ".secrets.baseline"]
        exclude: ".env.example|*.md"
```

---

## Least Privilege — Summary

Applies across all layers. Full policy → [least-privilege.md](least-privilege.md)

| Layer | Key rule |
|-------|---------|
| Cloud IAM | One service account per service; no admin/owner roles on workloads; temporary credentials via STS |
| Kubernetes | `automountServiceAccountToken: false`; namespaced roles with explicit verbs; no wildcards |
| Database | Exclusive user per service; only necessary tables/schemas; no DDL in production |
| CI/CD | OIDC (no static access keys); permissions per stage; production requires human approval |
| Human access | Zero permanent production access; JIT max 4h; session recording; hardware MFA |

---

## gitignore — Enterprise Template

Full template with categories → [gitignore-template.md](gitignore-template.md)

Categories covered:
- Credentials and secrets (`.env*`, `*.pem`, `*.key`, cloud credentials)
- PII and personal data (LGPD / GDPR / CCPA / PCI-DSS)
- Security tool outputs (SAST/DAST reports, pentest)
- Logs and telemetry
- Local databases
- AI tool context and history
- Developer local configurations
- Build artifacts and dependencies
