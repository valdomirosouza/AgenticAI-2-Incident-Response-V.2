import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.report import Severity, SpecialistFinding, IncidentReport


# ── Helpers para construir respostas mock do Anthropic ────────────────────────

def make_end_turn_response(json_data: dict) -> MagicMock:
    block = MagicMock()
    block.text = json.dumps(json_data)
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [block]
    return response


def make_tool_use_response(tool_name: str, tool_id: str = "tu_001") -> MagicMock:
    block = MagicMock(spec=["type", "id", "name", "input"])
    block.type = "tool_use"
    block.id = tool_id
    block.name = tool_name
    block.input = {}
    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [block]
    return response

OK_FINDING = SpecialistFinding(specialist="Test", severity=Severity.ok, summary="All good", details="No issues.")
WARNING_FINDING = SpecialistFinding(specialist="Test", severity=Severity.warning, summary="High latency", details="P99 > 500ms")
CRITICAL_FINDING = SpecialistFinding(specialist="Test", severity=Severity.critical, summary="High error rate", details="5xx > 10%")

OK_REPORT = IncidentReport(
    timestamp=datetime.now(timezone.utc),
    overall_severity=Severity.ok,
    title="System Healthy",
    diagnosis="All signals within normal bounds.",
    recommendations=[],
    findings=[OK_FINDING],
    similar_incidents=[],
)

CRITICAL_REPORT = IncidentReport(
    timestamp=datetime.now(timezone.utc),
    overall_severity=Severity.critical,
    title="High Error Rate",
    diagnosis="5xx error rate at 15%. Root cause: Redis saturation.",
    root_causes=["Redis configured with noeviction policy"],
    triggers=["Traffic spike 4x"],
    recommendations=["Change eviction policy to allkeys-lru", "Scale Redis memory"],
    findings=[CRITICAL_FINDING],
    similar_incidents=["INC-001"],
)

OK_SYNTH_DATA = {
    "overall_severity": "ok",
    "title": "System Healthy",
    "diagnosis": "All four Golden Signals within normal bounds.",
    "root_causes": [],
    "triggers": [],
    "recommendations": ["Continue monitoring"],
    "incident_commander_brief": "System is healthy — no action required.",
}


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def client_with_auth():
    with patch("app.config.settings.api_key", "test-secret-key"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


@pytest.fixture
def mock_run_analysis_ok():
    with patch("app.routers.analyze.run_analysis", new=AsyncMock(return_value=OK_REPORT)) as mock:
        yield mock


@pytest.fixture
def mock_run_analysis_critical():
    with patch("app.routers.analyze.run_analysis", new=AsyncMock(return_value=CRITICAL_REPORT)) as mock:
        yield mock
