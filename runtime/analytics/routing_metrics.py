"""Routing Metrics - Tracks routing decisions and model selection patterns."""
import time
from collections import defaultdict
from threading import Lock

_lock = Lock()
_routes_by_task = defaultdict(int)
_failovers = 0
_last_routes = []


def record_route(task: str, model: str, node: str, latency_ms: float = 0):
    with _lock:
        _routes_by_task[task] += 1
        _last_routes.append({
            "ts": time.strftime("%H:%M:%S"), "task": task,
            "model": model, "node": node, "latency_ms": round(latency_ms, 1)
        })
        if len(_last_routes) > 50:
            _last_routes.pop(0)


def record_failover():
    global _failovers
    with _lock:
        _failovers += 1


def get_routing_metrics():
    with _lock:
        total = sum(_routes_by_task.values())
        return {
            "total_routes": total,
            "failovers": _failovers,
            "routes_by_task": dict(_routes_by_task),
            "recent_routes": list(_last_routes[-20:]),
        }
