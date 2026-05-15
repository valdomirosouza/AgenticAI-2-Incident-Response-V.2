# Runbook: Alta Latência (P99 > 1000ms)

**Alerta:** `AnalysisSlowP95` ou finding de Latency CRITICAL pelo Agentic AI  
**Serviço afetado:** Log-Ingestion-and-Metrics e/ou Incident-Response-Agent  
**Severidade esperada:** WARNING (P95 > 500ms) → CRITICAL (P99 > 1000ms)  
**Última revisão:** 2026-05-14

---

## Sintomas

- Grafana: painel "P99 Latency" > 1s por mais de 2 minutos
- Finding do LatencyAgent: CRITICAL com `P99 > 1000ms`
- Alerta `AnalysisSlowP95`: análise do agente levando mais de 30s (degradação do Claude)
- Usuários reportando timeout no `POST /analyze`

## Diagrama de Causa Comum

```
Tráfego alto → Redis pipeline lento → ingest lento → métricas desatualizadas
                                                           ↓
                                   Agent consulta métricas stale → analysis imprecisa

Anthropic API lenta → _synthesize timeout → análise incompleta (fallback ativado)
```

## Diagnóstico

```bash
# 1. Verificar latência atual por endpoint
curl -s http://localhost:8000/metrics | grep http_request_duration

# 2. Verificar se Redis está saudável
docker exec redis redis-cli ping
docker exec redis redis-cli info stats | grep instantaneous_ops_per_sec

# 3. Verificar se o Anthropic API está lento
curl -s http://localhost:8001/metrics | grep incident_analysis_duration

# 4. Ver logs do agente para identificar qual fase está lenta
docker logs incident-response-agent --since 5m | grep -E "Analysis|specialist|KB"

# 5. Verificar se KB está respondendo
curl -sf http://localhost:8002/health
```

## Remediação por Causa

### Causa: Redis lento (pipeline congestionado)

```bash
# Verificar conexões ativas
docker exec redis redis-cli client list | wc -l

# Verificar latência de comando
docker exec redis redis-cli --latency -c 100

# Se > 10ms média: reiniciar redis (dados em memória, não persistidos)
docker compose restart redis
```

### Causa: Anthropic API degradada

```bash
# Fallback já é automático (fallback_analyzer.py)
# Verificar se fallback está ativo nos logs:
docker logs incident-response-agent | grep "Fallback rule-based"

# Se o fallback não reduzir latência, verificar thresholds:
docker exec incident-response-agent env | grep THRESHOLD
```

### Causa: Knowledge-Base lenta (Qdrant)

```bash
# Verificar saúde do Qdrant
curl http://localhost:6333/collections

# Ver collections e tamanho
curl http://localhost:6333/collections/postmortems

# Reiniciar Qdrant (dados persistidos em volume)
docker compose restart qdrant
```

## Pós-Incidente

- Abrir post-mortem em `docs/post-mortems/INC-XXX-latency-spike.md`
- Revisar `settings.latency_p99_threshold_ms` se threshold precisar ajuste
- Referência: [INC-002](../post-mortems/INC-002-latency-spike.md)
