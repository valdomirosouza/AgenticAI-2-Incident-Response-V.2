from pydantic import BaseModel, Field, field_validator
from app.models.report import Severity


class OrchestratorResponse(BaseModel):
    """Valida o output JSON do Claude antes de construir o IncidentReport (SDD §7.3.2 / LLM05)."""

    overall_severity: Severity
    title: str = Field(min_length=1, max_length=200)
    diagnosis: str = Field(min_length=1, max_length=1000)
    recommendations: list[str] = Field(min_length=1, max_length=5)
    root_causes: list[str] = Field(default_factory=list, max_length=5)
    triggers: list[str] = Field(default_factory=list, max_length=5)
    incident_commander_brief: str = Field(default="")

    @field_validator("incident_commander_brief", mode="before")
    @classmethod
    def truncate_brief(cls, v: object) -> str:
        return str(v)[:300] if v else ""

    @field_validator("recommendations", mode="before")
    @classmethod
    def validate_recommendations(cls, v: object) -> list[str]:
        if not isinstance(v, list):
            raise ValueError("recommendations deve ser uma lista")
        return [str(item)[:300] for item in v[:5]]

    @field_validator("root_causes", "triggers", mode="before")
    @classmethod
    def validate_string_list(cls, v: object) -> list[str]:
        if not isinstance(v, list):
            return []
        return [str(item)[:300] for item in v[:5]]
