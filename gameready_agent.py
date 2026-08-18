
from .base import BaseAgent
from ..schema import result

class GameReadyAgent(BaseAgent):
    id="gameready_agent"; name="GameReadyAgent"; domain="quality"
    description="Configurable game-ready validation including Metin2-oriented constraints."

    def run(self, task, context):
        asset=context.get("asset") or {}
        profile=task.get("profile","generic_pc")
        limits=task.get("limits") or {}
        mesh=asset.get("mesh") or context.get("mesh") or {}
        v=len(mesh.get("vertices",[])); t=len(mesh.get("faces",[]))
        issues=[]
        max_tri=int(limits.get("max_triangles",100000))
        max_vertices=int(limits.get("max_vertices",100000))
        if t>max_tri: issues.append({"severity":"error","category":"triangle_budget","message":f"{t}>{max_tri}"})
        if v>max_vertices: issues.append({"severity":"error","category":"vertex_budget","message":f"{v}>{max_vertices}"})
        if profile=="metin2":
            if not task.get("metin2_exporter_confirmed",False):
                issues.append({"severity":"warning","category":"export","message":"Metin2 profile requires an explicitly confirmed compatible exporter."})
        return result("gameready.validate",data={
            "profile":profile,"vertex_count":v,"triangle_count":t,"issues":issues,
            "game_ready":not any(x["severity"]=="error" for x in issues),
            "scores":{
                "geometry_score":1.0 if v else 0.0,
                "topology_score":1.0 if v and t else 0.0,
                "game_ready_score":0.0 if any(x["severity"]=="error" for x in issues) else 1.0
            }
        })
