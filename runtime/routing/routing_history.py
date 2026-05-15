"""Routing History — persistent JSONL record of every inference request.

Each completed (or failed) inference writes one line to the JSONL file.
This feeds model_performance.py and adaptive_scoring.py.

File: /opt/ai-lab/runtime/state/routing_history.jsonl
"""

import json, time
from pathlib import Path
from collections import defaultdict
from threading import Lock

HISTORY_FILE = Path("/opt/ai-lab/runtime/state/routing_history.jsonl")
_lock = Lock()

# ── in-memory cache (recent window only, for fast reads) ──────────────
_memory_cache = []
_MAX_CACHE = 500


def record_route_result(
    task_type: str = "general",
    model: str = "",
    node: str = "",
    host: str = "",
    latency_ms: float = 0.0,
    success: bool = True,
    stream: bool = False,
    failover: bool = False,
    error: str | None = None,
    context_size: int = 0,
    working_memory_used: bool = False,
    tokens_estimated: int = 0,
    gpu_load: int = 0,
):
    """Append one route record to the JSONL file."""
    record = {
        "timestamp": int(time.time()),
        "task_type": task_type,
        "model": model,
        "node": node,
        "host": host,
        "latency_ms": round(latency_ms, 1),
        "success": success,
        "stream": stream,
        "failover": failover,
        "error": error,
        "context_size": context_size,
        "working_memory_used": working_memory_used,
        "tokens_estimated": tokens_estimated,
        "gpu_load": gpu_load,
    }

    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass

    with _lock:
        _memory_cache.append(record)
        while len(_memory_cache) > _MAX_CACHE:
            _memory_cache.pop(0)


def read_route_history(limit: int = 500, from_disk: bool = False):
    """Return the last *limit* route records (newest first)."""
    if not from_disk:
        with _lock:
            recent = list(_memory_cache[-limit:])
        if recent:
            recent.reverse()
            return recent

    # fallback to disk
    if not HISTORY_FILE.exists():
        return []
    lines = HISTORY_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    records = []
    for line in reversed(lines[-limit * 3 :]):  # read a bit extra
        try:
            r = json.loads(line)
            records.append(r)
            if len(records) >= limit:
                break
        except json.JSONDecodeError:
            continue
    return records


def stats_by_model(task_type=None, window_minutes=60, stream_only=False):
    """Aggregated stats per model for the given task_type and time window."""
    records = read_route_history(500)
    cutoff = int(time.time()) - window_minutes * 60

    groups: dict[str, list] = defaultdict(list)
    for r in records:
        if r["timestamp"] < cutoff:
            continue
        if task_type and r["task_type"] != task_type:
            continue
        if stream_only and not r["stream"]:
            continue
        groups[r["model"]].append(r)

    result = {}
    for model, items in groups.items():
        streaming = [r for r in items if r["stream"]]
        non_streaming = [r for r in items if not r["stream"]]
        s_ok = [r for r in items if r["success"]]
        s_fail = [r for r in items if not r["success"]]

        result[model] = {
            "total_requests": len(items),
            "streaming": _aggregate(streaming),
            "non_streaming": _aggregate(non_streaming),
            "success_rate": round(len(s_ok) / len(items), 3) if items else 0,
            "failover_rate": round(sum(1 for r in items if r["failover"]) / len(items), 3) if items else 0,
            "avg_gpu_load": round(sum(r.get("gpu_load", 0) for r in items) / len(items), 1) if items else 0,
            "last_updated": max(r["timestamp"] for r in items) if items else 0,
        }
    return result


def stats_by_node(task_type=None, window_minutes=60):
    """Aggregated stats per node."""
    records = read_route_history(500)
    cutoff = int(time.time()) - window_minutes * 60

    groups: dict[str, list] = defaultdict(list)
    for r in records:
        if r["timestamp"] < cutoff:
            continue
        if task_type and r["task_type"] != task_type:
            continue
        groups[r["node"]].append(r)

    result = {}
    for node, items in groups.items():
        s_ok = [r for r in items if r["success"]]
        result[node] = {
            "total_requests": len(items),
            "success_rate": round(len(s_ok) / len(items), 3) if items else 0,
            "avg_latency_ms": round(sum(r["latency_ms"] for r in items) / len(items), 1) if items else 0,
            "avg_gpu_load": round(sum(r.get("gpu_load", 0) for r in items) / len(items), 1) if items else 0,
            "last_updated": max(r["timestamp"] for r in items) if items else 0,
        }
    return result


def _aggregate(recs):
    if not recs:
        return {"count": 0, "avg_latency_ms": 0, "success_rate": 0}
    ok = [r for r in recs if r["success"]]
    return {
        "count": len(recs),
        "avg_latency_ms": round(sum(r["latency_ms"] for r in recs) / len(recs), 1),
        "success_rate": round(len(ok) / len(recs), 3),
    }
