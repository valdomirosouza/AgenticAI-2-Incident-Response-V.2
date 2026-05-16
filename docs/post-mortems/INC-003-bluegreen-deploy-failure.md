# Post-Mortem: INC-003 — Falha de Deploy Blue/Green com Cascata de 5xx

**Data:** 2026-05-16  
**Duração:** ~18 minutos (02:04 UTC → 02:22 UTC)  
**Severidade:** SEV1 — Crítico (impacto direto em receita: checkout e pagamentos)  
**Status:** Resolvido ✓

---

## Resumo Executivo

Durante o deploy blue/green da versão `backend_app_v1 → v2`, a nova instância entrou em estado de inicialização lenta por causa de uma query Redis bloqueante no startup. O HAProxy roteou 37% do tráfego para `backend_app_v2` antes do health check confirmar prontidão, causando:

- **P95** de 178ms → 7681ms (43x acima do threshold de 500ms)
- **P99** de 179ms → 8672ms (8.7x acima do threshold de 1000ms)
- **Taxa de 5xx** de 0% → 32.5% (6.5x acima do threshold crítico de 5%)
- **Endpoints afetados:** `/api/checkout`, `/api/payments` (impacto financeiro direto)
- **MTTD:** < 2 minutos (acionado pelo Agentic AI Copilot via POST /analyze)
- **MTTR:** ~18 minutos (rollback executado pelo engenheiro on-call)

O Agentic AI Copilot identificou corretamente o padrão bimodal (P50 saudável vs. P95/P99 explosivos), recuperou incidente similar INC-002 da Knowledge Base (score=0.534), e emitiu recomendação explícita de rollback imediato.

---

## Linha do Tempo

| Horário (UTC) | Evento                                                                         |
| ------------- | ------------------------------------------------------------------------------ |
| 02:00         | Deploy blue/green iniciado: `backend_app_v1` → `v2`                           |
| 02:01         | HAProxy começa a rotear para `v2` (37% do tráfego) — health check não aguardou |
| 02:02         | P95 sobe para 566ms, 5xx=3% — SLO Availability entra em breach                |
| 02:04         | P95=7681ms, 5xx=32.5% — SEV1 declarado. Engenheiro on-call acionado            |
| 02:04:52      | `POST /analyze` disparado pelo engenheiro                                      |
| 02:05:55      | IncidentReport recebido: `severity=critical`, `incident_commander_brief` emitido |
| 02:06         | Engenheiro confirma `backend_app_v2` no pool → ROLLBACK INICIADO              |
| 02:07         | HAProxy remove `backend_app_v2` do pool, drena conexões                        |
| 02:10         | Tráfego 100% em `v1`. P50 normaliza para 175ms                                 |
| 02:22         | P95/P99 iniciam recuperação. Erros 5xx em queda (14.86% janela acumulada)       |

---

## Análise de Causa Raiz

### Causa Raiz (Root Cause)
**Ausência de health check baseado em comportamento no processo de deploy.**
`backend_app_v2` entrou no pool do HAProxy assim que o processo iniciou (TCP `LISTEN`), antes de completar a inicialização da aplicação — que inclui uma query Redis de warmup que bloqueia por 3-9 segundos em ambientes com latência de rede.

### Gatilho (Trigger)
**Deploy blue/green sem readiness probe adequado.**
O health check do HAProxy verificava apenas conectividade TCP (porta 8001), não a rota `/health` da aplicação FastAPI. O processo sobe e escuta na porta antes de estar pronto para servir requisições.

### Fator Agravante
HAProxy configurado com peso 37% para `backend_api_v1` e `backend_app_v1` cada, e o novo `backend_app_v2` com o mesmo peso (37%), resultando em quase 40% do tráfego sendo enviado para a instância travada durante o deploy.

---

## Impacto

| Métrica                | Valor                                    |
| ---------------------- | ---------------------------------------- |
| Duração do incidente   | ~18 minutos                              |
| Requisições afetadas   | ~52 de 160 (32.5% durante pico)          |
| Endpoints críticos     | `/api/checkout`, `/api/payments`         |
| Error budget consumido | 100% (Availability + Latency P95 + P99)  |
| MTTD                   | < 2 minutos (Agentic AI Copilot)         |
| MTTR                   | ~18 minutos (rollback manual)            |
| Impacto em receita     | Checkout e payments falhando por ~6 min  |

---

## Ações de Remediação (Imediata)

1. ✅ **Rollback executado:** `backend_app_v2` removido do pool HAProxy imediatamente
2. ✅ **Tráfego restaurado:** 100% roteado para `backend_app_v1` após drenagem de conexões
3. ✅ **Checkout e payments confirmados operacionais** após rollback
4. ✅ **Análise do IncidentReport** — root cause confirmado: startup sem readiness probe

---

## Ações Preventivas (Longo Prazo)

| Prioridade | Ação                                                                    | Responsável | Prazo   |
| ---------- | ----------------------------------------------------------------------- | ----------- | ------- |
| P0         | Adicionar readiness probe HTTP (`GET /health`) no HAProxy com threshold de 3 checks consecutivos antes de entrar no pool | SRE | 1 semana |
| P0         | Implementar deploy em canary progressivo: 1% → 5% → 25% → 100%, com gate automático no P95 | DevOps | 2 semanas |
| P1         | Configurar circuit breaker no HAProxy: remover backend automaticamente quando error rate > 10% por 60s | SRE | 1 semana |
| P1         | Adicionar Redis maxmemory e eviction policy ao processo de startup do backend | Dev | 1 semana |
| P2         | Integrar `POST /analyze` ao pipeline de CD: análise automática após cada deploy, com rollback automático se `severity=critical` | DevOps/AI | 1 mês |
| P2         | Configurar alerta Grafana para P95 > 300ms (early warning antes de breaching) | SRE | 2 semanas |

---

## Papel do Agentic AI Copilot no Incidente

O sistema funcionou conforme o modelo HOTL (Human-on-the-Loop):

**O que o agente fez:**
- Detectou o padrão bimodal (P50 saudável + P95/P99 críticos) — diagnóstico correto
- Recuperou INC-002 da Knowledge Base (deploy similar, score=0.534) como contexto histórico
- Emitiu `incident_commander_brief` com recomendação clara e acionável em 63 segundos
- Classificou corretamente como SEV1 / `critical` com `escalation_recommended: false`

**O que o humano fez:**
- Validou o diagnóstico do agente
- Executou o rollback (ação de remediação — não automatizável pelo HOTL)
- Declarou o incidente resolvido após confirmar normalização

**Limitação identificada:**
- `TrafficAgent` atingiu o limite de 5 iterações de tool-use sem completar a análise de distribuição de backends — blind spot que seria relevante para confirmar o deploy como trigger

---

## Lições para a Knowledge Base

- Deploy blue/green sem readiness probe HTTP → latência explosiva no startup da aplicação
- Padrão bimodal (P50 saudável + P95/P99 críticos) → indica falha em subconjunto de instâncias, não saturação global
- MTTD < 2min com Agentic AI Copilot vs. estimativa manual de 15-30min (SRE tradicional)
- Health check TCP (porta aberta) ≠ readiness HTTP (aplicação pronta)
- Rollback como primeira ação defensiva quando deploy coincide com degradação crítica

---

## Referências

- INC-002: Latency Spike no Deploy Blue/Green (padrão similar, menor severidade)
- SDD §9.2.1 — Princípio do menor privilégio e isolamento de rede
- SDD §9.13.3 — Modelo SoS Responder / Tech IRT (Google IMAG)
- Google SRE Book, Cap. 14 — Managing Incidents
- Google SRE Book, Cap. 15 — Postmortem Culture
