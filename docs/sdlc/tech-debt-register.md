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

## Métricas do Registro (atualizado 2026-05-16)

| Métrica                  | Valor | Target       |
| ------------------------ | ----- | ------------ |
| Total de debts abertos   | 6     | Decrescente  |
| Debts aceitos como risco | 2     | Documentados |
| Critical/High abertos    | 0     | = 0 ✅       |
| Medium abertos           | 3     | < 5          |
| Low abertos              | 3     | Backlog      |
| Idade média (dias)       | 2     | < 90         |
