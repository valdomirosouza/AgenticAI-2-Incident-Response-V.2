# ADR-2026-0003: Redis 7 como Armazenamento de Golden Signals

---

## Metadata

| Field            | Value                                                                    |
| ---------------- | ------------------------------------------------------------------------ |
| **ID**           | ADR-2026-0003                                                            |
| **Status**       | Accepted                                                                 |
| **Area**         | Data                                                                     |
| **Author**       | Valdomiro Souza                                                          |
| **Reviewers**    | Orientador PPGCA/Unisinos                                                |
| **Created**      | 2026-05-14                                                               |
| **Approved**     | 2026-05-14                                                               |
| **Related spec** | SDD v1.7.0 §3.2, §9.2 (Golden Signals)                                   |
| **AI-assisted**  | Yes — Claude Sonnet 4.6, trade-off analysis, reviewed by Valdomiro Souza |

---

## 1. Context and Problem

O sistema precisa armazenar métricas de Golden Signals (Latency, Traffic, Errors, Saturation) coletadas de logs HAProxy em tempo real para consulta pelos agentes especialistas. Os requisitos são:

- **Ingestão de alta frequência**: centenas de logs/segundo de proxies em produção
- **Consulta de percentis** (P50/P95/P99) sobre janelas de tempo recentes (últimos ~10 min)
- **Contadores incrementais**: total de requests, 4xx, 5xx por backend
- **RPS por minuto**: bucket temporal para cálculo de requests/segundo
- **Saturation**: métricas de memória Redis via `INFO memory`
- **Sem persistência obrigatória**: dados históricos ficam nos post-mortems (Qdrant); Redis armazena apenas janela operacional

**Driving forces:**

- Latência de leitura < 5 ms (agentes especialistas chamam metrics API durante análise ativa)
- Sorted Sets do Redis implementam percentis nativamente: `ZRANGEBYSCORE` para P50/P95/P99
- Equipe com expertise em Redis; sem necessidade de banco de séries temporais dedicado para o escopo atual
- `fakeredis` permite testes unitários sem infraestrutura real

**Constraints:**

- Dados de métricas têm TTL implícito (~60 min de histórico de RPS, janela deslizante de latências)
- Orçamento: Redis OSS (sem Redis Enterprise/Cloud)

---

## 2. Decision

Adotamos **Redis 7** com política `allkeys-lru` e limite de **256 MB** como armazenamento primário de Golden Signals, usando as seguintes estruturas de dados:

| Sinal               | Estrutura Redis        | Chave                                      |
| ------------------- | ---------------------- | ------------------------------------------ |
| Latency P50/P95/P99 | Sorted Set (`ZADD`)    | `metrics:response_times`                   |
| Error counters      | String (`INCR`)        | `metrics:errors:4xx`, `metrics:errors:5xx` |
| Request total       | String (`INCR`)        | `metrics:requests:total`                   |
| RPS por minuto      | String (`INCR`)        | `metrics:rps:YYYY-MM-DDTHH:MM`             |
| Backend hits        | String (`INCR`)        | `metrics:backend:<name>`                   |
| Saturation          | Lido via `INFO memory` | — (não armazenado)                         |

**Scope:**

- Applies to: Log-Ingestion-and-Metrics (escrita) e Incident-Response-Agent via métricas API (leitura indireta)
- Does not apply to: dados históricos de incidentes (→ Qdrant, ADR-2026-0004)

---

## 3. Alternatives Considered

| Alternative                   | Pros                                                                                                        | Cons                                                                                                 | Reason for Rejection                                                 |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **Redis 7 (escolhido)**       | Sub-ms latência, Sorted Sets para percentis, `fakeredis` para testes, `allkeys-lru` para pressão de memória | Sem persistência durável por padrão; dados perdidos em restart                                       | — Escolhido; persistência não é requisito para métricas operacionais |
| InfluxDB / TimescaleDB        | Time-series nativo, retenção automática, Grafana nativo                                                     | Dependência adicional pesada; query language separada (InfluxQL/SQL); sem Sorted Sets para percentis | Overhead desnecessário para escopo do projeto                        |
| Prometheus (push)             | Padrão SRE, Grafana nativo                                                                                  | Pull-based por design; push via Pushgateway é anti-pattern; sem persistência de alta frequência      | Arquitetura pull incompatível com ingestão de logs                   |
| PostgreSQL + TimescaleDB      | ACID, query SQL familiar                                                                                    | Latência de escrita 10–50× maior que Redis para alta frequência                                      | Latência incompatível com ingestão em tempo real                     |
| "Do nothing" (in-memory dict) | Zero dependências                                                                                           | Dados perdidos em restart; sem Sorted Sets; não escalável                                            | Inaceitável para ambiente de produção simulado                       |

---

## 4. Consequences

### Positive

- P50/P95/P99 calculados com `ZRANGEBYSCORE` — O(log N) — sem necessidade de código de percentil próprio
- `fakeredis[aioredis]` permite testes unitários 100% offline (sem Docker no CI para testes unitários)
- `allkeys-lru` garante que Redis nunca rejeita writes mesmo sob pressão de memória
- Configuração simples: `--maxmemory 256mb --save ""` (sem persistência RDB/AOF)

### Negative / Trade-offs

- Dados de métricas perdidos em restart do Redis (aceitável — janela operacional, não histórico)
- Sorted Set de latências cresce indefinidamente sem TTL explícito — requer `EXPIRE` ou limpeza periódica (não implementado; `allkeys-lru` mitiga)
- Sem suporte a query temporal nativa (ex: "P95 dos últimos 5 minutos") — cálculo feito no aplicativo

### Risks

| Risk                                    | Probability | Impact | Mitigation                                                         |
| --------------------------------------- | ----------- | ------ | ------------------------------------------------------------------ |
| Redis OOM com `noeviction` policy       | Médio       | Alto   | Policy `allkeys-lru` configurada; `maxmemory 256mb`                |
| Restart Redis apaga métricas em análise | Baixo       | Médio  | Análise IRA usa snapshot; restart improvável durante análise ativa |
| `fakeredis` diverge de Redis real       | Baixo       | Médio  | E2E tests com Redis real via testcontainers (`test_e2e_redis.py`)  |

### Tech Debt Introduced

- Sorted Set `metrics:response_times` não tem TTL explícito — cresce sem limite. Mitigado por `allkeys-lru`, mas ideal seria `EXPIRE` periódico.

---

## 5. Future Review Criteria

Esta ADR deve ser revisitada se:

- [ ] Volume de métricas ultrapassar 256 MB consistentemente (considerar Redis Cluster ou InfluxDB)
- [ ] Requisito de retenção histórica de métricas (>1h) emergir — considerar TimescaleDB
- [ ] Redis 7 atingir EOL (previsto 2026+; verificar redis.io/releases)
- [ ] Após 2 anos sem revisão (2028-05-14)

---

## 6. References

- SDD v1.7.0 §3.2 — Log Ingestion and Metrics
- SDD v1.7.0 §9.2 — Golden Signals (Google SRE Book)
- `Log-Ingestion-and-Metrics/app/ingestion.py` — escrita de métricas no Redis
- `Log-Ingestion-and-Metrics/app/routers/metrics.py` — leitura e cálculo de percentis
- `docker-compose.yml` — configuração Redis (`allkeys-lru`, `maxmemory 256mb`)

---

## 7. AI Assistance

| Field                      | Value                                                                        |
| -------------------------- | ---------------------------------------------------------------------------- |
| **AI used**                | Claude Sonnet 4.6                                                            |
| **AI role**                | Comparação de alternativas de storage, análise de trade-offs de persistência |
| **Output reviewed by**     | Valdomiro Souza                                                              |
| **Final decision made by** | Valdomiro Souza                                                              |

---

## 8. Approval

| Role       | Name            | Date       | Decision   |
| ---------- | --------------- | ---------- | ---------- |
| Author     | Valdomiro Souza | 2026-05-14 | Proposes   |
| Tech Lead  | Valdomiro Souza | 2026-05-14 | ✅ Approve |
| Orientador | PPGCA/Unisinos  | 2026-05-14 | ✅ Approve |
