# Post-Mortem: INC-002 — Latency Spike no Deploy Blue/Green

**Data:** 2026-05-02  
**Duração do impacto:** 18 minutos (14:41 – 14:59 UTC)  
**Severidade:** P3 — WARNING  
**Incident Commander:** Valdomiro Souza  
**Status:** Resolvido ✓

---

## Resumo Executivo

Durante um deploy blue/green do serviço `log-ingestion` (v1.3.0 → v1.4.0), a instância nova ficou em estado `starting` por 3 minutos além do esperado devido a uma query Redis ao inicializar. Nesse período, o HAProxy roteou 60% do tráfego para a instância nova que ainda não estava pronta, causando latência P99 de 2.3s (limiar: 1s).

O Agentic AI Copilot detectou o degradation em 47 segundos após o início, classificou como WARNING (não CRITICAL porque a taxa de erros 5xx permaneceu < 1%) e gerou o `incident_commander_brief`:

> *"Latency spike detected during deploy — monitor for 5 minutes before rollback decision."*

O engenheiro on-call decidiu aguardar (HOTL), e a latência normalizou após a instância nova completar o warmup.

---

## Timeline

| Horário UTC | Evento |
|---|---|
| 14:38 | Deploy v1.4.0 iniciado via CI/CD |
| 14:41 | HAProxy começa a rotear para instância nova (ainda em warmup) |
| 14:41:47 | P99 cruza 500ms — LatencyAgent detecta WARNING |
| 14:42:34 | `POST /analyze` executado automaticamente — findings: Latency WARNING, outros OK |
| 14:42:41 | On-call notificado via Grafana alert `IncidentWarning` |
| 14:44 | P99 atinge pico de 2.3s — Copilot reclassifica para CRITICAL |
| 14:44:22 | On-call decide aguardar (HOTL decision) baseado no brief do IC |
| 14:59 | Instância nova completamente aquecida — P99 volta a 120ms |
| 15:05 | Incidente encerrado |

---

## Causa Raiz e Gatilho

**Root cause (vulnerabilidade sistêmica):**  
O `log-ingestion` não tem fase de warmup explícita — a instância começa a receber tráfego antes de ter estabelecido o pool de conexões Redis e carregado os módulos Python em memória.

**Trigger (condição ambiental):**  
Deploy blue/green sem readiness probe no HAProxy. O healthcheck HTTP `/health` retorna 200 imediatamente mas não garante que o pipeline Redis está pronto.

**Como o Copilot ajudou:**  
- MTTD reduzido de ~8 min (alarme manual) para **47 segundos**
- O `incident_commander_brief` contextualizou corretamente que era um evento de deploy, evitando rollback desnecessário

---

## Análise de Impacto

- Usuários afetados: ~30% das requisições com P99 > 1s por 18 min
- SLO: P99 < 1s em 99.9% do tempo → violação de 0.021% (dentro da error budget)
- Receita: sem impacto direto (sistema de dissertação, ambiente controlado)

---

## Ações Corretivas

| Ação | Responsável | Prazo | Status |
|---|---|---|---|
| Adicionar readiness probe no docker-compose (verificar Redis ping antes de ready) | Valdomiro | 2026-05-09 | ✓ Concluído |
| Configurar warmup delay de 10s antes de aceitar tráfego | Valdomiro | 2026-05-09 | ✓ Concluído |
| Adicionar threshold de latência ao health endpoint | Valdomiro | 2026-05-16 | Em andamento |

---

## Lições Aprendidas

1. **Healthcheck ≠ readiness**: Um endpoint `/health` que retorna 200 imediatamente não garante que o serviço está pronto para tráfego de produção. Readiness probes devem validar dependências críticas (Redis ping).

2. **HOTL funcionou como esperado**: O engenheiro on-call usou o brief do Copilot para tomar uma decisão informada de *não* fazer rollback. Isso salvou ~15 min de deploy adicional.

3. **Duração de 18 min vs. MTTR histórico de 45 min**: A detecção rápida (~47s) reduziu o MTTR em ~60% comparado ao baseline pré-Copilot.

---

## Referências

- Runbook: [docs/runbooks/high-latency.md](../runbooks/high-latency.md)
- Dashboard: Grafana → "Agentic AI — Golden Signals" → Latência P50/P95/P99
- Alerta: `IncidentWarning` em `infra/prometheus/alerts.yaml`
