# Prompt Changelog

Histórico de versões dos prompts do Incident Response Agent.
Cada mudança de prompt segue o mesmo processo de PR e revisão que mudanças de código.

## v1.0.0 — 2026-01-01 (estimado)

**Prompts incluídos:**
- `v1/latency-specialist.txt` — Latency Specialist Agent (P50/P95/P99 thresholds)
- `v1/errors-specialist.txt` — Errors Specialist Agent (4xx/5xx thresholds)
- `v1/saturation-specialist.txt` — Saturation Specialist Agent (Redis memory thresholds)
- `v1/traffic-specialist.txt` — Traffic Specialist Agent (RPS patterns)
- `v1/orchestrator.txt` — SoS Orchestrator com raciocínio causal (root cause vs trigger)

**Thresholds v1.0.0:**
- Latência: P95 > 500ms → warning; P99 > 1000ms OR P95 > 2000ms → critical
- Erros: 5xx > 1% → warning; 5xx > 5% → critical; 4xx > 10% → warning
- Saturação: Redis > 80% maxmemory → warning; > 95% → critical

**Referências:** ADR-2026-0005 (LLM engine), SDD §4 (Ciclo PRAL), SDD §9.3.3 (prompt versioning)
