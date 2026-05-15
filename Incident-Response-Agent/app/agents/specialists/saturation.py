from app.agents.specialists.base import SpecialistAgent
from app.agents.prompts import SATURATION_SYSTEM_PROMPT_V1
from app.tools.metrics_client import MetricsClient


class SaturationAgent(SpecialistAgent):
    @property
    def name(self) -> str:
        return "Saturation"

    @property
    def system_prompt(self) -> str:
        return SATURATION_SYSTEM_PROMPT_V1

    @property
    def tools(self) -> list[dict]:
        return [
            {
                "name": "get_saturation",
                "description": "Returns Redis memory usage and active connection count.",
                "input_schema": {"type": "object", "properties": {}, "required": []},
            }
        ]

    async def _handle_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "get_saturation":
            client = MetricsClient()
            data = await client.get_saturation()
            return str(data)
        return '{"error": "unknown tool"}'
