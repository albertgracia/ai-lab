#!/usr/bin/env python3
"""AI-LAB Live API v3 - Status, Topology, SSE Events, Analytics."""
import json, subprocess
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from runtime.event_bus import emit
import time as _time

HOST = "0.0.0.0"; PORT = 8084
STATE_DIR = Path("/opt/ai-lab/runtime/state")

def get_cluster_topology():
    state = {}
    f = STATE_DIR / "cluster_state.json"
    if f.exists():
        try: state = json.loads(f.read_text())
        except: pass
    nl = state.get("nodes", [])
    vn = {"gateway": {"title": "Gateway AI-LAB", "subtitle": ":8008", "ip": "1.30"},
          "event-bus": {"title": "Event Bus", "subtitle": "Cognitivo", "ip": "1.30"},
          "episodic-memory": {"title": "Episodic Memory", "subtitle": "JSONL", "ip": "1.30"}}
    nodes = [{"id": n.get("name","?"), "title": n.get("name","?"), "subtitle": n.get("host",""),
              "mainstat": f"{n.get('latency_ms',0):.0f}ms" if n.get("online") else "OFFLINE",
              "secondarystat": f"{len(n.get('models',[]))} models",
              "arc__online": 1 if n.get("online") else 0, "arc__offline": 0 if n.get("online") else 1} for n in nl]
    for nid, info in vn.items():
        nodes.append({"id": nid, "title": info["title"], "subtitle": info["subtitle"],
            "mainstat": "OK", "secondarystat": info["ip"], "arc__online": 1, "arc__offline": 0})
    edges = [{"id": f"gateway-{n.get('name','?')}", "source": "gateway", "target": n.get("name","?"),
              "mainstat": f"{n.get('latency_ms',0):.0f}ms" if n.get("online") else "OFFLINE", "secondarystat": "RTT"} for n in nl]
    edges += [{"id": "gateway-eb", "source": "gateway", "target": "event-bus", "mainstat": "active", "secondarystat": "stream"},
              {"id": "eb-ep", "source": "event-bus", "target": "episodic-memory", "mainstat": "recording", "secondarystat": "JSONL"}]
    return {"nodes": nodes, "edges": edges}

def get_gpu():
    gpus = []
    for host, name in [("192.168.1.50", "RX9070"), ("192.168.1.60", "RX7900XT")]:
        try:
            r = subprocess.run(["curl", "-s", "--connect-timeout", "3", f"http://{host}:9182/metrics"], capture_output=True, text=True, timeout=5)
            if r.returncode: gpus.append({"node":name,"host":host,"vram_used_gib":0,"vram_total_gib":0}); continue
            m = r.stdout; vt = vu = 0
            for line in m.split("\n"):
                if "windows_gpu_dedicated_video_memory_size_bytes" in line and not line.startswith("#"):
                    vt = int(float(line.split()[-1]))
                if "windows_gpu_adapter_memory_dedicated_bytes" in line and not line.startswith("#"):
                    vu = int(float(line.split()[-1]))
            gpus.append({"node": name, "host": host, "vram_used_gib": round(vu/1073741824,2), "vram_total_gib": round(vt/1073741824,2)})
        except:
            gpus.append({"node": name, "host": host, "vram_used_gib": 0, "vram_total_gib": 0})
    return gpus

def get_docker():
    try:
        r = subprocess.run(["docker","ps","--format","json","--no-trunc"], capture_output=True, text=True, timeout=10)
        lines = [l for l in r.stdout.strip().split("\n") if l]
        return {"containers": [json.loads(l) for l in lines]} if lines else {"containers": []}
    except: return {"containers": []}

def get_analytics_data():
    try:
        from runtime.analytics.runtime_analytics import get_aggregated
        from runtime.analytics.health_score import calculate
        from runtime.analytics.session_metrics import get_session_metrics
        from runtime.analytics.routing_metrics import get_routing_metrics
        from runtime.event_bus import get_stats
        h = calculate() or {"score":0,"level":"unknown","reasons":["error"]}
        return {"health": h, "metrics": get_aggregated(), "sessions": get_session_metrics(),
                "routing": get_routing_metrics(), "event_bus": get_stats(), "timestamp": _time.time()}
    except Exception as e:
        return {"health": {"score": 0, "level": "error", "reasons": [str(e)]}, "error": str(e)}

class APIHandler(BaseHTTPRequestHandler):
    timeout = 10
    def do_GET(self):
        if self.path == "/api/status.json":
            self._json({"docker": get_docker(), "gpu": get_gpu()})
        elif self.path == "/api/topology":
            self._json(get_cluster_topology())
        elif self.path == "/api/analytics":
            self._json(get_analytics_data())
        elif self.path == "/api/events":
            self._sse()
        else: self._send_error(404)
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age","86400")
        self.end_headers()
    def _sse(self):
        self.send_response(200)
        self.send_header("Content-Type","text/event-stream")
        self.send_header("Cache-Control","no-cache")
        self.send_header("Connection","keep-alive")
        self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers()
        self.wfile.write(f"data: {json.dumps({'event':'snapshot','data':{'topology':get_cluster_topology(),'docker':get_docker(),'gpu':get_gpu()}},default=str)}\n\n".encode())
        self.wfile.flush()
        try:
            while True:
                data = {"event": "heartbeat", "data": {"gpu": get_gpu(), "topology": get_cluster_topology(), "ts": _time.time()}}
                self.wfile.write(f"data: {json.dumps(data, default=str)}\n\n".encode())
                self.wfile.flush()
                _time.sleep(3)
        except (BrokenPipeError, ConnectionResetError): pass
    def _json(self, data):
        body = json.dumps(data, indent=2, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def _send_error(self, code, msg="Not Found"):
        self.send_response(code); self.end_headers(); self.wfile.write(json.dumps({"error":msg}).encode())
    def log_message(self, fmt, *args): pass

def run():
    server = ThreadingHTTPServer((HOST, PORT), APIHandler)
    print(f"AI-LAB Live API v3 on :{PORT}")
    server.serve_forever()

if __name__ == "__main__": run()
