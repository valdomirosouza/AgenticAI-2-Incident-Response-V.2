from app.agents.specialists.base import SpecialistAgent
from app.agents.prompts import LATENCY_SYSTEM_PROMPT_V1
from app.tools.metrics_client import MetricsClient


class LatencyAgent(SpecialistAgent):
    @property
    def name(self) -> str:
        return "Latency"

    @property
    def system_prompt(self) -> str:
        return LATENCY_SYSTEM_PROMPT_V1

    # Menor privilégio: apenas a tool necessária (SDD §9.2.1)
    @property
    def tools(self) -> list[dict]:
        return [
            {
                "name": "get_response_time_percentiles",
                "description": "Returns P50, P95, P99 latency percentiles in milliseconds and sample count.",
                "input_schema": {"type": "object", "properties": {}, "required": []},
            }
        ]

    async def _handle_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "get_response_time_percentiles":
            client = MetricsClient()
            data = await client.get_response_times()
            return str(data)
        return '{"error": "unknown tool"}'
