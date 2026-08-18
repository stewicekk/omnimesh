
from __future__ import annotations
from typing import Any
from ..schema import result

class BaseAgent:
    id = "agent.base"
    name = "BaseAgent"
    domain = "system"
    description = ""

    def capabilities(self):
        return {"id": self.id, "name": self.name, "domain": self.domain, "description": self.description}

    def execute(self, task: dict, context: dict) -> dict:
        return self.run(task, context)

    def validate(self, output: dict, context: dict) -> dict:
        return {"ok": isinstance(output, dict), "issues": [] if isinstance(output, dict) else ["agent output is not an object"]}

    def run(self, task, context):
        raise NotImplementedError
