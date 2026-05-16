#!/usr/bin/env python3
"""AI-LAB Live API v3 - Status, Topology, SSE Events, Analytics."""
import json, subprocess, urllib.parse, uuid
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

def _model_performance():
    try:
        from runtime.routing.model_performance import get_model_performance
        return get_model_performance()
    except ImportError:
        return {"error": "model_performance module not available"}

def _cognitive_snapshot():
    try:
        from runtime.cognitive.cognitive_history import read_history
        from runtime.memory.working_memory import WorkingMemory
        records = read_history(1)
        latest = records[0] if records else {}
        wm_stats = WorkingMemory.stats()
        return {
            "latest_shaping": latest,
            "working_memory": wm_stats,
        }
    except ImportError:
        return {"error": "cognitive module not available"}

def _cognitive_history():
    try:
        from runtime.cognitive.cognitive_history import read_history
        return read_history(20)
    except ImportError:
        return {"error": "cognitive_history module not available"}

def _context_debug():
    try:
        from runtime.cognitive.cognitive_metrics import get_context_debug
        return get_context_debug()
    except ImportError:
        return {"error": "cognitive module not available"}

def _runtime_optimizer():
    try:
        from runtime.autonomous.runtime_optimizer import run_optimizer_cycle
        return run_optimizer_cycle()
    except ImportError:
        return {"error": "autonomous module not available"}

def _runtime_affinity():
    try:
        from runtime.autonomous.session_affinity import snapshot
        return snapshot()
    except ImportError:
        return {"error": "session_affinity not available"}

def _runtime_confidence():
    try:
        from runtime.autonomous.runtime_confidence import get_all_confidences
        return {"models": get_all_confidences()}
    except ImportError:
        return {"error": "runtime_confidence not available"}

def _runtime_adjustments():
    try:
        from runtime.autonomous.optimizer_history import read_optimizer_history
        return read_optimizer_history(20)
    except ImportError:
        return {"error": "optimizer_history not available"}

def _pending_actions():
    try:
        from runtime.autonomous.pending_adjustments import all_pending
        actions = all_pending()
        return {"pending": len(actions), "actions": actions}
    except ImportError:
        return {"error": "pending_adjustments not available"}

def _watchdog():
    try:
        from runtime.watchdog.runtime_watchdog import run_watchdog
        result = run_watchdog()
        try:
            from runtime.memory.watchdog_incident_hook import record_watchdog_incident
            record_watchdog_incident(result)
        except ImportError:
            pass
        return result
    except ImportError:
        return {"status": "error", "checks": {}, "error": "watchdog not available"}

class APIHandler(BaseHTTPRequestHandler):
    timeout = 10
    def do_GET(self):
        if self.path == "/api/status.json":
            self._json({"docker": get_docker(), "gpu": get_gpu()})
        elif self.path == "/api/topology":
            self._json(get_cluster_topology())
        elif self.path == "/api/analytics":
            self._json(get_analytics_data())
        elif self.path == "/api/model-performance":
            self._json(_model_performance())
        elif self.path == "/api/cognitive":
            self._json(_cognitive_snapshot())
        elif self.path == "/api/cognitive/history":
            self._json(_cognitive_history())
        elif self.path == "/api/context-debug":
            self._json(_context_debug())
        elif self.path == "/api/runtime-optimizer":
            self._json(_runtime_optimizer())
        elif self.path == "/api/runtime-affinity":
            self._json(_runtime_affinity())
        elif self.path == "/api/runtime-confidence":
            self._json(_runtime_confidence())
        elif self.path == "/api/runtime-adjustments":
            self._json(_runtime_adjustments())
        elif self.path == "/api/runtime-pending-actions":
            self._json(_pending_actions())
        elif self.path == "/api/watchdog":
            self._json(_watchdog())
        elif self.path == "/api/events":
            self._sse()
        elif self.path.startswith("/api/memory/search"):
            self._handle_memory_search()
        elif self.path.startswith("/api/incidents/search"):
            self._handle_incidents_search()
        elif self.path.startswith("/api/runtime/recall"):
            self._handle_runtime_recall()
        elif self.path == "/api/mode":
            self._handle_get_mode()
        elif self.path == "/api/commands/pending":
            self._handle_pending_commands()
        else: self._send_error(404)
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)
        adj_id = qs.get("id", [None])[0]

        if path == "/api/runtime-actions/approve" and adj_id:
            try:
                from runtime.autonomous.pending_adjustments import approve_adjustment
                result = approve_adjustment(adj_id)
                self._json(result or {"error": "not found"})
            except ImportError:
                self._json({"error": "pending_adjustments not available"})
        elif path == "/api/runtime-actions/reject" and adj_id:
            try:
                from runtime.autonomous.pending_adjustments import reject_adjustment
                result = reject_adjustment(adj_id)
                self._json(result or {"error": "not found"})
            except ImportError:
                self._json({"error": "pending_adjustments not available"})
        elif path == "/api/runtime-actions/apply":
            try:
                from runtime.autonomous.runtime_action_executor import apply_approved
                self._json(apply_approved())
            except ImportError:
                self._json({"error": "runtime_action_executor not available"})
        elif path == "/api/runtime-actions/apply-single" and adj_id:
            try:
                from runtime.autonomous.runtime_action_executor import apply_approved_action
                result = apply_approved_action(adj_id)
                self._json(result or {"error": "not found"})
            except ImportError:
                self._json({"error": "runtime_action_executor not available"})
        elif path == "/api/runtime-actions/rollback":
            try:
                from runtime.autonomous.runtime_action_executor import rollback_last
                self._json(rollback_last())
            except ImportError:
                self._json({"error": "runtime_action_executor not available"})
        elif path == "/api/runtime-actions/history":
            try:
                from runtime.autonomous.pending_adjustments import all_adjustments
                acts = all_adjustments(30)
                self._json({"total": len(acts), "actions": acts})
            except ImportError:
                self._json({"error": "pending_adjustments not available"})
        elif path == "/api/mode/switch":
            self._handle_switch_mode(qs)
        elif path == "/api/commands/propose":
            self._handle_propose_command()
        elif path == "/api/commands/approve" and adj_id:
            self._handle_approve_command(adj_id)
        elif path == "/api/commands/reject" and adj_id:
            self._handle_reject_command(adj_id)
        else:
            self._send_error(404)
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

    # ── Memory Recall handlers (DIA 3) ──────────────────────────────

    def _parse_qs(self) -> dict:
        parsed = urllib.parse.urlparse(self.path)
        return urllib.parse.parse_qs(parsed.query)

    def _handle_memory_search(self):
        try:
            from runtime.memory.qdrant_store import search_collection as _sc
            from runtime.memory.qdrant_collections import COLLECTION_SCHEMAS
            qs = self._parse_qs()
            collection = qs.get("collection", ["routing_history"])[0]
            query = qs.get("q", [""])[0]
            limit = int(qs.get("limit", ["5"])[0])
            valid = set(COLLECTION_SCHEMAS.keys())
            if collection not in valid:
                self._json({"error": f"Invalid collection. Valid: {sorted(valid)}"})
                return
            results = _sc(collection, query, limit=limit) if query else []
            self._json({"collection": collection, "query": query, "results": results, "count": len(results)})
        except ImportError:
            self._json({"error": "qdrant_store not available"})

    def _handle_incidents_search(self):
        try:
            from runtime.memory.qdrant_store import search_collection as _sc
            qs = self._parse_qs()
            query = qs.get("q", [""])[0]
            limit = int(qs.get("limit", ["10"])[0])
            severity = qs.get("severity", [""])[0]
            results = _sc("incidents", query, limit=limit) if query else []
            if severity and results:
                results = [r for r in results if r.get("payload", {}).get("severity") == severity]
            self._json({"collection": "incidents", "query": query, "severity_filter": severity, "results": results, "count": len(results)})
        except ImportError:
            self._json({"error": "qdrant_store not available"})

    def _handle_runtime_recall(self):
        try:
            from runtime.memory.qdrant_store import recall as _recall
            qs = self._parse_qs()
            query = qs.get("q", [""])[0]
            limit = int(qs.get("limit", ["3"])[0])
            results = _recall(query, limit=limit) if query else []
            self._json({"query": query, "results": results, "count": len(results)})
        except ImportError:
            self._json({"error": "qdrant_store not available"})

    # ── Mode handlers (FASE 11.1) ─────────────────────────────────────

    def _handle_get_mode(self):
        try:
            from runtime.modes.mode_manager import read_mode
            self._json(read_mode())
        except ImportError:
            self._json({"mode": "plan", "error": "mode_manager not available"})

    def _handle_switch_mode(self, qs):
        try:
            from runtime.modes.mode_manager import can_transition, requires_reason, write_mode, current_mode
            target = qs.get("mode", [None])[0]
            reason = qs.get("reason", [""])[0]
            if not target or target not in ("readonly", "plan", "build", "execute"):
                self._json({"error": "Invalid mode. Valid: readonly, plan, build, execute"})
                return
            cur = current_mode()
            allowed, msg = can_transition(cur, target)
            if not allowed:
                self._json({"error": msg})
                return
            if requires_reason(cur, target) and not reason:
                self._json({"error": f"Transition {cur}→{target} requires a 'reason' parameter"})
                return
            state = write_mode(target, "api", reason)
            self._json({"success": True, "previous": cur, **state})
        except ImportError:
            self._json({"error": "mode_manager not available"})

    # ── Command proposal handlers (FASE 11.2) ─────────────────────────

    def _handle_pending_commands(self):
        proposals = _load_proposals()
        pending = [p for p in proposals if p.get("status") == "pending"]
        self._json({"total": len(pending), "proposals": pending})

    def _handle_propose_command(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            self._json({"error": "empty body"})
            return
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        command = body.get("command", "").strip()
        reason = body.get("reason", "").strip()
        risk = body.get("risk", "low")
        if not command:
            self._json({"error": "command is required"})
            return
        proposals = _load_proposals()
        proposal = {
            "id": str(uuid.uuid4())[:12],
            "command": command,
            "reason": reason,
            "risk": risk,
            "status": "pending",
            "created_at": int(_time.time()),
            "proposed_by": "llm",
        }
        proposals.append(proposal)
        _save_proposals(proposals)
        _audit("command_proposed", {"command": command, "risk": risk, "reason": reason})
        self._json({"success": True, "proposal": proposal})

    def _handle_approve_command(self, adj_id):
        proposals = _load_proposals()
        found = None
        for p in proposals:
            if p["id"] == adj_id and p.get("status") == "pending":
                found = p
                break
        if not found:
            self._json({"error": "proposal not found or not pending"})
            return
        try:
            from runtime.execution.sandbox_runner import run_safe_command
            from runtime.execution.execute_v1_policy import is_allowed as v1_check
            from runtime.modes.mode_manager import current_mode
            mode = current_mode()
            allowed, reason = v1_check(found["command"])
            if not allowed:
                self._json({"error": f"EXECUTE v1 policy blocked: {reason}", "proposal_id": adj_id})
                return
            result = run_safe_command(mode, found["command"], "pilot")
            found["status"] = "executed"
            found["approved_at"] = int(_time.time())
            found["result"] = {
                "success": result.get("returncode", -1) == 0,
                "exit_code": result.get("returncode"),
                "output": result.get("stdout", "")[:2000],
                "errors": result.get("stderr", "")[:500],
            }
            _save_proposals(proposals)
            _audit("command_approved", {"id": adj_id, "command": found["command"]})
            self._json({"success": True, **found})
        except ImportError:
            self._json({"error": "sandbox_runner not available"})

    def _handle_reject_command(self, adj_id):
        proposals = _load_proposals()
        found = None
        for p in proposals:
            if p["id"] == adj_id and p.get("status") == "pending":
                found = p
                break
        if not found:
            self._json({"error": "proposal not found or not pending"})
            return
        found["status"] = "rejected"
        found["rejected_at"] = int(_time.time())
        _save_proposals(proposals)
        _audit("command_rejected", {"id": adj_id, "command": found["command"]})
        self._json({"success": True, "id": adj_id, "status": "rejected"})

    # ─────────────────────────────────────────────────────────────────

def _proposals_path() -> Path:
    return Path("/opt/ai-lab/runtime/state/command_proposals.jsonl")


def _load_proposals() -> list[dict]:
    p = _proposals_path()
    if not p.exists():
        return []
    proposals = []
    for line in p.read_text().strip().splitlines():
        if line:
            try:
                proposals.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return proposals


def _save_proposals(proposals: list[dict]):
    p = _proposals_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        for prop in proposals:
            f.write(json.dumps(prop, ensure_ascii=False) + "\n")


def _audit(event: str, payload: dict):
    try:
        from runtime.audit.audit_logger import audit_event
        audit_event(event, payload)
    except ImportError:
        pass
    try:
        from runtime.memory.qdrant_store import store_embedding
        store_embedding("incidents", {
            "event_type": event,
            "severity": "info",
            "message": payload.get("command", payload.get("reason", event)),
            "timestamp": int(_time.time()),
            "schema_version": "1.0",
            "source": "command_pipeline",
        })
    except ImportError:
        pass


def run():
    server = ThreadingHTTPServer((HOST, PORT), APIHandler)
    print(f"AI-LAB Live API v3 on :{PORT}")
    server.serve_forever()

if __name__ == "__main__": run()
