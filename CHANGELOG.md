# Changelog — AgenticAI-2 Incident Response

Todas as mudanças relevantes são documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versões seguem [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [Unreleased]

---

## [1.3.0] — 2026-05-16

### Added
- `docs/specs/` — 4 specs retroativas (SPEC-2026-001 a 004) seguindo SDD
- `docs/specs/nalsd/nalsd-capacity-planning.md` — NALSD back-of-envelope por serviço
- `prompts/v1/` — 5 prompts versionados extraídos de `prompts.py` com metadados de rastreabilidade
- `slo/slo.yaml` — definição declarativa de SLOs (anteriormente apenas em código Python)
- `docs/security/dpia.md` — Data Protection Impact Assessment (LGPD/GDPR)
- `docs/security/lgpd-checklist.md` — checklist de conformidade LGPD
- `docs/post-mortems/POSTMORTEM_TEMPLATE.md` — template formal de postmortem blameless
- `docs/runbooks/chaos-experiments.md` — experimentos de chaos engineering planejados
- `.github/BRANCH_PROTECTION.md` — regras de proteção de branch documentadas
- `docs/api/` — referências OpenAPI por serviço
- `docs/dependency-manifest-*.yaml` — manifests enriquecidos de dependências (Layer 2)
- README.md por serviço (Log-Ingestion, IRA, Knowledge-Base)
- `[tool.ruff.lint.mccabe] max-complexity = 10` em todos os `pyproject.toml`
- Step `license-check` (pip-licenses) adicionado ao workflow `sast.yml`

### Changed
- `pyproject.toml` (3 serviços): adicionada seção `[tool.ruff.lint]` com McCabe complexity enforcement

---

## [1.2.0] — 2026-05 (estimado)

### Added
- `docs/sdlc/tech-debt-register.md` — registro de dívida técnica (DEBT-2026-001 a 007)
- `docs/sdlc/eol-inventory.yaml` — inventário de EOL de dependências
- `docs/sdlc/rfc/RFC-2026-001-llm-metrics-prometheus-ira.md` — RFC de observabilidade LLM
- `docs/ai-governance/risk-classification.md` — classificação de risco de IA
- `docs/ai-governance/checklist.md` — checklist ético de governança de IA

### Added (segurança)
- Prometheus auth (A05) — `X-Prometheus-Key` obrigatório em staging/production
- LLM02 anonymization — IPs e hostnames redactados antes de envio ao Claude
- LLM07 system prompt classification — prompts marcados como SENSITIVE
- Trivy CI — scan de CVEs em filesystem e imagens Docker
- TruffleHog CI — detecção de secrets no histórico git
- ZAP DAST gate — OWASP ZAP baseline em todos os serviços
- API_KEY obrigatória em staging/production (A01/A05)

---

## [1.1.0] — 2026-04 (estimado)

### Added
- 13 ADRs cobrindo todas as decisões arquiteturais (ADR-0001 a ADR-0013)
- `docs/security/threat-model.md` — STRIDE + LINDDUN
- `docs/post-mortems/` — 3 postmortems (INC-001, INC-002, INC-003)
- `docs/runbooks/high-latency.md` e `redis-memory.md`
- Alertas Prometheus: SLOs, LLM health, infraestrutura

---

## [1.0.0] — 2026-01 (estimado)

### Added
- Arquitetura inicial de 3 microsserviços FastAPI
- Log-Ingestion-and-Metrics (:8000) — ingestão HAProxy + Golden Signals
- Incident-Response-Agent (:8001) — 4 specialists + orchestrator (Claude Sonnet 4.6)
- Knowledge-Base (:8002) — Qdrant + all-MiniLM-L6-v2
- Circuit breaker Anthropic com fallback rule-based
- Padrão Human-on-the-Loop (HOTL)
- CI/CD: ci.yml, sast.yml, dast.yml, sbom.yml, load-test.yml
- OpenTelemetry traces + Prometheus metrics + structured JSON logs
- SLOs: availability 99.5%, latency_p95 99%, latency_p99 99.9%
- Docker Compose orquestração completa
