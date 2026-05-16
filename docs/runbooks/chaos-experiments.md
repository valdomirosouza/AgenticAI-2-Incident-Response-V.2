# Chaos Experiments — AgenticAI-2 Incident Response

Experimentos de chaos engineering para validar resiliência do sistema.
Referência: `skills/sre-foundations/`, `skills/large-system-design/resilience-patterns.md`

> **Princípio:** "Hope is not a strategy. Test your failure modes before they happen in production."
> Cada experimento segue o ciclo: Hipótese → Injeção → Observação → Validação → Remediação.

---

## Pré-requisitos

Antes de executar qualquer experimento:
- [ ] Sistema em staging ou ambiente isolado
- [ ] Prometheus + Grafana operacionais (métricas de observação)
- [ ] On-call notificado (mesmo em staging)
- [ ] Plano de rollback definido
- [ ] Janela de manutenção confirmada

---

## CHAOS-001 — Redis Unavailability

**Objetivo:** Validar que o Log-Ingestion-and-Metrics responde com graceful degradation quando Redis está indisponível.

**Hipótese:** Quando o Redis está inacessível, o serviço retorna 503 em `/health` e 500 em `/logs`, sem crash do processo.

**Procedimento:**
```bash
# 1. Verificar estado inicial
curl http://localhost:8000/health

# 2. Parar Redis
docker compose stop redis

# 3. Tentar ingestão (deve retornar 500, não 200)
curl -X POST http://localhost:8000/logs -H "X-API-Key: $API_KEY" \
  -d '{"frontend":"fe","backend":"be","status_code":200,"time_response":50,"bytes_read":100}'

# 4. Verificar health (deve retornar 503 com Redis down)
curl http://localhost:8000/health

# 5. Restaurar Redis
docker compose start redis

# 6. Verificar recuperação (deve retornar 200 healthy)
sleep 5 && curl http://localhost:8000/health
```

**Métricas a observar:**
- `http_requests_total{status=~"5.."}` — deve aumentar durante falha
- `error_budget_remaining_pct` — deve ser impactado
- Alertas Prometheus: `LogIngestionHighErrorRate`

**Critério de sucesso:**
- [ ] Processo continua rodando sem crash
- [ ] Retorna 503/500 adequado (não 200)
- [ ] Recuperação automática após Redis voltar (sem restart manual)
- [ ] Alerta disparado no Prometheus dentro de 5 min

**Status:** Planejado — executar antes de primeiro deploy em staging

---

## CHAOS-002 — Anthropic API Unavailability (Circuit Breaker)

**Objetivo:** Validar circuit breaker e fallback rule-based do IRA.

**Hipótese:** Quando a Anthropic API está indisponível, após 3 falhas consecutivas o circuit breaker abre e o sistema retorna análise via fallback rule-based (não erro 500).

**Procedimento:**
```bash
# 1. Simular Anthropic API inacessível via variável inválida
# (em staging — não fazer em produção)
docker compose exec incident-response-agent env ANTHROPIC_API_KEY=invalid uvicorn app.main:app

# OU: bloquear domínio via /etc/hosts no container
# docker compose exec incident-response-agent bash -c \
#   "echo '0.0.0.0 api.anthropic.com' >> /etc/hosts"

# 2. Enviar 3+ análises para abrir o circuito
for i in 1 2 3 4; do
  curl -X POST http://localhost:8001/analyze -H "X-API-Key: $API_KEY"
  sleep 2
done

# 3. Verificar que a 4ª análise retorna fallback (analysis_source: "fallback")
curl -X POST http://localhost:8001/analyze -H "X-API-Key: $API_KEY" | jq .analysis_source

# 4. Verificar status do circuit breaker
curl http://localhost:8001/admin/circuit-breaker/status -H "X-Admin-Key: $ADMIN_KEY"

# 5. Restaurar Anthropic API
# (restaurar configuração original)

# 6. Aguardar recovery_timeout (60s) ou reset manual
sleep 65
# OU: curl -X POST http://localhost:8001/admin/circuit-breaker/reset -H "X-Admin-Key: $ADMIN_KEY"

# 7. Verificar que análise LLM volta (analysis_source: "llm")
curl -X POST http://localhost:8001/analyze -H "X-API-Key: $API_KEY" | jq .analysis_source
```

**Métricas a observar:**
- `llm_calls_total{outcome="error"}` — deve aumentar com API inválida
- `llm_calls_total{outcome="circuit_open"}` — deve aumentar após abrir
- Alerta `LLMCircuitBreakerOpen` — deve disparar

**Critério de sucesso:**
- [ ] 3 falhas consecutivas abrem o circuito
- [ ] Análise fallback retorna `analysis_source: "fallback"` (não 500)
- [ ] IncidentReport válido retornado mesmo com LLM indisponível
- [ ] Recuperação automática após `CB_RECOVERY_TIMEOUT_S` (60s)
- [ ] `analysis_source: "llm"` retorna após recuperação

**Status:** Planejado — executar antes de primeiro deploy em staging

---

## CHAOS-003 — Qdrant Unavailability

**Objetivo:** Validar graceful degradation quando Knowledge-Base está inacessível.

**Hipótese:** Quando o Qdrant está indisponível, o IRA retorna análise sem KB (recomendações genéricas) em vez de falhar completamente.

**Procedimento:**
```bash
# 1. Parar Qdrant
docker compose stop qdrant

# 2. Executar análise — deve completar com kb_references vazia
curl -X POST http://localhost:8001/analyze -H "X-API-Key: $API_KEY" | jq '{severity: .overall_severity, kb: .kb_references}'

# 3. Verificar KB health (deve retornar 503)
curl http://localhost:8002/health

# 4. Restaurar Qdrant
docker compose start qdrant
sleep 5

# 5. Verificar recuperação automática
curl http://localhost:8002/health
```

**Critério de sucesso:**
- [ ] IRA retorna IncidentReport válido mesmo sem KB
- [ ] `kb_references: []` no report (não erro)
- [ ] KB health retorna 503 (não crash)
- [ ] KB health retorna 200 após Qdrant recuperar

**Status:** Planejado

---

## CHAOS-004 — Memory Pressure no Redis

**Objetivo:** Validar comportamento com Redis sob pressão de memória (simular `maxmemory` baixo).

**Hipótese:** Com Redis em alto uso de memória, o sistema aciona alerta antes de degradação de serviço.

**Procedimento:**
```bash
# 1. Configurar maxmemory baixo no Redis (staging apenas)
docker compose exec redis redis-cli CONFIG SET maxmemory 10mb

# 2. Ingerir muitos logs para consumir memória
for i in $(seq 1 1000); do
  curl -s -X POST http://localhost:8000/logs -H "X-API-Key: $API_KEY" \
    -d "{\"frontend\":\"fe\",\"backend\":\"be$i\",\"status_code\":200,\"time_response\":$RANDOM,\"bytes_read\":100}" &
done
wait

# 3. Observar saturação
curl http://localhost:8000/metrics/saturation | jq .

# 4. Verificar alerta Prometheus
# Acesse Grafana: http://localhost:3000 — dashboard Golden Signals

# 5. Restaurar maxmemory
docker compose exec redis redis-cli CONFIG SET maxmemory 0
```

**Critério de sucesso:**
- [ ] Alerta `RedisHighMemoryUsage` dispara quando >80%
- [ ] Serviço continua respondendo (allkeys-lru evicta chaves antigas)
- [ ] SLO não breachado durante experimento

**Status:** Planejado

---

## Registro de Execuções

| Experimento | Data | Ambiente | Resultado | Ação pós |
|------------|------|----------|-----------|----------|
| CHAOS-001 | — | staging | Planejado | — |
| CHAOS-002 | — | staging | Planejado | — |
| CHAOS-003 | — | staging | Planejado | — |
| CHAOS-004 | — | staging | Planejado | — |

**Após cada execução:** Atualizar esta tabela e abrir postmortem se resultado inesperado.
