from .base import BaseAgent
from ..schema import result, stable_hash

class RepairAgent(BaseAgent):
    id = "repair_agent"
    name = "RepairAgent"
    domain = "repair"
    description = "bounded repair planning and safe manifest edits"

    def run(self, task, context):
        asset = context.get("asset") or {}
        operation = task.get("operation", "repair_agent.execute")
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
