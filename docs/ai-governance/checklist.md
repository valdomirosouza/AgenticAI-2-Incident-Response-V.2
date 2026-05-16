# AI Governance Checklist — AgenticAI-2-Incident-Response

**Sistema:** Agentic AI Copilot para Redução de MTTD/MTTR  
**Classificação de risco:** Medium Risk (ver `risk-classification.md`)  
**Revisado por:** Valdomiro Souza  
**Data:** 2026-05-16  
**Spec reference:** SDD v1.7.0 §7.3, skills/ai-governance/SKILL.md

---

## Princípio central

> O Claude não tem responsabilidade legal, moral ou organizacional. É uma ferramenta.
> O engenheiro humano é sempre o tomador de decisão final e é totalmente responsável pelos
> outputs do AI usados em produção. — Human-on-the-Loop (ADR-2026-0006)

---

## Transparência

- [x] Usuários informados quando interagem com sistema baseado em IA
  - `IncidentReport.specialist_model_version` expõe a versão do prompt usada
  - `IncidentReport.llm_calls_count` documenta quantas chamadas ao Claude foram feitas
  - `IncidentReport.title` inclui sufixo "(LLM Circuit Open)" quando fallback é ativado
- [x] Outputs de IA rotulados como tal nas interfaces internas
  - `IncidentReport.diagnosis` e `recommendations` são identificados como análise de IA
  - Fallback rule-based é explicitamente rotulado em `diagnosis`
- [x] Modelo e versão documentados e rastreáveis
  - `PROMPT_VERSION = "1.0.0"` em `agents/prompts.py` — logado em cada análise
  - Modelo configurável em `config.py` (`model: str = "claude-sonnet-4-6"`)
  - Todas as ADRs incluem seção "AI Assistance" com modelo, versão e papel

---

## Fairness

- [x] Outputs de IA revisados para viés em decisões que afetam usuários
  - Sistema analisa métricas técnicas (Golden Signals), não decisões sobre pessoas
  - HOTL garante que o engenheiro humano revisa antes de qualquer ação
- [x] Decisões automáticas com impacto significativo têm revisão humana obrigatória
  - **Nenhuma ação autônoma é executada** — ADR-2026-0006 (HOTL)
  - `recommended_actions` são sugestões; execução exclusivamente pelo engenheiro
- [x] Sistemas de alto risco documentados sob requisitos EU AI Act
  - Sistema classificado como **Medium Risk** (análise de logs de produção, sem PII)
  - Não se enquadra em High Risk EU AI Act (sem decisões de crédito, saúde ou emprego)

---

## Privacidade

- [x] PII NÃO é enviado a modelos de IA externos sem DPA
  - Logs HAProxy contêm apenas métricas agregadas (P50/P95/P99, contadores)
  - Sem IPs individuais de usuários nos Golden Signals
- [x] Dados de clientes não usados em prompts sem anonimização
  - `_sanitize_finding_text()` redacta IPv4, IPv6 e FQDNs internos antes de enviar ao Claude
  - `[IP_REDACTED]` e `[HOST_REDACTED]` substituem dados sensíveis (LLM02:2025)
- [x] Logs de prompts/respostas com dados sensíveis protegidos como logs de produção
  - `PROMPT_CLASSIFICATION = "SENSITIVE"` em `prompts.py` (LLM07:2025)
  - System prompts nunca logados — Semgrep rules detectam violações no CI

---

## Auditabilidade

- [x] Todo uso de IA em fluxos críticos é logado e rastreável
  - `logger.info("Analysis started", extra={"prompt_version": PROMPT_VERSION})`
  - `logger.info("Analysis completed", extra={"severity", "duration_s", "kb_chunks"})`
  - Métricas Prometheus: `llm_calls_total`, `llm_call_duration_seconds`
- [x] Decisões de IA com impacto ao usuário têm mecanismo de explicação
  - `IncidentReport.diagnosis` — narrativa causal gerada pelo Claude
  - `IncidentReport.root_causes` e `triggers` — explicação estruturada
  - `IncidentReport.incident_commander_brief` — resumo executivo para engenheiro
- [x] Versões de prompts versionadas junto ao código
  - `PROMPT_VERSION = "1.0.0"` em `agents/prompts.py` — versionado no Git
  - Mudanças em prompts seguem o mesmo processo de PR e review do código

---

## Segurança de IA

- [x] Proteção contra prompt injection em sistemas integrados com IA
  - `_sanitize_finding_text()` remove tags `<human>`, `<assistant>`, `<system>`, `<prompt>`
  - MAX_FINDING_LENGTH=500 limita tamanho de input por finding
  - Semgrep rule `prompt-injection-risk` no CI (sast.yml)
- [x] Outputs de IA validados antes de uso em operações críticas
  - `OrchestratorResponse.model_validate()` valida schema antes de construir `IncidentReport`
  - `SpecialistFinding.severity: Literal[...]` — validação de tipo estrita
  - ValidationError ativa fallback rule-based (LLM05:2025)
- [x] Rate limiting e auditoria de uso em chamadas à API de IA
  - `/analyze` limitado a 10 req/min via `slowapi` (SlowAPIMiddleware)
  - `MAX_TOOL_ITERATIONS = 5` previne tool-use loop infinito (LLM10:2025)
  - `max_tokens=512` (especialistas) e `max_tokens=1024` (síntese) limitam custo
- [x] Modelo de IA sem acesso direto a sistemas de produção sem camada intermediária
  - Claude apenas chama tools via orchestrator — sem acesso direto a Redis, Qdrant ou infraestrutura
  - HOTL: humano executa remediação; Claude nunca acessa APIs de infraestrutura

---

## Cabeçalhos de Rastreabilidade AI

Arquivos gerados com assistência de IA que incluem marcação:

| Arquivo                                  | Marcação                                    | Revisado por    |
| ---------------------------------------- | ------------------------------------------- | --------------- |
| `agents/prompts.py`                      | `PROMPT_VERSION`, `PROMPT_CLASSIFICATION`   | Valdomiro Souza |
| `agents/orchestrator.py`                 | Docstring com AI-GENERATED + spec reference | Valdomiro Souza |
| `agents/specialists/base.py`             | Docstring com AI-GENERATED + spec reference | Valdomiro Souza |
| `docs/adr/active/ADR-2026-0001` a `0012` | Seção §7 AI Assistance em cada ADR          | Valdomiro Souza |
| `AgenticAI-Incident-Response.md`         | Campo AI-assisted em cada seção relevante   | Valdomiro Souza |

---

## LLM Observability

Métricas expostas via `/prometheus/metrics` e scrapeadas pelo Prometheus:

| Métrica                                | Tipo      | Labels                              | Alerta                  |
| -------------------------------------- | --------- | ----------------------------------- | ----------------------- |
| `llm_call_duration_seconds`            | Histogram | `call_type` (specialist\|synthesis) | p99 > 30s               |
| `llm_calls_total`                      | Counter   | `call_type`, `outcome`              | error rate > 5% em 5min |
| `llm_output_validation_failures_total` | Counter   | —                                   | > 3 em 10min            |
| `prompt_injection_sanitized_total`     | Counter   | `sanitization_type`                 | qualquer detecção       |

Grafana dashboard: `infra/grafana/` — painel Golden Signals inclui métricas LLM.
