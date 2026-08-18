from .base import BaseAgent
from ..schema import result, stable_hash

class LODAgent(BaseAgent):
    id = "l_o_d_agent"
    name = "LODAgent"
    domain = "processing"
    description = "LOD budget and reduction planning"

    def run(self, task, context):
        asset = context.get("asset") or {}
        operation = task.get("operation", "l_o_d_agent.execute")
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
