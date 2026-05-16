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
    # Lowered to 0.30: post-mortems are in PT-BR while orchestrator queries are in EN;
    # all-MiniLM-L6-v2 cross-lingual cosine similarity peaks at ~0.38 for this pair.
    min_similarity_score: float = 0.30

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.app_env in ("production", "staging"):
            if not self.api_key:
                raise ValueError("API_KEY obrigatório em produção e staging (A01/A05)")
        if self.app_env == "production":
            if self.enable_docs:
                raise ValueError("enable_docs deve ser False em produção")
        return self


settings = Settings()
