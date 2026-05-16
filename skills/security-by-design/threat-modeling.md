# Threat Modeling — STRIDE, LINDDUN, DPIA

## Threat Modeling Template (STRIDE)

```markdown
## Threat Model — [Service / Feature]

### 1. Scope
- In-scope components: [list]
- Trust boundaries: [describe]
- Actors: [authenticated user, anonymous user, internal service, admin]

### 2. Data Flow Diagram (DFD)
> Insert diagram: processes, datastores, data flows, external actors
> Mark trust boundaries explicitly

### 3. Threat Identification (STRIDE per component)
| Component | STRIDE Category | Threat | Impact | Probability | Risk |
|-----------|----------------|--------|--------|-------------|------|
| API Gateway | Spoofing | Forged JWT token | High | Medium | HIGH |
| Database | Information Disclosure | SQL Injection | Critical | Low | HIGH |

### 4. Controls and Mitigations
| Threat | Control | Status | Owner |
|--------|---------|--------|-------|
| Forged JWT | RS256 signature validation + exp + iss check | Implemented | @eng |

### 5. Accepted Residual Risks
| Risk | Justification | Accepted by | Date |
|------|--------------|-------------|------|

### 6. Review Schedule
- Review on: major releases, architecture changes, new relevant attack vectors
- Next review: [date]
```

---

## LINDDUN — Privacy Threat Modeling

Use LINDDUN alongside STRIDE when the system processes PII (L1 or L2).

| Threat | Description | Control |
|--------|-------------|---------|
| **L**inkability | Linking data across contexts reveals more than intended | Data minimization, pseudonymization |
| **I**dentifiability | Identifying individuals from supposedly anonymous data | k-anonymity, differential privacy |
| **N**on-repudiation | User cannot deny having performed an action | Consent management, audit logs |
| **D**etectability | Detecting that a data item or operation exists | Obfuscation, access pattern protection |
| **D**isclosure | Unauthorized access to personal data | Encryption, RBAC, DLP |
| **U**nawareness | Users unaware of how their data is used | Transparency, privacy notice |
| **N**on-compliance | Violating legal requirements | DPIA, legal basis documentation |

---

## DPIA Template — Data Protection Impact Assessment

Required when: processing L1/L2 data, automated decision-making with user impact, systematic monitoring of individuals, or large-scale personal data processing.

```markdown
## DPIA — [System / Feature]

### 1. Processing Description
- Data collected: [list with L1-L4 classification]
- Purpose: [legal basis — LGPD Art. 7 / GDPR Art. 6]
- Retention: [period + legal justification]
- Sharing: [third parties, DPA referenced]

### 2. Necessity and Proportionality
- [ ] Data collected is minimal for the stated purpose?
- [ ] Is there a less privacy-invasive alternative?
- [ ] Data subject has been informed (transparency)?

### 3. Identified Risks
| Risk | Impact on Subject | Probability | Mitigation |
|------|------------------|-------------|-----------|

### 4. Controls Implemented
- Anonymization/pseudonymization: [describe]
- Encryption: [algorithm, key management]
- Access control: [who accesses, with what justification]
- Audit log: [what is logged, retention]

### 5. Data Subject Rights
| Right (LGPD/GDPR) | Mechanism | SLA |
|--------------------|-----------|-----|
| Access (DSAR) | [endpoint/process] | 15 business days |
| Correction | [endpoint/process] | 15 business days |
| Erasure | [purge process] | 15 business days |
| Portability | [format + endpoint] | 15 business days |
| Consent revocation | [mechanism] | Immediate |

### 6. Approval
- DPO: [name] — Date: [date]
- Legal: [name] — Date: [date]
```
