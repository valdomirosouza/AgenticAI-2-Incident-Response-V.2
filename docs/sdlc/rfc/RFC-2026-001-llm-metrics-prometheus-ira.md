# RFC-2026-001: LLM Observability — Prometheus Endpoint no IRA + Métricas AI Governance

## Metadata

| Campo                     | Valor                                         |
| ------------------------- | --------------------------------------------- |
| **ID**                    | RFC-2026-001                                  |
| **Tipo**                  | Normal                                        |
| **Solicitante**           | Valdomiro Souza                               |
| **Data de solicitação**   | 2026-05-16                                    |
| **Janela de execução**    | 2026-05-16 01:00–02:00 BRT                    |
| **Spec relacionada**      | SDD v1.7.0 §7.3, ADR-2026-0005, ADR-2026-0007 |
| **Incidente relacionado** | —                                             |
| **Status**                | ✅ Executado                                  |

---

## Descrição da Mudança

Adição de endpoint `/prometheus/metrics` ao serviço Incident-Response-Agent (IRA), com 4 novas métricas de observabilidade LLM e instrumentação dos agentes especialistas e orquestrador.

**O que muda:**

- `app/llm_metrics.py` — novo módulo com 4 métricas Prometheus
- `app/agents/specialists/base.py` — timing de chamadas de especialistas (histogram + counter)
- `app/agents/orchestrator.py` — timing de síntese + contadores por outcome + prompt injection counter
- `app/auth.py` — nova função `require_prometheus_key`
- `app/config.py` — novo campo `prometheus_api_key`
- `app/main.py` — `Instrumentator().expose()` com autenticação

**Ambiente:** Desenvolvimento/dissertação (docker-compose local)

---

## Motivação

O skill `ai-governance` (OWASP A09:2021 + AI Governance) exige LLM observability com métricas de latência, taxa de erro, falhas de validação e detecção de injeção. O IRA não expunha `/prometheus/metrics` — o Prometheus configurado em `prometheus.yml` já tinha `incident-response-agent` como scrape target mas sem endpoint funcional.

---

## Impacto Esperado

| Campo                                | Avaliação                                                                    |
| ------------------------------------ | ---------------------------------------------------------------------------- |
| **Sistemas afetados**                | Incident-Response-Agent (:8001), Prometheus (:9090), Grafana (:3000)         |
| **Usuários afetados durante janela** | Nenhum (ambiente local, fora de produção)                                    |
| **Downtime esperado**                | Não — mudança aditiva; sem modificação de lógica existente                   |
| **Impacto no SLO**                   | Zero — endpoint `/prometheus/metrics` não está no caminho crítico de análise |

---

## Plano de Execução

| Passo | Ação                                                                    | Owner          | Duração estimada |
| ----- | ----------------------------------------------------------------------- | -------------- | ---------------- |
| 1     | Criar `llm_metrics.py` com 4 métricas Prometheus                        | Valdomiro      | 10 min           |
| 2     | Adicionar `prometheus_api_key` ao `config.py` e validator               | Valdomiro      | 5 min            |
| 3     | Adicionar `require_prometheus_key` ao `auth.py`                         | Valdomiro      | 5 min            |
| 4     | Instrumentar `base.py` com timing de especialistas                      | Valdomiro      | 10 min           |
| 5     | Instrumentar `orchestrator.py` com synthesis timing + injection counter | Valdomiro      | 15 min           |
| 6     | Adicionar `Instrumentator` ao `main.py`                                 | Valdomiro      | 5 min            |
| 7     | Rodar suite de testes (202 testes, cobertura ≥ 85%)                     | CI / Valdomiro | 10 min           |
| 8     | Verificar `/prometheus/metrics` retorna métricas via `curl`             | Valdomiro      | 5 min            |

---

## Plano de Rollback

**Trigger:** Qualquer teste falhando ou erro de import no IRA  
**Tempo máximo antes de rollback:** 15 minutos após deploy  
**Procedimento:**

```bash
git revert HEAD  # reverte apenas as mudanças de AI Governance
docker compose restart incident-response-agent
```

**Testado em:** Sim — mudança aditiva, sem alteração de comportamento existente. Rollback é `git revert` simples.

---

## Pré-Mudança Verificações

- [x] Executado em ambiente de desenvolvimento com dados representativos (suite de 202 testes)
- [x] Plano de rollback testado (git revert — mudança aditiva)
- [x] Monitoramento configurado para a janela (`docker compose logs -f incident-response-agent`)
- [x] `prometheus_api_key` documentado em `.env.example` (DEBT-2026-005)

---

## Resultado (pós-execução)

| Métrica            | Valor                                                  |
| ------------------ | ------------------------------------------------------ |
| Testes antes       | 188 (IRA)                                              |
| Testes depois      | 202 (IRA) — +14 em `test_llm_metrics.py`               |
| Cobertura          | 98.32% → 97.30% (14 novos testes cobrindo llm_metrics) |
| Commit             | `af37c55`                                              |
| Incidentes gerados | Nenhum                                                 |

---

## Aprovação

| Papel       | Nome            | Data       | Decisão                                                       |
| ----------- | --------------- | ---------- | ------------------------------------------------------------- |
| Solicitante | Valdomiro Souza | 2026-05-16 | Propõe                                                        |
| Tech Lead   | Valdomiro Souza | 2026-05-16 | ✅ Aprovado                                                   |
| SecOps      | Valdomiro Souza | 2026-05-16 | ✅ Aprovado (sem impacto de segurança — endpoint autenticado) |
