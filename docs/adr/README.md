# Architecture Decision Records — AgenticAI-2-Incident-Response

Registro das decisões arquiteturais do projeto Agentic AI Copilot para Redução de MTTD/MTTR.
Dissertação de Mestrado PPGCA / Unisinos — Autor: Valdomiro Souza.

## Estrutura

```
docs/adr/
├── active/       ADRs vigentes
├── proposed/     ADRs em revisão
├── superseded/   ADRs substituídas por versões posteriores
└── deprecated/   ADRs obsoletas sem substituto direto
```

## Índice

| ID                                                                            | Título                                                     | Área         | Status   | Data       |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------- | ------------ | -------- | ---------- |
| [ADR-2026-0001](active/ADR-2026-0001-microservices-three-fastapi-services.md) | Arquitetura de 3 microsserviços FastAPI independentes      | Architecture | Accepted | 2026-05-14 |
| [ADR-2026-0002](active/ADR-2026-0002-fastapi-as-web-framework.md)             | FastAPI como framework web para todos os serviços          | Architecture | Accepted | 2026-05-14 |
| [ADR-2026-0003](active/ADR-2026-0003-redis-as-golden-signals-store.md)        | Redis 7 como armazenamento de Golden Signals               | Data         | Accepted | 2026-05-14 |
| [ADR-2026-0004](active/ADR-2026-0004-qdrant-as-vector-database.md)            | Qdrant como banco de dados vetorial para Knowledge Base    | Data         | Accepted | 2026-05-14 |
| [ADR-2026-0005](active/ADR-2026-0005-claude-as-llm-engine.md)                 | Anthropic Claude (claude-sonnet-4-6) como motor LLM        | Architecture | Accepted | 2026-05-14 |
| [ADR-2026-0006](active/ADR-2026-0006-human-on-the-loop-pattern.md)            | Human-on-the-Loop (HOTL) — sem remediação autônoma         | Architecture | Accepted | 2026-05-14 |
| [ADR-2026-0007](active/ADR-2026-0007-tool-use-parallel-specialist-agents.md)  | Tool-use loop com 4 agentes especialistas em paralelo      | Architecture | Accepted | 2026-05-14 |
| [ADR-2026-0008](active/ADR-2026-0008-all-minilm-l6-v2-embedding-model.md)     | all-MiniLM-L6-v2 como modelo de embeddings                 | Data         | Accepted | 2026-05-14 |
| [ADR-2026-0009](active/ADR-2026-0009-api-key-auth-hmac-compare-digest.md)     | API Key com hmac.compare_digest para autenticação          | Security     | Accepted | 2026-05-14 |
| [ADR-2026-0010](active/ADR-2026-0010-circuit-breaker-fallback-anthropic.md)   | Circuit breaker com fallback rule-based para Anthropic API | Architecture | Accepted | 2026-05-15 |
| [ADR-2026-0011](active/ADR-2026-0011-pydantic-v2-llm-output-validation.md)    | Pydantic v2 para validação de output do LLM                | Security     | Accepted | 2026-05-15 |
| [ADR-2026-0012](active/ADR-2026-0012-docker-compose-orchestration.md)         | Docker Compose como orquestração (não Kubernetes)          | Infra        | Accepted | 2026-05-14 |

## Processo

1. Copie o template em `../../skills/managing-adrs/adr-template.md`
2. Preencha todas as seções marcadas com `*`
3. Abra PR com label `adr`
4. Aprovação mínima: Author + Tech Lead
5. Mova para `active/` após aprovação

## Revisão

Revisão trimestral agendada: Q3-2026 (2026-08-01).
