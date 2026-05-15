from prometheus_client import Counter, Gauge, Histogram

HAPROXY_LOGS_INGESTED = Counter(
    "haproxy_logs_ingested_total",
    "Total de logs HAProxy ingeridos",
    ["backend", "status_class"],
)

REDIS_MEMORY_USAGE = Gauge(
    "redis_memory_usage_bytes",
    "Uso de memória Redis em bytes",
)

ERROR_BUDGET_REMAINING = Gauge(
    "error_budget_remaining_pct",
    "Error budget restante por SLO (0–100%)",
    ["slo"],
)
