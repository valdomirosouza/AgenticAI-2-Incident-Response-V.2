"""
Base do SpecialistAgent com tool-use loop limitado (SDD §9.3.2).
Cada especialista herda desta classe e define suas próprias tools e system prompt.
"""

import json
import logging
import re
from abc import ABC, abstractmethod

import anthropic

from app.agents.anthropic_circuit_breaker import (
    AnthropicCircuitOpenError,
    call_anthropic_with_retry,
)
from app.config import settings
from app.models.report import Severity, SpecialistFinding

logger = logging.getLogger(__name__)

# Hard stop no tool-use loop — evita divergência e consumo ilimitado (SDD §9.3.2 / LLM10)
MAX_TOOL_ITERATIONS = 5


class SpecialistAgent(ABC):
    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def system_prompt(self) -> str: ...

    @property
    @abstractmethod
    def tools(self) -> list[dict]: ...

    @abstractmethod
    async def _handle_tool(self, tool_name: str, tool_input: dict) -> str: ...

    async def analyze(self) -> SpecialistFinding:
        messages: list[dict] = [{"role": "user", "content": f"Analyze {self.name} metrics now."}]
        iterations = 0

        while True:
            if iterations >= MAX_TOOL_ITERATIONS:
                logger.error(
                    "Tool-use loop exceeded %d iterations for %s — forcing stop",
                    MAX_TOOL_ITERATIONS,
                    self.name,
                )
                return SpecialistFinding(
                    specialist=self.name,
                    severity=Severity.warning,
                    summary=f"Analysis incomplete — tool-use loop limit reached after {MAX_TOOL_ITERATIONS} iterations",
                    details=f"The agent exceeded the maximum of {MAX_TOOL_ITERATIONS} tool calls without completing.",
                )

            iterations += 1
            try:
                response = await call_anthropic_with_retry(
                    self._client.messages.create,
                    model=settings.model,
                    max_tokens=512,
                    system=self.system_prompt,
                    tools=self.tools,
                    messages=messages,
                )
            except AnthropicCircuitOpenError:
                return SpecialistFinding(
                    specialist=self.name,
                    severity=Severity.warning,
                    summary=f"{self.name}: Anthropic API circuit open — LLM unavailable",
                    details="Circuit breaker is OPEN. Analysis degraded to rule-based fallback.",
                )

            if response.stop_reason == "end_turn":
                return self._parse_finding(response)

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = await self._handle_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

    def _parse_finding(self, response) -> SpecialistFinding:
        for block in response.content:
            if hasattr(block, "text"):
                try:
                    text = block.text.strip()
                    # Claude sometimes wraps JSON in markdown fences despite instructions
                    start, end = text.find("{"), text.rfind("}")
                    if start >= 0 and end > start:
                        text = text[start : end + 1]
                    data = json.loads(text)
                    return SpecialistFinding(
                        specialist=self.name,
                        severity=Severity(data.get("severity", "warning")),
                        summary=str(data.get("summary", ""))[:300],
                        details=str(data.get("details", ""))[:1000],
                    )
                except (json.JSONDecodeError, ValueError) as exc:
                    logger.warning("Failed to parse %s finding: %s", self.name, exc)

        return SpecialistFinding(
            specialist=self.name,
            severity=Severity.warning,
            summary=f"{self.name}: could not parse LLM response",
            details="LLM response did not contain a valid JSON finding.",
        )
