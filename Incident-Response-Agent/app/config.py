from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    anthropic_api_key: str = ""
    api_key: str = ""        # API_KEY — suporta múltiplas chaves separadas por vírgula
    admin_key: str = ""      # ADMIN_KEY — acesso exclusivo aos endpoints /admin/*
    metrics_api_url: str = "http://localhost:8000"
    kb_api_url: str = "http://localhost:8002"
    kb_api_key: str = ""
    otlp_endpoint: str = ""
    enable_docs: bool = True
    service_name: str = "incident-response-agent"

    # Thresholds para fallback de análise por regras (SDD §9.4.3)
    latency_p99_threshold_ms: float = 1000.0
    error_rate_5xx_threshold_pct: float = 1.0

    # Circuit breaker para Anthropic API (S4-04 / SDD §9.4.2)
    cb_failure_threshold: int = 3    # falhas consecutivas para abrir o circuito
    cb_recovery_timeout_s: float = 60.0  # segundos até tentar recuperação
    cb_max_retries: int = 3          # tentativas por chamada antes de penalizar

    # Modelo Claude
    model: str = "claude-sonnet-4-6"

    # Prometheus scrape endpoint auth (A05 — obrigatório em staging/production)
    prometheus_api_key: str = ""

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.app_env in ("production", "staging"):
            if not self.api_key:
                raise ValueError("API_KEY obrigatório em produção e staging (A01/A05)")
        if self.app_env == "production":
            if not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY obrigatório em produção")
            if self.enable_docs:
                raise ValueError("enable_docs deve ser False em produção")
        return self


settings = Settings()
