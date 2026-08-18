
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List
import hashlib, json, time, uuid

def stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()

def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"

@dataclass
class Result:
    ok: bool
    operation: str
    data: Dict[str, Any]
    errors: List[Dict[str, Any]]
    warnings: List[str]
    trace_id: str

    def to_dict(self):
        return asdict(self)

def result(operation: str, data=None, errors=None, warnings=None, ok=True, trace_id=None):
    return Result(ok, operation, data or {}, errors or [], warnings or [], trace_id or new_id("trace")).to_dict()
