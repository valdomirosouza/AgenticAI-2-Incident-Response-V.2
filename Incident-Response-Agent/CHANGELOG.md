# Changelog — Incident-Response-Agent

## [1.3.0] — 2026-05-16
### Added
- `README.md` — documentação completa do serviço
- `prompts/v1/` — 5 prompts versionados com metadados de rastreabilidade

## [1.2.0] — 2026-05 (estimado)
### Added
- LLM observability: `llm_metrics.py` com 4 métricas Prometheus (latência, calls, validação, injection)
- AI risk classification em `docs/ai-governance/risk-classification.md`
- `PROMPT_CLASSIFICATION = "SENSITIVE"` — LLM07:2025 system prompt protection

## [1.1.0] — 2026-04 (estimado)
### Added
- ZAP DAST gate em `.github/workflows/dast.yml`
- TruffleHog secret scan em CI
- API_KEY obrigatória em staging/production (`@model_validator`)
- `_sanitize_finding_text()` — remove injection tags, redact IPs/FQDNs (LLM01+LLM02)

## [1.0.0] — 2026-01 (estimado)
### Added
- `POST /analyze` — 4 specialists (Latency, Errors, Saturation, Traffic) em paralelo
- Orchestrator SoS com raciocínio causal root cause vs trigger
- Claude Sonnet 4.6 via Anthropic tool-use API (ADR-2026-0005)
- Circuit breaker + fallback rule-based (ADR-2026-0010)
- Pydantic v2 output validation — OrchestratorResponse (ADR-2026-0011)
- Rate limiting 10/min (SlowAPI)
- HMAC API Key auth (ADR-2026-0009)
- Knowledge-Base integration para enriquecimento de recomendações
- Human-on-the-Loop pattern (ADR-2026-0006)
