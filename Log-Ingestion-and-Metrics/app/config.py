from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    redis_url: str = "redis://localhost:6379"
    redis_password: str = ""
    otlp_endpoint: str = ""
    enable_docs: bool = True
    service_name: str = "log-ingestion"

    # Janela de RPS em minutos (60 min de histórico)
    rps_window_minutes: int = 60

    # Chave para proteger /prometheus/metrics de acesso não autorizado (SDD §5 / A05)
    # Vazio em development = sem autenticação. Obrigatório em staging/production.
    prometheus_api_key: str = ""

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.app_env in ("production", "staging"):
            if not self.prometheus_api_key:
                raise ValueError("PROMETHEUS_API_KEY obrigatório em produção e staging (A05)")
        if self.app_env == "production" and self.enable_docs:
            raise ValueError("enable_docs deve ser False em produção")
        return self


settings = Settings()
