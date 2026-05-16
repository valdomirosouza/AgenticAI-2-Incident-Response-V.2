# ADR-2026-0010: Circuit Breaker com Fallback Rule-Based para Anthropic API

---

## Metadata

| Field            | Value                                                                    |
| ---------------- | ------------------------------------------------------------------------ |
| **ID**           | ADR-2026-0010                                                            |
| **Status**       | Accepted                                                                 |
| **Area**         | Architecture                                                             |
| **Author**       | Valdomiro Souza                                                          |
| **Reviewers**    | Orientador PPGCA/Unisinos                                                |
| **Created**      | 2026-05-15                                                               |
| **Approved**     | 2026-05-15                                                               |
| **Related spec** | SDD v1.7.0 §3.1 (IRA), §8.3 (Resiliência), §9.5 (Circuit Breaker)        |
| **AI-assisted**  | Yes — Claude Sonnet 4.6, trade-off analysis, reviewed by Valdomiro Souza |

---

## 1. Context and Problem

O Incident-Response-Agent depende exclusivamente da Anthropic API para análise de incidentes. Falhas na API externa (rate limit, timeout, erro 5xx, indisponibilidade) sem tratamento adequado resultam em:

- `500 Internal Server Error` propagado ao cliente
- Análise de incidente bloqueada enquanto o incidente ainda está ativo
- Sem diagnóstico útil mesmo que regras heurísticas locais possam fornecer análise parcial

**Driving forces:**

- SRE principle: **graceful degradation** — sistema deve continuar útil mesmo com degradação parcial
- Análise rule-based (thresholds de latência, taxa de erro) é possível sem LLM e produz findings úteis
- `tenacity` oferece retry com backoff exponencial sem implementação manual de estado
- Circuit breaker evita cascata de chamadas a API indisponível — protege rate limit e reduz latência de falha

**Constraints:**

- Sem biblioteca de circuit breaker dedicada (evitar overhead de `pybreaker`, `resilience4j-python`)
- Fallback deve retornar `IncidentReport` completo (mesmo schema) — cliente não deve distinguir fallback de análise LLM
- `ANTHROPIC_API_KEY` ausente em desenvolvimento — fallback deve ativar automaticamente

---

## 2. Decision

Adotamos **circuit breaker com estado local + retry backoff exponencial (tenacity) + fallback rule-based** para todas as chamadas à Anthropic API no orchestrator.

**Estados do circuit breaker:**

| Estado    | Condição de Entrada              | Comportamento                                           |
| --------- | -------------------------------- | ------------------------------------------------------- |
| Closed    | < `failure_threshold` falhas     | Chamadas normais à API Anthropic                        |
| Open      | ≥ `failure_threshold` falhas     | Retorna fallback imediatamente, sem chamar API          |
| Half-Open | Após `recovery_timeout` segundos | Tenta 1 chamada real; fecha se sucesso, reabre se falha |

**Scope:**

- Applies to: Incident-Response-Agent (:8001) — `orchestrator.py`
- Does not apply to: Knowledge-Base (Qdrant falha retorna `[]` sem circuit breaker formal), Log-Ingestion (Redis falha retorna erro 503 direto)

---

## 3. Alternatives Considered

| Alternative                                        | Pros                                                                            | Cons                                                                                                 | Reason for Rejection                                                 |
| -------------------------------------------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **Circuit breaker + retry + fallback (escolhido)** | Degradação graciosa, retry automático, fallback com mesmo schema, sem lib extra | Estado do circuit breaker é por-processo (perdido em restart); fallback é análise rasa vs Claude     | — Escolhido; resiliência suficiente para corpus de dissertação       |
| Sem circuit breaker (fail-fast puro)               | Simples, sem estado                                                             | 500 propagado para cliente durante falha da API; análise bloqueada durante incidente ativo           | Inaceitável para sistema de resposta a incidentes                    |
| `pybreaker` library                                | Circuit breaker maduro, thread-safe, métricas integradas                        | Dependência extra; API síncrona (sem suporte asyncio nativo); mais complexo que necessário           | Overhead desnecessário; implementação simples suficiente para escopo |
| Retry infinito sem circuit breaker                 | Eventualmente sucesso                                                           | Bloqueia request indefinidamente; cascata de chamadas durante outage prolongado; rate limit esgotado | Pior que falha rápida — agrava outage da API                         |
| Cache de última análise bem-sucedida               | Zero latência para análises repetidas                                           | Cache staleness inaceitável para incidentes (cada análise é de um incidente diferente)               | Semântica incorreta para caso de uso de análise de incidentes        |

---

## 4. Consequences

### Positive

- `@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))` (tenacity) cobre falhas transitórias sem código de retry manual
- Fallback rule-based produz `IncidentReport` com findings baseados em thresholds: P95 > 500 ms, error_rate > 5%, etc.
- `circuit_breaker_state: "open"` incluído no `IncidentReport.metadata` — operador sabe que análise foi rule-based
- Em desenvolvimento sem `ANTHROPIC_API_KEY`, fallback ativa automaticamente — testes offline funcionam

### Negative / Trade-offs

- Fallback rule-based é análise superficial: sem reasoning contextual, sem RAG, sem correlação entre sinais
- Estado do circuit breaker é em memória por processo — múltiplas instâncias do IRA não compartilham estado
- `failure_threshold=5` e `recovery_timeout=60s` são valores empíricos — podem precisar de ajuste em produção

### Risks

| Risk                                          | Probability | Impact | Mitigation                                                                            |
| --------------------------------------------- | ----------- | ------ | ------------------------------------------------------------------------------------- |
| Circuit breaker abre durante análise crítica  | Baixo       | Alto   | Fallback garante `IncidentReport` com análise parcial; operador alertado via metadata |
| Fallback retorna falsos negativos             | Médio       | Médio  | Fallback é conservador: thresholds calibrados para baixa taxa de falso negativo       |
| `tenacity` não importado corretamente no mock | Baixo       | Baixo  | `requirements.txt` pinado com hash; testado em CI                                     |

### Tech Debt Introduced

- Estado do circuit breaker não é compartilhado entre instâncias — em deploy multi-instância, cada réplica tem estado independente

---

## 5. Future Review Criteria

Esta ADR deve ser revisitada se:

- [ ] IRA for deployado com múltiplas réplicas (considerar circuit breaker distribuído via Redis)
- [ ] Anthropic API atingir SLA de 99.9% — rever se circuit breaker é necessário
- [ ] Fallback rule-based produzir falsos negativos em incidentes reais — rever thresholds
- [ ] Após 2 anos sem revisão (2028-05-14)

---

## 6. References

- SDD v1.7.0 §8.3 — Resiliência e Degradação Graciosa
- SDD v1.7.0 §9.5 — Circuit Breaker Pattern (Michael Nygard, Release It!)
- `Incident-Response-Agent/app/agents/orchestrator.py` — `_call_anthropic_with_circuit_breaker()`
- `Incident-Response-Agent/app/agents/fallback.py` — `rule_based_analysis()`
- `tenacity` docs: `stop_after_attempt`, `wait_exponential`

---

## 7. AI Assistance

| Field                      | Value                                                                           |
| -------------------------- | ------------------------------------------------------------------------------- |
| **AI used**                | Claude Sonnet 4.6                                                               |
| **AI role**                | Análise de padrões de resiliência, comparação de bibliotecas de circuit breaker |
| **Output reviewed by**     | Valdomiro Souza                                                                 |
| **Final decision made by** | Valdomiro Souza                                                                 |

---

## 8. Approval

| Role       | Name            | Date       | Decision   |
| ---------- | --------------- | ---------- | ---------- |
| Author     | Valdomiro Souza | 2026-05-15 | Proposes   |
| Tech Lead  | Valdomiro Souza | 2026-05-15 | ✅ Approve |
| Orientador | PPGCA/Unisinos  | 2026-05-15 | ✅ Approve |
