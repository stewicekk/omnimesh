from .base import BaseAgent
from ..schema import result, stable_hash

class CriticAgent(BaseAgent):
    id = "critic_agent"
    name = "CriticAgent"
    domain = "quality"
    description = "aggregate machine-readable quality critique"

    def run(self, task, context):
        asset = context.get("asset") or {}
        operation = task.get("operation", "critic_agent.execute")
        data = {
            "agent": self.id,
            "domain": self.domain,
            "task": task,
            "asset_id": asset.get("asset_id"),
            "input_hash": stable_hash({"task": task, "asset": asset}),
            "analysis": self._analysis(task, asset, context),
        }
        return result(operation, data=data)

    def _analysis(self, task, asset, context):
        return {
            "status": "completed",
            "description": self.description,
            "deterministic": True,
            "actionable": True
        }
