# ADR-2026-0007: Tool-Use Loop com 4 Agentes Especialistas em Paralelo

---

## Metadata

| Field            | Value                                                                    |
| ---------------- | ------------------------------------------------------------------------ |
| **ID**           | ADR-2026-0007                                                            |
| **Status**       | Accepted                                                                 |
| **Area**         | Architecture                                                             |
| **Author**       | Valdomiro Souza                                                          |
| **Reviewers**    | Orientador PPGCA/Unisinos                                                |
| **Created**      | 2026-05-14                                                               |
| **Approved**     | 2026-05-14                                                               |
| **Related spec** | SDD v1.7.0 §3.1 (IRA), §4 (Ciclo PRAL), §9.7 (Tool Use)                  |
| **AI-assisted**  | Yes — Claude Sonnet 4.6, trade-off analysis, reviewed by Valdomiro Souza |

---

## 1. Context and Problem

O sistema precisa analisar um incidente sob 4 perspectivas dos Golden Signals (Latency, Traffic, Errors, Saturation) simultaneamente. A questão arquitetural é: **como organizar a chamada a múltiplos agentes especialistas dentro de um único contexto LLM?**

Opções:

- **4 chamadas LLM sequenciais**: um agente por sinal, chamadas independentes
- **Tool-use loop**: Claude orquestra chamadas a tools que representam cada agente especialista
- **1 chamada LLM com prompt único**: análise de todos os sinais em uma única chamada massiva
- **Framework multi-agente externo** (LangChain, AutoGen, CrewAI): orquestração via framework

**Driving forces:**

- Análise dos 4 sinais é **independente entre si** — pode ser paralelizada
- Tool use nativo do Claude permite que o orquestrador decida **quais tools chamar e em qual ordem** (reasoning explícito)
- `asyncio.gather()` permite execução simultânea das 4 ferramentas — latência total ≈ max(t_latency, t_traffic, t_error, t_saturation) em vez de soma
- Sem dependência de frameworks externos (LangChain, CrewAI) — menos superfície de ataque, menos dependências

**Constraints:**

- `max_tokens=4096` por chamada Claude — contexto de tools deve ser compacto
- Anthropic SDK não suporta streaming de tool use em todas as versões — não há streaming no MVP
- Cada agente especialista chama `GET /metrics` via HTTP interno (Log-Ingestion :8000)

---

## 2. Decision

Adotamos **tool-use loop com 4 agentes especialistas executados em paralelo via `asyncio.gather()`**. O orquestrador Claude recebe um único prompt com os findings e decide quais ferramentas chamar; cada ferramenta encapsula a lógica de um agente especialista.

**Ferramentas registradas:**

| Tool                 | Responsabilidade                                       |
| -------------------- | ------------------------------------------------------ |
| `analyze_latency`    | Analisa P50/P95/P99, identifica degradação de latência |
| `analyze_traffic`    | Analisa RPS, detecta spikes ou quedas anômalas         |
| `analyze_errors`     | Analisa taxa 4xx/5xx, identifica padrões de erro       |
| `analyze_saturation` | Analisa uso de memória Redis, detecta saturação        |

**Scope:**

- Applies to: Incident-Response-Agent (:8001) — `orchestrator.py`, `agents/`
- Does not apply to: Knowledge-Base (RAG é chamado separadamente antes do loop de tools)

---

## 3. Alternatives Considered

| Alternative                                    | Pros                                                                                        | Cons                                                                                                           | Reason for Rejection                                                       |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **Tool-use loop paralelo (escolhido)**         | Paralelismo nativo, reasoning explícito do orquestrador, sem frameworks externos, auditável | Tool use aumenta número de tokens (~+20%); Anthropic cobra por tool call tokens                                | — Escolhido                                                                |
| 4 chamadas LLM sequenciais                     | Simples, independentes, fáceis de debugar                                                   | Latência ~4× maior (cada chamada ~5–15 s); custo ~4× maior; sem reasoning holístico entre sinais               | Latência inaceitável para SLO de 60 s com 4 agentes                        |
| 1 chamada LLM com prompt único                 | Custo mínimo, latência mínima                                                               | Prompt massivo (>8k tokens com findings de 4 sinais); sem isolamento de análise por sinal; difícil de auditar  | Context window sobrecarregado; análise menos estruturada                   |
| LangChain / CrewAI / AutoGen                   | Abstrações ricas para multi-agente, callbacks, memory                                       | Dependência externa (~500 MB); breaking changes frequentes; obscurece o funcionamento do sistema (dissertação) | Dependência desnecessária que obscurece a arquitetura para fins acadêmicos |
| Agente único sem tool use (análise rule-based) | Zero latência LLM, determinístico                                                           | Sem capacidade de raciocínio contextual; análise superficial; não atende objetivo da dissertação               | Substitui objeto de pesquisa (IA generativa) por heurísticas               |

---

## 4. Consequences

### Positive

- `asyncio.gather(analyze_latency(), analyze_traffic(), analyze_errors(), analyze_saturation())` reduz latência total de ~40 s (sequencial) para ~12 s (paralelo)
- Cada agente retorna `SpecialistFinding` com `signal`, `severity`, `details`, `recommendations` — output estruturado e validável
- Claude decide autonomamente se chama todos os 4 ou apenas os relevantes (tool choice = `auto`) — reasoning transparente
- Facilidade de adicionar 5º agente (ex: `analyze_dependencies`) sem refatoração do orquestrador

### Negative / Trade-offs

- Tool use aumenta uso de tokens ~20% vs prompt único — custo marginal de ~$0.002 por análise
- `asyncio.gather()` com `return_exceptions=True` — falha de um agente não bloqueia os demais, mas requer tratamento explícito de exceções parciais
- Debugging mais complexo: falha no tool use requer rastreamento da mensagem de erro no ciclo de tool call/result

### Risks

| Risk                                        | Probability | Impact | Mitigation                                                                         |
| ------------------------------------------- | ----------- | ------ | ---------------------------------------------------------------------------------- |
| Claude não chama todas as 4 tools esperadas | Baixo       | Médio  | `tool_choice={"type": "auto"}` com fallback rule-based se `specialist_findings=[]` |
| Tool result excede context window           | Baixo       | Médio  | `MAX_FINDING_LENGTH=500` trunca cada finding antes de retornar                     |
| Rate limit Anthropic durante parallelism    | Baixo       | Alto   | Circuit breaker com retry backoff exponencial (ADR-2026-0010)                      |

### Tech Debt Introduced

- `analyze_saturation` lê `INFO memory` diretamente do Redis via metrics API — não há tool de saturation de CPU/disco (corpus de dissertação é suficiente mas incompleto)

---

## 5. Future Review Criteria

Esta ADR deve ser revisitada se:

- [ ] 5º sinal (ex: dependency health) for adicionado — verificar se paralelismo ainda é ótimo
- [ ] Anthropic lançar suporte a tool use streaming (pode reduzir latência percebida)
- [ ] Latência de análise ultrapassar SLO de 60 s consistentemente com 4 tools em paralelo
- [ ] Framework multi-agente (ex: Anthropic Agent SDK) atingir maturidade suficiente para substituição sem dependência excessiva
- [ ] Após 2 anos sem revisão (2028-05-14)

---

## 6. References

- SDD v1.7.0 §3.1 — Incident-Response-Agent
- SDD v1.7.0 §4 — Ciclo PRAL (fase Reasoning)
- SDD v1.7.0 §9.7 — Tool Use (Anthropic)
- `Incident-Response-Agent/app/agents/orchestrator.py` — `asyncio.gather()`, tool registration
- `Incident-Response-Agent/app/agents/` — `latency_agent.py`, `traffic_agent.py`, `error_agent.py`, `saturation_agent.py`

---

## 7. AI Assistance

| Field                      | Value                                                                                 |
| -------------------------- | ------------------------------------------------------------------------------------- |
| **AI used**                | Claude Sonnet 4.6                                                                     |
| **AI role**                | Comparação de padrões de orquestração multi-agente, análise de trade-offs de latência |
| **Output reviewed by**     | Valdomiro Souza                                                                       |
| **Final decision made by** | Valdomiro Souza                                                                       |

---

## 8. Approval

| Role       | Name            | Date       | Decision   |
| ---------- | --------------- | ---------- | ---------- |
| Author     | Valdomiro Souza | 2026-05-14 | Proposes   |
| Tech Lead  | Valdomiro Souza | 2026-05-14 | ✅ Approve |
| Orientador | PPGCA/Unisinos  | 2026-05-14 | ✅ Approve |
