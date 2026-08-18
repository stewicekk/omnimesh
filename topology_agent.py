
from .base import BaseAgent
from ..schema import result
import math

class TopologyAgent(BaseAgent):
    id="topology_agent"; name="TopologyAgent"; domain="processing"
    description="Topology diagnostics for canonical triangle meshes."

    def run(self, task, context):
        mesh=(context.get("mesh") or {})
        v=mesh.get("vertices",[]); f=mesh.get("faces",[])
        issues=[]; degenerate=0; bad_index=0
        for i,face in enumerate(f):
            if len(face)!=3 or any(not isinstance(x,int) for x in face):
                issues.append({"severity":"error","category":"format","face":i,"message":"face is not a triangle"})
                continue
            if any(x<0 or x>=len(v) for x in face):
                bad_index+=1
                continue
            a,b,c=(v[x] for x in face)
            ax,ay,az=a; bx,by,bz=b; cx,cy,cz=c
            ux,uy,uz=bx-ax,by-ay,bz-az
            vx,vy,vz=cx-ax,cy-ay,cz-az
            cross=(uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx)
            area2=sum(x*x for x in cross)
            if area2 <= 1e-20: degenerate+=1
        if bad_index: issues.append({"severity":"error","category":"index","count":bad_index,"message":"faces reference invalid vertices"})
        if degenerate: issues.append({"severity":"error","category":"degenerate","count":degenerate,"message":"zero-area triangles detected"})
        return result("topology.analyze", data={
            "vertex_count":len(v),"face_count":len(f),"degenerate_faces":degenerate,
            "invalid_index_faces":bad_index,"issues":issues,
            "valid":not issues
        }, ok=not issues)
