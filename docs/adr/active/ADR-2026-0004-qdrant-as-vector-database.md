# ADR-2026-0004: Qdrant como Banco de Dados Vetorial para Knowledge Base

---

## Metadata

| Field            | Value                                                                    |
| ---------------- | ------------------------------------------------------------------------ |
| **ID**           | ADR-2026-0004                                                            |
| **Status**       | Accepted                                                                 |
| **Area**         | Data                                                                     |
| **Author**       | Valdomiro Souza                                                          |
| **Reviewers**    | Orientador PPGCA/Unisinos                                                |
| **Created**      | 2026-05-14                                                               |
| **Approved**     | 2026-05-14                                                               |
| **Related spec** | SDD v1.7.0 §3.3 (Knowledge Base), §7.3.4 (LLM08:2025)                    |
| **AI-assisted**  | Yes — Claude Sonnet 4.6, trade-off analysis, reviewed by Valdomiro Souza |

---

## 1. Context and Problem

O sistema precisa de uma base de conhecimento de post-mortems históricos para o ciclo PRAL (fase Reasoning — recuperação de contexto similar). Os requisitos são:

- **Busca semântica por similaridade** (cosine similarity): dado um query de findings atuais, recuperar incidentes históricos semanticamente similares
- **Vetores de 384 dimensões** (saída do `all-MiniLM-L6-v2`)
- **Threshold de relevância configurável** para evitar recuperação de chunks irrelevantes (LLM08:2025 — RAG Poisoning)
- **Metadata por chunk**: `incident_id`, `source_file`, `chunk_index`
- **Corpus atual**: ~34 chunks (INC-001: 8, INC-002: 10, INC-003: 16)
- **Docker-native**: serviço deve ser inicializável via `docker-compose`

**Driving forces:**

- Busca por similaridade semântica é inviável com banco relacional tradicional
- Qdrant é open-source, auto-hospedado, com imagem Docker oficial — zero custo e sem dependência de cloud
- API REST nativa facilita integração com `qdrant-client` Python sem ORM adicional
- Healthcheck TCP nativo (sem curl/wget na imagem v1.18.0 — resolvido com `bash /dev/tcp`)

**Constraints:**

- Auto-hospedado (sem serviço gerenciado cloud — Pinecone, Weaviate Cloud)
- Corpus pequeno no escopo da dissertação (~100–500 chunks planejados)
- `sentence-transformers` e `torch` (~800 MB) já são dependências obrigatórias para embedding

---

## 2. Decision

Adotamos **Qdrant v1.18.0** como banco de dados vetorial, hospedado via Docker na porta `:6333`, com coleção `postmortems` usando distância cosine e vetores de 384 dimensões. O `score_threshold` configurável (`min_similarity_score`) protege contra chunks irrelevantes.

**Scope:**

- Applies to: Knowledge-Base service (:8002) e Incident-Response-Agent (via `kb_client.py`)
- Does not apply to: métricas operacionais (→ Redis, ADR-2026-0003)

---

## 3. Alternatives Considered

| Alternative                 | Pros                                                                                                | Cons                                                                                                          | Reason for Rejection                                  |
| --------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| **Qdrant v1.18.0**          | Open-source, Docker nativo, API REST, cosine similarity, filtros por metadata, sem cloud dependency | Sem curl na imagem (healthcheck via bash/tcp); configuração de auth com string vazia habilita auth por engano | — Escolhido                                           |
| Pinecone                    | Managed, fácil setup                                                                                | Custo, dependência de cloud, dados saem do ambiente local                                                     | Violação de controle de dados para dissertação        |
| ChromaDB                    | Embedded (sem servidor), simples                                                                    | Sem API REST nativa; difícil escalar para servico separado; menos recursos de filtro                          | Arquitetura de microsserviço requer servidor separado |
| pgvector (PostgreSQL)       | SQL familiar, ACID, uma dependência a menos                                                         | Requer PostgreSQL adicional; performance de ANN inferior ao Qdrant para corpus grande                         | Dependência extra sem ganho real para corpus pequeno  |
| FAISS (in-memory)           | Ultra-rápido, sem servidor                                                                          | Sem persistência, sem API REST, sem metadata                                                                  | Sem persistência após restart                         |
| "Do nothing" (busca linear) | Zero dependências                                                                                   | O(N) por query — inviável para corpus > 1000 chunks                                                           | Performance inaceitável                               |

---

## 4. Consequences

### Positive

- Busca semântica em ~34 chunks em < 10 ms (benchmark local)
- `score_threshold=0.30` filtra chunks com similaridade < 30% (proteção LLM08:2025)
- Metadata por chunk permite rastrear qual post-mortem originou cada resultado
- Mock de `qdrant-client` em testes unitários via `sys.modules` stub (sem Docker no CI unitário)

### Negative / Trade-offs

- Healthcheck não trivial: imagem v1.18.0 sem `curl`/`wget` — resolvido com `bash -c 'exec 3<>/dev/tcp/localhost/6333'`
- `QDRANT__SERVICE__API_KEY=""` habilita autenticação com chave vazia (bug de configuração descoberto em produção) — variável removida do `docker-compose.yml`
- `min_similarity_score` baixado de 0.70 para 0.30: post-mortems em PT-BR vs queries em EN geram cosine similarity máximo ~0.38 com `all-MiniLM-L6-v2` (ver ADR-2026-0008)
- Corpus pequeno atual (34 chunks) não exercita HNSW index — benefício de ANN realizado com >1000 chunks

### Risks

| Risk                                                    | Probability | Impact | Mitigation                                                                      |
| ------------------------------------------------------- | ----------- | ------ | ------------------------------------------------------------------------------- |
| Qdrant indisponível durante análise                     | Baixo       | Médio  | `kb_client.py` retorna `[]` em qualquer exception — análise continua sem KB     |
| Score threshold muito baixo retorna chunks irrelevantes | Médio       | Médio  | Monitorar qualidade de retrieval em INC-003+ ; rever threshold com corpus maior |
| Qdrant v1.18.0 CVE                                      | Baixo       | Alto   | grype SBOM scan em CI bloqueia em CRITICAL                                      |

### Tech Debt Introduced

- `min_similarity_score=0.30` é subótimo para segurança (LLM08:2025 recomenda ≥0.70) — debt até que post-mortems sejam reescritos em inglês ou modelo multilíngue seja adotado

---

## 5. Future Review Criteria

Esta ADR deve ser revisitada se:

- [ ] Corpus de post-mortems ultrapassar 1.000 chunks (benefício de HNSW index se realiza plenamente)
- [ ] Post-mortems migrados para inglês — rever `min_similarity_score` de volta para 0.70
- [ ] Modelo multilíngue (ex: `paraphrase-multilingual-MiniLM-L12-v2`) adotado (ver ADR-2026-0008)
- [ ] Qdrant v1.18.0 atingir EOL
- [ ] Após 2 anos sem revisão (2028-05-14)

---

## 6. References

- SDD v1.7.0 §3.3 — Knowledge Base Service
- SDD v1.7.0 §7.3.4 — LLM08:2025 (RAG Poisoning)
- `Knowledge-Base/app/config.py` — `min_similarity_score=0.30`
- `Knowledge-Base/app/services/qdrant_service.py` — operações de upsert e search
- `docker-compose.yml` — configuração Qdrant (porta 6333, healthcheck TCP)

---

## 7. AI Assistance

| Field                      | Value                                                            |
| -------------------------- | ---------------------------------------------------------------- |
| **AI used**                | Claude Sonnet 4.6                                                |
| **AI role**                | Comparação de bancos vetoriais, análise de trade-offs de hosting |
| **Output reviewed by**     | Valdomiro Souza                                                  |
| **Final decision made by** | Valdomiro Souza                                                  |

---

## 8. Approval

| Role       | Name            | Date       | Decision   |
| ---------- | --------------- | ---------- | ---------- |
| Author     | Valdomiro Souza | 2026-05-14 | Proposes   |
| Tech Lead  | Valdomiro Souza | 2026-05-14 | ✅ Approve |
| Orientador | PPGCA/Unisinos  | 2026-05-14 | ✅ Approve |
