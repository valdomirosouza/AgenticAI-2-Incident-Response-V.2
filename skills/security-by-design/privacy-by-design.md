# Privacy by Design — 7 Principles Operationalized

| Principle | Implementation |
|-----------|---------------|
| 1. Proactive, not reactive | Threat modeling with LINDDUN in spec; DPIA for L1/L2 systems |
| 2. Privacy as default | Minimal collection; optional fields not collected by default; opt-in not opt-out |
| 3. Embedded in design | Field-level encryption for PII in DB; automatic masking in logs |
| 4. Full functionality | Pseudonymization enables analytics without exposing real PII |
| 5. End-to-end security | TLS in transit + AES-256 at rest + secure purge at end of retention |
| 6. Visibility and transparency | Versioned privacy policy; consent logs; automated DSAR |
| 7. Respect for users | Right to erasure implemented; data portability; consent revocation |

## Data Minimization in Code

```python
# ❌ Excessive model — collects everything "just in case"
class UserProfile(BaseModel):
    name: str
    email: str
    cpf: str
    birth_date: date
    full_address: str
    phone: str
    ip_address: str           # Why, if not needed?
    browser_fingerprint: str  # Disproportionate
    purchase_history: list    # Belongs to another domain

# ✅ Minimized model — only what is needed for the purpose
class UserProfile(BaseModel):
    """
    Legal basis: LGPD Art. 7, I (consent)
    Retention: 5 years after last access (legal obligation)
    DPIA: legal/dpia/user-profile-2024.pdf
    """
    name: str   # Required for personalization
    email: str  # Required for communication
    # CPF collected only in billing module (domain separation)
    # Address collected only in delivery module (domain separation)

    class Config:
        extra = "forbid"  # Future fields require DPIA review
```

## Right to Erasure — Implementation Checklist

```markdown
### Erasure Request Process
1. Receive request through official channel (email, portal, API)
2. Verify identity of data subject
3. Create erasure ticket with 15-business-day SLA
4. Execute purge across:
   - [ ] Primary database
   - [ ] Read replicas
   - [ ] Backups (mark for deletion at next backup cycle)
   - [ ] Log archives (purge or anonymize where legally required)
   - [ ] Caches (immediate invalidation)
   - [ ] Third parties notified (with their confirmation)
5. Generate purge certificate
6. Notify data subject of completion
7. Archive evidence for 5 years (audit trail)
```
