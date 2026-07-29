import random

from enterpriseagent.agent.tools.base import Tool


class QueryMetric(Tool):
    @property
    def name(self) -> str:
        return "query_metric"

    @property
    def description(self) -> str:
        return "Consulta una métrica del sistema"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "metric_name": {
                    "type": "string",
                    "enum": ["cpu", "memory", "requests_per_sec"],
                    "description": "Nombre de la métrica",
                },
            },
            "required": ["metric_name"],
        }

    async def execute(self, metric_name: str = "") -> str:
        values = {
            "cpu": f"{random.uniform(10, 95):.1f}%",
            "memory": f"{random.uniform(30, 90):.1f}%",
            "requests_per_sec": str(random.randint(100, 5000)),
        }
        value = values.get(metric_name, "unknown")
        return f"{metric_name}: {value}"
