# SPEC-2026-002: Incident Response Agent

> ⚠️ SPEC RETROATIVA — Reconstruída em 2026-05-16 a partir do código-fonte, ADRs e histórico git.
> Revisada e validada por Valdomiro Souza.

## Metadata
- **ID:** SPEC-2026-002
- **Status:** Approved
- **Author:** Valdomiro Souza
- **Reviewers:** Valdomiro Souza (Tech Lead)
- **Created:** 2026-01-01 (estimado) — Formalizado: 2026-05-16
- **Version:** 1.0.0
- **AI-assisted:** Yes — Claude Sonnet 4.6 / Prompt ID: PROMPT_VERSION 1.0.0

## Context and Problem

O núcleo inteligente do sistema. Recebe um gatilho de análise (`POST /analyze`), aciona quatro
agentes especialistas em paralelo (latência, erros, saturação, tráfego), e um orquestrador
sintetiza os findings em um `IncidentReport` estruturado usando Claude Sonnet 4.6 via
Anthropic tool-use API (ADR-2026-0005, ADR-2026-0007). O padrão Human-on-the-Loop garante que
o agente recomenda ações mas nunca executa (ADR-2026-0006). O serviço roda na porta :8001.

## Scope
### Includes
- `POST /analyze` — orquestra análise completa e retorna `IncidentReport`
- 4 agentes especialistas (Latency, Errors, Saturation, Traffic) com tool-use loop
- Orquestrador SoS com raciocínio causal root-cause vs trigger
- Circuit breaker para Anthropic API com fallback rule-based (ADR-2026-0010)
- Sanitização de inputs antes de envio ao LLM (`_sanitize_finding_text`)
- Validação de output LLM com Pydantic v2 (ADR-2026-0011)
- Busca em Knowledge Base para enriquecer recomendações
- Rate limiting: 10 req/min por IP
- Admin endpoints: `GET /admin/circuit-breaker/status`, `POST /admin/circuit-breaker/reset`
- LLM observability metrics: latência, token cost, error rate, injection detection

### Out of Scope
- Execução automática de ações de remediação (HOTL — humano decide)
- Alerting direto (responsabilidade Prometheus/PagerDuty)
- Persistência de IncidentReports (stateless por design)
- UI de visualização

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| RF-01 | `POST /analyze` retorna `IncidentReport` com overall_severity, title, diagnosis, root_causes, triggers, recommendations | Must Have | Validado pelo schema Pydantic `IncidentReport`; sem exposição de API keys em logs |
| RF-02 | 4 especialistas executam em paralelo via `asyncio.gather` | Must Have | Tempo total ≈ tempo do especialista mais lento (não soma) |
| RF-03 | Orquestrador sintetiza findings com raciocínio causal explícito (root cause vs trigger) | Must Have | JSON OrchestratorResponse válido; `diagnosis` com causalidade |
| RF-04 | Circuit breaker detecta ≥3 falhas consecutivas e abre circuito por 60s | Must Have | `cb_failure_threshold=3`, `cb_recovery_timeout_s=60`; fallback retorna análise rule-based |
| RF-05 | Fallback rule-based analisa métricas sem LLM quando circuito aberto | Must Have | `fallback_analyzer.py` usa thresholds: P99>1000ms→critical; 5xx>1%→warning |
| RF-06 | `_sanitize_finding_text` remove tags injection e anonimiza IPs/FQDNs antes de envio ao Claude | Must Have | Regex para IPv4, IPv6, FQDNs; comprimento máximo 500 chars |
| RF-07 | Output LLM validado com Pydantic `OrchestratorResponse` antes de construir `IncidentReport` | Must Have | ValidationError incrementa counter `llm_output_validation_failures_total` |
| RF-08 | `POST /analyze` requer API key via `X-API-Key` header | Must Have | 401 sem key; timing-safe via `hmac.compare_digest` |
| RF-09 | Rate limiting: 10 req/min por IP (SlowAPI) | Should Have | 429 Too Many Requests após limite |
| RF-10 | KB consulta enriquece recomendações com runbooks históricos | Should Have | `search_kb()` com score_threshold=0.70 |

## Non-Functional Requirements

| ID | Category | Requirement | Metric |
|----|----------|-------------|--------|
| RNF-01 | Performance | Análise completa p99 < 30s (limitada pelo LLM) | Prometheus `llm_call_duration_seconds` |
| RNF-02 | Reliability | Circuit breaker mantém disponibilidade com fallback quando Anthropic API falha | Fallback coverage ≥ 100% dos cenários de failure |
| RNF-03 | Security | Zero prompt injection passando para o Claude | `prompt_injection_sanitized_total` > 0 em testes com payloads maliciosos |
| RNF-04 | Security | API key nunca logada — só hash SHA-256 (8 chars) | `hash_key()` em todos os logs de auth |
| RNF-05 | Observability | LLM latency, token cost, error rate expostos em Prometheus | `llm_call_duration_seconds`, `llm_calls_total` |
| RNF-06 | Coverage | ≥ 85% branch coverage | `--cov-fail-under=85` |
| RNF-07 | Correctness | enable_docs=False obrigatório em produção | `@model_validator` em `config.py` bloqueia startup |

## Architecture

```
Trigger externo
    │
    ▼ POST /analyze (rate limited, API key auth)
[Incident-Response-Agent :8001]
    │
    ├── asyncio.gather ───────── 4 Specialists em paralelo
    │   ├── LatencyAgent ──── tool-use → GET /metrics/response-times
    │   ├── ErrorsAgent ───── tool-use → GET /metrics/overview
    │   ├── SaturationAgent ─ tool-use → GET /metrics/saturation
    │   └── TrafficAgent ──── tool-use → GET /metrics/rps + /backends
    │
    ├── OrchestratorAgent ─── sintetiza findings (causal reasoning)
    │   └── search_kb() ─────── enriquece com Knowledge Base
    │
    ├── AnthropicCircuitBreaker ── detecta falhas; abre/fecha circuito
    └── FallbackAnalyzer ──────── análise rule-based sem LLM
```

### Back-of-Envelope Summary (NALSD)
- **Peak RPS:** 10 req/min (rate limited); análise ~15s por request LLM
- **Latência budget p99:** 5 specialists × latência LLM (~8s cada, paralelo) + overhead = ~10-20s
- **Token budget por análise:** ~2000 tokens input + ~500 output × 5 calls = ~12500 tokens/análise
- **Storage:** stateless — nenhum dado persiste; IncidentReport retornado e descartado
- **Instâncias:** 1 (rate limit 10/min é suficiente para uso acadêmico + produção controlada)

ADRs: ADR-0001, ADR-0005, ADR-0006, ADR-0007, ADR-0009, ADR-0010, ADR-0011, ADR-0013

## Observability
- **Logs:** JSON estruturado; `prompt_version` incluso em cada análise para reproducibilidade; API keys apenas como hash SHA-256 (8 chars)
- **Metrics:** `llm_call_duration_seconds{call_type}`, `llm_calls_total{call_type,outcome}`, `llm_output_validation_failures_total`, `prompt_injection_sanitized_total{sanitization_type}`
- **Traces:** OTel spans por chamada Anthropic e por specialist; propagação de trace_id nos logs
- **SLI:** `llm_calls_total{outcome="error"}` / `llm_calls_total` < 1% por 5 min
- **SLO:** error rate LLM < 1%; circuit breaker aberto < 5% do tempo

## Security
- PII involved: No — findings de métricas de infra; IPs sanitizados antes do LLM
- Anonymization: `_sanitize_finding_text()` — remove tags, redact IPs/FQDNs, trunca 500 chars
- Credentials: `ANTHROPIC_API_KEY`, `API_KEY`, `ADMIN_KEY` via env vars (vault-ready)
- Communication: TLS com Anthropic API; mTLS-ready para inter-service (ADR-0013)
- Threat model: `/docs/security/threat-model.md` — LLM01 (prompt injection), LLM02 (insecure output), LLM05 (output validation), LLM07 (system prompt leakage), LLM08 (score threshold)
- OWASP review: A01 (HMAC auth), A04 (rate limiting), A05 (security headers), A09 (structured logging)
- DPIA required: No — nenhum dado pessoal processado

## Dependencies
Referência: `docs/dependency-manifest-ira.yaml`

Runtime principais: `fastapi`, `anthropic`, `pydantic==2.11.4`, `pydantic-settings`,
`slowapi` (rate limiting), `tenacity` (retry), `prometheus-fastapi-instrumentator`

Serviços externos: Anthropic API (claude-sonnet-4-6), Log-Ingestion-and-Metrics (:8000), Knowledge-Base (:8002)

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Anthropic API indisponível | Alta — sem análise LLM | Média | Circuit breaker + fallback rule-based |
| Prompt injection via findings de logs | Alta — LLM manipulation | Baixa | `_sanitize_finding_text()` com múltiplas camadas |
| Output LLM inválido / hallucination | Alta — report incorreto | Baixa | Pydantic v2 validation; ValidationError → fallback |
| Rate limit esgotado (API cost) | Média — custo | Baixa | SlowAPI 10/min; circuit breaker |
| System prompt leak (LLM07) | Média — segurança | Baixa | `enable_docs=False` em prod; prompts nunca logados |

## Approval
| Role | Name | Date | Status |
|------|------|------|--------|
| Tech Lead | Valdomiro Souza | 2026-05-16 | Approved (retroativo) |
| Security | Valdomiro Souza | 2026-05-16 | Approved (retroativo) |
| Architect | Valdomiro Souza | 2026-05-16 | Approved (retroativo) |
