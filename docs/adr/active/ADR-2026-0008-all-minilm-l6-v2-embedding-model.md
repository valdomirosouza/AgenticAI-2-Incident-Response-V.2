# ADR-2026-0008: all-MiniLM-L6-v2 como Modelo de Embeddings

---

## Metadata

| Field            | Value                                                                    |
| ---------------- | ------------------------------------------------------------------------ |
| **ID**           | ADR-2026-0008                                                            |
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

O Knowledge-Base precisa converter textos de post-mortems em vetores para busca semântica no Qdrant. Os requisitos são:

- **Dimensionalidade compatível com Qdrant collection**: vetores de N dimensões configurados em `VectorParams(size=N)`
- **Execução local/offline**: sem chamadas a APIs externas para embedding (privacidade, custo zero, sem latência de rede)
- **Tamanho de modelo razoável**: deve caber no container Docker Knowledge-Base sem exceder limites de CI
- **Qualidade semântica suficiente**: recuperar post-mortems relevantes dado query de findings em inglês

**Contexto adicional crítico:**

- Post-mortems foram escritos em **PT-BR** mas queries de busca chegam em **EN** (findings dos agentes)
- Isso criou um gap de similaridade: cosine similarity máximo observado entre chunks PT-BR e queries EN foi **~0.38** com modelo monolíngue
- `min_similarity_score` precisou ser reduzido de **0.70 → 0.30** para recuperar qualquer resultado relevante (ver ADR-2026-0004)

**Driving forces:**

- `sentence-transformers` é a biblioteca padrão de facto para embeddings locais em Python
- `all-MiniLM-L6-v2` é o modelo de referência para prototipagem rápida: 22M parâmetros, 384 dimensões, ~80 MB
- Sem chamadas a OpenAI Embeddings API — zero custo incremental, privacidade de dados
- `torch` já é dependência obrigatória de `sentence-transformers` — sem custo extra de dependência

**Constraints:**

- Imagem Docker Knowledge-Base: `sentence-transformers` + `torch` somam ~800 MB — pesado mas aceitável para runtime
- CI unitário usa `requirements-test.txt` (sem `sentence-transformers`/`torch`) + `sys.modules` stub — evita os 800 MB no CI
- Modelo deve ser carregado uma vez no startup do serviço (não por request)

---

## 2. Decision

Adotamos **`all-MiniLM-L6-v2`** (via `sentence-transformers==2.7.0`) como modelo de embeddings para o Knowledge-Base, gerando vetores de **384 dimensões** usados na coleção `postmortems` do Qdrant.

**Scope:**

- Applies to: Knowledge-Base (:8002) — `services/embedding_service.py`, `seed_kb.py`
- Does not apply to: análise LLM do IRA (→ Claude Sonnet 4.6, ADR-2026-0005)

---

## 3. Alternatives Considered

| Alternative                             | Pros                                                             | Cons                                                                                                                | Reason for Rejection                                                              |
| --------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| **all-MiniLM-L6-v2 (escolhido)**        | 22M params, 384 dims, ~80 MB, padrão de referência, rápido (CPU) | Monolíngue EN; cosine max ~0.38 para PT-BR vs EN queries; `min_similarity_score` precisa ser reduzido               | — Escolhido; limitação conhecida, documentada e mitigada                          |
| `paraphrase-multilingual-MiniLM-L12-v2` | Suporte nativo PT-BR + EN; cosine similarity esperado ~0.60-0.70 | 118M params (~400 MB vs 80 MB); mais lento no CPU; requer reindexação completa do corpus                            | Migrável quando post-mortems forem reescritos em EN ou corpus crescer (tech debt) |
| `text-embedding-3-small` (OpenAI API)   | Alta qualidade, 1536 dims, multilíngue, sem instalação local     | Custo por token ($0.02/1M tokens); dependência de cloud; dados saem do ambiente local; latência de rede             | Violação de privacidade e custo para corpus de dissertação                        |
| `all-mpnet-base-v2`                     | Maior qualidade que MiniLM (SBERT benchmark)                     | 110M params, 768 dims; mais lento; container maior; sem ganho multilíngue                                           | Custo de tamanho sem benefício multilíngue; MiniLM suficiente para ~34 chunks     |
| `nomic-embed-text` (Ollama)             | Multilíngue, local, alta qualidade                               | Requer Ollama server como dependência adicional; complexidade de setup; não integra com sentence-transformers nativ | Dependência extra sem ganho claro sobre alternativas existentes                   |
| "Do nothing" (bag-of-words / TF-IDF)    | Zero dependências ML                                             | Sem semântica; não captura sinônimos ou contexto; inviável para busca de incidentes similares                       | Qualidade de retrieval inaceitável                                                |

---

## 4. Consequences

### Positive

- Embedding gerado em < 50 ms por chunk no CPU (startup do serviço carrega modelo uma vez)
- `SentenceTransformer("all-MiniLM-L6-v2")` com `encode(texts, batch_size=32)` — eficiente para corpus atual (~34 chunks)
- `sys.modules` stub no CI permite testar `embedding_service.py` sem carregar 800 MB de torch
- Dimensionalidade 384 é compatível com Qdrant `VectorParams(size=384, distance=Distance.COSINE)`

### Negative / Trade-offs

- **Gap multilíngue crítico**: PT-BR post-mortems vs EN queries → `min_similarity_score=0.30` (subótimo para LLM08:2025 que recomenda ≥0.70)
- ~800 MB de dependências (`sentence-transformers` + `torch`) aumentam o build time e tamanho do container KB
- Modelo não atualiza automaticamente — se HuggingFace deprecar `all-MiniLM-L6-v2`, requer migração manual

### Risks

| Risk                                                    | Probability | Impact | Mitigation                                                                             |
| ------------------------------------------------------- | ----------- | ------ | -------------------------------------------------------------------------------------- |
| `min_similarity_score=0.30` retorna chunks irrelevantes | Médio       | Médio  | Monitorar qualidade de retrieval; migrar para modelo multilíngue quando corpus crescer |
| Divergência entre `sys.modules` stub e API real         | Baixo       | Médio  | E2E tests com KB real via `tests/test_e2e_qdrant.py` (Docker required)                 |
| `all-MiniLM-L6-v2` descontinuado no HuggingFace Hub     | Muito baixo | Médio  | Modelo open-source amplamente usado; fallback: especificar `revision` hash no código   |

### Tech Debt Introduced

- `min_similarity_score=0.30` é tech debt explícito (documentado em ADR-2026-0004): subótimo para LLM08:2025. Mitigado quando:
  - Post-mortems migrados para inglês → rever threshold para 0.70
  - Modelo multilíngue (`paraphrase-multilingual-MiniLM-L12-v2`) adotado

---

## 5. Future Review Criteria

Esta ADR deve ser revisitada se:

- [ ] Post-mortems forem reescritos em inglês — rever modelo e `min_similarity_score` (voltar para 0.70)
- [ ] Corpus ultrapassar 500 chunks — avaliar se `all-MiniLM-L6-v2` mantém qualidade de retrieval
- [ ] Modelo multilíngue for adotado (migração: reindex completo do Qdrant collection)
- [ ] `sentence-transformers` lançar breaking change em `SentenceTransformer.encode()` API
- [ ] Após 2 anos sem revisão (2028-05-14)

---

## 6. References

- SDD v1.7.0 §3.3 — Knowledge Base Service
- SDD v1.7.0 §7.3.4 — LLM08:2025 (RAG Poisoning) — `min_similarity_score` threshold
- `Knowledge-Base/app/services/embedding_service.py` — `SentenceTransformer("all-MiniLM-L6-v2")`
- `Knowledge-Base/app/config.py` — `min_similarity_score: float = 0.30`
- ADR-2026-0004 — Qdrant como banco vetorial (`VectorParams(size=384)`)

---

## 7. AI Assistance

| Field                      | Value                                                                      |
| -------------------------- | -------------------------------------------------------------------------- |
| **AI used**                | Claude Sonnet 4.6                                                          |
| **AI role**                | Comparação de modelos de embedding, análise do gap multilíngue PT-BR vs EN |
| **Output reviewed by**     | Valdomiro Souza                                                            |
| **Final decision made by** | Valdomiro Souza                                                            |

---

## 8. Approval

| Role       | Name            | Date       | Decision   |
| ---------- | --------------- | ---------- | ---------- |
| Author     | Valdomiro Souza | 2026-05-14 | Proposes   |
| Tech Lead  | Valdomiro Souza | 2026-05-14 | ✅ Approve |
| Orientador | PPGCA/Unisinos  | 2026-05-14 | ✅ Approve |
