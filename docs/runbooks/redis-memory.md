# Runbook: Redis Memory Saturation

**Alerta:** `KBDegradedFrequent` ou `IncidentCritical` com finding de Saturation  
**Serviço afetado:** Log-Ingestion-and-Metrics (Redis)  
**Severidade esperada:** WARNING (>80% memória) → CRITICAL (>95%)  
**Última revisão:** 2026-05-14

---

## Sintomas

- `HAPROXY_LOGS_INGESTED` counter para de crescer (pipeline Redis falha silenciosamente)
- Grafana: painel "5xx Rate" sobe abruptamente após Redis atingir `maxmemory`
- Logs do `log-ingestion`: `redis.exceptions.ResponseError: OOM command not allowed`
- Alert `IncidentCritical` disparado pelo Agentic AI Copilot com finding de Saturation CRITICAL

## Diagnóstico

```bash
# 1. Verificar uso de memória atual
docker exec redis redis-cli info memory | grep used_memory_human

# 2. Verificar política de evicção ativa
docker exec redis redis-cli config get maxmemory-policy

# 3. Ver quantas chaves existem e os maiores consumidores
docker exec redis redis-cli dbsize
docker exec redis redis-cli --bigkeys

# 4. Verificar TTLs (chaves sem TTL são o problema)
docker exec redis redis-cli randomkey
docker exec redis redis-cli ttl <key>
```

## Remediação Imediata (< 5 min)

```bash
# Opção A: Forçar evicção manual (sem restart)
docker exec redis redis-cli config set maxmemory-policy allkeys-lru

# Verificar se a política foi aplicada
docker exec redis redis-cli config get maxmemory-policy
```

## Remediação Estrutural (próximas 2h)

1. Confirmar que `docker-compose.yml` tem `--maxmemory-policy allkeys-lru` no comando do Redis
2. Verificar no código (`app/ingestion.py`) que todas as chaves têm TTL configurado:
   - `metrics:rps:<minute>` → TTL 61 min ✓
   - `metrics:requests:total`, `metrics:errors:*` → **sem TTL** (aceitável, são contadores cumulativos)
   - `metrics:response_times` (sorted set) → verificar se está crescendo ilimitado
3. Adicionar `EXPIRE` no sorted set de response_times se count > 10.000

## Rollback

```bash
# Se a mudança de política piorou: restaurar noeviction (aceita OOM em vez de perder dados)
docker exec redis redis-cli config set maxmemory-policy noeviction
```

## Pós-Incidente

- Abrir post-mortem em `docs/post-mortems/INC-XXX-redis-oom.md`
- Ajustar alerta `KBDegradedFrequent` se threshold for muito sensível
- Referência: [INC-001](../post-mortems/INC-001-redis-oom.md)
