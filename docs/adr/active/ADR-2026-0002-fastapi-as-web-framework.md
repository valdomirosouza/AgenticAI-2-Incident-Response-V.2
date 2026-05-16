# ADR-2026-0002: FastAPI como Framework Web para Todos os Serviços

---

## Metadata

| Field            | Value                                                                    |
| ---------------- | ------------------------------------------------------------------------ |
| **ID**           | ADR-2026-0002                                                            |
| **Status**       | Accepted                                                                 |
| **Area**         | Architecture                                                             |
| **Author**       | Valdomiro Souza                                                          |
| **Reviewers**    | Orientador PPGCA/Unisinos                                                |
| **Created**      | 2026-05-14                                                               |
| **Approved**     | 2026-05-14                                                               |
| **Related spec** | SDD v1.7.0 §3.1, §9.6                                                    |
| **AI-assisted**  | Yes — Claude Sonnet 4.6, trade-off analysis, reviewed by Valdomiro Souza |

---

## 1. Context and Problem

O sistema requer 3 serviços HTTP com as seguintes necessidades:

- Endpoints assíncronos (ingestão de logs de alta frequência, chamadas LLM latentes)
- Validação automática de request/response via schemas tipados (segurança + SDD §7.3.2)
- Geração automática de documentação OpenAPI (obrigatória em desenvolvimento, desabilitada em produção via `enable_docs`)
- Integração nativa com OpenTelemetry para observabilidade
- Equipe com expertise consolidada em Python 3.12

**Driving forces:**

- async/await nativo para não bloquear I/O durante chamadas a Redis, Qdrant e Anthropic API
- Pydantic v2 integrado nativamente — validação de input e output sem boilerplate
- OpenAPI automático facilita DAST com Schemathesis fuzzing
- Ecossistema Python 3.12 como único constraint de linguagem

**Constraints:**

- Python 3.12 obrigatório
- Framework deve suportar Pydantic v2 e `asyncio_mode = "auto"` (pytest-asyncio)
- Sem dependência de ORM (sem banco relacional — apenas Redis e Qdrant)

---

## 2. Decision

Adotamos **FastAPI 0.111.0** como framework web para os 3 serviços, com `uvicorn[standard]` como ASGI server.

**Scope:**

- Applies to: Log-Ingestion-and-Metrics (:8000), Incident-Response-Agent (:8001), Knowledge-Base (:8002)
- Does not apply to: scripts utilitários (`seed_kb.py`, `check_slos.py`) — usam `httpx` diretamente

---

## 3. Alternatives Considered

| Alternative                         | Pros                                                                                 | Cons                                                                                    | Reason for Rejection                                                 |
| ----------------------------------- | ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **FastAPI 0.111.0**                 | Pydantic v2 nativo, async, OpenAPI automático, OpenTelemetry instrumentor disponível | Versão específica pode ter bugs; overhead de startup vs Flask                           | — Escolhido                                                          |
| Flask + Marshmallow                 | Maturidade, ecossistema amplo                                                        | Sem async nativo, validação manual, sem OpenAPI automático                              | Async obrigatório para I/O não bloqueante                            |
| Django REST Framework               | Admin, ORM, batteries-included                                                       | Overhead desnecessário sem banco relacional; complexidade excessiva para microsserviços | Sem banco relacional no projeto                                      |
| Starlette puro                      | Performance máxima, zero overhead                                                    | Sem Pydantic integrado, sem OpenAPI automático, mais código boilerplate                 | FastAPI é Starlette + Pydantic; usar diretamente perde produtividade |
| "Do nothing" (scripts HTTP simples) | Zero dependências                                                                    | Sem validação, sem docs, sem middleware pipeline                                        | Inaceitável para sistema de produção                                 |

---

## 4. Consequences

### Positive

- `@router.get("/metrics", response_model=MetricsOverview)` valida automaticamente output — implementa LLM05 (output validation) sem código extra
- `docs_url=None` em produção (controlado por `enable_docs` via `@model_validator`) — superfície de ataque reduzida
- Schemathesis fuzzing via `GET /openapi.json` sem configuração adicional (DAST pipeline)
- `pytest` + `httpx.AsyncClient(transport=ASGITransport(app=app))` — testes de integração sem servidor real

### Negative / Trade-offs

- Startup time ligeiramente maior que Flask (~200 ms vs ~50 ms) — aceitável para serviços long-running
- Versão pinada `0.111.0` requer atualização manual para novos releases (pip-audit monitorado em CI)

### Risks

| Risk                               | Probability | Impact | Mitigation                                       |
| ---------------------------------- | ----------- | ------ | ------------------------------------------------ |
| CVE em FastAPI 0.111.0             | Baixo       | Alto   | pip-audit em CI bloqueia em CRITICAL; grype SBOM |
| Breaking change em Pydantic v2 API | Baixo       | Médio  | Testes automatizados (≥85% coverage) detectam    |

### Tech Debt Introduced

- Nenhum

---

## 5. Future Review Criteria

Esta ADR deve ser revisitada se:

- [ ] FastAPI 0.111.0 atingir EOL ou CVE CRITICAL não remediado
- [ ] Pydantic v3 lançado com breaking changes em `BaseModel`
- [ ] Requisito de suporte a protocolo diferente de HTTP/HTTPS (ex: gRPC) emergir
- [ ] Após 2 anos sem revisão (2028-05-14)

---

## 6. References

- FastAPI docs: https://fastapi.tiangolo.com
- SDD v1.7.0 §9.6 — Stack tecnológico
- `Incident-Response-Agent/requirements.txt` — `fastapi==0.111.0`, `uvicorn[standard]==0.29.0`
- `.github/workflows/ci.yml` — pipeline de testes dos 3 serviços

---

## 7. AI Assistance

| Field                      | Value                                           |
| -------------------------- | ----------------------------------------------- |
| **AI used**                | Claude Sonnet 4.6                               |
| **AI role**                | Comparação de frameworks, análise de trade-offs |
| **Output reviewed by**     | Valdomiro Souza                                 |
| **Final decision made by** | Valdomiro Souza                                 |

---

## 8. Approval

| Role       | Name            | Date       | Decision   |
| ---------- | --------------- | ---------- | ---------- |
| Author     | Valdomiro Souza | 2026-05-14 | Proposes   |
| Tech Lead  | Valdomiro Souza | 2026-05-14 | ✅ Approve |
| Orientador | PPGCA/Unisinos  | 2026-05-14 | ✅ Approve |
