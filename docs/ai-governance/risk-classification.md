# AI Risk Classification — AgenticAI-2-Incident-Response

**Classificação:** Medium Risk  
**Revisado por:** Valdomiro Souza  
**Data:** 2026-05-16  
**Aprovação:** Tech Lead (Valdomiro Souza) + SecOps (Valdomiro Souza)

---

## Sistema Avaliado

| Campo             | Valor                                                 |
| ----------------- | ----------------------------------------------------- |
| Sistema           | Agentic AI Copilot para Redução de MTTD/MTTR          |
| Modelo de IA      | Claude Sonnet 4.6 (`claude-sonnet-4-6`)               |
| Uso               | Análise de incidentes de TI (Golden Signals + RAG)    |
| Supervisão        | Human-on-the-Loop (HOTL) — ADR-2026-0006              |
| Dados processados | Métricas técnicas agregadas (P50/P95/P99, contadores) |

---

## Critérios de Classificação

### High Risk — NÃO SE APLICA

| Critério                                      | Avaliação                                               |
| --------------------------------------------- | ------------------------------------------------------- |
| IA toma decisões de crédito, saúde ou emprego | ❌ Não — análise de logs de infraestrutura              |
| IA tem acesso a PII de clientes               | ❌ Não — sem dados pessoais nos Golden Signals          |
| IA executa ações irreversíveis                | ❌ Não — HOTL garante que engenheiro executa remediação |

→ Sistema **não** se enquadra em High Risk do EU AI Act.

### Medium Risk — APLICÁVEL ✅

| Critério                              | Avaliação                                                                 |
| ------------------------------------- | ------------------------------------------------------------------------- |
| IA gera código para sistemas críticos | ⚠️ Parcial — IRA foi gerado com IA; em produção analisa sistemas críticos |
| IA analisa logs de produção           | ✅ Sim — analisa logs HAProxy e métricas Redis                            |
| IA em fluxos de resposta a incidentes | ✅ Sim — core use case do sistema                                         |

→ Sistema classificado como **Medium Risk**.

**Requisitos obrigatórios para Medium Risk:**

- [x] Review do Tech Lead (**Valdomiro Souza**)
- [x] Review do SecOps (**Valdomiro Souza**)
- [x] HOTL implementado — nenhuma ação autônoma (ADR-2026-0006)
- [x] Outputs validados com Pydantic v2 antes de uso (ADR-2026-0011)
- [x] Circuit breaker com fallback determinístico (ADR-2026-0010)
- [x] Prompt injection prevention ativo (LLM01:2025, `_sanitize_finding_text`)

---

## Controles de Mitigação Implementados

| Risco                                      | Controle                                                    | Evidência                    |
| ------------------------------------------ | ----------------------------------------------------------- | ---------------------------- |
| Hallucination estrutural (output inválido) | Pydantic `OrchestratorResponse.model_validate()`            | `app/models/llm_response.py` |
| Ação autônoma não autorizada               | HOTL — `recommended_actions` são sugestões                  | ADR-2026-0006, SDD §2.3      |
| Indisponibilidade do Claude API            | Circuit breaker + fallback rule-based                       | ADR-2026-0010                |
| Prompt injection via findings              | `_sanitize_finding_text()` — remove tags e redacta IPs      | `app/agents/orchestrator.py` |
| Vazamento de system prompt                 | `PROMPT_CLASSIFICATION="SENSITIVE"`, Semgrep CI             | `app/agents/prompts.py`      |
| Consumo ilimitado de tokens                | `MAX_TOOL_ITERATIONS=5`, `max_tokens` por chamada           | ADR-2026-0007                |
| PII em logs de análise                     | `[IP_REDACTED]`, `[HOST_REDACTED]` antes de envio ao Claude | LLM02:2025                   |

---

## Conformidade EU AI Act

O sistema está no escopo do **EU AI Act - Anexo III** (sistemas de IA de alto risco) somente se:

- Usado em decisões que afetam direitos fundamentais de pessoas físicas
- Usado em infraestrutura crítica para fins além de manutenção interna

**Avaliação:** O sistema analisa métricas técnicas de infraestrutura interna (logs HAProxy, Redis) para auxiliar engenheiros SRE. Não toma decisões sobre pessoas físicas. **Não se enquadra em Anexo III.**

---

## Revisão Periódica

Esta classificação deve ser reavaliada se:

- [ ] Sistema passar a processar dados de usuários finais (PII)
- [ ] Claude ganhar acesso a APIs de execução em produção (rollback, deploy, scaling)
- [ ] EU AI Act regulamentações nacionais (LGPD/Brasil) exigirem classificação diferente
- [ ] Após 1 ano sem revisão (2027-05-16)
