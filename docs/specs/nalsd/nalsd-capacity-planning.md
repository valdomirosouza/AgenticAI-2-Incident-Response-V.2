# NALSD — Capacity Planning — AgenticAI-2 Incident Response

Seguindo a metodologia NALSD (Non-Abstract Large System Design) do Google SRE Book.
As quatro perguntas fundamentais devem ser respondidas para cada serviço.

> Contexto: dissertação de mestrado (PPGCA/Unisinos). Carga projetada = ambiente acadêmico
> controlado + simulação de produção via Locust. Valores de pico são conservadores.

---

## As 4 Perguntas Fundamentais NALSD

| Pergunta | Resposta consolidada |
|----------|----------------------|
| 1. O design funciona? | Sim — 3 microserviços com responsabilidades bem separadas; validado em testes |
| 2. Aguenta a carga? | Sim para carga acadêmica; produção leve (≤ 100 RPS) |
| 3. Sobrevive a falhas? | Sim — circuit breaker, fallback rule-based, retry com backoff |
| 4. Pode evoluir? | Sim — ADRs documentados; modelos e prompts versionados; Docker Compose |

---

## Step 1 — Napkin Design

```
[HAProxy logs] ──POST /logs──► [Log-Ingestion :8000] ──Redis──► [métricas Golden Signals]
                                                                         │
[Trigger] ──POST /analyze──► [IRA :8001] ──tool-use──► [4 Specialists]──┘
                                    │
                                    ├── Anthropic API (Claude Sonnet 4.6)
                                    └── [Knowledge-Base :8002] ──Qdrant──► [runbooks/postmortems]
```

---

## Step 2 — Back-of-Envelope por Serviço

### Log-Ingestion-and-Metrics (:8000)

```
Tráfego:
  Ambiente acadêmico: 1000 logs/sessão de teste
  Produção real estimada: 10 req/s (HAProxy médio)
  Peak factor: 10× → peak 100 req/s

Latência:
  FastAPI overhead:     ~5ms
  Redis ZADD/INCR:      ~1ms (local) / ~5ms (remoto)
  Pydantic validation:  ~1ms
  Total p99 estimado:   ~15ms (muito abaixo do SLO de 500ms p95)

Storage Redis:
  Por log: ~200 bytes (score em sorted set + counters)
  1000 logs/sessão: 200 KB
  Produção 30 dias × 10 req/s × 86400s = ~25 GB (sem TTL)
  Com TTL / sliding window 24h: ~1.7 GB

Capacidade:
  Redis single-node: 10k ops/s → suporta 100× o peak estimado
  FastAPI worker: 500 req/s → suporta 5× o peak
  Instâncias necessárias: 1 + 1 standby (N+1)
```

### Incident-Response-Agent (:8001)

```
Tráfego:
  Rate limit: 10 req/min = 0.17 req/s
  Análise típica: ~15s (4 specialists paralelos + orchestrator)
  Concurrent analyses: 1 (rate limited)

Latência por análise:
  Specialists paralelos (asyncio.gather):
    LatencyAgent tool-use:    ~3-8s (Claude latency)
    ErrorsAgent tool-use:     ~3-8s (paralelo)
    SaturationAgent tool-use: ~3-8s (paralelo)
    TrafficAgent tool-use:    ~3-8s (paralelo)
  Tempo = max(specialists) ≈ 8s

  Orchestrator synthesis:     ~5-10s
  KB search:                  ~15ms
  Total p99 estimado:         ~20s (SLO: sem SLO definido — LLM-bound)

Token budget:
  Por specialist: ~800 input + ~200 output = 1000 tokens
  Orchestrator: ~2000 input + ~500 output = 2500 tokens
  Total/análise: 4 × 1000 + 2500 = 6500 tokens
  Custo (claude-sonnet-4-6): ~$0.03/análise

Storage:
  Stateless — nenhum estado persistido
  Logs: ~2 KB/análise

Capacidade:
  10 análises/min (rate limit) → 600/hora → 14400/dia
  Para dissertação: < 100 análises/dia → bem dentro do orçamento
```

### Knowledge-Base (:8002)

```
Tráfego:
  5 buscas/análise × 10 análises/min = 50 buscas/min = 0.83 req/s
  Peak: 5 req/s (5× normal)

Latência:
  Embedding (all-MiniLM-L6-v2, CPU): ~10ms
  Qdrant cosine search (1000 chunks): ~5ms
  FastAPI overhead: ~2ms
  Total p99: ~20ms

Storage Qdrant:
  1000 chunks × 384 dims × 4 bytes = 1.5 MB vectors
  Payloads (content + metadata): ~500 KB
  Total: ~2 MB (trivial)
  Crescimento: +2 KB por chunk adicionado

Capacidade:
  Qdrant single-node: > 10k searches/s
  CPU embedding: 100 req/s por core
  Instâncias: 1 (sem necessidade de escala para carga acadêmica)
```

---

## Step 3 — Bottlenecks Identificados

| Componente | Bottleneck | Capacidade atual | Solução se necessário |
|-----------|-----------|------------------|----------------------|
| IRA — Anthropic API | Latência LLM ~8s por specialist | 10 análises/min (rate limit) | Paralelismo já implementado via asyncio.gather |
| IRA — Anthropic API | Custo por token | $0.03/análise | Rate limiting 10/min; circuit breaker |
| Redis — Log-Ingestion | Memória sob carga alta | ~1.7 GB/24h | `maxmemory-policy allkeys-lru`; alerta em 80% |
| KB — Embedding CPU | Latência CPU-bound | ~10ms/embedding | Leve para carga atual; GPU opcional em produção |

---

## Step 4 — Refinamentos Iterativos

**Iteração 1:** Specialists sequenciais → **Paralelos via asyncio.gather** (ADR-0007)
- Antes: ~40s (4 × 10s sequencial)
- Depois: ~10s (paralelo, limitado pelo mais lento)
- Tradeoff documentado: maior uso de conexões Anthropic simultâneas

**Iteração 2:** LLM sempre chamado → **Circuit Breaker + Fallback Rule-Based** (ADR-0010)
- Antes: falha total quando Anthropic API indisponível
- Depois: análise degradada mas funcional via `fallback_analyzer.py`
- Tradeoff: fallback menos preciso que LLM; documentado em postmortem INC-003

**Iteração 3:** Busca KB sem filtro → **Score Threshold 0.70** (CLAUDE.md §Segurança)
- Antes: resultados irrelevantes poluíam contexto do LLM (LLM08:2025)
- Depois: apenas chunks com similaridade ≥ 0.70 passam
- Tradeoff: pode não retornar nada se KB vazio; fallback para análise sem histórico

---

## Step 5 — Tradeoffs Documentados em ADRs

| Decisão | ADR | Tradeoff |
|---------|-----|----------|
| Microservices vs Monolith | ADR-0001 | Complexidade operacional ↑; isolamento de falhas ↑ |
| Redis como metrics store | ADR-0003 | Sem persistência histórica; latência ↓ |
| Claude Sonnet 4.6 | ADR-0005 | Custo por token; capacidade de raciocínio causal ↑ |
| asyncio.gather paralelo | ADR-0007 | Conexões simultâneas ↑; latência total ↓ |
| Docker Compose vs K8s | ADR-0012 | Simplicidade ↑ (acadêmico); orquestração avançada ✗ |

---

## Limites de Complexidade Ciclomática

Configurado em todos os `pyproject.toml` via `[tool.ruff.lint.mccabe]`:

```toml
[tool.ruff.lint]
select = ["C90"]

[tool.ruff.lint.mccabe]
max-complexity = 10  # limite por função
```

Funções acima de 10 → warning no CI. Módulos com complexidade agregada > 50 → refatorar.
