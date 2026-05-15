from app.agents.specialists.base import SpecialistAgent
from app.agents.prompts import ERRORS_SYSTEM_PROMPT_V1
from app.tools.metrics_client import MetricsClient


class ErrorsAgent(SpecialistAgent):
    @property
    def name(self) -> str:
        return "Errors"

    @property
    def system_prompt(self) -> str:
        return ERRORS_SYSTEM_PROMPT_V1

    @property
    def tools(self) -> list[dict]:
        return [
            {
                "name": "get_overview",
                "description": "Returns total requests, 4xx/5xx error counts and error rate percentages.",
                "input_schema": {"type": "object", "properties": {}, "required": []},
            }
        ]

    async def _handle_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "get_overview":
            client = MetricsClient()
            data = await client.get_overview()
            return str(data)
        return '{"error": "unknown tool"}'
