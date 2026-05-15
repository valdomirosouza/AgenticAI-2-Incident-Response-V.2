# Memória da Sessão — AgenticAI-2-Incident-Response

**Data:** 14–15 de Maio de 2026  
**Projeto:** Dissertação de Mestrado — PPGCA / Unisinos  
**Autor:** Valdomiro Souza — valdomiro.souza@zsms.cloud  
**Modelo IA:** Claude Sonnet 4.6 (claude-sonnet-4-6)  
**Repositório:** github.com/valdomirosouza/AgenticAI-2-Incident-Response

---

## 1. Contexto do Projeto

**Objetivo:** Copiloto de Agentic AI para reduzir MTTD (Mean Time to Detect) e MTTR (Mean Time to Recovery) em incidentes de TI. Substitui triagem manual (minutos a horas) por análise multi-agente paralela em ~10 segundos.

**Modelo de supervisão:** Human-on-the-Loop (HOTL) — agente analisa e recomenda; humano decide e executa a remediação. Nenhuma ação automática de remediação é tomada.

**Contexto acadêmico:** Cada decisão de implementação tem justificativa científica rastreável à RSL (Revisão Sistemática da Literatura) documentada no SDD.

---

## 2. Arquitetura — 3 Microsserviços FastAPI

| Serviço | Porta | Stack | Responsabilidade |
|---|---|---|---|
| Log-Ingestion-and-Metrics | :8000 | FastAPI + Redis 7 | Ingestão de logs HAProxy; Golden Signals (Traffic, Errors, Latency, Saturation) |
| Incident-Response-Agent | :8001 | FastAPI + Anthropic SDK | Orquestração de 4 agentes especialistas; geração de `IncidentReport` |
| Knowledge-Base | :8002 | FastAPI + Qdrant + sentence-transformers | Base vetorial de incidentes históricos; busca semântica |

**Infraestrutura de suporte:** Redis :6379, Qdrant :6333, Prometheus, Grafana

---

## 3. Fluxo Principal

### Fase 1 — Ingestão Contínua
```
HAProxy → POST /logs → Log-Ingestion
  Redis: INCR requests:total, errors:4xx/5xx, ZADD response_times, INCR rps:{minute}
  → 202 Accepted
```

### Fase 2 — Análise de Incidente
```
Engenheiro On-call → POST /analyze (X-API-Key)
  → require_api_key + rate_limit (10 req/min)
  → asyncio.gather() — 4 especialistas em paralelo (~10s)
      LatencyAgent   → GET /metrics/response-times → Claude tool-use → SpecialistFinding
      ErrorsAgent    → GET /metrics/overview       → Claude tool-use → SpecialistFinding
      SaturationAgent→ GET /metrics/saturation      → Claude tool-use → SpecialistFinding
      TrafficAgent   → GET /metrics/rps + /backends → Claude tool-use → SpecialistFinding
  → [findings não-OK] → POST /kb/search → Qdrant → kb_results[]
  → _synthesize(findings, kb_results) → Claude → IncidentReport JSON
  → Pydantic validation (OrchestratorResponse)
  → IncidentReport {overall_severity, title, diagnosis, recommendations}
```

---

## 4. Roadmap — Todos os Sprints Concluídos ✅

### Sprint 1 — Fundação
| ID | Tarefa | Status |
|---|---|---|
| S1-01 | Scaffolding do repositório (3 serviços FastAPI) | ✅ |
| S1-02 | Log-Ingestion: ingestão HAProxy + Redis + Golden Signals | ✅ |
| S1-03 | IRA: 4 agentes especialistas + orquestrador Claude | ✅ |
| S1-04 | Knowledge-Base: Qdrant + embeddings + busca semântica | ✅ |
| S1-05 | Sanitização de findings (LLM01:2025 defense) | ✅ |
| S1-06 | score_threshold=0.70 no Qdrant (LLM08:2025) | ✅ |

### Sprint 2 — Testes Knowledge-Base
| ID | Tarefa | Status |
|---|---|---|
| S2-01 | 49 testes unitários KB (97.60% cobertura) | ✅ |
| S2-02 | sys.modules stub para sentence-transformers/torch (800 MB excluídos do CI) | ✅ |
| S2-03 | requirements-test.txt (CI sem pacotes ML pesados) | ✅ |

### Sprint 3 — Testes Incident-Response-Agent
| ID | Tarefa | Status |
|---|---|---|
| S3-01 | 174 testes IRA (99.35% cobertura) | ✅ |
| S3-02 | docker-compose.yml (stack completa) | ✅ |
| S3-03 | ci.yml, sast.yml, dast.yml | ✅ |

### Sprint 4 — Maturidade SRE ✅ CONCLUÍDO
| ID | Tarefa | Status |
|---|---|---|
| S4-01 | SLOs formais com error budget tracking | ✅ |
| S4-02 | E2E tests com testcontainers-python (Redis + Qdrant) | ✅ |
| S4-03 | Load tests Locust + check_slos.py + load-test.yml | ✅ |
| S4-04 | Circuit breaker Anthropic API (tenacity) | ✅ |
| S4-05 | Fallback analyzer baseado em regras | ✅ |
| S4-06 | SBOM com syft/grype | ✅ |
| S4-07 | Rotação automática de API Keys | ✅ |

---

## 5. Detalhes de Implementação por Sprint 4

### S4-01 — SLOs com Error Budget

**Arquivos criados/modificados:**
- `Log-Ingestion-and-Metrics/app/slo.py` — cálculo puro (testável sem Redis)
- `Log-Ingestion-and-Metrics/app/models.py` — `SloHealth`, `SloStatus`, `SloStatusReport`
- `Log-Ingestion-and-Metrics/app/metrics_registry.py` — gauge `error_budget_remaining_pct{slo=...}`
- `Log-Ingestion-and-Metrics/app/routers/metrics.py` — `GET /metrics/slo-status`
- `Log-Ingestion-and-Metrics/tests/test_slo.py` — 22 testes unitários

**SLOs definidos:**
| SLO | Target | Threshold | Error Budget |
|---|---|---|---|
| availability | 99.5% | 5xx rate ≤ 0.5% | 0.5% |
| latency_p95 | 99.0% | P95 ≤ 500ms | 1.0% |
| latency_p99 | 99.9% | P99 ≤ 1000ms | 0.1% |

**Health states:** `healthy` (burned ≤ 50%), `at_risk` (burned > 50%, compliant), `breaching` (violando threshold)

---

### S4-02 — E2E Tests (testcontainers-python)

**Arquivos criados:**
- `Log-Ingestion-and-Metrics/tests/test_e2e_redis.py` — 4 testes com `RedisContainer`
- `Knowledge-Base/tests/test_e2e_qdrant.py` — 6 testes com `DockerContainer("qdrant/qdrant:v1.18.0")`

**Decisão chave:** Skip automático quando Docker não disponível via `subprocess.run(["docker", "info"])`. Endpoint correto: `POST /logs` retorna 202 (não 200).

---

### S4-03 — Load Tests (Locust)

**Arquivos criados:**
- `load-tests/locustfile.py` — `LogIngestionUser` (constant_throughput 1 RPS) + `AnalysisUser` (between 6–10s, respeita rate limit 10/min)
- `load-tests/check_slos.py` — lê CSV Locust, valida P95 e failure% contra thresholds; exit 0=pass, 1=violação, 2=arquivo ausente
- `load-tests/Makefile` — targets: run-ingest, run-analyze, check-slos, clean
- `.github/workflows/load-test.yml` — workflow_dispatch com inputs (users, spawn_rate, run_time)

**SLO thresholds para load tests:**
```python
SLO_RULES = {
    "POST /logs":                SloRule(p95_ms=100.0,    failure_pct=1.0),
    "GET /metrics/overview":     SloRule(p95_ms=200.0,    failure_pct=1.0),
    "GET /metrics/response-times": SloRule(p95_ms=200.0,  failure_pct=1.0),
    "GET /health":               SloRule(p95_ms=50.0,     failure_pct=0.1),
    "POST /analyze":             SloRule(p95_ms=30_000.0, failure_pct=5.0),
}
```

---

### S4-04 — Circuit Breaker (tenacity)

**Arquivos criados/modificados:**
- `Incident-Response-Agent/app/agents/anthropic_circuit_breaker.py` — implementação completa
- `Incident-Response-Agent/app/config.py` — campos cb_failure_threshold, cb_recovery_timeout_s, cb_max_retries
- `Incident-Response-Agent/app/agents/specialists/base.py` — integrado com circuit breaker
- `Incident-Response-Agent/app/agents/orchestrator.py` — fallback em `AnthropicCircuitOpenError`
- `Incident-Response-Agent/tests/test_circuit_breaker.py` — 19 testes

**Máquina de estados:**
```
CLOSED → (failure_threshold falhas consecutivas) → OPEN
OPEN   → (recovery_timeout segundos)             → HALF_OPEN
HALF_OPEN → (sucesso)  → CLOSED
HALF_OPEN → (falha)    → OPEN
```

**Retry (tenacity):** `wait_exponential(multiplier=1, min=2s, max=30s)`, `stop_after_attempt(cb_max_retries=3)`

**Exceções retryáveis:** `APIConnectionError`, `APITimeoutError`, `InternalServerError`, `RateLimitError`

**Fallback quando OPEN:**
- SpecialistAgent → `SpecialistFinding(severity=warning, summary="circuit open...")`
- Orchestrator `_synthesize()` → `IncidentReport(title="Incident Detected (LLM Circuit Open)", ...)`

**Decisão crítica de implementação:** `from app.config import settings` deve ser import de módulo (não lazy dentro de função) para ser patchável em testes via `patch("app.agents.anthropic_circuit_breaker.settings")`.

---

### S4-05 — Fallback Analyzer

**Arquivo:** `Incident-Response-Agent/app/agents/fallback_analyzer.py`

Análise baseada em regras quando Claude indisponível:
- P99 > 1000ms → severity critical
- error_rate_5xx > 1.0% → severity critical
- Thresholds configuráveis em `settings.latency_p99_threshold_ms` e `settings.error_rate_5xx_threshold_pct`

---

### S4-06 — SBOM (syft + grype)

**Arquivo criado:** `.github/workflows/sbom.yml`

**Comportamento:**
- Trigger: push/PR para `main`, `workflow_dispatch`
- Matrix strategy: 3 jobs paralelos (log-ingestion, incident-agent, knowledge-base)
- `syft scan dir:<serviço> --output spdx-json` → SBOM em formato SPDX JSON
- `grype sbom:<slug>.spdx.json --fail-on critical` → bloqueia build em CVE crítico
- SARIF → GitHub Security tab (Code Scanning Alerts) via `codeql-action/upload-sarif`
- Artefatos SPDX retidos 90 dias como evidência de supply chain

**Versões fixadas:** syft v1.4.1, grype v0.79.0

---

### S4-07 — Rotação de API Keys

**Arquivos criados/modificados:**
- `Incident-Response-Agent/app/key_manager.py` — módulo puro de gerenciamento
- `Incident-Response-Agent/app/auth.py` — reescrito com suporte multi-key
- `Incident-Response-Agent/app/routers/admin.py` — 3 endpoints admin
- `Incident-Response-Agent/app/config.py` — campo `admin_key`
- `Incident-Response-Agent/app/main.py` — registro do router admin
- `Incident-Response-Agent/tests/test_key_rotation.py` — 33 testes

**Funcionalidades do `key_manager.py`:**
```python
parse_keys(raw: str) -> list[str]      # CSV do env var
generate_key() -> str                  # secrets.token_urlsafe(32) — 256 bits
hash_key(key: str) -> str              # SHA-256 truncado (8 chars) — só para logs
is_valid(candidate, env_key_raw) -> bool  # hmac.compare_digest em todas as chaves
add_rotated_key(key: str) -> None      # adiciona ao store em memória
revoke_extra_keys() -> int             # limpa chaves rotacionadas
has_any_keys(env_key_raw: str) -> bool
key_status(env_key_raw: str) -> list[dict]  # nunca expõe valores reais
reset_for_testing() -> None
```

**Endpoints admin (`/admin/*` protegidos por ADMIN_KEY):**
- `POST /admin/rotate-key` → gera nova chave, retorna uma única vez, ativa imediatamente
- `POST /admin/revoke-legacy` → remove chaves rotacionadas em memória
- `GET /admin/key-status` → lista hashes + labels, nunca os valores reais

**Padrão de rotação sem downtime:**
- Chave antiga (`API_KEY` env) permanece válida durante a transição
- Nova chave ativada imediatamente via store em memória (`_extra_keys`)
- Para persistir após restart: atualizar `API_KEY` no `.env` e reiniciar o serviço

**Separação de privilégios:** `API_KEY` para acesso à API; `ADMIN_KEY` para operações de rotação — princípio do menor privilégio.

---

## 6. Números do Harness de Testes

| Serviço | Testes | Cobertura | Gate CI |
|---|---|---|---|
| Log-Ingestion-and-Metrics | 77 unit/integration + 4 E2E | 95.61% | ≥ 85% |
| Incident-Response-Agent | 174 unit/integration | 99.35% | ≥ 85% |
| Knowledge-Base | 49 unit/integration + 6 E2E | 97.60% | ≥ 85% |
| **Total** | **~300 + 10 E2E** | — | — |

**Configuração de cobertura KB:** `omit = ["tests/*", "app/telemetry.py", "app/scripts/*"]` — `seed_kb.py` excluído propositalmente (script de carga, não lógica de produção). Rodar sempre de dentro do diretório do serviço para respeitar o `pyproject.toml`.

---

## 7. CI/CD — 5 Workflows GitHub Actions

| Workflow | Trigger | O que faz |
|---|---|---|
| `ci.yml` | push/PR (todos os branches) | 3 jobs de teste paralelos + docker-build gate |
| `sast.yml` | push/PR | Bandit + Semgrep + pip-audit + Checkov (SARIF) |
| `dast.yml` | push para `main` | Schemathesis (API fuzzing) + OWASP ZAP baseline |
| `load-test.yml` | `workflow_dispatch` | Locust headless + check_slos.py + artifact upload |
| `sbom.yml` | push/PR `main` + dispatch | syft (SPDX) + grype (CVE scan) — matrix 3 serviços |

---

## 8. Documentação — SDD v1.7.0

**Arquivo:** `AgenticAI-Incident-Response.md` (~2600+ linhas)

**Seções principais:**
- §1 — Visão Geral e Contexto
- §2 — Arquitetura (incluindo §2.6 com 5 diagramas Mermaid sequenceDiagram)
- §3 — Observabilidade (Golden Signals, SLOs, Prometheus, Grafana)
- §4 — TDD (pirâmide de testes, CUJs, métricas de qualidade, CI/CD gates)
- §5 — SAST (Bandit, Semgrep, pip-audit, §5.7 SBOM)
- §6 — DAST (OWASP ZAP, Schemathesis)
- §7 — Desenvolvimento Seguro (OWASP Top 10 Web + LLM Top 10 2025)
- §8 — Roadmap (Sprints 1–4 todos ✅)
- §9 — Building Secure & Reliable Systems (mapeamento Google SRE)
- §10 — Fundamentação Acadêmica (RSL Agentic AI)
- §11 — Referências

**Diagramas Mermaid (§2.6):**
- 2.6.1 — Ingestão Contínua de Logs
- 2.6.2 — Análise de Incidente com IA (fluxo principal com `par` para 4 especialistas)
- 2.6.2b — Rotação de API Keys (S4-07)
- 2.6.3 — Circuit Breaker (CLOSED/OPEN/HALF_OPEN + tenacity retry)
- 2.6.4 — SLO Status e Error Budget

---

## 9. Segurança — Estado Atual

### OWASP Top 10 Web (2021)
| ID | Status |
|---|---|
| A01 Broken Access Control | ⚠️ PARCIAL — `API_KEY=''` desabilita auth em dev; obrigatória em produção via `@model_validator` |
| A02 Cryptographic Failures | ✅ OK |
| A03 Injection | ✅ OK — `_sanitize_finding_text()` + delimitadores XML + MAX_FINDING_LENGTH=500 |
| A04 Insecure Design | ✅ OK |
| A05 Security Misconfiguration | ⚠️ PARCIAL — `/docs` bloqueado em produção; Prometheus sem auth |
| A06 Vulnerable Components | ✅ OK — pip-audit + grype no CI |
| A07 Authentication Failures | ✅ OK — multi-key CSV, rotação sem downtime, ADMIN_KEY separada, hmac.compare_digest |
| A08 Software Integrity | ✅ OK — SBOM syft (SPDX) + grype (--fail-on critical) |
| A09 Security Logging | ⚠️ PARCIAL — logs estruturados; sem alertas automáticos |
| A10 SSRF | ✅ BAIXO — URLs de serviços via env vars |

### OWASP LLM Top 10 (2025)
| ID | Status |
|---|---|
| LLM01 Prompt Injection | ✅ — `_sanitize_finding_text()`, XML delimiters, MAX_FINDING_LENGTH |
| LLM02 Sensitive Disclosure | ⚠️ PARCIAL — métricas agregadas, sem IPs individuais |
| LLM03 Supply Chain | ✅ — circuit breaker + fallback rule-based |
| LLM04 Data Poisoning | ✅ — auth em `/kb/ingest` + ChunkValidator |
| LLM05 Improper Output | ✅ — Pydantic `OrchestratorResponse` valida antes de construir `IncidentReport` |
| LLM06 Excessive Agency | ✅ — HOTL: humano decide, agente analisa |
| LLM07 System Prompt Leakage | ⚠️ PARCIAL — prompts nunca logados; sem classificação formal |
| LLM08 Embedding Weaknesses | ✅ — `score_threshold=0.70`, `top_k=5` |
| LLM09 Misinformation | ✅ — HOTL + `incident_commander_brief` com incertezas |
| LLM10 Unbounded Consumption | ✅ — `kb_results[:5]`, sanitização, `max_tokens=1024` |

---

## 10. Estrutura de Arquivos Relevantes

```
AgenticAI-2-Incident-Response/
├── .github/workflows/
│   ├── ci.yml              — testes paralelos + docker-build gate
│   ├── sast.yml            — Bandit + Semgrep + pip-audit + Checkov
│   ├── dast.yml            — Schemathesis + OWASP ZAP
│   ├── load-test.yml       — Locust headless (workflow_dispatch)
│   └── sbom.yml            — syft + grype (matrix 3 serviços)
├── Log-Ingestion-and-Metrics/
│   ├── app/
│   │   ├── slo.py          — S4-01: cálculo puro de SLOs
│   │   ├── metrics_registry.py  — gauges Prometheus (error_budget_remaining_pct)
│   │   ├── models.py       — SloHealth, SloStatus, SloStatusReport
│   │   └── routers/metrics.py   — GET /metrics/slo-status
│   └── tests/
│       ├── test_slo.py     — 22 testes S4-01
│       └── test_e2e_redis.py — 4 testes E2E (testcontainers)
├── Incident-Response-Agent/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── anthropic_circuit_breaker.py  — S4-04
│   │   │   ├── fallback_analyzer.py           — S4-05
│   │   │   ├── orchestrator.py                — _synthesize + fallback
│   │   │   └── specialists/{base,latency,errors,saturation,traffic}.py
│   │   ├── auth.py         — S4-07: require_api_key multi-key + require_admin_key
│   │   ├── key_manager.py  — S4-07: parse/generate/validate/rotate keys
│   │   └── routers/
│   │       ├── analyze.py
│   │       └── admin.py    — S4-07: /admin/rotate-key, /revoke-legacy, /key-status
│   └── tests/
│       ├── test_circuit_breaker.py  — 19 testes S4-04
│       └── test_key_rotation.py     — 33 testes S4-07
├── Knowledge-Base/
│   ├── app/services/
│   │   ├── qdrant_service.py   — score_threshold=0.70
│   │   ├── embedding_service.py
│   │   └── chunk_validator.py
│   └── tests/
│       └── test_e2e_qdrant.py  — 6 testes E2E (testcontainers)
├── load-tests/
│   ├── locustfile.py       — LogIngestionUser + AnalysisUser
│   ├── check_slos.py       — validação de SLOs via CSV Locust
│   └── Makefile
├── infra/
│   ├── grafana/            — dashboard Golden Signals
│   └── prometheus/         — alerts.yaml + prometheus.yml
├── docs/
│   ├── post-mortems/       — INC-001 (Redis OOM), INC-002 (latency spike)
│   └── runbooks/           — high-latency.md, redis-memory.md
├── AgenticAI-Incident-Response.md  — SDD v1.7.0
├── prompt.md               — histórico de 21 interações com timestamps BRT
└── SESSION_MEMORY.md       — este arquivo
```

---

## 11. Decisões Técnicas Relevantes

| Decisão | Alternativa Descartada | Razão |
|---|---|---|
| `asyncio.gather()` para 4 especialistas | Execução sequencial | Reduz latência ~40s → ~10s |
| Redis sorted sets para latência | Média aritmética | P50/P95/P99 exatos sem janela deslizante |
| `API_KEY` como lista CSV | Restart obrigatório para rotação | Zero downtime na troca de chaves |
| `settings` import de módulo no circuit breaker | Import lazy dentro da função | Patchável em testes via `patch()` |
| `sys.modules` stub para sentence-transformers | Docker com modelos ML no CI | Evita 800 MB de dependências; CI < 60s |
| `app/scripts/*` excluído de coverage KB | Incluir seed_kb.py no coverage | Script de carga ≠ lógica de produção |
| `pytestmark` global removido de test_circuit_breaker | Mark global em todos os testes | Evita warnings em testes síncronos com pytest-asyncio `auto` mode |
| `hmac.compare_digest` em TODAS as chaves da lista | Primeiro match vence | Previne timing attacks em multi-key |
| `fail-fast: false` no sbom.yml matrix | fail-fast: true (default) | 3 serviços escaneados independentemente |

---

## 12. Erros Encontrados e Corrigidos

| Erro | Causa | Correção |
|---|---|---|
| E2E usava `POST /logs/ingest` | Endpoint real é `POST /logs` (202) | Corrigido antes de rodar |
| `ModuleNotFoundError: tenacity` | tenacity no requirements.txt mas não instalado | `pip install tenacity==8.3.0` |
| `AttributeError: module has no settings` no CB | `settings` importado lazy dentro de função | Movido para import de módulo |
| `return` faltando em `except AnthropicCircuitOpenError` | Bloco setava `overall` mas não retornava | Adicionado `return IncidentReport(...)` |
| Warnings `@pytest.mark.asyncio` em testes síncronos | `pytestmark = pytest.mark.asyncio` global | Removido; marca individual só em `async def` |
| Coverage KB 75% ao rodar da raiz do projeto | pyproject.toml omit não honrado fora do dir | Sempre rodar `pytest` de dentro do serviço |
| CSV Locust com `Name="/logs"` em vez de `"POST /logs"` | Locust usa o parâmetro `name=` no CSV | check_slos.py usa os mesmos nomes customizados |

---

## 13. Auditoria SDD × Harness (2026-05-15)

Realizada comparação sistemática entre o SDD e o código real. **9 gaps identificados e corrigidos:**

1. §4.5 contagens: IRA 122→174, Log-Ingestion 55→77
2. §4.5 cobertura: IRA 98.41%→99.35%, Log-Ingestion 94.06%→95.61%
3. §4.6 job descriptions desatualizados → corrigidos
4. §4.6 `sbom.yml` ausente da seção CI/CD → adicionado
5. A03:2021 `🔴 RISCO` → `✅ OK` (`_sanitize_finding_text()` implementado)
6. A06:2021 `⚠️ A VERIFICAR` → `✅ OK` (pip-audit + grype no CI)
7. SAST-03 aberto → `✅ MITIGADO`
8. SAST-07 "Falta CSP" → `✅ MITIGADO` (SecurityHeadersMiddleware)
9. LLM Top 10: coluna Status adicionada; LLM01/03/04/05/08/09/10 → ✅

---

## 14. Histórico de Commits

```
bc4655b  docs: atualiza prompt.md com prompt #21
2755d8c  docs: SDD v1.7.0 — auditoria de alinhamento SDD×Harness (9 gaps corrigidos)
3edb216  docs: atualiza prompt.md com prompt #19
d5a98db  feat: projeto completo — Sprints 1–4 concluídos
```

**Branch:** `main`  
**Arquivos commitados:** 133 arquivos, 11.302 inserções no commit inicial  
**`.claude/` excluído** via `.gitignore` — dados de sessão privados não versionados

---

## 15. Próximos Passos Sugeridos

Os itens abaixo **não foram implementados** nesta sessão e permanecem como trabalho futuro:

- [ ] **LLM02** — Anonimizar IPs/hostnames nas métricas antes de enviar ao Claude
- [ ] **LLM07** — Classificação formal de system prompts como dados sensíveis
- [ ] **A01/A05** — `API_KEY` obrigatória em todos os ambientes; Prometheus com auth básica
- [ ] **A09** — Alertas automáticos em Grafana/PagerDuty para breaching de SLOs
- [ ] **Mutmut** — Mutation testing (meta: ≥ 70% mutation score)
- [ ] **pip-compile --generate-hashes** — Pinnar dependências com hashes para supply chain completo
- [ ] **GitHub remote** — Push para github.com/valdomirosouza/AgenticAI-2-Incident-Response
- [ ] **Defesa da dissertação** — Apresentação dos resultados MTTD/MTTR ao orientador
