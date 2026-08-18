
from .base import BaseAgent
from ..schema import result, stable_hash

class GeometryAgent(BaseAgent):
    id="geometry_agent"; name="GeometryAgent"; domain="generation"
    description="Deterministic procedural geometry generation and mesh statistics."

    def run(self, task, context):
        p=task.get("parameters",{})
        seed=int(p.get("seed",0))
        kind=p.get("primitive","box")
        size=float(p.get("size",1.0))
        # Compact canonical mesh representation; no external dependencies.
        if kind=="box":
            s=size/2
            v=[[-s,-s,-s],[s,-s,-s],[s,s,-s],[-s,s,-s],[-s,-s,s],[s,-s,s],[s,s,s],[-s,s,s]]
            f=[[0,1,2],[0,2,3],[4,6,5],[4,7,6],[0,4,5],[0,5,1],[1,5,6],[1,6,2],[2,6,7],[2,7,3],[4,0,3],[4,3,7]]
        elif kind=="plane":
            v=[[-size/2,0,-size/2],[size/2,0,-size/2],[size/2,0,size/2],[-size/2,0,size/2]]
            f=[[0,1,2],[0,2,3]]
        else:
            raise ValueError("Unsupported deterministic primitive. Use box or plane.")
        mesh={"vertices":v,"faces":f,"primitive":kind,"seed":seed}
        return result("geometry.generate", data={
            "agent":self.id,"mesh":mesh,"vertex_count":len(v),"triangle_count":len(f),
            "content_hash":stable_hash(mesh)
        })
