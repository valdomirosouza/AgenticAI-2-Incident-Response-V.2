# Product Requirements Document

## AgenticAI-2-Incident-Response

**Agentic AI Copilot para Resposta a Incidentes de TI**

| Campo       | Valor                                                      |
| ----------- | ---------------------------------------------------------- |
| Versão      | 1.0.0 — Maio 2026                                          |
| Status      | Aprovado                                                   |
| Projeto     | Dissertação de Mestrado — PPGCA / Unisinos                 |
| Autor       | Valdomiro Souza                                            |
| Revisão SDD | [AgenticAI-Incident-Response.md](../AgenticAI-Incident-Response.md) v1.8.0 |

---

## Sumário

1. [Visão do Produto](#1-visão-do-produto)
2. [Problema](#2-problema)
3. [Objetivos e Métricas de Sucesso](#3-objetivos-e-métricas-de-sucesso)
4. [Usuários e Stakeholders](#4-usuários-e-stakeholders)
5. [Requisitos Funcionais](#5-requisitos-funcionais)
6. [Requisitos Não-Funcionais](#6-requisitos-não-funcionais)
7. [Fora do Escopo](#7-fora-do-escopo)
8. [Restrições e Premissas](#8-restrições-e-premissas)
9. [Dependências](#9-dependências)
10. [Roadmap](#10-roadmap)
11. [Critérios de Aceite](#11-critérios-de-aceite)
12. [Glossário](#12-glossário)

---

## 1. Visão do Produto

O **AgenticAI-2-Incident-Response** é um copiloto de IA para equipes de SRE que reduz o tempo de triagem de incidentes de TI de minutos para aproximadamente **10 segundos**. O sistema opera no modelo **Human-on-the-Loop (HOTL)**: quatro agentes especialistas analisam métricas em paralelo, consultam uma base de conhecimento histórica e produzem um relatório estruturado com severidade, diagnóstico e recomendações priorizadas. O engenheiro on-call decide e executa — o sistema nunca age de forma autônoma.

> "Substituir triagem manual de incidentes por análise orquestrada por IA, mantendo o humano no controle."

---

## 2. Problema

### 2.1 Contexto

Em ambientes de produção de alta disponibilidade, a detecção e diagnóstico inicial de incidentes é um processo manual que exige que o engenheiro on-call:

1. Consulte múltiplos dashboards (latência, erros, saturação, tráfego)
2. Correlacione métricas de fontes distintas
3. Recorde ou pesquise incidentes históricos similares
4. Formule um diagnóstico inicial e priorize ações

Esse processo pode levar de **5 a 30 minutos** apenas na fase de triagem (MTTD), durante os quais o impacto ao usuário final continua crescendo.

### 2.2 Dor Principal

| Dor | Impacto |
|-----|---------|
| Triagem manual lenta | MTTD alto → maior impacto ao usuário |
| Correlação de métricas dispersa | Diagnóstico incompleto ou incorreto |
| Ausência de contexto histórico | Reincidência de incidentes já resolvidos |
| Fadiga do engenheiro on-call | Decisões ruins sob pressão e fora do horário comercial |

---

## 3. Objetivos e Métricas de Sucesso

### 3.1 Objetivos

| ID | Objetivo | Métrica | Meta |
|----|----------|---------|------|
| OBJ-01 | Reduzir MTTD | Tempo de triagem inicial | ≤ 10 segundos (P95) |
| OBJ-02 | Alta disponibilidade | Taxa de erros 5xx | ≤ 0.5% |
| OBJ-03 | Latência da API de análise | P95 de `/analyze` | ≤ 500 ms (excluindo tempo LLM) |
| OBJ-04 | Cobertura de testes | Cobertura de branches | ≥ 85% por serviço |
| OBJ-05 | Qualidade do diagnóstico | Incidentes históricos recuperados corretamente | Score semântico ≥ 0.70 (coseno) |

### 3.2 Anti-objetivos

- O sistema **não** deve executar ações de remediação automaticamente.
- O sistema **não** deve ser a única fonte de decisão — é um copiloto, não um piloto automático.

---

## 4. Usuários e Stakeholders

### 4.1 Usuário Principal — Engenheiro On-call (SRE)

**Perfil:** Engenheiro de confiabilidade responsável pelo plantão de incidentes.

**Jornadas principais:**

1. **Triagem imediata:** Disparar `POST /analyze` ao receber alerta; obter `IncidentReport` com severidade e diagnóstico em ≤ 10s.
2. **Priorização de ações:** Usar as `recommendations` do relatório para decidir a primeira ação de mitigação.
3. **Busca de contexto histórico:** Verificar `similar_incidents` para aplicar solução já conhecida.

### 4.2 Stakeholders Secundários

| Stakeholder | Interesse Principal |
|-------------|---------------------|
| Pesquisador (Autor) | Validade científica dos resultados para a dissertação |
| Orientador PPGCA | Rigor metodológico e fundamentação na RSL |
| Equipe de Segurança | Conformidade OWASP Top 10 e OWASP LLM Top 10 (2025) |
| Operações | Observabilidade, uptime e operabilidade da stack |

---

## 5. Requisitos Funcionais

### RF-01 — Ingestão de Logs (Log-Ingestion-and-Metrics, :8000)

| ID | Requisito |
|----|-----------|
| RF-01.1 | Aceitar logs HAProxy via `POST /logs` (JSON) e persistir no Redis em < 50 ms |
| RF-01.2 | Agregar Golden Signals: RPS, latência (P50/P95/P99), taxa de erros 4xx/5xx, saturação Redis |
| RF-01.3 | Expor métricas via `GET /metrics/overview`, `/response-times`, `/rps`, `/saturation`, `/backends` |
| RF-01.4 | Expor endpoint Prometheus `GET /prometheus/metrics` para scrape por Prometheus/Grafana |
| RF-01.5 | Calcular e expor status de SLOs via `GET /metrics/slo-status` com error budget |
| RF-01.6 | Sanitizar dados pessoais (IPs, FQDNs internos) antes de persistir (`pii.py`) |

### RF-02 — Análise de Incidente por IA (Incident-Response-Agent, :8001)

| ID | Requisito |
|----|-----------|
| RF-02.1 | Aceitar `POST /analyze` com autenticação por `X-API-Key` e rate limit de 10 req/min |
| RF-02.2 | Executar 4 agentes especialistas em paralelo (`asyncio.gather`): Latency, Errors, Saturation, Traffic |
| RF-02.3 | Cada agente deve executar tool-use loop com Claude (`claude-sonnet-4-6`) para buscar e interpretar métricas |
| RF-02.4 | Consultar Knowledge-Base via `POST /kb/search` quando houver findings não-OK |
| RF-02.5 | Sintetizar findings em `IncidentReport` com: timestamp, overall_severity, title, diagnosis, recommendations, findings[4], similar_incidents[] |
| RF-02.6 | Ativar fallback baseado em regras quando a API Anthropic estiver indisponível (circuit breaker via tenacity) |
| RF-02.7 | Sanitizar texto de findings antes de incluir em prompts LLM (`_sanitize_finding_text()`, MAX=500 chars) |
| RF-02.8 | Expor rotação de API Keys sem downtime via `POST /admin/rotate-key` |

### RF-03 — Base de Conhecimento (Knowledge-Base, :8002)

| ID | Requisito |
|----|-----------|
| RF-03.1 | Aceitar ingestão de chunks de post-mortems via `POST /kb/ingest` (autenticado) com embeddings `all-MiniLM-L6-v2` |
| RF-03.2 | Executar busca semântica via `POST /kb/search` com score_threshold ≥ 0.70 |
| RF-03.3 | Retornar lista vazia (sem erro) quando KB estiver indisponível — degradação graciosa |
| RF-03.4 | Rejeitar chunks maiores que o limite configurado (`validate_chunk_size()`) |
| RF-03.5 | Detectar e rejeitar linguagem de culpa em chunks (`detect_blameful_language()`) |

### RF-04 — Observabilidade

| ID | Requisito |
|----|-----------|
| RF-04.1 | Todos os serviços devem expor `GET /health` com status HTTP 200 quando saudáveis |
| RF-04.2 | Prometheus deve scraper métricas dos 3 serviços; Grafana deve exibir dashboard Golden Signals |
| RF-04.3 | Logs estruturados em JSON com `request_id`, `duration_ms`, `status_code` em todos os serviços |

---

## 6. Requisitos Não-Funcionais

### RNF-01 — Desempenho

| ID | Requisito | Threshold |
|----|-----------|-----------|
| RNF-01.1 | Latência P95 de `POST /analyze` (excluindo tempo de resposta Claude) | ≤ 500 ms |
| RNF-01.2 | Latência P99 de `POST /logs` | ≤ 100 ms |
| RNF-01.3 | Tempo total de `POST /analyze` end-to-end (incluindo Claude) | ≤ 30 s (P95) |

### RNF-02 — Disponibilidade e SLOs

| SLO | Target | Threshold |
|-----|--------|-----------|
| Disponibilidade | 99.5% | Taxa 5xx ≤ 0.5% |
| Latência P95 | 99.0% | P95 ≤ 500 ms |
| Latência P99 | 99.9% | P99 ≤ 1000 ms |

### RNF-03 — Segurança

| ID | Requisito |
|----|-----------|
| RNF-03.1 | Autenticação por API Key com suporte a múltiplas chaves (CSV) e rotação sem downtime |
| RNF-03.2 | Comparação de API Keys com `hmac.compare_digest` (timing-safe) |
| RNF-03.3 | Nunca logar API Keys — usar apenas hash SHA-256 truncado (8 chars) |
| RNF-03.4 | Validação de output do Claude com Pydantic antes de construir `IncidentReport` |
| RNF-03.5 | Todos os containers executam como usuário não-root (`USER appuser`) |
| RNF-03.6 | Documentação desabilitada em produção (`enable_docs=False`) |
| RNF-03.7 | SBOM gerado por `syft` (SPDX JSON) + scan de CVEs por `grype` (bloqueia CRITICAL) |
| RNF-03.8 | Conformidade com OWASP Top 10 Web (2021) e OWASP LLM Top 10 (2025) |

### RNF-04 — Qualidade de Código

| ID | Requisito |
|----|-----------|
| RNF-04.1 | Cobertura mínima de testes: 85% (branch coverage) por serviço |
| RNF-04.2 | Complexidade ciclomática máxima: 10 (McCabe, via ruff `max-complexity`) |
| RNF-04.3 | Formatação: `black` + `ruff`, line-length=110, target `py312` |

### RNF-05 — Operabilidade

| ID | Requisito |
|----|-----------|
| RNF-05.1 | Stack completa deve subir com `docker compose up -d --wait` sem intervenção manual |
| RNF-05.2 | Cada serviço deve ter `README.md` com instruções de instalação, execução e testes |
| RNF-05.3 | Runbooks operacionais disponíveis para os cenários de falha mais comuns |

---

## 7. Fora do Escopo

- **Remediação automática:** O sistema nunca executará ações corretivas de forma autônoma (ex: reiniciar serviços, fazer rollback, escalar recursos).
- **Interface gráfica (UI):** Toda interação ocorre via API REST. Não há frontend web ou mobile nesta versão.
- **Multi-tenant:** O sistema é projetado para uma única organização/equipe. Não há isolamento de dados entre clientes.
- **Integração com sistemas de pagerduty/alerting:** Notificações ativas ou webhooks de alerta estão fora do escopo desta versão.
- **Treinamento ou fine-tuning de modelos:** O sistema usa Claude via API; não há customização do modelo LLM.
- **Persistência de longo prazo de `IncidentReport`:** Os relatórios são retornados na resposta HTTP e não são armazenados automaticamente pelo sistema.

---

## 8. Restrições e Premissas

### 8.1 Restrições

| ID | Restrição |
|----|-----------|
| R-01 | Python 3.12 como runtime obrigatório |
| R-02 | Modelo LLM fixo em `claude-sonnet-4-6` (Anthropic) |
| R-03 | Ambiente de execução: Docker + Docker Compose (sem Kubernetes nesta versão) |
| R-04 | Chave `ANTHROPIC_API_KEY` obrigatória em produção |
| R-05 | Licenças de dependências não podem incluir GPL, AGPL, LGPL, SSPL ou CC-BY-NC |

### 8.2 Premissas

| ID | Premissa |
|----|----------|
| P-01 | HAProxy envia logs em formato JSON compatível com o modelo `HaproxyLog` |
| P-02 | Redis 7 está disponível no mesmo namespace de rede que o Log-Ingestion |
| P-03 | Qdrant v1.18.0 está disponível no mesmo namespace de rede que o Knowledge-Base |
| P-04 | A API Anthropic tem disponibilidade ≥ 99.5%; o circuit breaker cobre falhas temporárias |
| P-05 | O engenheiro on-call tem acesso à API Key para disparar análises |

---

## 9. Dependências

| Componente | Dependência | Versão | Criticidade |
|------------|-------------|--------|-------------|
| Incident-Response-Agent | Anthropic API (`claude-sonnet-4-6`) | — | Crítica (circuit breaker presente) |
| Incident-Response-Agent | Log-Ingestion-and-Metrics (`:8000`) | — | Crítica |
| Incident-Response-Agent | Knowledge-Base (`:8002`) | — | Alta (degradação graciosa) |
| Knowledge-Base | Qdrant | v1.18.0 | Crítica |
| Log-Ingestion-and-Metrics | Redis | 7-alpine | Crítica |
| Todos | Python | 3.12 | Crítica |
| Todos | Docker + Docker Compose | — | Crítica |

---

## 10. Roadmap

| Sprint | Foco | Status |
|--------|------|--------|
| Sprint 1 | Ingestão de logs, Golden Signals, Redis | ✅ Concluído |
| Sprint 2 | Agentes IA, tool-use loop, IncidentReport | ✅ Concluído |
| Sprint 3 | Knowledge-Base (Qdrant + RAG), circuit breaker | ✅ Concluído |
| Sprint 4 | Observabilidade (Prometheus, Grafana, SLOs, alertas LLM) | ✅ Concluído |
| Sprint 5 | Skill-based Governance Maturity (12 skills, specs, NALSD, DPIA, chaos) | ✅ Concluído |
| Sprint 6 | DPA com Anthropic, LGPD DSAR portal, Grafana LLM dashboard | Planejado |

Detalhamento completo no [SDD §8 — Roadmap de Implementação](../AgenticAI-Incident-Response.md).

---

## 11. Critérios de Aceite

### CA-01 — Análise de Incidente

- [ ] `POST /analyze` retorna `IncidentReport` válido (Pydantic) em ≤ 30s (P95)
- [ ] `overall_severity` reflete corretamente o pior finding entre os 4 especialistas
- [ ] `similar_incidents` contém IDs de incidentes históricos relevantes quando disponíveis
- [ ] `recommendations` contém entre 1 e 5 itens priorizados

### CA-02 — Resiliência

- [ ] Com Anthropic API indisponível: circuit breaker ativa fallback baseado em regras sem erro HTTP 5xx
- [ ] Com Knowledge-Base indisponível: análise completa com `similar_incidents: []` sem erro

### CA-03 — Segurança

- [ ] `POST /analyze` sem `X-API-Key` retorna HTTP 401
- [ ] `POST /analyze` com mais de 10 req/min retorna HTTP 429
- [ ] Nenhum log contém API Key em texto plano (somente hash 8-char)

### CA-04 — Observabilidade

- [ ] `GET /health` de todos os 3 serviços retorna HTTP 200 com stack ativa
- [ ] `GET /metrics/slo-status` retorna `SloStatusReport` com campos `budget_remaining` calculados

### CA-05 — CI/CD

- [ ] Pipeline `ci.yml` passa com cobertura ≥ 85% nos 3 serviços
- [ ] Pipeline `sast.yml` não detecta secrets expostos (trufflehog) nem CVEs CRITICAL (grype)
- [ ] Pipeline `sbom.yml` gera SBOM SPDX JSON e assina com cosign sem erros

---

## 12. Glossário

| Termo | Definição |
|-------|-----------|
| MTTD | Mean Time to Detect — tempo médio para detecção de incidente |
| MTTR | Mean Time to Recovery — tempo médio para recuperação |
| HOTL | Human-on-the-Loop — humano supervisiona, IA analisa e recomenda |
| SLO | Service Level Objective — objetivo de nível de serviço |
| SLI | Service Level Indicator — indicador mensurável do SLO |
| Golden Signals | Latência, Tráfego, Erros e Saturação (Google SRE) |
| RAG | Retrieval-Augmented Generation — busca vetorial + geração LLM |
| DPIA | Data Protection Impact Assessment — avaliação de impacto à privacidade (LGPD/GDPR) |
| SBOM | Software Bill of Materials — inventário de dependências de software |
| Circuit Breaker | Padrão de resiliência que interrompe chamadas a serviços com falha |
| Tool-use loop | Ciclo em que o LLM invoca ferramentas externas para coletar dados antes de responder |
