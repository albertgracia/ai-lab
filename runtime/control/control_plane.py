"""Control Plane — centralized operational state aggregation.

Reads from existing runtime modules (routing_history, cluster_state,
mode_manager, health_score, Qdrant) and exposes consolidated views
without duplicating logic.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_STATE_DIR = Path("/opt/ai-lab/runtime/state")


def get_control_runtime() -> dict[str, Any]:
    """Ultra-compact status for status bars, CLI checks, mobile."""
    try:
        from runtime.modes.mode_manager import current_mode
        mode = current_mode()
    except Exception:
        mode = "plan"

    try:
        from runtime.analytics.health_score import calculate
        health = calculate()
    except Exception:
        health = {"score": 0, "level": "unknown"}

    nodes_online = 0
    try:
        cluster = _read_json(_STATE_DIR / "cluster_state.json")
        discovered = cluster.get("discovered_nodes", [])
        nodes_online = len([n for n in discovered if n.get("online")])
    except Exception:
        pass

    router_latency_ms = 0
    try:
        from runtime.routing.routing_history import read_route_history
        last = read_route_history(1)
        if last:
            router_latency_ms = last[0].get("latency_ms", 0)
    except Exception:
        pass

    return {
        "mode": mode,
        "health": health.get("level", "unknown"),
        "health_score": health.get("score", 0),
        "nodes_online": nodes_online,
        "router_latency_ms": router_latency_ms,
        "tool_fastpath": True,
        "governance": get_governance_state(),
    }


def get_control_status() -> dict[str, Any]:
    """Full operational status."""
    from datetime import datetime

    base = dict(get_control_runtime())

    uptime_hours = 0.0
    try:
        with open("/proc/uptime") as f:
            uptime_hours = round(float(f.read().split()[0]) / 3600, 1)
    except Exception:
        try:
            boot = _read_json(_STATE_DIR / "system_snapshot.json")
            if boot and boot.get("boot_time"):
                delta = time.time() - boot["boot_time"]
                uptime_hours = round(delta / 3600, 1)
        except Exception:
            pass

    nodes_offline = 0
    try:
        cluster = _read_json(_STATE_DIR / "cluster_state.json")
        discovered = cluster.get("discovered_nodes", [])
        nodes_offline = len([n for n in discovered if not n.get("online")])
    except Exception:
        pass

    semantic_recall = True
    qdrant = "unknown"
    try:
        from runtime.memory.qdrant_store import ensure_collections, QDRANT_HOST
        if QDRANT_HOST:
            qdrant = "healthy"
        else:
            qdrant = "degraded"
    except Exception:
        qdrant = "unreachable"

    base.update({
        "uptime_hours": uptime_hours,
        "nodes_online": base.get("nodes_online", 0),
        "nodes_offline": nodes_offline,
        "tool_fastpath": True,
        "semantic_recall": semantic_recall,
        "qdrant": qdrant,
    })
    return base


def get_control_nodes() -> dict[str, Any]:
    """Consolidated node status."""
    try:
        cluster = _read_json(_STATE_DIR / "cluster_state.json")
        discovered = cluster.get("discovered_nodes") or cluster.get("nodes") or []
    except Exception:
        discovered = []

    nodes: dict[str, dict[str, Any]] = {}
    for n in discovered:
        name = n.get("name") or n.get("host") or "unknown"
        online = n.get("online", n.get("status") == "online")
        models = n.get("models", [])
        nodes[name] = {
            "online": bool(online),
            "host": n.get("host", ""),
            "models": len(models) if isinstance(models, list) else 0,
            "avg_latency_ms": n.get("latency_ms", 0),
            "tool_use": any(
                (isinstance(m, dict) and (
                    m.get("tool_use") or "tool_use" in str(m.get("capabilities", ""))
                ))
                for m in (models if isinstance(models, list) else [])
            ),
        }
    return {"nodes": nodes, "count": len(nodes)}


def get_control_routes(limit: int = 10) -> list[dict[str, Any]]:
    """Last routing decisions from history."""
    try:
        from runtime.routing.routing_history import read_route_history
        history = read_route_history(limit)
        routes: list[dict[str, Any]] = []
        for h in history:
            routes.append({
                "selected_model": h.get("model"),
                "node": h.get("node"),
                "task_type": h.get("task_type"),
                "latency_ms": h.get("latency_ms"),
                "success": h.get("success"),
                "failover": h.get("failover"),
                "reason_codes": h.get("reason_codes", []),
            })
        return routes
    except Exception:
        return []


def get_control_policies() -> dict[str, Any]:
    """Active policies."""
    return {
        "execute_policy": "v1",
        "observe_policy": "readonly",
        "tool_fastpath": True,
        "governance_state": get_governance_state(),
    }


def explain_last_route() -> dict[str, Any]:
    """Explain why the last routing decision was made."""
    try:
        from runtime.routing.routing_history import read_route_history
        history = read_route_history(1)
        if not history:
            return {"error": "no routing history yet"}
        last = history[0]
        return {
            "selected_model": last.get("model"),
            "node": last.get("node"),
            "task_type": last.get("task_type"),
            "reason_codes": last.get("reason_codes", []),
            "failover": last.get("failover", False),
            "fallback_triggered": bool(last.get("failover")),
        }
    except Exception:
        return {"error": "routing history unavailable"}


def get_governance_state() -> str:
    """NORMAL | ELEVATED | DEGRADED | LOCKDOWN based on runtime metrics."""
    blocked_1h = 0
    fallback_rate = 0.0
    parser_failures = 0
    qdrant_ok = True

    try:
        from runtime.routing.routing_history import stats_by_model
        stats = stats_by_model()
        total = sum(s.get("total", 0) for s in stats.values())
        fails = sum(s.get("failover_count", 0) for s in stats.values())
        if total > 0:
            fallback_rate = fails / total
    except Exception:
        pass

    try:
        from runtime.gateway.openai_gateway import (
            BLOCKED_PROMPTS,
            PARSER_FAILURES as _PARSER_FAILURES,
        )
        blocked_1h = BLOCKED_PROMPTS
        parser_failures = _PARSER_FAILURES or 0
    except Exception:
        pass

    try:
        from runtime.memory.qdrant_store import QDRANT_HOST
        if not QDRANT_HOST:
            qdrant_ok = False
    except Exception:
        pass

    if blocked_1h > 5 and fallback_rate > 0.3 and not qdrant_ok:
        return "LOCKDOWN"
    if blocked_1h > 5 or fallback_rate > 0.3:
        return "ELEVATED"
    if parser_failures > 5 or not qdrant_ok:
        return "DEGRADED"
    return "NORMAL"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}
