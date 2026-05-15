from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class HaproxyLog(BaseModel):
    """Log de uma requisição processada pelo HAProxy."""

    frontend: str = Field(min_length=1, max_length=100)
    backend: str = Field(min_length=1, max_length=100)
    status_code: int = Field(ge=100, le=599)
    time_response: float = Field(ge=0, description="Tempo de resposta em ms")
    bytes_read: int = Field(ge=0)
    request_method: str = Field(default="GET", max_length=10)
    request_path: str = Field(default="/", max_length=2000)


class MetricsOverview(BaseModel):
    requests_total: int
    errors_4xx: int
    errors_5xx: int
    error_rate_4xx_pct: float
    error_rate_5xx_pct: float


class ResponseTimesData(BaseModel):
    p50_ms: float
    p95_ms: float
    p99_ms: float
    sample_count: int


class SaturationData(BaseModel):
    response_time_samples: int
    redis: dict


class RpsData(BaseModel):
    """RPS por minuto na janela de 60 minutos."""

    buckets: dict[str, int]
    current_rps: float


class BackendsData(BaseModel):
    backends: dict[str, int]


# ── SLO models (S4-01) ────────────────────────────────────────────────────────

class SloHealth(str, Enum):
    healthy = "healthy"      # compliant, budget > 50% remaining
    at_risk = "at_risk"      # compliant, but > 50% of budget consumed
    breaching = "breaching"  # currently violating SLO target


class SloStatus(BaseModel):
    """Status de um único SLO com error budget."""

    name: str
    slo_id: str
    target_pct: float        # e.g., 99.5 (99.5% compliance target)
    threshold: float         # limite absoluto (ms ou %)
    unit: str                # "ms" ou "5xx_rate_pct"
    current_value: float     # valor atual medido
    compliant: bool          # está dentro do threshold?
    error_budget_pct: float  # budget total disponível (100 - target_pct ou threshold)
    budget_consumed_pct: float   # quanto do budget foi consumido
    budget_remaining_pct: float  # budget restante
    budget_burned_pct: float     # % do budget consumido (0-100)
    health: SloHealth


class SloStatusReport(BaseModel):
    """Relatório de todos os SLOs com error budget — resposta de GET /metrics/slo-status."""

    timestamp: datetime
    window: str              # "session" — desde o início do serviço
    requests_total: int
    sample_count: int        # amostras de latência disponíveis
    slos: list[SloStatus]
    overall_health: SloHealth  # pior estado entre todos os SLOs
