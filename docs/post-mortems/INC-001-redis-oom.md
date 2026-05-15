# Post-Mortem: INC-001 — Redis Out-of-Memory durante pico de tráfego

**Data:** 2026-04-10
**Duração:** 8 min (detecção) → 23 min (mitigação) → 45 min (resolução)
**Severidade:** P2
**Autor:** Equipe SRE
**Status:** FECHADO

## Impacto
- Ingestão de logs HAProxy interrompida por 23 minutos
- Métricas de Golden Signals indisponíveis para o Agent durante o período
- SLO de disponibilidade impactado: 99.3% no dia (abaixo do target de 99.5%)

## Linha do Tempo

| Horário (UTC) | Evento |
|---|---|
| 14:32 | RPS aumentou 4x (200 → 800 req/min) — tráfego legítimo de deploy |
| 14:38 | Redis atingiu 95% de uso de memória |
| 14:40 | Primeiros erros de escrita no Redis (COMMAND OOM) |
| 14:40 | Log-Ingestion começa a retornar 500 nos endpoints de ingestão |
| 14:42 | GET /health continua respondendo 200 (Redis liveness não verificado no health check) |
| 14:48 | Engenheiro on-call acionado via alerta de error rate 5xx |
| 14:55 | Mitigação: redis-cli CONFIG SET maxmemory-policy allkeys-lru |
| 15:03 | Redis começa a evictar chaves antigas; ingestão normaliza |
| 15:17 | Métricas históricas parcialmente recuperadas; incident encerrado |

## Causa Raiz
**Root cause:** Redis configurado com `maxmemory-policy: noeviction` (padrão) sem `maxmemory` explícito definido. O sistema não tinha limite de memória e a política de noeviction causa erros em vez de evictar dados antigos.

**Trigger:** Pico de tráfego 4x acima da média (deploy de nova feature com AB test para 100% dos usuários).

## Análise dos 5 Porquês
1. Por que o Redis ficou sem memória? → Política noeviction sem maxmemory
2. Por que noeviction estava configurado? → Configuração padrão nunca foi revisada
3. Por que o alerta não disparou antes de atingir 95%? → Sem alerta de memória Redis configurado
4. Por que o health check não detectou a falha? → Health check verificava apenas disponibilidade de rede, não operações Redis
5. Por que não havia runbook? → Sistema novo; runbooks ainda não escritos

## O que foi bem
- Rate limiting do Agent protegeu contra avalanche de análises durante a degradação
- Degradação graciosa da KB (Qdrant) não foi afetada (componente independente)
- Engenheiro reconheceu o padrão de OOM rapidamente

## O que pode melhorar
- Configurar `maxmemory` explícito e `maxmemory-policy: allkeys-lru` no Redis
- Adicionar alerta de memória Redis em 80%
- Adicionar verificação Redis operacional no `/health` do Log-Ingestion
- Escrever runbook de Redis OOM

## Itens de Ação

| Ação | Responsável | Prazo | Status |
|---|---|---|---|
| Configurar maxmemory e política allkeys-lru no docker-compose | SRE | 1 semana | ✅ Concluído |
| Adicionar alerta Prometheus para Redis memory > 80% | SRE | 1 semana | ✅ Concluído |
| Atualizar health check para verificar operação Redis (PING) | Dev | 2 semanas | ✅ Concluído |
| Escrever runbook de Redis OOM | SRE | 1 semana | ✅ Concluído |

## Lições para a Knowledge Base
- Redis com noeviction e sem maxmemory → OOM em picos de tráfego
- Solução imediata: `redis-cli CONFIG SET maxmemory-policy allkeys-lru`
- Pico de tráfego 4x pode esgotar Redis em minutos se política não estiver configurada
- Health check deve verificar operações Redis reais, não apenas conectividade de rede
