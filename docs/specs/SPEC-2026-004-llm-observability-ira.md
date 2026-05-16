# SPEC-2026-004: LLM Observability — Incident Response Agent

> ⚠️ SPEC RETROATIVA — Baseada em RFC-2026-001. Formalizada em 2026-05-16.
> Revisada e validada por Valdomiro Souza.

## Metadata
- **ID:** SPEC-2026-004
- **Status:** Approved
- **Author:** Valdomiro Souza
- **Reviewers:** Valdomiro Souza (Tech Lead)
- **Created:** 2026-05-16
- **Version:** 1.0.0
- **AI-assisted:** Yes — Claude Sonnet 4.6 / Prompt ID: PROMPT_VERSION 1.0.0
- **RFC reference:** RFC-2026-001

## Context and Problem

O IRA usa o Claude Sonnet 4.6 para análise de incidentes, mas sem observabilidade específica
de LLM o sistema não detecta degradação de qualidade, aumento de custo por token, ou tentativas
de prompt injection. A skill `ai-governance` exige métricas de: latência por chamada, token cost,
error rate, output quality e injection attempts. Este spec formaliza a implementação do módulo
`llm_metrics.py` e sua integração com o Prometheus já configurado.

## Scope
### Includes
- Métricas Prometheus para chamadas LLM: latência, contagem, erros, validação, injection
- Integração com AlertManager: alertas em error rate > 1% e circuit breaker aberto
- `PROMPT_VERSION` logado em cada análise para rastreabilidade científica
- Alertas Prometheus em `/infra/prometheus/alerts.yaml`

### Out of Scope
- Output quality score automatizado (requer dataset de ground-truth — roadmap)
- Token cost tracking automático via API (Anthropic API não retorna token count em streaming)
- Model drift detection automatizada (análise semanal manual via logs)
- Dashboard Grafana dedicado para LLM (roadmap — v2)

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| RF-01 | `llm_call_duration_seconds` Histogram por `call_type` (specialist/synthesis) | Must Have | Métrica presente em `/prometheus/metrics`; labels `call_type` |
| RF-02 | `llm_calls_total` Counter por `call_type` e `outcome` (success/error/circuit_open/validation_error) | Must Have | Incrementado em cada chamada; outcome correto por caso |
| RF-03 | `llm_output_validation_failures_total` Counter para falhas Pydantic no output Claude | Must Have | Incrementado quando `OrchestratorResponse` ValidationError |
| RF-04 | `prompt_injection_sanitized_total` Counter por `sanitization_type` (tag_removal/ip_redaction/host_redaction) | Must Have | Incrementado por cada tipo de sanitização aplicada |
| RF-05 | Alerta Prometheus `LLMHighErrorRate` dispara quando error rate > 1% por 5 min | Should Have | Regra em `alerts.yaml`; severidade `warning` |
| RF-06 | Alerta `LLMCircuitBreakerOpen` dispara quando circuito permanece aberto | Should Have | Regra em `alerts.yaml`; severidade `critical` |
| RF-07 | `PROMPT_VERSION` logado em campo `extra` de cada análise | Must Have | `logger.info(..., extra={"prompt_version": PROMPT_VERSION})` |

## Non-Functional Requirements

| ID | Category | Requirement | Metric |
|----|----------|-------------|--------|
| RNF-01 | Performance | Overhead de métricas < 1ms por chamada | Prometheus client Python é lock-free |
| RNF-02 | Security | Métricas não expõem conteúdo de prompts/responses | Apenas contadores e histogramas; sem labels de conteúdo |
| RNF-03 | Compliance | AI Governance checklist satisfeita (skills/ai-governance) | `llm_metrics.py` cobre todas as 5 métricas obrigatórias |
| RNF-04 | Coverage | ≥ 85% branch coverage incluindo `llm_metrics.py` | `pyproject.toml` threshold |

## Architecture

```
run_analysis() / call_anthropic_with_retry()
    │
    ├── LLM_CALL_DURATION.labels(call_type).observe(elapsed)
    ├── LLM_CALLS_TOTAL.labels(call_type, outcome).inc()
    ├── LLM_OUTPUT_VALIDATION_FAILURES.inc()  ← em ValidationError
    └── PROMPT_INJECTION_SANITIZED.labels(sanitization_type).inc()
            │
            ▼
    /prometheus/metrics ── scrapeado pelo Prometheus
            │
            ▼
    AlertManager ── LLMHighErrorRate | LLMCircuitBreakerOpen
```

### Back-of-Envelope Summary (NALSD)
- **Overhead:** 4 counters + 1 histogram; ~0.1ms por chamada (Prometheus client thread-safe)
- **Cardinalidade:** `call_type` = 2 valores; `outcome` = 4 valores; `sanitization_type` = 3 — cardinalidade controlada
- **Alerting latência:** Prometheus scrape a cada 15s; alerta dispara após 5 min → MTTD ≤ 5.25 min

ADRs: ADR-0005 (Claude), ADR-0010 (circuit breaker)
RFC: RFC-2026-001

## Observability
- **Logs:** `prompt_version` em cada análise; `call_type` e `outcome` em structured logs
- **Metrics:** ver RF-01 a RF-04 acima
- **Traces:** spans de chamadas LLM propagam trace_id para correlação com métricas
- **SLI:** `llm_calls_total{outcome="error"}` / `llm_calls_total` < 1%
- **SLO:** LLM error rate < 1% (5 min window); circuit breaker aberto < 5% do tempo

## Security
- PII involved: No — métricas são contadores e histogramas sem conteúdo
- Credentials: N/A (métricas locais Prometheus)
- Threat model: LLM01 (injection — `PROMPT_INJECTION_SANITIZED` rastreia tentativas), LLM05 (output validation — `LLM_OUTPUT_VALIDATION_FAILURES`), LLM07 (system prompt — PROMPT_VERSION versionado em repo)
- DPIA required: No

## Dependencies
Módulos: `llm_metrics.py`, `orchestrator.py`, `anthropic_circuit_breaker.py`, `prompts.py`
Infra: Prometheus (:9090), AlertManager

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Alta cardinalidade de labels futuros | Alta — OOM Prometheus | Baixa | Labels pré-definidos em spec; sem labels dinâmicos |
| Token cost invisível | Média — custo surpresa | Média | Anthropic dashboard + alerta manual mensal |
| Output quality degradado silenciosamente | Alta — reports incorretos | Baixa | `LLM_OUTPUT_VALIDATION_FAILURES` captura erros estruturais |

## Approval
| Role | Name | Date | Status |
|------|------|------|--------|
| Tech Lead | Valdomiro Souza | 2026-05-16 | Approved (retroativo) |
| Security | Valdomiro Souza | 2026-05-16 | Approved (retroativo) |
| Architect | Valdomiro Souza | 2026-05-16 | Approved (retroativo) |
