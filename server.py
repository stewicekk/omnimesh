
from __future__ import annotations
import sys, json, traceback, platform, time, os, math
from pathlib import Path
from .schema import result, new_id, stable_hash
from .state import StateStore
from .agents import AGENT_CLASSES
from .pipeline.runtime import plan as plan_pipeline, describe as describe_pipeline

TOOLS = {}

def tool(name, description, schema):
    def deco(fn):
        TOOLS[name]={"name":name,"description":description,"inputSchema":schema,"fn":fn}
        return fn
    return deco

def obj_schema(props=None, required=None):
    return {"type":"object","properties":props or {},"required":required or []}

STORE=StateStore(os.environ.get("OMNIMESH_DB",":memory:"))
PIPELINES={}

@tool("system.health","Return runtime health.",obj_schema())
def system_health(a):
    return result("system.health",{"status":"healthy","runtime":"omnimcp-python","version":"1.0.0"})

@tool("system.resources","Return host resource information.",obj_schema())
def system_resources(a):
    return result("system.resources",{"platform":platform.platform(),"cpu_count":os.cpu_count(),"python":platform.python_version()})

@tool("system.logs","Return a bounded runtime log view.",obj_schema({"limit":{"type":"integer","minimum":1,"maximum":500}}))
def system_logs(a):
    return result("system.logs",{"entries":[],"note":"No persistent application log sink is attached to the standalone runtime."})

@tool("project.create","Create a project manifest.",obj_schema({"name":{"type":"string"}} ,["name"]))
def project_create(a):
    name=a["name"]; aid=new_id("asset")
    manifest={"asset_id":aid,"name":name,"source":{"type":"generated"},
              "generation":{},"processing":[],"validation":{},"quality":{},
              "license":{},"outputs":[],"provenance":{"created_by":"omnimcp"}}
    STORE.put_asset(manifest)
    return result("project.create",{"asset":manifest})

@tool("asset.create","Create an empty canonical asset.",obj_schema({"name":{"type":"string"}} ,["name"]))
def asset_create(a): return project_create(a)

@tool("asset.import","Import a canonical JSON asset manifest.",obj_schema({"manifest":{"type":"object"}} ,["manifest"]))
def asset_import(a):
    m=a["manifest"]
    if "asset_id" not in m: m["asset_id"]=new_id("asset")
    STORE.put_asset(m); return result("asset.import",{"asset":m})

@tool("asset.export","Export an asset manifest or OBJ.",obj_schema({"asset_id":{"type":"string"},"format":{"type":"string","enum":["json","obj"]},"path":{"type":"string"}} ,["asset_id","format","path"]))
def asset_export(a):
    m=STORE.get_asset(a["asset_id"])
    if not m: return result("asset.export",errors=[{"code":"NOT_FOUND","message":"asset not found"}],ok=False)
    path=Path(a["path"]).resolve()
    path.parent.mkdir(parents=True,exist_ok=True)
    if a["format"]=="json":
        path.write_text(json.dumps(m,indent=2,ensure_ascii=False),encoding="utf-8")
    else:
        mesh=m.get("mesh") or {}
        lines=["# OmniMesh canonical OBJ export"]
        for v in mesh.get("vertices",[]): lines.append("v "+" ".join(str(float(x)) for x in v))
        for f in mesh.get("faces",[]): lines.append("f "+" ".join(str(int(x)+1) for x in f))
        path.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return result("asset.export",{"path":str(path),"sha256":stable_hash(path.read_bytes().hex())})

@tool("asset.validate","Validate an asset manifest.",obj_schema({"asset_id":{"type":"string"}} ,["asset_id"]))
def asset_validate(a):
    m=STORE.get_asset(a["asset_id"])
    if not m:return result("asset.validate",errors=[{"code":"NOT_FOUND","message":"asset not found"}],ok=False)
    issues=[]
    if not m.get("asset_id"): issues.append({"severity":"error","message":"missing asset_id"})
    if "generation" not in m: issues.append({"severity":"error","message":"missing generation section"})
    mesh=m.get("mesh") or {}
    if mesh and ("vertices" not in mesh or "faces" not in mesh): issues.append({"severity":"error","message":"incomplete mesh"})
    return result("asset.validate",{"valid":not any(i["severity"]=="error" for i in issues),"issues":issues})

@tool("asset.compare","Compare two asset manifests by structural metrics.",obj_schema({"asset_a":{"type":"string"},"asset_b":{"type":"string"}} ,["asset_a","asset_b"]))
def asset_compare(a):
    x,y=STORE.get_asset(a["asset_a"]),STORE.get_asset(a["asset_b"])
    if not x or not y:return result("asset.compare",errors=[{"code":"NOT_FOUND","message":"asset not found"}],ok=False)
    def metrics(m):
        mesh=m.get("mesh") or {}; return {"vertices":len(mesh.get("vertices",[])),"triangles":len(mesh.get("faces",[]))}
    mx,my=metrics(x),metrics(y)
    return result("asset.compare",{"a":mx,"b":my,"equal_metrics":mx==my})

@tool("mesh.analyze","Analyze canonical triangle mesh.",obj_schema({"mesh":{"type":"object"}} ,["mesh"]))
def mesh_analyze(a):
    mesh=a["mesh"]; v=mesh.get("vertices",[]); f=mesh.get("faces",[])
    bad=0; deg=0
    for face in f:
        if len(face)!=3 or any(not isinstance(i,int) or i<0 or i>=len(v) for i in face): bad+=1; continue
        p,q,r=(v[i] for i in face)
        ux,uy,uz=q[0]-p[0],q[1]-p[1],q[2]-p[2]
        vx,vy,vz=r[0]-p[0],r[1]-p[1],r[2]-p[2]
        c=(uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx)
        if sum(k*k for k in c)<=1e-20: deg+=1
    return result("mesh.analyze",{"vertices":len(v),"triangles":len(f),"invalid_faces":bad,"degenerate_faces":deg,"valid":bad==0 and deg==0})

@tool("mesh.repair","Repair duplicate vertices and invalid/degenerate triangle faces.",obj_schema({"mesh":{"type":"object"}} ,["mesh"]))
def mesh_repair(a):
    mesh=a["mesh"]; verts=mesh.get("vertices",[]); faces=mesh.get("faces",[])
    unique=[]; remap={}; key_to_idx={}
    for i,v in enumerate(verts):
        key=tuple(round(float(x),12) for x in v)
        if key not in key_to_idx: key_to_idx[key]=len(unique); unique.append(list(v))
        remap[i]=key_to_idx[key]
    new=[]; removed=0
    for f in faces:
        if len(f)!=3 or any(i not in remap for i in f): removed+=1; continue
        nf=[remap[i] for i in f]
        if len(set(nf))<3: removed+=1; continue
        new.append(nf)
    out={"vertices":unique,"faces":new}
    return result("mesh.repair",{"mesh":out,"removed_faces":removed,"merged_vertices":len(verts)-len(unique)})

@tool("mesh.remesh","Apply deterministic quantized vertex remeshing.",obj_schema({"mesh":{"type":"object"},"grid":{"type":"number","minimum":1e-9}} ,["mesh","grid"]))
def mesh_remesh(a):
    g=float(a["grid"]); m=a["mesh"]
    out={**m,"vertices":[[round(float(x)/g)*g for x in v] for v in m.get("vertices",[])]}
    return result("mesh.remesh",{"mesh":out,"grid":g})

@tool("mesh.decimate","Deterministically reduce faces by a target ratio.",obj_schema({"mesh":{"type":"object"},"ratio":{"type":"number","minimum":0.01,"maximum":1.0}} ,["mesh","ratio"]))
def mesh_decimate(a):
    m=a["mesh"]; ratio=float(a["ratio"]); n=max(1,int(len(m.get("faces",[]))*ratio))
    return result("mesh.decimate",{"mesh":{**m,"faces":m.get("faces",[])[:n]},"target_faces":n})

@tool("mesh.weld","Alias for deterministic vertex welding.",obj_schema({"mesh":{"type":"object"}} ,["mesh"]))
def mesh_weld(a): return mesh_repair(a)

@tool("mesh.optimize","Optimize ordering metadata without changing geometry.",obj_schema({"mesh":{"type":"object"}} ,["mesh"]))
def mesh_optimize(a):
    m=a["mesh"]; return result("mesh.optimize",{"mesh":m,"optimization":{"geometry_changed":False,"cache_locality":"not_reordered_in_standalone_runtime"}})

@tool("uv.analyze","Analyze UV presence and utilization metadata.",obj_schema({"mesh":{"type":"object"}} ,["mesh"]))
def uv_analyze(a):
    m=a["mesh"]; uv=m.get("uv")
    return result("uv.analyze",{"has_uv":bool(uv),"uv_count":len(uv or []),"utilization":0.0 if not uv else 1.0})

@tool("uv.unwrap","Create deterministic planar UVs for the mesh.",obj_schema({"mesh":{"type":"object"}} ,["mesh"]))
def uv_unwrap(a):
    m=a["mesh"]; vs=m.get("vertices",[])
    if not vs:return result("uv.unwrap",{"mesh":m,"uv":[]})
    xs=[float(v[0]) for v in vs]; zs=[float(v[2]) for v in vs]
    minx,maxx,minz,maxz=min(xs),max(xs),min(zs),max(zs)
    dx=max(maxx-minx,1e-12); dz=max(maxz-minz,1e-12)
    uv=[[(v[0]-minx)/dx,(v[2]-minz)/dz] for v in vs]
    return result("uv.unwrap",{"mesh":{**m,"uv":uv}})

@tool("uv.repack","Normalize UV coordinates into [0,1].",obj_schema({"mesh":{"type":"object"}} ,["mesh"]))
def uv_repack(a):
    m=a["mesh"]; uv=m.get("uv",[])
    if not uv:return result("uv.repack",{"mesh":m})
    xs=[u[0] for u in uv]; ys=[u[1] for u in uv]; dx=max(max(xs)-min(xs),1e-12); dy=max(max(ys)-min(ys),1e-12)
    out=[[(u[0]-min(xs))/dx,(u[1]-min(ys))/dy] for u in uv]
    return result("uv.repack",{"mesh":{**m,"uv":out}})

@tool("material.generate","Generate a canonical PBR material description.",obj_schema({"name":{"type":"string"},"base_color":{"type":"array"}} ,["name","base_color"]))
def material_generate(a):
    return result("material.generate",{"material":{"name":a["name"],"baseColor":a["base_color"],"metallic":0.0,"roughness":0.6,"normal":None,"ao":None,"emissive":None}})

@tool("texture.generate","Generate texture metadata for a canonical material.",obj_schema({"resolution":{"type":"integer","enum":[256,512,1024,2048,4096]}} ,["resolution"]))
def texture_generate(a):
    r=int(a["resolution"]); return result("texture.generate",{"texture":{"width":r,"height":r,"channels":["RGBA"],"generated":True,"backend":"metadata"}})

@tool("ai.generate3d","Generate a deterministic local primitive as a safe fallback.",obj_schema({"primitive":{"type":"string","enum":["box","plane"]},"size":{"type":"number"},"seed":{"type":"integer"}} ,["primitive","size","seed"]))
def ai_generate3d(a):
    from .agents.geometry_agent import GeometryAgent
    return GeometryAgent().run({"operation":"ai.generate3d","parameters":a},{"asset":{}})

@tool("ai.generate_texture","Generate deterministic texture metadata fallback.",obj_schema({"resolution":{"type":"integer"},"seed":{"type":"integer"}} ,["resolution","seed"]))
def ai_generate_texture(a):
    return texture_generate({"resolution":a["resolution"]})

@tool("ai.generate_material","Generate deterministic material fallback.",obj_schema({"name":{"type":"string"},"base_color":{"type":"array"}} ,["name","base_color"]))
def ai_generate_material(a): return material_generate(a)

@tool("ai.generate_parts","Generate deterministic part plan.",obj_schema({"parts":{"type":"array","items":{"type":"string"}}} ,["parts"]))
def ai_generate_parts(a): return result("ai.generate_parts",{"parts":[{"name":p,"index":i} for i,p in enumerate(a["parts"])]})

@tool("model.list","List available logical model backends.",obj_schema())
def model_list(a):
    models=[
      {"id":"trellis2","local":True,"capabilities":["image_to_3d","pbr"],"license":"MIT","status":"unconfigured"},
      {"id":"hunyuan3d","local":True,"capabilities":["image_to_3d","pbr"],"license":"custom","status":"unconfigured"},
      {"id":"sam3d","local":True,"capabilities":["reconstruction","segmentation"],"license":"SAM","status":"unconfigured"},
      {"id":"meshy","local":False,"capabilities":["text_to_3d","image_to_3d","texture"],"license":"provider_terms","status":"adapter_only"},
      {"id":"tripo","local":False,"capabilities":["text_to_3d","image_to_3d","multi_view"],"license":"provider_terms","status":"adapter_only"},
      {"id":"atlas","local":False,"capabilities":["workflow","generation"],"license":"provider_terms","status":"adapter_only"},
      {"id":"ollama","local":True,"capabilities":["llm"],"license":"model_dependent","status":"adapter_only"},
      {"id":"comfyui","local":True,"capabilities":["workflow"],"license":"workflow_dependent","status":"adapter_only"},
    ]
    return result("model.list",{"models":models})

@tool("model.health","Return model health policy.",obj_schema({"model_id":{"type":"string"}} ,["model_id"]))
def model_health(a):
    return result("model.health",{"model_id":a["model_id"],"state":"UNAVAILABLE","reason":"No external worker is configured in the standalone package."})

@tool("model.route","Select a model by deterministic capability policy.",obj_schema({"capability":{"type":"string"},"local_first":{"type":"boolean"}} ,["capability"]))
def model_route(a):
    cap=a["capability"]; local=a.get("local_first",True)
    order=["trellis2","hunyuan3d","sam3d","meshy","tripo","atlas"]
    if cap=="reconstruction": order=["sam3d","trellis2","hunyuan3d","tripo"]
    if cap=="text_to_3d": order=["trellis2","hunyuan3d","tripo","meshy"]
    return result("model.route",{"selected":order[0],"candidates":order,"policy":"local_first" if local else "capability_first"})

@tool("model.benchmark","Record a benchmark result.",obj_schema({"model_id":{"type":"string"},"metrics":{"type":"object"}} ,["model_id","metrics"]))
def model_benchmark(a):
    bid=new_id("bench"); STORE.conn.execute("INSERT INTO benchmarks VALUES(?,?,?,?)",(bid,a["model_id"],json.dumps(a["metrics"],sort_keys=True),time.time())); STORE.conn.commit()
    return result("model.benchmark",{"benchmark_id":bid})

@tool("agent.plan","Plan a specialist agent task.",obj_schema({"agent_id":{"type":"string"},"task":{"type":"object"}} ,["agent_id","task"]))
def agent_plan(a):
    if a["agent_id"] not in AGENT_CLASSES:return result("agent.plan",errors=[{"code":"UNKNOWN_AGENT","message":a["agent_id"]}],ok=False)
    return result("agent.plan",{"agent_id":a["agent_id"],"plan":{"action":"execute","validation_required":True,"transactional":True}})

@tool("agent.execute","Execute one of the 22 concrete agents.",obj_schema({"agent_id":{"type":"string"},"task":{"type":"object"},"context":{"type":"object"}} ,["agent_id","task"]))
def agent_execute(a):
    cls=AGENT_CLASSES.get(a["agent_id"])
    if not cls:return result("agent.execute",errors=[{"code":"UNKNOWN_AGENT","message":a["agent_id"]}],ok=False)
    try:return cls().execute(a["task"],a.get("context",{}))
    except Exception as e:return result("agent.execute",errors=[{"code":"AGENT_FAILURE","message":str(e)}],ok=False)

@tool("agent.review","Review an agent result.",obj_schema({"agent_id":{"type":"string"},"output":{"type":"object"}} ,["agent_id","output"]))
def agent_review(a):
    cls=AGENT_CLASSES.get(a["agent_id"])
    if not cls:return result("agent.review",errors=[{"code":"UNKNOWN_AGENT","message":a["agent_id"]}],ok=False)
    return result("agent.review",cls().validate(a["output"],{}))

@tool("agent.repair","Execute bounded repair planning.",obj_schema({"agent_id":{"type":"string"},"issues":{"type":"array"}} ,["agent_id","issues"]))
def agent_repair(a):
    return result("agent.repair",{"repair_agent":a["agent_id"],"issues":a["issues"],"attempt":1,"max_attempts":3,"requires_revalidation":True})

@tool("memory.store","Store structured memory.",obj_schema({"domain":{"type":"string"},"key":{"type":"string"},"value":{"type":"object"},"confidence":{"type":"number"}} ,["domain","key","value"]))
def memory_store(a):
    mid=STORE.put_memory(a["domain"],a["key"],a["value"],a.get("confidence",1.0)); return result("memory.store",{"memory_id":mid})

@tool("memory.search","Search structured memory.",obj_schema({"domain":{"type":"string"},"key":{"type":"string"}}))
def memory_search(a): return result("memory.search",{"entries":STORE.search_memory(a.get("domain"),a.get("key"))})

@tool("memory.learn","Record bounded model routing evidence.",obj_schema({"model_id":{"type":"string"},"asset_class":{"type":"string"},"success":{"type":"boolean"}} ,["model_id","asset_class","success"]))
def memory_learn(a):
    mid=STORE.put_memory("model_routing",f'{a["model_id"]}:{a["asset_class"]}',{"success":a["success"]},0.5)
    return result("memory.learn",{"memory_id":mid,"bounded":True})

@tool("pipeline.describe","Describe the default asset pipeline.",obj_schema())
def pipeline_describe(a): return result("pipeline.describe",describe_pipeline())

@tool("pipeline.execute","Create and execute a deterministic planning graph.",obj_schema({"request":{"type":"string"},"game_target":{"type":"string"}} ,["request"]))
def pipeline_execute(a):
    p=plan_pipeline(a["request"],a.get("game_target","generic_pc")); PIPELINES[p["pipeline_id"]]=p
    return result("pipeline.execute",{"pipeline":p})

@tool("pipeline.cancel","Cancel a pipeline.",obj_schema({"pipeline_id":{"type":"string"}} ,["pipeline_id"]))
def pipeline_cancel(a):
    p=PIPELINES.get(a["pipeline_id"])
    if not p:return result("pipeline.cancel",errors=[{"code":"NOT_FOUND","message":"pipeline not found"}],ok=False)
    for s in p["stages"]:
        if s["state"]=="PENDING":s["state"]="CANCELLED"
    return result("pipeline.cancel",{"pipeline":p})

def dispatch(req):
    method=req.get("method")
    params=req.get("params") or {}
    if method=="initialize":
        return {"protocolVersion":"2025-06-18","capabilities":{"tools":{"listChanged":False},"resources":{"subscribe":False,"listChanged":False},"prompts":{"listChanged":False}},"serverInfo":{"name":"omnimcp","version":"1.0.0"}}
    if method=="notifications/initialized": return None
    if method=="tools/list": return {"tools":[{k:v[k] for k in ("name","description","inputSchema")} for v in TOOLS.values()]}
    if method=="tools/call":
        name=params.get("name"); args=params.get("arguments") or {}
        if name not in TOOLS: raise ValueError(f"Unknown tool: {name}")
        out=TOOLS[name]["fn"](args)
        return {"content":[{"type":"text","text":json.dumps(out,ensure_ascii=False)}],"structuredContent":out,"isError":not out.get("ok",False)}
    if method=="resources/list": return {"resources":[{"uri":"omnimcp://agents","name":"Agent Registry","mimeType":"application/json"},{"uri":"omnimcp://pipeline","name":"Pipeline Definition","mimeType":"application/json"}]}
    if method=="resources/read":
        uri=params.get("uri")
        if uri=="omnimcp://agents":
            data=[{"id":k,"class":v.__name__,"capabilities":v().capabilities()} for k,v in AGENT_CLASSES.items()]
        elif uri=="omnimcp://pipeline": data=describe_pipeline()
        else: raise ValueError("Unknown resource")
        return {"contents":[{"uri":uri,"mimeType":"application/json","text":json.dumps(data,ensure_ascii=False)}]}
    if method=="prompts/list":
        return {"prompts":[{"name":"game_ready_asset","description":"Plan a validated game-ready asset workflow."},{"name":"debug_pipeline","description":"Diagnose a failed pipeline without bypassing validators."}]}
    if method=="prompts/get":
        name=params.get("name")
        if name=="game_ready_asset":
            text="Create a game-ready asset. Analyze reference, generate, compare, repair, retopologize, UV, material, texture, LOD, collision, validate, optimize and export."
        elif name=="debug_pipeline":
            text="Reproduce the failure, isolate root cause, repair transactionally, revalidate, and add a regression test."
        else: raise ValueError("Unknown prompt")
        return {"description":name,"messages":[{"role":"user","content":{"type":"text","text":text}}]}
    raise ValueError(f"Unsupported MCP method: {method}")

def main():
    for line in sys.stdin:
        if not line.strip(): continue
        try:
            req=json.loads(line)
            if "id" not in req:
                dispatch(req); continue
            resp={"jsonrpc":"2.0","id":req["id"],"result":dispatch(req)}
        except Exception as e:
            resp={"jsonrpc":"2.0","id":req.get("id") if isinstance(req,dict) else None,
                  "error":{"code":-32603,"message":str(e),"data":{"traceback":traceback.format_exc(limit=3)}}}
        sys.stdout.write(json.dumps(resp,ensure_ascii=False,separators=(",",":"))+"\n")
        sys.stdout.flush()

if __name__=="__main__":
    main()
