# .gitignore Enterprise Template

Copy the block below to your repository's `.gitignore`.
Always use `!` for explicit exceptions — document why each exception exists.

---

```gitignore
# =============================================================
# .gitignore — Enterprise Security Standard
# Version: 1.0 | Aligned with: LGPD, GDPR, OWASP, PCI-DSS
# NEVER remove entries from this section without SecOps approval
# =============================================================


# ─────────────────────────────────────────────────────────────
# CREDENTIALS AND SECRETS — ABSOLUTE BLOCK
# ─────────────────────────────────────────────────────────────
.env
.env.*
.env.local
.env.*.local
.env.development
.env.staging
.env.production
.env.test
*.env

# Keys and certificates
*.pem
*.key
*.p12
*.pfx
*.jks
*.keystore
*.truststore
*.crt
*.cer
*.der
id_rsa
id_rsa.*
id_ed25519
id_ed25519.*
id_ecdsa

# Cloud credentials
.aws/credentials
.aws/config
.gcp/
gcloud-service-key.json
*-service-account*.json
*-credentials*.json
terraform.tfvars
terraform.tfvars.json
*.tfvars
*.tfvars.json
.terraform/
*.tfstate
*.tfstate.*
*.tfstate.backup

# Kubeconfig
kubeconfig
kubeconfig.*
.kube/
*.kubeconfig

# Vault
.vault-token
vault_token
*.vault


# ─────────────────────────────────────────────────────────────
# PII AND PERSONAL DATA — LGPD / GDPR / CCPA / PCI-DSS
# ─────────────────────────────────────────────────────────────
*.csv                     # Re-evaluate: add explicit exceptions if needed
*.tsv
data/raw/
data/pii/
data/personal/
data/sensitive/
datasets/
exports/
dumps/
*.dump
*.sql.gz
*.sql.bz2
backup/
backups/

# Fixtures/seeds with real data (use synthetic data only)
fixtures/real/
seeds/production/
seeds/staging/

# Reports that may contain user data
reports/
report_*.pdf
report_*.xlsx
export_*.csv
user_data_*.json


# ─────────────────────────────────────────────────────────────
# SECURITY TOOLS — SENSITIVE OUTPUTS
# ─────────────────────────────────────────────────────────────
.semgrep/
semgrep_results.json
zap_report.*
burp_report.*
nessus_report.*
trivy_report.*
grype_report.*
snyk_report.*
checkov_results.*
tfsec_results.*
security_report.*

# Pentest and recon
*.nmap
*.masscan
recon/
loot/

# Secret scanning results
gitleaks_report.*
trufflehog_results.*
detect-secrets.*


# ─────────────────────────────────────────────────────────────
# LOGS AND TELEMETRY
# ─────────────────────────────────────────────────────────────
*.log
*.logs
logs/
log/
*.log.*
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pip-log.txt

# Local traces and profiles
*.trace
*.prof
*.hprof
traces/
profiles/


# ─────────────────────────────────────────────────────────────
# LOCAL DATABASES
# ─────────────────────────────────────────────────────────────
*.sqlite
*.sqlite3
*.db
*.db-shm
*.db-wal
*.mdb
local.db
dev.db
test.db


# ─────────────────────────────────────────────────────────────
# AI TOOLS — CONTEXT AND HISTORY
# ─────────────────────────────────────────────────────────────
.cursorrules
.cursor/
.copilot/
*.aiprompt
prompts/sensitive/
ai_context/
llm_cache/
*.prompt.local
ai_output/
generated/unreviewed/


# ─────────────────────────────────────────────────────────────
# DEVELOPER LOCAL CONFIGURATIONS
# ─────────────────────────────────────────────────────────────
.idea/
.vscode/settings.json
.vscode/launch.json
*.iml
*.suo
*.user
.DS_Store
Thumbs.db

# Local config overrides (may contain secrets)
config/local.yaml
config/local.json
config/local.toml
*.local.yaml
*.local.json
*.local.toml
application-local.properties
application-local.yml
settings_local.py
local_settings.py


# ─────────────────────────────────────────────────────────────
# BUILD AND DEPENDENCIES
# ─────────────────────────────────────────────────────────────
node_modules/
__pycache__/
*.pyc
*.pyo
.venv/
venv/
env/
dist/
build/
target/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/


# ─────────────────────────────────────────────────────────────
# INFRASTRUCTURE AND CONTAINERS
# ─────────────────────────────────────────────────────────────
docker-compose.override.yml
docker-compose.local.yml
.dockerenv

# Ansible
*.retry
group_vars/*/vault.yml
host_vars/*/vault.yml
ansible-vault-password*

# SSH
.ssh/
ssh_config_local


# ─────────────────────────────────────────────────────────────
# EXPLICIT EXCEPTIONS — WHAT SHOULD BE COMMITTED
# Document each exception with justification
# ─────────────────────────────────────────────────────────────
# !config/example.env          # Example file with NO real values
# !fixtures/synthetic/         # Fixtures with SYNTHETIC data only
# !docs/security/threat-model/ # Documentation (no real data)
```

---

## Pre-commit Validation Script

Save as `scripts/check_env_files.py` and reference in `.pre-commit-config.yaml`:

```python
import sys, re

SENSITIVE_PATTERNS = [
    r"PASSWORD\s*=\s*\S+",
    r"SECRET\s*=\s*\S+",
    r"API_KEY\s*=\s*\S+",
    r"TOKEN\s*=\s*\S+",
    r"PRIVATE_KEY\s*=\s*\S+",
]

def check_env_file(filepath: str) -> bool:
    with open(filepath) as f:
        content = f.read()
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            print(f"BLOCKED: {filepath} contains sensitive values.")
            print("Use the credential vault. Never commit .env with real values.")
            return False
    return True

if __name__ == "__main__":
    for filepath in sys.argv[1:]:
        if not check_env_file(filepath):
            sys.exit(1)
```
