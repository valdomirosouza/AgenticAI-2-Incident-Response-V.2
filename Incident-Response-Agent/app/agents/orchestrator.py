"""
Orquestrador principal — executa os 4 especialistas em paralelo e sintetiza o IncidentReport.
Implementa o papel de SoS Responder / Tech IRT (SDD §9.13.3).
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone

import anthropic
from pydantic import ValidationError

from app.agents.anthropic_circuit_breaker import (
    AnthropicCircuitOpenError,
    call_anthropic_with_retry,
)
from app.agents.prompts import ORCHESTRATOR_SYSTEM_PROMPT_V1, PROMPT_VERSION
from app.agents.specialists.errors import ErrorsAgent
from app.agents.specialists.latency import LatencyAgent
from app.agents.specialists.saturation import SaturationAgent
from app.agents.specialists.traffic import TrafficAgent
from app.config import settings
from app.models.llm_response import OrchestratorResponse
from app.models.report import IncidentReport, Severity, SpecialistFinding, max_severity
from app.tools.kb_client import search_kb

logger = logging.getLogger(__name__)

MAX_FINDING_LENGTH = 500


def _sanitize_finding_text(text: str) -> str:
    """Remove tags que podem ser usadas em prompt injection (SDD §7.3.1 / LLM01:2025)."""
    text = re.sub(r"<\/?(?:human|assistant|system|prompt)>", "", text, flags=re.IGNORECASE)
    return text[:MAX_FINDING_LENGTH]


def _should_escalate(findings: list[SpecialistFinding]) -> bool:
    """Recomenda escalação quando ≥3 componentes críticos simultaneamente (SDD §9.13.9)."""
    return sum(1 for f in findings if f.severity == Severity.critical) >= 3


async def run_analysis() -> IncidentReport:
    start = time.monotonic()
    logger.info("Analysis started", extra={"prompt_version": PROMPT_VERSION})

    # 4 especialistas em paralelo — reduz latência de ~40s para ~10s (SDD §2.5)
    findings: list[SpecialistFinding] = list(
        await asyncio.gather(
            _safe_analyze(LatencyAgent()),
            _safe_analyze(ErrorsAgent()),
            _safe_analyze(SaturationAgent()),
            _safe_analyze(TrafficAgent()),
        )
    )

    # KB consultada apenas quando há findings não-OK (evita custo desnecessário)
    kb_results: list[dict] = []
    if any(f.severity != Severity.ok for f in findings):
        query = " ".join(f.summary for f in findings if f.severity != Severity.ok)
        kb_results = await search_kb(query)

    report = await _synthesize(findings, kb_results)
    report.analysis_duration_seconds = round(time.monotonic() - start, 3)
    report.specialist_model_version = PROMPT_VERSION
    report.escalation_recommended = _should_escalate(findings)

    logger.info(
        "Analysis completed",
        extra={
            "severity": report.overall_severity.value,
            "duration_s": report.analysis_duration_seconds,
            "kb_chunks": len(kb_results),
        },
    )
    return report


async def _safe_analyze(agent) -> SpecialistFinding:
    try:
        return await agent.analyze()
    except Exception as exc:
        logger.error("Specialist %s failed: %s", agent.name, exc)
        return SpecialistFinding(
            specialist=agent.name,
            severity=Severity.warning,
            summary=f"{agent.name}: metrics unavailable",
            details=f"Agent failed to complete analysis: {type(exc).__name__}",
        )


async def _synthesize(findings: list[SpecialistFinding], kb_results: list[dict]) -> IncidentReport:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Sanitizar findings antes de inserir no prompt (LLM01)
    findings_xml = "\n\n".join(
        f'<finding specialist="{f.specialist}" severity="{f.severity.value}">\n'
        f"Summary: {_sanitize_finding_text(f.summary)}\n"
        f"Details: {_sanitize_finding_text(f.details)}\n"
        f"</finding>"
        for f in findings
    )

    kb_text = ""
    if kb_results:
        kb_text = "\n\nRelated historical incidents:\n" + "\n".join(
            f"- {r.get('id', 'unknown')}: {_sanitize_finding_text(str(r.get('content', '')))}"
            for r in kb_results[:5]
        )

    user_message = f"<findings>\n{findings_xml}\n</findings>{kb_text}"

    try:
        response = await call_anthropic_with_retry(
            client.messages.create,
            model=settings.model,
            max_tokens=1024,
            system=ORCHESTRATOR_SYSTEM_PROMPT_V1,
            messages=[{"role": "user", "content": user_message}],
        )

        body = next((b.text for b in response.content if hasattr(b, "text")), "")
        # Strip markdown code fences Claude may add despite "Respond ONLY with JSON" instruction
        start, end = body.find("{"), body.rfind("}")
        if start >= 0 and end > start:
            body = body[start : end + 1]
        data = json.loads(body)
        validated = OrchestratorResponse(**data)

        similar_ids = list(
            dict.fromkeys(r.get("id") for r in kb_results if r.get("id"))
        )

        return IncidentReport(
            overall_severity=validated.overall_severity,
            title=validated.title,
            diagnosis=validated.diagnosis,
            recommendations=validated.recommendations,
            root_causes=validated.root_causes,
            triggers=validated.triggers,
            incident_commander_brief=validated.incident_commander_brief,
            findings=findings,
            similar_incidents=similar_ids,
            llm_calls_count=5,  # 4 specialists + 1 synthesis
            kb_chunks_retrieved=len(kb_results),
            kb_score_max=max((r.get("score", 0) for r in kb_results), default=None) if kb_results else None,
        )

    except AnthropicCircuitOpenError as exc:
        logger.warning("Synthesis skipped — circuit breaker OPEN: %s", exc)
        overall = max_severity([f.severity for f in findings])
        return IncidentReport(
            overall_severity=overall,
            title="Incident Detected (LLM Circuit Open)",
            diagnosis="Anthropic API circuit breaker is OPEN. Severity derived from specialist rule-based findings.",
            recommendations=["Check Anthropic API status", "Review Grafana metrics manually"],
            findings=findings,
            similar_incidents=[],
        )
    except (json.JSONDecodeError, ValidationError, Exception) as exc:
        logger.warning("Synthesis fallback triggered: %s", exc)
        overall = max_severity([f.severity for f in findings])
        return IncidentReport(
            overall_severity=overall,
            title="Incident Detected (synthesis unavailable)",
            diagnosis="LLM synthesis failed. Severity derived from specialist findings.",
            recommendations=["Review specialist findings below", "Check Anthropic API status"],
            findings=findings,
            similar_incidents=[],
        )
