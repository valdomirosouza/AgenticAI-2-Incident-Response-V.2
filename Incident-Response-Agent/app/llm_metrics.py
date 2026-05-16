"""
Registro de métricas Prometheus para observabilidade do LLM (AI Governance — skills/ai-governance).

Métricas expostas em /prometheus/metrics (scrapeadas pelo Prometheus — infra/prometheus/prometheus.yml).
"""
from prometheus_client import Counter, Histogram

LLM_CALL_DURATION = Histogram(
    "llm_call_duration_seconds",
    "Duração de chamadas ao Claude por tipo de agente",
    ["call_type"],  # specialist | synthesis
    buckets=[1, 2, 5, 10, 15, 20, 30, 60],
)

LLM_CALLS_TOTAL = Counter(
    "llm_calls_total",
    "Total de chamadas ao Claude por tipo e resultado",
    ["call_type", "outcome"],  # outcome: success | error | circuit_open | validation_error
)

LLM_OUTPUT_VALIDATION_FAILURES = Counter(
    "llm_output_validation_failures_total",
    "Falhas de validação Pydantic no output do Claude (LLM05:2025)",
)

PROMPT_INJECTION_SANITIZED = Counter(
    "prompt_injection_sanitized_total",
    "Ocorrências de sanitização antes de envio ao Claude (LLM01+LLM02:2025)",
    ["sanitization_type"],  # tag_removal | ip_redaction | host_redaction
)
