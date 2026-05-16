# Deprecation and EOL — Process and Templates

## 4-Phase Deprecation Process

```
PHASE 1: ANNOUNCEMENT    PHASE 2: DEPRECATION     PHASE 3: SUNSET        PHASE 4: REMOVAL
     |                        |                        |                      |
Decision in ADR         Deprecation header       Warnings in logs       Code removed
Communication to        added (APIs)             for each use           Infrastructure
consumers               Sunset date announced    Block new onboarding   decommissioned
Alternative             Monitoring of            Escalate to active     DEBT for dependents
documented              usage started            consumers              Data purged/archived
Min: 1 month            Min: 3 months            Min: 1 month           Permanent
```

## Deprecation Notice Template

```markdown
# DEPRECATION-[NNN]: [Deprecated Artifact Name]

## Metadata
- **ID:** DEP-YYYY-NNN
- **Type:** API endpoint | Service | Library | Schema | Feature
- **Artifact:** [exact name — URL, package, service]
- **Owner:** [responsible team]
- **Announcement date:** YYYY-MM-DD
- **Sunset date (removal):** YYYY-MM-DD
- **Related ADR:** ADR-NNN

## Motivation
> Why is this artifact being deprecated?

## Alternative
- **Replacement:** [name + documentation link]
- **Migration guide:** [link]
- **Migration support:** [channel + owner]

## Known Consumers
| Consumer | Team | Migration Status | Deadline |
|----------|------|-----------------|----------|

## Removal Criteria
- [ ] Zero traffic for 30 consecutive days
- [ ] All consumers confirmed migration
- [ ] Data migrated or purged per retention policy
- [ ] Secrets and credentials revoked
- [ ] Infrastructure decommissioned (instances, DNS, LB rules)
- [ ] Monitoring and alerts removed
- [ ] Documentation archived
```

## Decommission Checklist — Services

### Infrastructure
- [ ] Pods / instances terminated
- [ ] DNS entries removed
- [ ] Load balancer rules removed
- [ ] Auto-scaling groups deleted
- [ ] Buckets and storage purged or transferred

### Security
- [ ] Service accounts revoked
- [ ] Secrets deleted from vault
- [ ] Certificates revoked
- [ ] IAM roles and policies removed
- [ ] Network rules (SGs, NetworkPolicies) removed

### Data
- [ ] Data purged per retention policy
- [ ] Purge certificate generated
- [ ] Backups deleted after legal period

### Observability
- [ ] Dashboards archived or deleted
- [ ] Alerts removed
- [ ] Log streams closed
- [ ] Traces deactivated

### Documentation
- [ ] Deprecation ADR updated with completion date
- [ ] README archived in repository
- [ ] Runbooks removed or marked obsolete

## EOL Inventory Template

```yaml
# eol-inventory.yaml — versioned per service, reviewed quarterly
service: payment-service
last_review: "2024-01-15"
next_review: "2024-04-15"

runtimes:
  - name: Python
    version: "3.11"
    eol_date: "2027-10-31"
    status: current
    action_required: false

dependencies_eol_watch:
  - name: django
    version: "4.2 LTS"
    eol_date: "2026-04-01"
    status: monitoring
    action: "Plan upgrade to 5.x in Q1 2026"

deprecated_apis_published:
  - id: DEP-2024-001
    endpoint: "/v1/payments/legacy"
    sunset_date: "2024-06-01"
    consumers_migrated: 2/3
    status: in_progress

deprecated_apis_consumed:
  - service: notification-service
    endpoint: "/v1/notify/sms"
    sunset_date: "2024-03-01"
    migration_status: completed
```
