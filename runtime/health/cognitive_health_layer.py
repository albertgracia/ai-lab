"""COGNITIVE-HEALTH-LAYER-01 (FASE 37A)

Bounded, deterministic, metadata-only health layer.

Rules:
- Read-only over runtime state (may read files under /opt/ai-lab/runtime/state).
- No routing behavior changes (observability only).
- Fail-safe: every public function must return a valid payload.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Any


COGNITIVE_HEALTH_CONTRACT_VERSION = "37A-COGNITIVE-HEALTH-LAYER-01"


_WD_LOCK = Lock()
_WATCHDOG_TRIGGER_TOTAL = 0
_LAST_WATCHDOG_TS = 0.0


def _now() -> float:
    return time.time()


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _score_latency(avg_latency_ms: float) -> tuple[float, str]:
    if avg_latency_ms <= 1000:
        return 0.20, "latency_excellent"
    if avg_latency_ms <= 5000:
        return 0.12, "latency_good"
    if avg_latency_ms <= 15000:
        return 0.05, "latency_ok"
    if avg_latency_ms <= 30000:
        return 0.00, "latency_high"
    return -0.20, "latency_very_high"


@dataclass
class NodeHealth:
    node: str
    online: bool
    score: float
    reasons: list[str]
    stats: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "node": self.node,
            "online": self.online,
            "score": round(self.score, 3),
            "reasons": list(self.reasons),
            "stats": self.stats,
        }


def build_node_scores(*, window_minutes: int = 60) -> list[NodeHealth]:
    """Compute per-node health scores (0.0-1.0).

    Uses:
    - control_plane node list (online/models/avg_latency_ms)
    - routing_history stats_by_node (success_rate/avg_latency_ms)
    """
    try:
        from runtime.control.control_plane import get_control_nodes
        ctrl = get_control_nodes() or {}
        nodes = (ctrl.get("nodes") or {}) if isinstance(ctrl, dict) else {}
    except Exception:
        nodes = {}

    try:
        from runtime.routing.routing_history import stats_by_node
        hist = stats_by_node(window_minutes=window_minutes) or {}
    except Exception:
        hist = {}

    results: list[NodeHealth] = []
    for node_name in sorted(nodes.keys()):
        n = nodes.get(node_name) or {}
        online = bool(n.get("online"))
        reasons: list[str] = []

        score = 0.50
        if online:
            score += 0.20
            reasons.append("node_online")
        else:
            score -= 0.40
            reasons.append("node_offline")

        # Prefer routing_history latency if available.
        h = hist.get(node_name) or {}
        succ = h.get("success_rate")
        if isinstance(succ, (int, float)):
            # centered around 0.5 to be neutral when unknown.
            score += (float(succ) - 0.5) * 0.60
            if succ < 0.9:
                reasons.append("success_rate_low")
            else:
                reasons.append("success_rate_ok")

        avg_lat = h.get("avg_latency_ms")
        if not isinstance(avg_lat, (int, float)):
            avg_lat = n.get("avg_latency_ms")
        if isinstance(avg_lat, (int, float)) and avg_lat:
            delta, lat_reason = _score_latency(float(avg_lat))
            score += delta
            reasons.append(lat_reason)

        score = _clamp01(score)
        stats = {
            "models": int(n.get("models", 0) or 0),
            "avg_latency_ms": float(avg_lat or 0),
            "success_rate": float(succ) if isinstance(succ, (int, float)) else None,
            "total_requests": int((h.get("total_requests") or 0) if isinstance(h, dict) else 0),
            "last_updated": int((h.get("last_updated") or 0) if isinstance(h, dict) else 0),
        }
        results.append(NodeHealth(node=node_name, online=online, score=score, reasons=reasons, stats=stats))

    # Include nodes that only appear in routing history.
    for node_name in sorted(set(hist.keys()) - set(nodes.keys())):
        h = hist.get(node_name) or {}
        succ = h.get("success_rate", None)
        avg_lat = h.get("avg_latency_ms", 0)
        score = 0.50
        reasons = ["node_unknown_in_control_plane"]
        if isinstance(succ, (int, float)):
            score += (float(succ) - 0.5) * 0.60
        if isinstance(avg_lat, (int, float)) and avg_lat:
            delta, lat_reason = _score_latency(float(avg_lat))
            score += delta
            reasons.append(lat_reason)
        score = _clamp01(score)
        results.append(NodeHealth(node=node_name, online=False, score=score, reasons=reasons, stats=dict(h)))

    return results


def build_routing_confidence(node_scores: list[NodeHealth]) -> dict[str, Any]:
    """Return a bounded routing confidence snapshot (0.0-1.0)."""
    online = [n for n in node_scores if n.online]
    nodes_online = len(online)
    if nodes_online <= 0:
        return {"confidence": 0.0, "nodes_online": 0, "reasons": ["no_nodes_online"]}

    avg = sum(n.score for n in online) / nodes_online
    conf = 0.50 + (avg - 0.5) * 0.60
    reasons = ["avg_node_score"]

    if nodes_online >= 2:
        conf += 0.15
        reasons.append("redundancy_ok")
    else:
        conf -= 0.10
        reasons.append("single_node")

    return {
        "confidence": round(_clamp01(conf), 3),
        "nodes_online": nodes_online,
        "avg_node_score": round(float(avg), 3),
        "reasons": reasons,
    }


def _overall_success_rate(*, window_minutes: int = 60) -> float | None:
    try:
        from runtime.routing.routing_history import read_route_history

        recs = read_route_history(500)
    except Exception:
        return None
    if not recs:
        return None
    cutoff = int(time.time()) - window_minutes * 60
    items = [r for r in recs if int(r.get("timestamp", 0) or 0) >= cutoff]
    if not items:
        return None
    ok = [r for r in items if r.get("success") is True]
    return float(len(ok) / len(items)) if items else None


def build_watchdog_snapshot(
    *,
    node_scores: list[NodeHealth],
    window_minutes: int = 60,
) -> dict[str, Any]:
    """Watchdog that emits metadata-only triggers.

    No remediation. Only classification.
    """
    global _WATCHDOG_TRIGGER_TOTAL, _LAST_WATCHDOG_TS

    triggers: list[dict[str, Any]] = []
    online = [n for n in node_scores if n.online]
    nodes_online = len(online)

    if nodes_online == 0:
        triggers.append({"id": "no_nodes_online", "severity": "critical"})

    # Latency from bounded in-memory store.
    try:
        from runtime.telemetry.gateway_metrics import get_latency_stats

        total = get_latency_stats(kind="request_total")
        ttfb = get_latency_stats(kind="ttfb")
    except Exception:
        total = {"count": 0, "p95_ms": 0.0}
        ttfb = {"count": 0, "p95_ms": 0.0}

    if float(total.get("p95_ms", 0) or 0) >= 60000 and int(total.get("count", 0) or 0) >= 10:
        triggers.append({"id": "latency_p95_high", "severity": "warning", "p95_ms": total.get("p95_ms")})

    if float(ttfb.get("p95_ms", 0) or 0) >= 15000 and int(ttfb.get("count", 0) or 0) >= 10:
        triggers.append({"id": "ttfb_p95_high", "severity": "warning", "p95_ms": ttfb.get("p95_ms")})

    succ = _overall_success_rate(window_minutes=window_minutes)
    if isinstance(succ, float) and succ < 0.90:
        triggers.append({"id": "success_rate_low", "severity": "warning", "success_rate": round(succ, 3)})

    # Update counters (bounded, in-memory)
    with _WD_LOCK:
        if triggers:
            _WATCHDOG_TRIGGER_TOTAL += len(triggers)
            _LAST_WATCHDOG_TS = _now()

    return {
        "watchdog": "enabled",
        "triggers": triggers,
        "triggers_total": int(_WATCHDOG_TRIGGER_TOTAL),
        "last_trigger_ts": float(_LAST_WATCHDOG_TS) if _LAST_WATCHDOG_TS else None,
    }


def build_cognitive_health_snapshot(*, window_minutes: int = 60) -> dict[str, Any]:
    """Top-level health snapshot for /runtime/health.* endpoints."""
    try:
        unavailable_fields: list[str] = []
        unknowns: list[str] = []

        try:
            nodes = build_node_scores(window_minutes=window_minutes)
        except Exception:
            nodes = []
            unavailable_fields.append("nodes")

        try:
            conf = build_routing_confidence(nodes)
        except Exception:
            conf = {"confidence": 0.0, "nodes_online": 0, "reasons": ["routing_confidence_unavailable"]}
            unavailable_fields.append("routing_confidence")

        try:
            wd = build_watchdog_snapshot(node_scores=nodes, window_minutes=window_minutes)
        except Exception:
            wd = {"watchdog": "degraded", "triggers": [], "triggers_total": 0}
            unavailable_fields.append("watchdog")

        online = [n for n in nodes if n.online]
        nodes_online = len(online)
        avg_score = (sum(n.score for n in online) / nodes_online) if nodes_online else 0.0

        # Overall score (0-100) is an operational metadata score.
        overall = 100.0 * (0.60 * avg_score + 0.40 * float(conf.get("confidence", 0.0) or 0.0))
        overall = max(0.0, min(100.0, overall))

        watchdog_state = "enabled" if wd.get("watchdog") == "enabled" else "degraded"

        overall_health = {
            "score": round(float(overall), 1),
            "status": "healthy" if overall >= 80 else "warning" if overall >= 60 else "degraded" if overall >= 40 else "critical",
        }

        # Include a GPU summary derived from sensor_fusion if available.
        gpu_states: dict[str, str] = {"rx9070": "unknown", "rx7900xt": "unknown"}
        try:
            from runtime.context.sensor_fusion import SensorFusionEngine
            snap = SensorFusionEngine().collect().to_dict(max_chars=16000)
            gpus = snap.get("gpu_operational_summaries", []) or []
            for g in gpus:
                if not isinstance(g, dict):
                    continue
                gid = str(g.get("gpu_id", "")).lower()
                st = str(g.get("operational_state", g.get("observed_state", "unknown")) or "unknown").lower()
                if "rx9070" in gid:
                    gpu_states["rx9070"] = st
                if "rx7900" in gid:
                    # Keep it explicit: expected_offline/down/unknown are valid; never map to healthy.
                    gpu_states["rx7900xt"] = st
        except Exception:
            unavailable_fields.append("gpu_states")

        # Unknowns: anything we could not resolve deterministically.
        if gpu_states.get("rx9070") == "unknown":
            unknowns.append("rx9070_state_unknown")
        if gpu_states.get("rx7900xt") == "unknown":
            unknowns.append("rx7900xt_state_unknown")

        return {
            "status": "ok",
            "service": "ai-lab-openai-gateway",
            "endpoint": "runtime/health",
            "timestamp": _now(),
            "contract_version": COGNITIVE_HEALTH_CONTRACT_VERSION,
            "overall_health": overall_health,
            "score": overall_health["score"],
            "routing_confidence": conf,
            "nodes": [n.to_dict() for n in nodes],
            "nodes_total": len(nodes),
            "nodes_online": nodes_online,
            "watchdog": wd,
            "watchdog_state": watchdog_state,
            "gpu_states": gpu_states,
            "unavailable_fields": sorted(set(unavailable_fields)),
            "unknowns": sorted(set(unknowns)),
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": "runtime/health",
            "timestamp": _now(),
            "contract_version": COGNITIVE_HEALTH_CONTRACT_VERSION,
            "overall_health": {"score": 0.0, "status": "critical"},
            "score": 0.0,
            "routing_confidence": {"confidence": 0.0, "nodes_online": 0, "reasons": ["health_unavailable"]},
            "nodes": [],
            "nodes_total": 0,
            "nodes_online": 0,
            "watchdog": {"watchdog": "degraded", "triggers": [], "triggers_total": 0, "error": str(exc)},
            "watchdog_state": "degraded",
            "gpu_states": {"rx9070": "unknown", "rx7900xt": "unknown"},
            "unavailable_fields": ["health_snapshot"],
            "unknowns": ["health_unavailable"],
            "error": str(exc),
        }


def build_degradations_snapshot(*, window_minutes: int = 60) -> dict[str, Any]:
    """Bounded degradations view for /runtime/health/degradations.

    Deterministic ordering, fail-safe, no stacktrace.
    """
    try:
        snap = build_cognitive_health_snapshot(window_minutes=window_minutes)
        nodes = snap.get("nodes", []) if isinstance(snap, dict) else []
        watchdog = snap.get("watchdog", {}) if isinstance(snap, dict) else {}
        unavailable_fields = snap.get("unavailable_fields", []) if isinstance(snap, dict) else []
        unknowns = snap.get("unknowns", []) if isinstance(snap, dict) else []

        offline_nodes: list[dict[str, Any]] = []
        degraded_nodes: list[dict[str, Any]] = []
        for n in nodes:
            if not isinstance(n, dict):
                continue
            name = str(n.get("node", "unknown"))
            online = bool(n.get("online"))
            score = float(n.get("score", 0) or 0)
            entry = {"node": name, "online": online, "score": round(score, 3), "reasons": n.get("reasons", [])}
            if not online:
                offline_nodes.append(entry)
            elif score < 0.60:
                degraded_nodes.append(entry)

        offline_nodes.sort(key=lambda x: x.get("node", ""))
        degraded_nodes.sort(key=lambda x: (x.get("score", 0), x.get("node", "")))

        triggers = watchdog.get("triggers", []) if isinstance(watchdog, dict) else []
        if not isinstance(triggers, list):
            triggers = []

        degradations: list[dict[str, Any]] = []
        if offline_nodes:
            degradations.append({"id": "offline_nodes", "severity": "critical", "count": len(offline_nodes)})
        if degraded_nodes:
            degradations.append({"id": "degraded_nodes", "severity": "warning", "count": len(degraded_nodes)})
        if triggers:
            # summarize severities deterministically
            sev = sorted({str(t.get("severity", "warning")) for t in triggers if isinstance(t, dict)})
            degradations.append({"id": "watchdog_triggers", "severity": "warning" if "critical" not in sev else "critical", "count": len(triggers)})

        return {
            "status": snap.get("status", "ok"),
            "service": "ai-lab-openai-gateway",
            "endpoint": "runtime/health/degradations",
            "timestamp": _now(),
            "contract_version": COGNITIVE_HEALTH_CONTRACT_VERSION,
            "degradations": degradations,
            "offline_nodes": offline_nodes[:20],
            "degraded_nodes": degraded_nodes[:20],
            "watchdog_triggers": triggers[:20],
            "unavailable_fields": list(unavailable_fields)[:50] if isinstance(unavailable_fields, list) else [],
            "unknowns": list(unknowns)[:50] if isinstance(unknowns, list) else [],
            "fallback_status": "degraded" if snap.get("status") != "ok" else "ok",
        }
    except Exception:
        return {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": "runtime/health/degradations",
            "timestamp": _now(),
            "contract_version": COGNITIVE_HEALTH_CONTRACT_VERSION,
            "degradations": [{"id": "health_unavailable", "severity": "critical", "count": 1}],
            "offline_nodes": [],
            "degraded_nodes": [],
            "watchdog_triggers": [],
            "unavailable_fields": ["health_degradations"],
            "unknowns": ["health_unavailable"],
            "fallback_status": "degraded",
        }


def build_cognitive_health_prometheus_metrics() -> str:
    """Render cognitive health metrics as Prometheus text.

    Fail-safe: returns zeros on any error.
    """
    try:
        snap = build_cognitive_health_snapshot(window_minutes=60)
        score = float(snap.get("score", 0) or 0)
        conf = float((snap.get("routing_confidence") or {}).get("confidence", 0) or 0)
        nodes_online = float(snap.get("nodes_online", 0) or 0)
        wd = snap.get("watchdog") or {}
        trig_total = float(wd.get("triggers_total", 0) or 0)

        try:
            from runtime.telemetry.gateway_metrics import get_latency_stats

            total = get_latency_stats(kind="request_total")
            ttfb = get_latency_stats(kind="ttfb")
        except Exception:
            total = {"p50_ms": 0.0, "p95_ms": 0.0}
            ttfb = {"p50_ms": 0.0, "p95_ms": 0.0}

        return (
            f"ailab_cognitive_health_score {score}\n"
            f"ailab_cognitive_health_routing_confidence {conf}\n"
            f"ailab_cognitive_health_nodes_online {nodes_online}\n"
            f"ailab_cognitive_health_watchdog_triggers_total {trig_total}\n"
            f"ailab_gateway_latency_p50_ms{{kind=\"request_total\"}} {float(total.get('p50_ms', 0) or 0)}\n"
            f"ailab_gateway_latency_p95_ms{{kind=\"request_total\"}} {float(total.get('p95_ms', 0) or 0)}\n"
            f"ailab_gateway_latency_p50_ms{{kind=\"ttfb\"}} {float(ttfb.get('p50_ms', 0) or 0)}\n"
            f"ailab_gateway_latency_p95_ms{{kind=\"ttfb\"}} {float(ttfb.get('p95_ms', 0) or 0)}\n"
        )
    except Exception:
        return (
            "ailab_cognitive_health_score 0\n"
            "ailab_cognitive_health_routing_confidence 0\n"
            "ailab_cognitive_health_nodes_online 0\n"
            "ailab_cognitive_health_watchdog_triggers_total 0\n"
            "ailab_gateway_latency_p50_ms{kind=\"request_total\"} 0\n"
            "ailab_gateway_latency_p95_ms{kind=\"request_total\"} 0\n"
            "ailab_gateway_latency_p50_ms{kind=\"ttfb\"} 0\n"
            "ailab_gateway_latency_p95_ms{kind=\"ttfb\"} 0\n"
        )
