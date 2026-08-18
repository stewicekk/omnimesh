
from __future__ import annotations
from ..schema import result, new_id

DEFAULT_STAGES=[
 "reference","understand","segment","generate","compare","candidate_rank",
 "topology_cleanup","retopology","uv","material","texture","lod","collision",
 "validate","repair","final_validate","optimize","export"
]

def plan(request: str, game_target="generic_pc"):
    return {
        "pipeline_id":new_id("pipe"),
        "request":request,
        "game_target":game_target,
        "stages":[{"id":s,"state":"PENDING"} for s in DEFAULT_STAGES],
        "editable":True,
        "deterministic_core":True
    }

def describe():
    return {"stages":DEFAULT_STAGES,"description":"Closed-loop AI 3D asset pipeline with validation and repair."}
