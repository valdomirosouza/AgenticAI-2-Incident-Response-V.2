from app.agents.specialists.base import SpecialistAgent
from app.agents.prompts import TRAFFIC_SYSTEM_PROMPT_V1
from app.tools.metrics_client import MetricsClient


class TrafficAgent(SpecialistAgent):
    @property
    def name(self) -> str:
        return "Traffic"

    @property
    def system_prompt(self) -> str:
        return TRAFFIC_SYSTEM_PROMPT_V1

    @property
    def tools(self) -> list[dict]:
        return [
            {
                "name": "get_rps",
                "description": "Returns requests-per-second buckets for the last 60 minutes.",
                "input_schema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "get_backends",
                "description": "Returns request count per backend.",
                "input_schema": {"type": "object", "properties": {}, "required": []},
            },
        ]

    async def _handle_tool(self, tool_name: str, tool_input: dict) -> str:
        client = MetricsClient()
        if tool_name == "get_rps":
            data = await client.get_rps()
            return str(data)
        if tool_name == "get_backends":
            data = await client.get_backends()
            return str(data)
        return '{"error": "unknown tool"}'
