
from __future__ import annotations
import json, sqlite3, time
from pathlib import Path
from .schema import new_id, stable_hash

class StateStore:
    def __init__(self, db_path: str | Path = ":memory:"):
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS assets(
          asset_id TEXT PRIMARY KEY, name TEXT NOT NULL, manifest_json TEXT NOT NULL,
          created REAL NOT NULL, updated REAL NOT NULL, content_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS memory(
          memory_id TEXT PRIMARY KEY, domain TEXT NOT NULL, key TEXT NOT NULL,
          value_json TEXT NOT NULL, confidence REAL NOT NULL, created REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS benchmarks(
          benchmark_id TEXT PRIMARY KEY, model_id TEXT NOT NULL, payload_json TEXT NOT NULL,
          created REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tasks(
          task_id TEXT PRIMARY KEY, state TEXT NOT NULL, payload_json TEXT NOT NULL,
          created REAL NOT NULL, updated REAL NOT NULL
        );
        """)
        self.conn.commit()

    def put_asset(self, manifest: dict) -> dict:
        now=time.time()
        aid=manifest["asset_id"]
        h=stable_hash(manifest)
        self.conn.execute("""INSERT INTO assets(asset_id,name,manifest_json,created,updated,content_hash)
          VALUES(?,?,?,?,?,?) ON CONFLICT(asset_id) DO UPDATE SET
          name=excluded.name, manifest_json=excluded.manifest_json, updated=excluded.updated,
          content_hash=excluded.content_hash""",
          (aid, manifest.get("name", aid), json.dumps(manifest, sort_keys=True), now, now, h))
        self.conn.commit()
        return {"asset_id": aid, "content_hash": h}

    def get_asset(self, aid: str):
        row=self.conn.execute("SELECT manifest_json FROM assets WHERE asset_id=?", (aid,)).fetchone()
        return json.loads(row["manifest_json"]) if row else None

    def list_assets(self):
        rows=self.conn.execute("SELECT asset_id,name,updated,content_hash FROM assets ORDER BY updated DESC").fetchall()
        return [dict(r) for r in rows]

    def put_memory(self, domain, key, value, confidence=1.0):
        mid=new_id("mem")
        self.conn.execute("INSERT INTO memory VALUES(?,?,?,?,?)",
                          (mid,domain,key,json.dumps(value,sort_keys=True),float(confidence),time.time()))
        self.conn.commit()
        return mid

    def search_memory(self, domain=None, key=None):
        sql="SELECT * FROM memory WHERE 1=1"; args=[]
        if domain: sql+=" AND domain=?"; args.append(domain)
        if key: sql+=" AND key LIKE ?"; args.append(f"%{key}%")
        rows=self.conn.execute(sql+" ORDER BY confidence DESC, created DESC LIMIT 100",args).fetchall()
        return [dict(r) | {"value": json.loads(r["value_json"])} for r in rows]

    def put_task(self, task_id, state, payload):
        now=time.time()
        self.conn.execute("""INSERT INTO tasks VALUES(?,?,?,?,?) ON CONFLICT(task_id) DO UPDATE SET
        state=excluded.state,payload_json=excluded.payload_json,updated=excluded.updated""",
        (task_id,state,json.dumps(payload,sort_keys=True),now,now))
        self.conn.commit()
