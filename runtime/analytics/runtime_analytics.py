"""Runtime Analytics Engine - Reads from gateway state and event bus."""
import time
import sys
from pathlib import Path
from collections import defaultdict

STATE_DIR = Path("/opt/ai-lab/runtime/state")


def _get_gateway_metrics():
    """Read gateway metrics from its /metrics endpoint."""
    import subprocess
    try:
        r = subprocess.run(["curl", "-s", "--max-time", "3", "http://localhost:8008/metrics"], capture_output=True, text=True, timeout=5)
        if r.returncode != 0: return {}
        metrics = {}
        for line in r.stdout.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        metrics[parts[0]] = float(parts[1])
                    except: pass
        return metrics
    except: return {}


def _get_cluster_state():
    f = STATE_DIR / "cluster_state.json"
    if f.exists():
        try: return __import__("json").loads(f.read_text())
        except: pass
    return {}


def get_aggregated():
    metrics = _get_gateway_metrics()
    state = _get_cluster_state()
    
    discovered = state.get("discovered_nodes", [])
    nodes = discovered if discovered else state.get("nodes", [])
    online_nodes = len([n for n in nodes if n.get("online")])
    total_nodes = len(nodes)
    
    # Read gateway metrics
    requests_total = int(metrics.get("ailab_requests_total", 0))
    streams_total = int(metrics.get("ailab_streams_total", 0))
    errors_total = int(metrics.get("ailab_errors_total", 0))
    routing_total = int(metrics.get("ailab_routing_decisions_total", 0))
    sessions_total = int(metrics.get("ailab_sessions_total", 0))
    sessions_concurrent = int(metrics.get("ailab_sessions_concurrent", 0))
    latency_ms = metrics.get("ailab_last_latency_ms", 0)
    active_streams = int(metrics.get("ailab_active_streams", 0))
    
    return {
        "requests_total": requests_total,
        "streams_total": streams_total,
        "errors_total": errors_total,
        "routing_decisions_total": routing_total,
        "sessions_total": sessions_total,
        "active_sessions": sessions_concurrent,
        "last_latency_ms": round(latency_ms, 1),
        "active_streams": active_streams,
        "online_nodes": online_nodes,
        "total_nodes": total_nodes,
        "events_per_minute": 0,
    }
