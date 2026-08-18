
import json, subprocess, sys

def rpc(proc, i, method, params=None):
    proc.stdin.write(json.dumps({"jsonrpc":"2.0","id":i,"method":method,"params":params or {}})+"\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())

def main():
    p=subprocess.Popen([sys.executable,"-m","omnimcp.server"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
    x=rpc(p,1,"initialize",{})
    assert x["result"]["serverInfo"]["name"]=="omnimcp"
    x=rpc(p,2,"tools/list",{})
    names={t["name"] for t in x["result"]["tools"]}
    assert "asset.validate" in names and "agent.execute" in names
    x=rpc(p,3,"tools/call",{"name":"ai.generate3d","arguments":{"primitive":"box","size":2,"seed":7}})
    assert x["result"]["isError"] is False
    p.terminate()
    print("smoke: OK")

if __name__=="__main__": main()
