# AgenticAI-2-Incident-Response

**Agentic AI Copilot para Resposta a Incidentes de TI**

Sistema multi-agente que reduz o MTTD (_Mean Time to Detect_) e o MTTR (_Mean Time to Recovery_) substituindo a triagem manual de incidentes por análise orquestrada por IA em ~10 segundos.

> Dissertação de Mestrado — PPGCA / Unisinos  
> Autor: Valdomiro Souza

---

## Visão Geral

O sistema opera no modelo **Human-on-the-Loop (HOTL)**: quatro agentes especialistas analisam métricas em paralelo, consultam uma base de conhecimento histórica e produzem um `IncidentReport` estruturado com severidade, diagnóstico e recomendações priorizadas. O engenheiro on-call decide e executa — o sistema nunca age de forma autônoma.

```
HAProxy → Log-Ingestion (:8000) → Redis (Golden Signals)
                                         ↓
Engenheiro On-call → POST /analyze → Incident-Response-Agent (:8001)
                                         ├── LatencyAgent   → Claude tool-use
                                         ├── ErrorsAgent    → Claude tool-use
                                         ├── SaturationAgent→ Claude tool-use
                                         └── TrafficAgent   → Claude tool-use
                                         ↓
                                    Knowledge-Base (:8002) → Qdrant (RAG)
                                         ↓
                                    IncidentReport {severity, diagnosis, recommendations}
```

---

## Arquitetura

| Serviço                   | Porta         | Stack                                          |
| ------------------------- | ------------- | ---------------------------------------------- |
| Log-Ingestion-and-Metrics | :8000         | FastAPI + Redis 7                              |
| Incident-Response-Agent   | :8001         | FastAPI + Anthropic SDK (`claude-sonnet-4-6`)  |
| Knowledge-Base            | :8002         | FastAPI + Qdrant + sentence-transformers       |
| Redis                     | :6379         | Métricas em tempo real (Golden Signals)        |
| Qdrant                    | :6333         | Vector DB para busca semântica de post-mortems |
| Prometheus + Grafana      | :9090 / :3000 | Observabilidade                                |

---

## Pré-requisitos

- Python 3.12
- Docker + Docker Compose
- Chave de API da Anthropic

---

## Instalação e Execução

### 1. Variáveis de ambiente

```bash
cp .env.example .env
# Preencher: ANTHROPIC_API_KEY, API_KEY, ADMIN_KEY, REDIS_PASSWORD
```

### 2. Stack completa via Docker

```bash
docker compose up -d --wait
```

Serviços disponíveis após o start:

| URL                            | Descrição                            |
| ------------------------------ | ------------------------------------ |
| `http://localhost:8000/health` | Log-Ingestion health check           |
| `http://localhost:8001/health` | Incident-Response-Agent health check |
| `http://localhost:8002/health` | Knowledge-Base health check          |
| `http://localhost:3000`        | Grafana (Golden Signals dashboard)   |
| `http://localhost:9090`        | Prometheus                           |

### 3. Disparar uma análise de incidente

```bash
curl -X POST http://localhost:8001/analyze \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json"
```

Resposta (`IncidentReport`):

```json
{
  "timestamp": "2026-05-15T20:00:00Z",
  "overall_severity": "warning",
  "title": "Latency Spike Detected",
  "diagnosis": "P95 response time elevated at 620ms...",
  "recommendations": ["Scale backend pool", "Check Redis memory usage"],
  "findings": [...],
  "similar_incidents": ["INC-002"]
}
```

---

## Testes

Cada serviço tem seu próprio venv e configuração de cobertura (`pyproject.toml`). Gate mínimo: **85%** de cobertura.

```bash
# Setup (uma vez por serviço)
cd <serviço>
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt   # ou requirements-test.txt para KB

# Rodar testes unitários
.venv/bin/pytest tests/ -q --tb=short --ignore=tests/test_e2e_*.py

# Rodar testes E2E (requer Docker ativo)
.venv/bin/pip install testcontainers
.venv/bin/pytest tests/test_e2e_*.py -v
```

### Cobertura atual

| Serviço                   | Testes          | Cobertura |
| ------------------------- | --------------- | --------- |
| Log-Ingestion-and-Metrics | 77 unit + 4 E2E | 96.96%    |
| Incident-Response-Agent   | 174 unit        | 98.26%    |
| Knowledge-Base            | 49 unit + 6 E2E | 97.60%    |

---

## CI/CD

| Workflow        | Trigger           | O que faz                                  |
| --------------- | ----------------- | ------------------------------------------ |
| `ci.yml`        | push / PR         | pytest nos 3 serviços + docker build gate  |
| `sast.yml`      | push / PR → main  | bandit + semgrep + pip-audit + checkov     |
| `dast.yml`      | push → main       | Schemathesis fuzzing + OWASP ZAP baseline  |
| `sbom.yml`      | push / PR → main  | syft (SPDX) + grype (bloqueia CVE crítico) |
| `load-test.yml` | workflow_dispatch | Locust + validação de SLOs                 |

---

## SLOs

| SLO             | Target | Threshold       |
| --------------- | ------ | --------------- |
| Disponibilidade | 99.5%  | taxa 5xx ≤ 0.5% |
| Latência P95    | 99.0%  | P95 ≤ 500 ms    |
| Latência P99    | 99.9%  | P99 ≤ 1000 ms   |

Endpoint de status: `GET http://localhost:8000/metrics/slo-status`

---

## Segurança

- Autenticação por API Key com suporte a múltiplas chaves (CSV) e rotação sem downtime (`POST /admin/rotate-key`)
- Sanitização de input LLM contra prompt injection (`_sanitize_finding_text()`)
- Validação Pydantic do output do Claude antes de construir o `IncidentReport`
- Circuit breaker para a Anthropic API (tenacity) com fallback baseado em regras
- Dockerfiles com usuário não-root (`USER appuser`), imagem `python:3.12-slim-bookworm`
- SBOM gerado por `syft` (SPDX JSON) + scan de CVEs por `grype`

Mapeamento completo OWASP Top 10 Web (2021) e OWASP LLM Top 10 (2025) no [SDD](AgenticAI-Incident-Response.md) §7.

---

## Documentação

| Arquivo                                                            | Descrição                                                |
| ------------------------------------------------------------------ | -------------------------------------------------------- |
| [`AgenticAI-Incident-Response.md`](AgenticAI-Incident-Response.md) | SDD v1.7.0 — especificação completa do sistema           |
| [`CLAUDE.md`](CLAUDE.md)                                           | Guia para Claude Code (comandos, convenções, regras)     |
| [`docs/post-mortems/`](docs/post-mortems/)                         | Post-mortems dos incidentes de referência                |
| [`docs/runbooks/`](docs/runbooks/)                                 | Runbooks operacionais                                    |
| [`SESSION_MEMORY.md`](SESSION_MEMORY.md)                           | Histórico técnico detalhado da sessão de desenvolvimento |

---

## Estrutura do Repositório

```
├── Incident-Response-Agent/   # Serviço :8001 — orquestrador + 4 agentes IA
├── Knowledge-Base/            # Serviço :8002 — RAG com Qdrant
├── Log-Ingestion-and-Metrics/ # Serviço :8000 — ingestão HAProxy + Golden Signals
├── load-tests/                # Locust + check_slos.py
├── infra/                     # Prometheus + Grafana
├── docs/                      # Post-mortems e runbooks
├── .github/workflows/         # 5 pipelines CI/CD
├── docker-compose.yml
└── .env.example
```

---

## Licença

Projeto acadêmico — PPGCA / Unisinos. Uso para fins de pesquisa e dissertação de mestrado.
