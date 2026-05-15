from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    api_key: str = ""
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "postmortems"
    embedding_model: str = "all-MiniLM-L6-v2"
    otlp_endpoint: str = ""
    enable_docs: bool = True
    service_name: str = "knowledge-base"

    # Score mínimo para evitar chunks irrelevantes (SDD §7.3.4 / LLM08:2025)
    min_similarity_score: float = 0.70

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.app_env == "production":
            if not self.api_key:
                raise ValueError("API_KEY obrigatório em produção")
            if self.enable_docs:
                raise ValueError("enable_docs deve ser False em produção")
        return self


settings = Settings()
