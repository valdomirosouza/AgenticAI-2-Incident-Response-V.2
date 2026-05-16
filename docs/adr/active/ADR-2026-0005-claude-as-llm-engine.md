# ADR-2026-0005: Anthropic Claude (claude-sonnet-4-6) como Motor LLM

---

## Metadata

| Field            | Value                                                                    |
| ---------------- | ------------------------------------------------------------------------ |
| **ID**           | ADR-2026-0005                                                            |
| **Status**       | Accepted                                                                 |
| **Area**         | Architecture                                                             |
| **Author**       | Valdomiro Souza                                                          |
| **Reviewers**    | Orientador PPGCA/Unisinos                                                |
| **Created**      | 2026-05-14                                                               |
| **Approved**     | 2026-05-14                                                               |
| **Related spec** | SDD v1.7.0 §3.1, §4 (Ciclo PRAL), §9.6                                   |
| **AI-assisted**  | Yes — Claude Sonnet 4.6, trade-off analysis, reviewed by Valdomiro Souza |

---

## 1. Context and Problem

O sistema precisa de um motor LLM para orquestrar 4 agentes especialistas (Latency, Traffic, Error, Saturation) no ciclo PRAL (Perceive → Reasoning → Act → Learn). Os requisitos são:

- **Context window ≥ 100k tokens**: análise de incidente consome findings de 4 agentes + histórico RAG + system prompt (~15k tokens por chamada)
- **Tool use nativo**: agentes precisam chamar ferramentas (fetch_metrics, search_kb, rule_based_analysis) de forma estruturada
- **Latência aceitável para análise**: SLO de resposta ≤ 60 s (análise não é real-time)
- **Saída JSON estruturada e validável**: output deve ser parseável por Pydantic v2 (`OrchestratorResponse`)
- **SDK Python oficial**: integração com `asyncio` e suporte a streaming

**Driving forces:**

- Anthropic SDK Python (`anthropic==0.25.8`) tem suporte nativo a tool use e JSON mode
- Claude Sonnet 4.6 supera GPT-4o em raciocínio multi-step para análise de incidentes (benchmarks internos)
- `ANTHROPIC_API_KEY` isolada no IRA — decisão de segurança alinhada com ADR-2026-0001
- Dissertação usa Claude como objeto de pesquisa — coerência metodológica

**Constraints:**

- API externa (sem modelo local) — latência de rede ~2–10 s por chamada
- Custo por token: Sonnet 4.6 ~$3/MTok input, ~$15/MTok output — aceitável para corpus de dissertação
- `ANTHROPIC_API_KEY` obrigatória em produção (validada por `@model_validator`)

---

## 2. Decision

Adotamos **Anthropic Claude (modelo `claude-sonnet-4-6`)** como motor LLM exclusivo do Incident-Response-Agent, via `anthropic==0.25.8` SDK Python.

**Scope:**

- Applies to: Incident-Response-Agent (:8001) — `orchestrator.py`, prompts em `agents/prompts.py`
- Does not apply to: embeddings (→ `all-MiniLM-L6-v2`, ADR-2026-0008), análise rule-based de fallback (→ ADR-2026-0010)

---

## 3. Alternatives Considered

| Alternative                       | Pros                                                                         | Cons                                                                                              | Reason for Rejection                                              |
| --------------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| **Claude Sonnet 4.6 (escolhido)** | Tool use nativo, 200k context, JSON mode, SDK Python maduro, suporte asyncio | API externa (latência de rede); custo por token; dependência de provedor único                    | — Escolhido                                                       |
| GPT-4o (OpenAI)                   | Tool use nativo, JSON mode, ecossistema amplo                                | Sem vantagem técnica sobre Claude para este caso; mudaria objeto de pesquisa da dissertação       | Dissertação pesquisa especificamente capacidades de Claude em SRE |
| Llama 3 70B (local/Ollama)        | Zero custo, sem dependência de cloud, privacidade total                      | Context window 8k (insuficiente para análise multi-agente); tool use instável; GPU não disponível | Context window insuficiente; hardware indisponível                |
| Mistral Large (Mistral AI)        | Competitivo em raciocínio, API europeia (GDPR)                               | Tool use menos maduro que Claude; SDK Python em beta; menos documentação para casos de uso SRE    | Maturidade de SDK inferior; dissertação foca em Claude            |
| Gemini 1.5 Pro (Google)           | Context window 1M tokens, multimodal                                         | Tool use em beta no momento da decisão; SDK Python menos maduro para asyncio                      | Maturidade insuficiente no momento da decisão (2026-05-14)        |
| "Do nothing" (rule-based apenas)  | Zero custo, zero latência, determinístico                                    | Sem capacidade de raciocínio contextual; análise superficial; não atende objetivo de dissertação  | Inaceitável para pesquisa de IA generativa aplicada a SRE         |

---

## 4. Consequences

### Positive

- Tool use estruturado permite que Claude chame `fetch_metrics()`, `search_kb()`, `rule_based_analysis()` de forma controlada e auditável
- `messages=[{"role": "user", "content": prompt}]` com `max_tokens=4096` limita custo por chamada
- Circuit breaker (`ADR-2026-0010`) protege contra falha da API Anthropic — fallback rule-based disponível
- Prompt classification `SENSITIVE` (LLM07:2025) protege system prompts de vazamento em logs

### Negative / Trade-offs

- Dependência de provedor único (Anthropic) — sem fallback LLM equivalente (rule-based é degradação, não substituição)
- Latência ~5–15 s por chamada (aceitável para SLO de 60 s, inaceitável para real-time)
- Custo cresce linearmente com número de análises — monitorado via API dashboard Anthropic

### Risks

| Risk                                  | Probability | Impact | Mitigation                                                            |
| ------------------------------------- | ----------- | ------ | --------------------------------------------------------------------- |
| API Anthropic indisponível            | Baixo       | Alto   | Circuit breaker + fallback rule-based (ADR-2026-0010)                 |
| Mudança de preço ou rate limit        | Médio       | Médio  | `max_tokens=4096` limita custo; retry com backoff exponencial         |
| Model deprecation (claude-sonnet-4-6) | Médio       | Alto   | Configurável em `config.py`; ADR revisada em EOL                      |
| Prompt injection via findings         | Médio       | Alto   | `_sanitize_finding_text()` remove tags system/human/assistant (LLM01) |

### Tech Debt Introduced

- Modelo hardcoded em `config.py` (`model_name: str = "claude-sonnet-4-6"`) — deve ser atualizado quando nova versão for lançada

---

## 5. Future Review Criteria

Esta ADR deve ser revisitada se:

- [ ] `claude-sonnet-4-6` atingir EOL (verificar anthropic.com/changelog)
- [ ] Requisito de análise em < 5 s emergir (considerar modelo menor ou streaming)
- [ ] Custo mensal ultrapassar orçamento acadêmico (considerar Llama local com GPU)
- [ ] Modelo open-source local atingir paridade em tool use e context window
- [ ] Após 2 anos sem revisão (2028-05-14)

---

## 6. References

- SDD v1.7.0 §4 — Ciclo PRAL (Perceive → Reasoning → Act → Learn)
- SDD v1.7.0 §9.6 — Stack tecnológico
- `Incident-Response-Agent/app/config.py` — `model_name`, `max_tokens`, `temperature`
- `Incident-Response-Agent/app/agents/orchestrator.py` — chamada à API Anthropic
- `Incident-Response-Agent/app/agents/prompts.py` — system prompts (SENSITIVE)

---

## 7. AI Assistance

| Field                      | Value                                                                   |
| -------------------------- | ----------------------------------------------------------------------- |
| **AI used**                | Claude Sonnet 4.6                                                       |
| **AI role**                | Comparação de modelos LLM, análise de trade-offs de tool use e latência |
| **Output reviewed by**     | Valdomiro Souza                                                         |
| **Final decision made by** | Valdomiro Souza                                                         |

---

## 8. Approval

| Role       | Name            | Date       | Decision   |
| ---------- | --------------- | ---------- | ---------- |
| Author     | Valdomiro Souza | 2026-05-14 | Proposes   |
| Tech Lead  | Valdomiro Souza | 2026-05-14 | ✅ Approve |
| Orientador | PPGCA/Unisinos  | 2026-05-14 | ✅ Approve |
