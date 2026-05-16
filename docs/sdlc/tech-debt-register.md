# Tech Debt Register — AgenticAI-2-Incident-Response

**Processo:** skills/sdlc-governance/tech-debt-process.md  
**Revisão trimestral:** Q3-2026 (2026-08-01)  
**Responsável:** Valdomiro Souza  
**Budget de resolução:** ≥ 20% da capacidade de cada sprint

---

## Índice de Debts

| ID                              | Título                                                              | Tipo          | Severidade | Serviço        | Status        |
| ------------------------------- | ------------------------------------------------------------------- | ------------- | ---------- | -------------- | ------------- |
| [DEBT-2026-001](#debt-2026-001) | `min_similarity_score=0.30` subótimo para LLM08:2025                | Security      | Medium     | Knowledge-Base | Open          |
| [DEBT-2026-002](#debt-2026-002) | Sorted Set `response_times` sem TTL explícito                       | Reliability   | Low        | Log-Ingestion  | Open          |
| [DEBT-2026-003](#debt-2026-003) | Estado do circuit breaker não compartilhado entre réplicas          | Reliability   | Low        | IRA            | Accepted Risk |
| [DEBT-2026-004](#debt-2026-004) | `ConfigDict(extra="ignore")` pode mascarar mudanças no schema LLM   | Observability | Low        | IRA            | Open          |
| [DEBT-2026-005](#debt-2026-005) | Sem rate limiting no endpoint Prometheus                            | Security      | Medium     | Log-Ingestion  | Open          |
| [DEBT-2026-006](#debt-2026-006) | Chave API única para todos os clientes                              | Security      | Low        | IRA + KB       | Accepted Risk |
| [DEBT-2026-007](#debt-2026-007) | `analyze_saturation` mede apenas memória Redis, sem CPU/disco       | Observability | Low        | IRA            | Open          |
| [DEBT-2026-008](#debt-2026-008) | `requirements.txt` de KB runtime sem hashes (só `-test` tem hashes) | Security      | Medium     | Knowledge-Base | Open          |
| [DEBT-2026-009](#debt-2026-009) | DPA formal com Anthropic ausente para uso em produção real           | Compliance    | Medium     | IRA            | Open          |
| [DEBT-2026-010](#debt-2026-010) | Sem mecanismo self-service para direitos dos titulares (LGPD Art. 18) | Compliance   | Low        | Sistema        | Open          |
| [DEBT-2026-011](#debt-2026-011) | Dashboard Grafana dedicado a métricas LLM ausente                    | Observability | Low        | IRA            | Open          |
| [DEBT-2026-012](#debt-2026-012) | Chaos experiments planejados mas não executados em staging           | Reliability   | Low        | Sistema        | Open          |
| [DEBT-2026-013](#debt-2026-013) | ADR lifecycle não exercitado (superseded/proposed/deprecated vazios) | Compliance    | Low        | Transversal    | Open          |

---

## DEBT-2026-001

**Título:** `min_similarity_score=0.30` subótimo para LLM08:2025  
**Tipo:** Security  
**Severidade:** Medium  
**Serviço afetado:** Knowledge-Base  
**Registrado por:** Valdomiro Souza em 2026-05-15  
**Descoberto via:** Cenário de teste E2E (INC-003) + ADR-2026-0004/0008

### Descrição

O threshold de similaridade cosine foi reduzido de 0.70 para 0.30 porque os post-mortems estão escritos em PT-BR enquanto as queries dos agentes chegam em inglês. Com `all-MiniLM-L6-v2` (monolíngue EN), o cosine similarity máximo observado entre chunks PT-BR e queries EN foi ~0.38.

**Estado atual:** `min_similarity_score: float = 0.30`  
**Estado desejado:** `min_similarity_score: float = 0.70` (recomendação OWASP LLM08:2025)

### Impacto

- **Risco operacional:** Threshold baixo aumenta risco de RAG Poisoning — chunks com similaridade baixa mas lexicalmente ruidosos podem ser recuperados
- **Custo atual:** Tolerado; corpus pequeno (34 chunks) reduz superfície de ataque
- **Bloqueadores:** Nenhum técnico — apenas falta de corpus em EN ou modelo multilíngue

### Critérios de Resolução

- [ ] Post-mortems migrados para inglês **ou** modelo multilíngue adotado
- [ ] `min_similarity_score` restaurado para `0.70` em `Knowledge-Base/app/config.py`
- [ ] Testes E2E confirmam KB retrieval com score > 0.70

### Esforço

- Reescrever post-mortems em EN: ~2h
- Migrar para `paraphrase-multilingual-MiniLM-L12-v2`: ~4h (reindexação completa)

**Prioridade:** P2 — Target Q3-2026

---

## DEBT-2026-002

**Título:** Sorted Set `metrics:response_times` sem TTL explícito  
**Tipo:** Reliability  
**Severidade:** Low  
**Serviço afetado:** Log-Ingestion-and-Metrics  
**Registrado por:** Valdomiro Souza em 2026-05-14  
**Descoberto via:** Análise de design — ADR-2026-0003

### Descrição

O sorted set Redis `metrics:response_times` cresce indefinidamente sem TTL explícito. Atualmente mitigado pela política `allkeys-lru`, mas a eviction pode remover métricas recentes em vez de antigas.

**Estado atual:** Sem `EXPIRE` no sorted set; depende de `allkeys-lru`  
**Estado desejado:** `EXPIRE` periódico ou limpeza de entradas com mais de N horas

### Impacto

- **Risco operacional:** Sob carga alta, `allkeys-lru` pode evictar dados recentes
- **Custo atual:** Baixo — corpus pequeno de dissertação não pressiona memória
- **Bloqueadores:** Nenhum

### Critérios de Resolução

- [ ] Lógica de limpeza periódica adicionada em `ingestion.py` (ex: `ZREMRANGEBYSCORE` com cutoff de 1h)
- [ ] Teste unitário cobrindo o comportamento de limpeza

**Esforço:** ~2h  
**Prioridade:** P3 — Backlog

---

## DEBT-2026-003

**Título:** Estado do circuit breaker não compartilhado entre réplicas do IRA  
**Tipo:** Reliability  
**Severidade:** Low  
**Serviço afetado:** Incident-Response-Agent  
**Registrado por:** Valdomiro Souza em 2026-05-15  
**Descoberto via:** Design review — ADR-2026-0010

### Descrição

O estado CLOSED/OPEN/HALF_OPEN do circuit breaker é mantido em memória por processo. Em deploy com múltiplas réplicas, cada instância tem estado independente — uma pode estar OPEN enquanto outra está CLOSED.

**Estado atual:** Estado em `AnthropicCircuitBreaker` (memória local por processo)  
**Estado desejado:** Estado compartilhado via Redis (consistente entre réplicas)

### Impacto

- **Risco operacional:** Em multi-instância, sistema não para de chamar API Anthropic mesmo com circuit OPEN em algumas réplicas
- **Custo atual:** Zero — deploy atual é single-instance (dissertação)

### Aceite de Risco

**Aceito como risco por:** Valdomiro Souza em 2026-05-15  
**Justificativa:** Sistema roda single-instance; Kubernetes HPA não está no escopo da dissertação  
**Revisão:** Se deploy multi-instância for adicionado

---

## DEBT-2026-004

**Título:** `ConfigDict(extra="ignore")` pode mascarar mudanças no schema LLM  
**Tipo:** Observability  
**Severidade:** Low  
**Serviço afetado:** Incident-Response-Agent  
**Registrado por:** Valdomiro Souza em 2026-05-15  
**Descoberto via:** ADR-2026-0011

### Descrição

`OrchestratorResponse` usa `model_config = ConfigDict(extra="ignore")` para tolerar campos extras no JSON do Claude. Isso significa que se o Claude começar a retornar um campo importante novo, será silenciosamente descartado.

**Estado atual:** Campos extras silenciosamente ignorados  
**Estado desejado:** Log de warning quando campos extras são detectados

### Critérios de Resolução

- [ ] `model_validator` que loga `WARNING` ao detectar campos não esperados
- [ ] Teste cobrindo o comportamento de log

**Esforço:** ~1h  
**Prioridade:** P3 — Backlog

---

## DEBT-2026-005

**Título:** Endpoint `/prometheus/metrics` sem auth no Log-Ingestion em staging  
**Tipo:** Security  
**Severidade:** Medium  
**Serviço afetado:** Log-Ingestion-and-Metrics  
**Registrado por:** Valdomiro Souza em 2026-05-16  
**Descoberto via:** Auditoria de segurança A05

### Descrição

O `prometheus_api_key` está configurado como obrigatório em staging/production no validator do config, mas o `.env.example` não inclui `PROMETHEUS_API_KEY`. Deployments em staging podem iniciar sem a variável configurada.

**Estado atual:** Validator obriga em staging mas `.env.example` não documenta  
**Estado desejado:** `.env.example` inclui `PROMETHEUS_API_KEY=<change-me>`

### Critérios de Resolução

- [ ] `.env.example` atualizado com `PROMETHEUS_API_KEY=<change-me>` (IRA + LI)

**Esforço:** ~15 min  
**Prioridade:** P2 — Target próximo sprint

---

## DEBT-2026-006

**Título:** Chave API única compartilhada entre todos os clientes  
**Tipo:** Security  
**Severidade:** Low  
**Serviço afetado:** IRA + Knowledge-Base  
**Registrado por:** Valdomiro Souza em 2026-05-14  
**Descoberto via:** ADR-2026-0009

### Descrição

Uma única `API_KEY` autentica todos os clientes (IRA chamando KB, operador chamando IRA). Sem auditoria granular por cliente — se comprometida, todos os acessos são revogados juntos.

**Estado atual:** `API_KEY` única por serviço  
**Estado desejado:** Chave por serviço chamador com label de auditoria

### Aceite de Risco

**Aceito como risco por:** Valdomiro Souza em 2026-05-14  
**Justificativa:** Apenas 1 cliente por serviço no escopo da dissertação; multi-key CSV já implementado se necessário  
**Revisão:** Se novos consumers forem adicionados

---

## DEBT-2026-007

**Título:** `analyze_saturation` mede apenas memória Redis, sem CPU/disco  
**Tipo:** Observability  
**Severidade:** Low  
**Serviço afetado:** Incident-Response-Agent  
**Registrado por:** Valdomiro Souza em 2026-05-14  
**Descoberto via:** ADR-2026-0007

### Descrição

O agente de Saturation analisa apenas `INFO memory` do Redis. Saturação de CPU do host e espaço em disco não são monitorados pelos especialistas de IA.

**Estado atual:** `SaturationAgent` analisa apenas Redis memory  
**Estado desejado:** Métricas de CPU e disco via `node_exporter` ou endpoint dedicado

### Critérios de Resolução

- [ ] Adicionar `node_exporter` ao `docker-compose.yml`
- [ ] `SaturationAgent` expandido para analisar CPU% e disk%

**Esforço:** ~4h  
**Prioridade:** P3 — Backlog

---

## DEBT-2026-008

**Título:** `Knowledge-Base/requirements.txt` (runtime) sem `--generate-hashes`  
**Tipo:** Security  
**Severidade:** Medium  
**Serviço afetado:** Knowledge-Base  
**Registrado por:** Valdomiro Souza em 2026-05-16  
**Descoberto via:** Auditoria pip-compile — sprint de segurança

### Descrição

`Knowledge-Base/requirements-test.txt` tem SHA-256 hashes (supply chain protection), mas `Knowledge-Base/requirements.txt` (runtime com `sentence-transformers`/`torch`) não tem hashes porque `torch` é incompatível com `--generate-hashes` sem `--allow-unsafe` e `find-links`.

**Estado atual:** Runtime KB sem hashes; container KB usa `pip install` sem `--require-hashes`  
**Estado desejado:** Hashes também no requirements.txt runtime

### Critérios de Resolução

- [ ] Investigar compatibilidade de `pip-compile --generate-hashes` com `torch` + `--find-links`
- [ ] KB Dockerfile atualizado com `--require-hashes`

**Esforço:** ~3h (investigação + teste)  
**Prioridade:** P2 — Target Q3-2026

---

## DEBT-2026-009

**Título:** DPA formal com Anthropic ausente para uso em produção real
**Tipo:** Compliance
**Severidade:** Medium
**Serviço afetado:** Incident-Response-Agent
**Registrado por:** Valdomiro Souza em 2026-05-16
**Descoberto via:** Análise de gaps das skills — DPIA (docs/security/dpia.md §4)

### Descrição

O sistema envia findings de métricas de infraestrutura para a Anthropic API (Claude Sonnet 4.6).
Embora os dados sejam anonimizados (IPs/FQDNs redactados antes do envio), não há um Data
Processing Agreement (DPA) formal assinado com a Anthropic PBC.

Para uso acadêmico (dissertação) o risco é baixo. Para produção real com dados de clientes,
um DPA é obrigatório pela LGPD (Art. 26 e 39) e GDPR (Art. 28).

**Estado atual:** Sem DPA; base legal = Anthropic Privacy Policy pública
**Estado desejado:** DPA formal assinado com Anthropic antes de produção com dados reais

### Impacto

- **Risco jurídico:** Transferência internacional sem DPA viola LGPD Art. 33 em produção
- **Custo atual:** Zero — sistema acadêmico; dados de infra anonimizados
- **Bloqueadores:** Requer processo jurídico/contratual com Anthropic

### Critérios de Resolução

- [ ] DPA formal assinado com Anthropic (ou uso de Anthropic Claude API Enterprise)
- [ ] Referência ao DPA adicionada em `docs/dependency-manifest-ira.yaml` (campo `dpa_reference`)
- [ ] `docs/security/dpia.md §4` atualizado com referência ao DPA

**Esforço:** Jurídico/contratual — 2-4 semanas
**Prioridade:** P2 — Obrigatório antes de produção real com dados de usuários

---

## DEBT-2026-010

**Título:** Sem mecanismo self-service para direitos dos titulares (LGPD Art. 18)
**Tipo:** Compliance
**Severidade:** Low
**Serviço afetado:** Sistema (transversal)
**Registrado por:** Valdomiro Souza em 2026-05-16
**Descoberto via:** Análise de gaps — docs/security/lgpd-checklist.md §3

### Descrição

A LGPD (Art. 18) garante aos titulares o direito de acesso, correção, eliminação e portabilidade
de dados. Atualmente o mecanismo é apenas via email (valdomiro.souza@zsms.cloud) — sem portal
ou API self-service. Para sistema acadêmico é aceitável; para produção com usuários reais,
é exigido um mecanismo mais formal.

**Estado atual:** Direitos atendidos manualmente via email
**Estado desejado:** Endpoint ou portal de DSAR (Data Subject Access Request)

### Impacto

- **Risco jurídico:** Baixo — sistema interno/acadêmico sem titulares identificados
- **Custo atual:** Zero no escopo da dissertação
- **Bloqueadores:** Fora do escopo acadêmico; relevante apenas em produção real

### Critérios de Resolução

- [ ] Endpoint `POST /privacy/dsar` para solicitar acesso/eliminação de dados
- [ ] SLA de resposta documentado (LGPD: 15 dias)
- [ ] `docs/security/lgpd-checklist.md §3` atualizado

**Esforço:** ~8h (endpoint + documentação)
**Prioridade:** P3 — Backlog (pré-requisito para produção real)

---

## DEBT-2026-011

**Título:** Dashboard Grafana dedicado a métricas LLM ausente
**Tipo:** Observability
**Severidade:** Low
**Serviço afetado:** Incident-Response-Agent
**Registrado por:** Valdomiro Souza em 2026-05-16
**Descoberto via:** Análise de gaps — skill ai-governance §LLM Observability

### Descrição

As métricas LLM (`llm_call_duration_seconds`, `llm_calls_total`, `llm_output_validation_failures_total`,
`prompt_injection_sanitized_total`) estão expostas no Prometheus, mas o dashboard Grafana existente
(`golden-signals.json`) cobre apenas métricas HTTP e Redis. Não há visualização dedicada para
observabilidade do LLM — latência por tipo de agente, taxa de erros, circuit breaker status,
detecções de injection.

**Estado atual:** Métricas LLM em Prometheus sem visualização Grafana
**Estado desejado:** Dashboard `llm-observability.json` com painéis para todas as métricas LLM

### Critérios de Resolução

- [ ] Criar `infra/grafana/dashboards/llm-observability.json`
- [ ] Painéis: latência p50/p95/p99 por call_type; error rate; circuit breaker state; injection detections
- [ ] Dashboard provisionado automaticamente no `docker-compose.yml`

**Esforço:** ~4h
**Prioridade:** P3 — Backlog

---

## DEBT-2026-012

**Título:** Chaos experiments planejados mas não executados em staging
**Tipo:** Reliability
**Severidade:** Low
**Serviço afetado:** Sistema (transversal)
**Registrado por:** Valdomiro Souza em 2026-05-16
**Descoberto via:** Análise de gaps — skill sre-foundations; docs/runbooks/chaos-experiments.md

### Descrição

Quatro experimentos de chaos engineering foram documentados em `docs/runbooks/chaos-experiments.md`
(CHAOS-001 a CHAOS-004), cobrindo: Redis unavailability, Anthropic API unavailability (circuit breaker),
Qdrant unavailability e memory pressure no Redis. Nenhum foi executado ainda — o sistema não foi
formalmente validado quanto à sua resiliência em cenários de falha reais.

**Estado atual:** Experimentos documentados, tabela de execuções vazia
**Estado desejado:** Todos os 4 experimentos executados e resultados registrados

### Critérios de Resolução

- [ ] CHAOS-001 executado em staging: Redis unavailability → graceful degradation
- [ ] CHAOS-002 executado em staging: Anthropic circuit breaker + fallback validado
- [ ] CHAOS-003 executado em staging: Qdrant unavailability → análise sem KB
- [ ] CHAOS-004 executado em staging: Redis memory pressure → alerta + lru eviction
- [ ] Tabela de execuções em `chaos-experiments.md` preenchida
- [ ] Postmortems abertos para resultados inesperados

**Esforço:** ~6h (execução + documentação de resultados)
**Prioridade:** P2 — Obrigatório antes de PRR (Production Readiness Review)

---

## DEBT-2026-013

**Título:** ADR lifecycle não exercitado — superseded/proposed/deprecated vazios
**Tipo:** Compliance
**Severidade:** Low
**Serviço afetado:** Transversal (docs/adr/)
**Registrado por:** Valdomiro Souza em 2026-05-16
**Descoberto via:** Análise de gaps — skill managing-adrs

### Descrição

Os 13 ADRs estão todos em `/docs/adr/active/`. Os diretórios `/superseded/`, `/proposed/`
e `/deprecated/` existem mas estão vazios. O processo de lifecycle (Draft → Proposed → Accepted
→ Superseded) definido na skill `managing-adrs` nunca foi exercitado neste projeto.

Isso não representa problema imediato — as decisões estão corretas e documentadas. Mas quando
uma decisão for revisada (ex: migrar de Docker Compose para K8s, ou trocar Claude por outro
modelo), o processo de superseder o ADR antigo não tem precedente estabelecido no projeto.

**Estado atual:** Lifecycle documentado na skill mas nunca exercitado
**Estado desejado:** Ao menos uma revisão de ADR completa demonstrando o processo

### Critérios de Resolução

- [ ] Identificar um ADR candidato à revisão ou marcação como deprecated (ex: ADR-0012 se K8s for adotado)
- [ ] Executar o processo completo: criar novo ADR em `/proposed/` → revisão → aceite → mover antigo para `/superseded/`
- [ ] README de ADRs (`docs/adr/README.md`) atualizado com entry em "Superseded ADRs"

**Esforço:** ~2h (processo + documentação)
**Prioridade:** P3 — Backlog (exercitar na próxima decisão arquitetural relevante)

---

## Métricas do Registro (atualizado 2026-05-16)

| Métrica                  | Valor | Target       |
| ------------------------ | ----- | ------------ |
| Total de debts abertos   | 11    | Decrescente  |
| Debts aceitos como risco | 2     | Documentados |
| Critical/High abertos    | 0     | = 0 ✅       |
| Medium abertos           | 4     | < 5          |
| Low abertos              | 7     | Backlog      |
| Compliance abertos       | 3     | < 5          |
| Idade média (dias)       | 2     | < 90         |

### Distribuição por tipo (2026-05-16)

| Tipo          | Abertos | Aceitos como risco |
| ------------- | ------- | ------------------ |
| Security      | 3       | 0                  |
| Reliability   | 2       | 1                  |
| Observability | 2       | 0                  |
| Compliance    | 3       | 0                  |
| Code          | 0       | 0                  |
| Operational   | 0       | 0                  |
| **Total**     | **11**  | **1** (DEBT-003, DEBT-006) |

### Próximas ações (Q3-2026)

| Prioridade | Debt | Ação | Owner |
| ---------- | ---- | ---- | ----- |
| P2 | DEBT-2026-001 | Migrar KB corpus para EN ou adotar modelo multilíngue | Valdomiro Souza |
| P2 | DEBT-2026-005 | Adicionar `PROMETHEUS_API_KEY` no `.env.example` | Valdomiro Souza |
| P2 | DEBT-2026-008 | Investigar hashes para `torch` no KB runtime | Valdomiro Souza |
| P2 | DEBT-2026-009 | DPA formal com Anthropic (pré-produção real) | Valdomiro Souza |
| P2 | DEBT-2026-012 | Executar 4 chaos experiments em staging | Valdomiro Souza |
