# PII Anonymization Patterns

## Anonymization Techniques by Context

| Context | Technique | Reversible |
|---------|-----------|------------|
| Production logs | Masking / Redaction | No |
| Analytics / BI | Pseudonymization (salted hash) | No (one-way) |
| Development / QA | Synthetic data | N/A |
| Long-term backup | Tokenization + token vault | Yes (controlled) |
| Load testing | Synthetic generation (Faker) | N/A |

## Python — PIIAnonymizer

```python
import hashlib, re

class PIIAnonymizer:
    """
    Use before any data reaches logs, traces, or analytics.
    NEVER log raw user data.
    """

    @staticmethod
    def anonymize_cpf(cpf: str) -> str:
        """Replaces CPF with deterministic hash."""
        return f"CPF_HASH_{hashlib.sha256(cpf.encode()).hexdigest()[:8]}"

    @staticmethod
    def mask_email(email: str) -> str:
        """Masks email: j***@example.com"""
        parts = email.split("@")
        if len(parts) != 2:
            return "[INVALID_EMAIL]"
        return f"{parts[0][0]}***@{parts[1]}"

    @staticmethod
    def mask_card(card: str) -> str:
        """Keeps only last 4 digits."""
        digits = re.sub(r'\D', '', card)
        return f"****-****-****-{digits[-4:]}"

    @staticmethod
    def sanitize_log_data(data: dict) -> dict:
        """Removes/masks PII from dictionaries before logging."""
        PII_FIELDS = {
            "cpf", "password", "card_number", "ssn", "email",
            "phone", "full_address", "birth_date", "token",
            "api_key", "secret", "national_id"
        }
        return {
            k: "[REDACTED]" if k.lower() in PII_FIELDS else v
            for k, v in data.items()
        }
```

## Synthetic Data Generation (Development/QA)

```python
from faker import Faker

fake = Faker("pt_BR")  # or "en_US", "de_DE", etc.

def generate_synthetic_user():
    """
    Use ONLY for dev/test environments.
    Never use real user data in non-production.
    """
    return {
        "name": fake.name(),
        "email": fake.email(),
        "cpf": fake.cpf(),          # Faker generates valid-format CPFs
        "phone": fake.phone_number(),
        "address": fake.address(),
    }
```

## Data Retention and Purge

```yaml
data_retention_policy:
  L1_critical:
    retention: "Defined by legal obligation (e.g., fiscal records 5 years)"
    purge_method: "Cryptographic erasure (destroy encryption key)"
    evidence: "Purge certificate generated and archived"

  L2_sensitive:
    retention: "Required for purpose + legal margin"
    purge_method: "Automated + verification across all replicas"

  L3_restricted:
    retention: "90 days (access logs) — adjust per regulation"
    purge_method: "Automated via TTL in storage"

right_to_erasure:
  sla: "15 business days after request"
  scope: "Primary data + backups + logs + caches + third parties notified"
  evidence: "Purge certificate generated and filed"
```

## LGPD / GDPR — Legal Bases (Art. 7 LGPD / Art. 6 GDPR)

| Base | When to use |
|------|-------------|
| Consent | User explicitly opted in — store consent record with timestamp |
| Legal obligation | Required by law (tax, regulatory) — cite the specific norm |
| Contract | Necessary to fulfill a contract with the user |
| Legitimate interest | Must pass balancing test — document reasoning |

**Rule:** Every PII field in the data model must have a documented legal basis. No legal basis = do not collect.
