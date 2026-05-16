# PRR Checklist — Production Readiness Review

## Contents
- Architecture and Design
- Observability
- Reliability
- Security
- Operations
- Documentation

---

## Architecture and Design
- [ ] Architecture diagram updated and reviewed
- [ ] Single points of failure (SPOF) identified and mitigated
- [ ] Graceful degradation strategy defined
- [ ] Capacity limits documented (from NALSD back-of-envelope)
- [ ] Critical dependencies mapped (including third-parties with SLO)
- [ ] NALSD design checklist completed (see large-system-design skill)

## Observability
- [ ] All four Golden Signals instrumented (Error, Latency, Traffic, Saturation)
- [ ] Dashboards created and validated
- [ ] Alerts configured with SLO-based thresholds
- [ ] Log levels correct in production (no DEBUG by default)
- [ ] Distributed traces with context propagation validated
- [ ] SLI/SLO defined in `slo.yaml` and committed to repo

## Reliability
- [ ] SLI and SLO defined and documented
- [ ] Error budget calculated and monitored
- [ ] Load tests executed with documented baseline
- [ ] Chaos experiments planned (Gameday scheduled)
- [ ] Rollback plan documented and tested
- [ ] Circuit breakers configured for all external dependencies

## Security
- [ ] Security PRR completed (see security-by-design skill)
- [ ] Threat model reviewed and approved
- [ ] All credentials in vault — zero hardcoded secrets
- [ ] mTLS or TLS 1.3 on all inter-service communication
- [ ] PII audited and anonymized at source
- [ ] SAST, DAST, SCA all green in CI

## Operations
- [ ] Runbook written and reviewed by someone outside the team
- [ ] On-call escalation path defined
- [ ] Incident response process documented
- [ ] Postmortem template referenced
- [ ] DR (Disaster Recovery) tested with RTO/RPO documented
- [ ] Feature flags for all new functionality

## Documentation
- [ ] `dependency-manifest.yaml` updated (see documentation-standards skill)
- [ ] ADRs written for all architectural decisions (see managing-adrs skill)
- [ ] API documented (OpenAPI/AsyncAPI)
- [ ] CHANGELOG updated
- [ ] `eol-inventory.yaml` updated for all runtimes

## NALSD + Google SRE Pre-PRR Gate
- [ ] Back-of-envelope calculations completed
- [ ] Bottlenecks identified and resolved
- [ ] Tradeoffs documented in ADRs
- [ ] Understandability checklist passed (invariants listed, complexity within limits)
- [ ] Resilience checklist passed (timeouts, fallbacks, circuit breakers)
- [ ] Overload handling configured (rate limiting, load shedding)

## Approval
| Role | Name | Date | Status |
|------|------|------|--------|
| Engineering owner | | | |
| Tech Lead | | | |
| SRE | | | |
| SecOps | | | |
