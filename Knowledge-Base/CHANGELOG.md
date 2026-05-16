# Changelog — Knowledge-Base

## [1.3.0] — 2026-05-16
### Added
- `README.md` — documentação completa do serviço

## [1.1.0] — 2026-04 (estimado)
### Added
- `detect_blameful_language()` — detecção de linguagem de culpa em chunks (cultura blameless)
- `validate_chunk_size()` — rejeita chunks acima do limite para proteger qualidade do embedding

## [1.0.0] — 2026-01 (estimado)
### Added
- `POST /kb/ingest` — ingestão de chunks com embedding all-MiniLM-L6-v2 (ADR-2026-0008)
- `POST /kb/search` — busca semântica coseno com score_threshold=0.70 (LLM08:2025)
- Qdrant AsyncQdrantClient (ADR-2026-0004)
- Criação automática de coleção no startup (`ensure_collection()`)
- API Key auth em `/kb/ingest`
- `requirements-test.txt` — CI sem sentence-transformers/torch (~800 MB)
- sys.modules stub para testes unitários (conftest.py)
- Docker container non-root (appuser)
