"""FASE 37D: GRAPH-HOTSPOT-HISTORY-01

Bounded, deterministic, metadata-only hotspot history for AI-LAB.

Goals:
- Keep a small in-memory time series of critical-path / chokepoint snapshots.
- Provide trends (latest vs previous), recurrence and a deterministic drift_score.

Non-goals:
- No routing mutation, no remediation, no background loops/daemons.
- No writes to runtime/state/* or snapshots/*.
- No unbounded persistence. (Persistence is disabled by default.)
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from typing import Any


GRAPH_HOTSPOT_HISTORY_CONTRACT_VERSION = "37D-GRAPH-HOTSPOT-HISTORY-01"

_LOCK = Lock()
_SNAPSHOTS: deque[dict[str, Any]] = deque(maxlen=256)

_MAX_MODULES_PER_SNAPSHOT = 25
_MAX_RECOMMENDATIONS_PER_SNAPSHOT = 20


def _now() -> float:
    return time.time()


def _clamp01(x: float) -> float:
    try:
        v = float(x)
    except Exception:
        v = 0.0
    return max(0.0, min(1.0, v))


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return int(default)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _severity_from_score(score: float) -> str:
    s = float(score)
    if s < 0.25:
        return "INFO"
    if s < 0.50:
        return "LOW"
    if s < 0.70:
        return "MEDIUM"
    if s < 0.85:
        return "HIGH"
    return "CRITICAL"


def _trend_from_delta(delta: float, *, eps: float = 0.01) -> str:
    if delta > eps:
        return "increasing"
    if delta < -eps:
        return "decreasing"
    return "stable"


def _parse_limit(q: Any, default: int, *, lo: int, hi: int) -> int:
    try:
        v = int(q)
    except Exception:
        v = int(default)
    return int(max(lo, min(hi, v)))


def _read_dependencies_snapshot(*, top_n: int) -> tuple[dict[str, Any], list[str], list[str]]:
    """Read inputs from 37A/37B/37C + SLO/Triage/Graph.

    Returns (bundle, unknowns, unavailable_fields).
    """

    unknowns: list[str] = []
    unavailable_fields: list[str] = []

    # 37C: critical-path
    try:
        from runtime.critical_path.critical_path_analysis import (
            build_critical_path_snapshot,
            get_critical_path_chokepoints,
            get_critical_path_blast_radius,
        )
        cp = build_critical_path_snapshot(top_n=top_n)
        chokepoints = get_critical_path_chokepoints(top_n=top_n)
        blast = get_critical_path_blast_radius(top_n=top_n)
    except Exception:
        cp = {"status": "degraded", "score": 0.0, "severity": "INFO", "top_files": [], "unknowns": ["critical_path_unavailable"], "unavailable_fields": ["critical_path_unavailable"]}
        chokepoints = {"status": "degraded", "chokepoints": [], "unknowns": ["critical_path_chokepoints_unavailable"]}
        blast = {"status": "degraded", "blast_radius_summary": {}, "unknowns": ["critical_path_blast_radius_unavailable"]}
        unknowns.append("critical_path_unavailable")

    # 37B: correlation summary
    try:
        from runtime.correlation.graph_runtime_correlation import get_graph_runtime_correlation_summary
        corr = get_graph_runtime_correlation_summary()
    except Exception:
        corr = {"status": "degraded", "correlation_score": 0.0, "unknowns": ["correlation_unavailable"], "unavailable_fields": ["correlation_unavailable"]}
        unknowns.append("correlation_unavailable")

    # 37A: health snapshot
    try:
        from runtime.health.cognitive_health_layer import build_cognitive_health_snapshot
        health = build_cognitive_health_snapshot(window_minutes=60)
    except Exception:
        health = {"status": "degraded", "score": 0.0, "routing_confidence": {"confidence": 0.0}, "unknowns": ["cognitive_health_unavailable"], "unavailable_fields": ["cognitive_health_unavailable"]}
        unknowns.append("cognitive_health_unavailable")

    # SLO
    try:
        from runtime.slo.cognitive_slo import get_slo_status
        slo = get_slo_status() or {}
    except Exception:
        slo = {"overall_status": "unknown", "violations_total": 0}
        unknowns.append("slo_status_unavailable")

    # triage
    try:
        from runtime.triage.autonomous_triage import get_triage_summary
        triage = get_triage_summary() or {}
    except Exception:
        triage = {"total_incidents": 0, "total_critical": 0, "total_high": 0}
        unknowns.append("triage_summary_unavailable")

    # graph snapshot summary
    try:
        from runtime.graph_reasoning.gitnexus_graph_reasoning import get_graph_reasoning_summary
        graph = get_graph_reasoning_summary() or {}
    except Exception:
        graph = {"contract_version": "unknown", "unknowns": ["graph_summary_unavailable"]}
        unknowns.append("graph_summary_unavailable")

    # federation guard summary is best-effort (avoid pulling runtime/state).
    guard_state = "unknown"
    try:
        # Prefer the existing summary path used by 37B.
        from runtime.correlation.graph_runtime_correlation import _read_guard_summary  # type: ignore
        g = _read_guard_summary() or {}
        if isinstance(g, dict):
            st = g.get("state")
            if isinstance(st, dict):
                guard_state = str(st.get("state") or "unknown")
            else:
                guard_state = str(st or "unknown")
    except Exception:
        unknowns.append("guard_summary_unavailable")

    # propagate unknowns/unavailable from CP + correlation + health
    unknowns.extend([str(x) for x in (cp.get("unknowns") or []) if x])
    unknowns.extend([str(x) for x in (corr.get("unknowns") or []) if x])
    unknowns.extend([str(x) for x in (health.get("unknowns") or []) if x])
    unavailable_fields.extend([str(x) for x in (cp.get("unavailable_fields") or []) if x])
    unavailable_fields.extend([str(x) for x in (corr.get("unavailable_fields") or []) if x])
    unavailable_fields.extend([str(x) for x in (health.get("unavailable_fields") or []) if x])

    bundle = {
        "critical_path": cp,
        "chokepoints": chokepoints,
        "blast_radius": blast,
        "correlation": corr,
        "health": health,
        "slo": slo,
        "triage": triage,
        "graph": graph,
        "guard_state": guard_state,
    }
    return bundle, sorted(set(unknowns)), sorted(set(unavailable_fields))


def _extract_module_key(d: dict[str, Any]) -> str:
    # Normalize to file_path for CP, fallback to module for graph hotspots.
    fp = d.get("file_path")
    if isinstance(fp, str) and fp:
        return fp
    mod = d.get("module")
    if isinstance(mod, str) and mod:
        return mod
    return ""


def _merge_top_modules(*, cp_top: list[dict[str, Any]], chokepoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Union of CP top_files + chokepoints, bounded/deterministic."""

    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in (cp_top or []):
        if not isinstance(item, dict):
            continue
        k = _extract_module_key(item)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(item)

    for item in (chokepoints or []):
        if not isinstance(item, dict):
            continue
        k = _extract_module_key(item)
        if not k or k in seen:
            continue
        seen.add(k)
        # In chokepoints response, the payload is smaller than CP file dict.
        # Keep as-is; downstream trend extraction handles missing fields.
        out.append(item)

    # Deterministic: sort by score desc then key
    out.sort(key=lambda x: (-_safe_float(x.get("score"), 0.0), _extract_module_key(x)))
    return out[:_MAX_MODULES_PER_SNAPSHOT]


def build_hotspot_history_snapshot(*, top_n: int = 10, scope: str = "runtime_only", source: str = "internal") -> dict[str, Any]:
    """Build a single snapshot (does not record it)."""

    top_n = _parse_limit(top_n, 10, lo=1, hi=25)
    bundle, unknowns, unavailable_fields = _read_dependencies_snapshot(top_n=top_n)

    cp = bundle["critical_path"]
    chok = bundle["chokepoints"]
    br = bundle["blast_radius"]
    corr = bundle["correlation"]
    health = bundle["health"]
    slo = bundle["slo"]
    triage = bundle["triage"]
    guard_state = bundle["guard_state"]

    cp_score = _safe_float(cp.get("score"), 0.0)
    cp_sev = str(cp.get("severity") or "INFO")
    corr_score = _safe_float(corr.get("correlation_score"), 0.0)
    health_score = _safe_float(health.get("score"), 0.0)
    routing_conf = _safe_float(((health.get("routing_confidence") or {}).get("confidence") if isinstance(health.get("routing_confidence"), dict) else 0.0), 0.0)

    slo_status = str((slo.get("overall_status") if isinstance(slo, dict) else "unknown") or "unknown")
    triage_incidents = _safe_int(triage.get("total_incidents"), 0) if isinstance(triage, dict) else 0

    chokepoints_list = chok.get("chokepoints", []) if isinstance(chok, dict) else []
    chokepoints_total = _safe_int(chok.get("total"), len(chokepoints_list)) if isinstance(chok, dict) else len(chokepoints_list)
    blast_radius_summary = (br.get("blast_radius_summary") if isinstance(br, dict) else {}) or {}

    cp_top_files = cp.get("top_files", []) if isinstance(cp, dict) else []
    top_modules = _merge_top_modules(cp_top=cp_top_files if isinstance(cp_top_files, list) else [], chokepoints=chokepoints_list if isinstance(chokepoints_list, list) else [])

    hard_facts: list[str] = []
    hard_facts.append("snapshots_in_memory")
    hard_facts.append(f"critical_path_score={round(cp_score,3)}")
    hard_facts.append(f"correlation_score={round(corr_score,3)}")
    hard_facts.append(f"health_score={round(health_score,1)}")

    inferred: list[str] = []
    if routing_conf and routing_conf < 0.70:
        inferred.append("routing_confidence_degraded")
    if str(slo_status).lower() in {"degraded", "critical"}:
        inferred.append("slo_not_healthy")
    if triage_incidents > 0:
        inferred.append("triage_active")

    # Persistence is intentionally disabled by default in 37D.
    persistence_mode = "in_memory_only"
    persistence_enabled = False
    if not persistence_enabled:
        unknowns.append("persistent_store_not_configured")

    return {
        "status": "ok",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/hotspot-history/snapshot",
        "timestamp": _now(),
        "contract_version": GRAPH_HOTSPOT_HISTORY_CONTRACT_VERSION,
        "source": str(source or "internal"),
        "scope": str(scope or "runtime_only"),
        "persistence": {"mode": persistence_mode, "enabled": persistence_enabled},
        "critical_path_score": round(cp_score, 3),
        "critical_path_severity": cp_sev,
        "correlation_score": round(corr_score, 3),
        "health_score": round(health_score, 1),
        "routing_confidence": round(routing_conf, 3),
        "slo_status": slo_status,
        "triage_incidents": triage_incidents,
        "federation_guard_state": guard_state,
        "hotspots_total": _safe_int(corr.get("hotspots_total"), 0) if isinstance(corr, dict) else 0,
        "chokepoints_total": chokepoints_total,
        "blast_radius_summary": blast_radius_summary,
        "top_modules": top_modules,
        "recommendations": (cp.get("recommendations", []) if isinstance(cp, dict) else [])[:_MAX_RECOMMENDATIONS_PER_SNAPSHOT],
        "unknowns": sorted(set([str(u) for u in unknowns if u])),
        "unavailable_fields": sorted(set([str(u) for u in unavailable_fields if u])),
        "hard_facts": hard_facts,
        "inferred": inferred,
    }


def record_hotspot_snapshot(*, top_n: int = 10, scope: str = "runtime_only", source: str = "runtime") -> dict[str, Any]:
    snap = build_hotspot_history_snapshot(top_n=top_n, scope=scope, source=source)
    with _LOCK:
        _SNAPSHOTS.append(snap)
    return snap


def _latest_and_previous() -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    with _LOCK:
        if not _SNAPSHOTS:
            return None, None
        latest = _SNAPSHOTS[-1]
        prev = _SNAPSHOTS[-2] if len(_SNAPSHOTS) >= 2 else None
    return latest, prev


def get_hotspot_history_latest(*, top_n: int = 10, scope: str = "runtime_only", record: bool = True) -> dict[str, Any]:
    if record:
        snap = record_hotspot_snapshot(top_n=top_n, scope=scope, source="runtime")
    else:
        snap = build_hotspot_history_snapshot(top_n=top_n, scope=scope, source="runtime")
    return {
        "status": "ok",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/hotspot-history/latest",
        "timestamp": _now(),
        "contract_version": GRAPH_HOTSPOT_HISTORY_CONTRACT_VERSION,
        "snapshot": snap,
    }


def get_hotspot_history_summary(*, limit: int = 10) -> dict[str, Any]:
    limit = _parse_limit(limit, 10, lo=1, hi=50)
    with _LOCK:
        snaps = list(_SNAPSHOTS)[-limit:]
        total = len(_SNAPSHOTS)

    latest = snaps[-1] if snaps else None
    unknowns_total = len(latest.get("unknowns", []) or []) if isinstance(latest, dict) else 0
    recs_total = len(latest.get("recommendations", []) or []) if isinstance(latest, dict) else 0

    return {
        "status": "ok",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/hotspot-history/summary",
        "timestamp": _now(),
        "contract_version": GRAPH_HOTSPOT_HISTORY_CONTRACT_VERSION,
        "snapshots_total": total,
        "returned": len(snaps),
        "latest_timestamp": latest.get("timestamp") if isinstance(latest, dict) else None,
        "latest_critical_path_score": latest.get("critical_path_score") if isinstance(latest, dict) else None,
        "latest_drift_score": get_hotspot_drift().get("drift_score") if total >= 2 else 0.0,
        "unknowns_total": unknowns_total,
        "recommendations_total": recs_total,
        "persistence_enabled": 1 if (isinstance(latest, dict) and (latest.get("persistence") or {}).get("enabled")) else 0,
    }


def _module_index(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    mods = snapshot.get("top_modules", []) if isinstance(snapshot, dict) else []
    for m in mods if isinstance(mods, list) else []:
        if not isinstance(m, dict):
            continue
        k = _extract_module_key(m)
        if not k:
            continue
        idx[k] = m
    return idx


def get_hotspot_trends(*, limit: int = 10, top_n: int = 10) -> dict[str, Any]:
    limit = _parse_limit(limit, 10, lo=1, hi=50)
    with _LOCK:
        total = len(_SNAPSHOTS)
    if total == 0:
        record_hotspot_snapshot(top_n=top_n, scope="runtime_only", source="runtime")
    with _LOCK:
        snaps = list(_SNAPSHOTS)[-limit:]
        total = len(_SNAPSHOTS)

    latest = snaps[-1] if snaps else None
    prev = snaps[-2] if len(snaps) >= 2 else None

    if not isinstance(latest, dict):
        return {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": "runtime/hotspot-history/trends",
            "timestamp": _now(),
            "contract_version": GRAPH_HOTSPOT_HISTORY_CONTRACT_VERSION,
            "trends": [],
            "total": 0,
            "unknowns": ["no_snapshots"],
        }

    unknowns: list[str] = []
    if total < 2:
        unknowns.append("insufficient_history")

    cur_idx = _module_index(latest)
    prev_idx = _module_index(prev) if isinstance(prev, dict) else {}
    trends: list[dict[str, Any]] = []
    increasing = 0
    decreasing = 0

    for k in sorted(cur_idx.keys()):
        cur = cur_idx[k]
        cur_score = _safe_float(cur.get("score"), _safe_float(cur.get("current_score"), 0.0))
        prev_score = _safe_float(prev_idx.get(k, {}).get("score"), 0.0) if prev_idx else 0.0
        if total < 2:
            delta = 0.0
            trend = "unknown"
        else:
            delta = float(cur_score - prev_score)
            trend = _trend_from_delta(delta)
        if trend == "increasing":
            increasing += 1
        if trend == "decreasing":
            decreasing += 1

        trends.append({
            "module": k,
            "current_score": round(cur_score, 3),
            "previous_score": round(prev_score, 3) if total >= 2 else None,
            "delta": round(delta, 3) if total >= 2 else None,
            "trend": trend,
            "recurrence": _recurrence_count(snaps, k),
            "blast_radius": cur.get("blast_radius"),
            "severity": cur.get("severity"),
            "domain": cur.get("domain"),
        })

    trends.sort(key=lambda t: (-_safe_float(t.get("current_score"), 0.0), str(t.get("module") or "")))
    trends = trends[: _MAX_MODULES_PER_SNAPSHOT]

    return {
        "status": "ok",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/hotspot-history/trends",
        "timestamp": _now(),
        "contract_version": GRAPH_HOTSPOT_HISTORY_CONTRACT_VERSION,
        "trends": trends,
        "total": len(trends),
        "increasing_total": increasing,
        "decreasing_total": decreasing,
        "unknowns": sorted(set(unknowns + list(latest.get("unknowns", []) or []))),
    }


def _recurrence_count(snaps: list[dict[str, Any]], key: str) -> int:
    cnt = 0
    for s in snaps:
        if not isinstance(s, dict):
            continue
        idx = _module_index(s)
        if key in idx:
            cnt += 1
    return cnt


def get_recurring_hotspots(*, limit: int = 10, min_recurrence: int = 3) -> dict[str, Any]:
    limit = _parse_limit(limit, 10, lo=1, hi=50)
    min_recurrence = _parse_limit(min_recurrence, 3, lo=2, hi=20)

    with _LOCK:
        total0 = len(_SNAPSHOTS)
    if total0 == 0:
        record_hotspot_snapshot(top_n=10, scope="runtime_only", source="runtime")

    with _LOCK:
        snaps = list(_SNAPSHOTS)[-limit:]
        total = len(_SNAPSHOTS)

    if total < 2:
        return {
            "status": "ok",
            "service": "ai-lab-openai-gateway",
            "endpoint": "runtime/hotspot-history/recurring",
            "timestamp": _now(),
            "contract_version": GRAPH_HOTSPOT_HISTORY_CONTRACT_VERSION,
            "recurring": [],
            "total": 0,
            "unknowns": ["insufficient_history"],
        }

    counts: dict[str, int] = defaultdict(int)
    last_seen: dict[str, float] = {}
    last_score: dict[str, float] = {}
    for s in snaps:
        if not isinstance(s, dict):
            continue
        ts = _safe_float(s.get("timestamp"), 0.0)
        for k, m in _module_index(s).items():
            counts[k] += 1
            last_seen[k] = ts
            last_score[k] = _safe_float(m.get("score"), _safe_float(m.get("current_score"), 0.0))

    recurring = [
        {"module": k, "recurrence": counts[k], "last_seen": last_seen.get(k), "current_score": round(last_score.get(k, 0.0), 3)}
        for k in counts
        if counts[k] >= min_recurrence
    ]
    recurring.sort(key=lambda r: (-int(r.get("recurrence") or 0), -_safe_float(r.get("current_score"), 0.0), str(r.get("module") or "")))
    recurring = recurring[:25]

    return {
        "status": "ok",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/hotspot-history/recurring",
        "timestamp": _now(),
        "contract_version": GRAPH_HOTSPOT_HISTORY_CONTRACT_VERSION,
        "recurring": recurring,
        "total": len(recurring),
        "unknowns": [],
    }


@dataclass(frozen=True)
class DriftInputs:
    critical_path_delta: float
    max_module_delta: float
    severity_escalations: int
    blast_radius_escalations: int
    routing_conf_delta: float
    health_delta: float
    unknowns_delta: int


def _drift_inputs(latest: dict[str, Any], prev: dict[str, Any]) -> DriftInputs:
    cp_delta = _safe_float(latest.get("critical_path_score"), 0.0) - _safe_float(prev.get("critical_path_score"), 0.0)
    rc_delta = _safe_float(latest.get("routing_confidence"), 0.0) - _safe_float(prev.get("routing_confidence"), 0.0)
    health_delta = _safe_float(latest.get("health_score"), 0.0) - _safe_float(prev.get("health_score"), 0.0)
    unknowns_delta = len(latest.get("unknowns", []) or []) - len(prev.get("unknowns", []) or [])

    cur_idx = _module_index(latest)
    prev_idx = _module_index(prev)
    max_mod_delta = 0.0
    sev_escalations = 0
    br_escalations = 0
    order = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    br_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    for k in cur_idx.keys():
        cur = cur_idx[k]
        prev_m = prev_idx.get(k, {})
        d = _safe_float(cur.get("score"), 0.0) - _safe_float(prev_m.get("score"), 0.0)
        if abs(d) > abs(max_mod_delta):
            max_mod_delta = d
        cur_sev = str(cur.get("severity") or "INFO")
        prev_sev = str(prev_m.get("severity") or "INFO")
        if order.get(cur_sev, 0) > order.get(prev_sev, 0):
            sev_escalations += 1
        cur_br = str(cur.get("blast_radius") or "low").lower()
        prev_br = str(prev_m.get("blast_radius") or "low").lower()
        if br_order.get(cur_br, 0) > br_order.get(prev_br, 0):
            br_escalations += 1

    return DriftInputs(
        critical_path_delta=cp_delta,
        max_module_delta=max_mod_delta,
        severity_escalations=sev_escalations,
        blast_radius_escalations=br_escalations,
        routing_conf_delta=rc_delta,
        health_delta=health_delta,
        unknowns_delta=unknowns_delta,
    )


def _compute_drift_score(inputs: DriftInputs) -> float:
    # Deterministic formula, no adaptive weights.
    score = 0.0
    score += 0.30 * _clamp01(max(0.0, inputs.critical_path_delta) / 0.10)
    score += 0.25 * _clamp01(max(0.0, inputs.max_module_delta) / 0.10)
    score += 0.10 * _clamp01(inputs.severity_escalations / 3.0)
    score += 0.10 * _clamp01(inputs.blast_radius_escalations / 3.0)
    score += 0.15 * _clamp01(max(0.0, -inputs.routing_conf_delta) / 0.10)
    score += 0.05 * _clamp01(max(0.0, -inputs.health_delta) / 10.0)
    score += 0.05 * _clamp01(max(0.0, float(inputs.unknowns_delta)) / 3.0)
    return _clamp01(score)


def get_hotspot_drift(*, window: int = 10) -> dict[str, Any]:
    window = _parse_limit(window, 10, lo=2, hi=50)
    with _LOCK:
        total0 = len(_SNAPSHOTS)
    if total0 == 0:
        record_hotspot_snapshot(top_n=10, scope="runtime_only", source="runtime")

    with _LOCK:
        snaps = list(_SNAPSHOTS)[-window:]
        total = len(_SNAPSHOTS)

    if total < 2 or len(snaps) < 2:
        return {
            "status": "ok",
            "service": "ai-lab-openai-gateway",
            "endpoint": "runtime/hotspot-history/drift",
            "timestamp": _now(),
            "contract_version": GRAPH_HOTSPOT_HISTORY_CONTRACT_VERSION,
            "drift_score": 0.0,
            "severity": "INFO",
            "unknowns": ["insufficient_history"],
            "hard_facts": [f"snapshots_total={total}"],
            "inferred": [],
        }

    latest = snaps[-1]
    prev = snaps[-2]
    inputs = _drift_inputs(latest, prev)
    drift = _compute_drift_score(inputs)

    hard_facts = [
        f"snapshots_total={total}",
        f"critical_path_delta={round(inputs.critical_path_delta,3)}",
        f"max_module_delta={round(inputs.max_module_delta,3)}",
        f"severity_escalations={inputs.severity_escalations}",
        f"blast_radius_escalations={inputs.blast_radius_escalations}",
        f"routing_conf_delta={round(inputs.routing_conf_delta,3)}",
        f"health_delta={round(inputs.health_delta,3)}",
        f"unknowns_delta={inputs.unknowns_delta}",
    ]

    inferred: list[str] = []
    if drift >= 0.50:
        inferred.append("drift_risk_elevated")
    if inputs.max_module_delta > 0.01:
        inferred.append("module_score_increasing")
    if inputs.severity_escalations > 0:
        inferred.append("severity_escalation_detected")
    if inputs.blast_radius_escalations > 0:
        inferred.append("blast_radius_escalation_detected")
    if inputs.routing_conf_delta < -0.01:
        inferred.append("routing_confidence_degraded")

    return {
        "status": "ok",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/hotspot-history/drift",
        "timestamp": _now(),
        "contract_version": GRAPH_HOTSPOT_HISTORY_CONTRACT_VERSION,
        "window": window,
        "drift_score": round(float(drift), 3),
        "severity": _severity_from_score(drift),
        "hard_facts": hard_facts,
        "inferred": inferred,
        "unknowns": sorted(set([str(u) for u in (latest.get("unknowns", []) or []) if u])),
    }


def get_blast_radius_history(*, limit: int = 10) -> dict[str, Any]:
    limit = _parse_limit(limit, 10, lo=1, hi=50)
    with _LOCK:
        total0 = len(_SNAPSHOTS)
    if total0 == 0:
        record_hotspot_snapshot(top_n=10, scope="runtime_only", source="runtime")

    with _LOCK:
        snaps = list(_SNAPSHOTS)[-limit:]

    timeline: list[dict[str, Any]] = []
    for s in snaps:
        if not isinstance(s, dict):
            continue
        br = s.get("blast_radius_summary") if isinstance(s.get("blast_radius_summary"), dict) else {}
        by = br.get("by_blast_radius") if isinstance(br, dict) else None
        timeline.append({
            "timestamp": s.get("timestamp"),
            "critical_path_score": s.get("critical_path_score"),
            "by_blast_radius": by if isinstance(by, dict) else {},
            "unknowns_total": len(s.get("unknowns", []) or []),
        })

    return {
        "status": "ok",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/hotspot-history/blast-radius",
        "timestamp": _now(),
        "contract_version": GRAPH_HOTSPOT_HISTORY_CONTRACT_VERSION,
        "timeline": timeline,
        "total": len(timeline),
    }


def get_hotspot_recommendations() -> dict[str, Any]:
    drift = get_hotspot_drift(window=10)
    drift_score = _safe_float(drift.get("drift_score"), 0.0)
    severity = str(drift.get("severity") or "INFO")

    latest, prev = _latest_and_previous()
    unknowns = (latest.get("unknowns", []) if isinstance(latest, dict) else []) or []

    recs: list[dict[str, Any]] = []
    if "insufficient_history" in (drift.get("unknowns") or []):
        recs.append({
            "severity": "LOW",
            "recommendation": "Insufficient history to compute trends; collect more snapshots",
            "rationale": "snapshots_total<2",
            "confidence": "high",
        })
    if "persistent_store_not_configured" in unknowns:
        recs.append({
            "severity": "LOW",
            "recommendation": "History is in-memory only; restart will reset trends",
            "rationale": "persistence_disabled",
            "confidence": "high",
        })
    if drift_score >= 0.70:
        recs.append({
            "severity": "HIGH",
            "recommendation": "Drift score high; avoid adding responsibilities to recurring chokepoints",
            "rationale": f"drift_score={round(drift_score,3)}",
            "confidence": "medium",
        })
    elif drift_score >= 0.50:
        recs.append({
            "severity": "MEDIUM",
            "recommendation": "Drift score elevated; monitor increasing modules and blast-radius expansion",
            "rationale": f"drift_score={round(drift_score,3)}",
            "confidence": "medium",
        })
    else:
        recs.append({
            "severity": "INFO",
            "recommendation": "No immediate drift action",
            "rationale": f"severity={severity}",
            "confidence": "medium",
        })

    # bounded + deterministic
    recs = recs[:10]
    recs.sort(key=lambda r: (r.get("severity", ""), r.get("recommendation", "")))

    return {
        "status": "ok",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/hotspot-history/recommendations",
        "timestamp": _now(),
        "contract_version": GRAPH_HOTSPOT_HISTORY_CONTRACT_VERSION,
        "drift_score": round(float(drift_score), 3),
        "severity": severity,
        "recommendations": recs,
        "total": len(recs),
        "unknowns": sorted(set([str(u) for u in unknowns if u])),
    }


def reset_hotspot_history_runtime_state() -> dict[str, Any]:
    with _LOCK:
        _SNAPSHOTS.clear()
    return {"reset": True, "timestamp": _now(), "contract_version": GRAPH_HOTSPOT_HISTORY_CONTRACT_VERSION}


def build_hotspot_history_prometheus_metrics() -> str:
    """Render hotspot history metrics as Prometheus text (fail-safe)."""
    try:
        latest, prev = _latest_and_previous()
        if latest is None:
            record_hotspot_snapshot(top_n=10, scope="runtime_only", source="runtime")
            latest, prev = _latest_and_previous()
        snapshots_total = 0
        with _LOCK:
            snapshots_total = len(_SNAPSHOTS)

        drift = get_hotspot_drift(window=10)
        trends = get_hotspot_trends(limit=10, top_n=10)
        recurring = get_recurring_hotspots(limit=10, min_recurrence=3)
        recs = get_hotspot_recommendations()

        increasing_total = _safe_int(trends.get("increasing_total"), 0)
        decreasing_total = _safe_int(trends.get("decreasing_total"), 0)
        unknowns_total = float(len((latest or {}).get("unknowns", []) or []) + len((latest or {}).get("unavailable_fields", []) or []))
        persistence_enabled = 1.0 if ((latest or {}).get("persistence") or {}).get("enabled") else 0.0

        return (
            f"ailab_hotspot_history_snapshots_total {float(snapshots_total)}\n"
            f"ailab_hotspot_history_recurring_total {float(_safe_int(recurring.get('total'), 0))}\n"
            f"ailab_hotspot_history_drift_score {float(_safe_float(drift.get('drift_score'), 0.0))}\n"
            f"ailab_hotspot_history_increasing_total {float(increasing_total)}\n"
            f"ailab_hotspot_history_decreasing_total {float(decreasing_total)}\n"
            f"ailab_hotspot_history_unknowns_total {float(unknowns_total)}\n"
            f"ailab_hotspot_history_recommendations_total {float(_safe_int(recs.get('total'), 0))}\n"
            f"ailab_hotspot_history_persistence_enabled {float(persistence_enabled)}\n"
        )
    except Exception:
        return (
            "ailab_hotspot_history_snapshots_total 0\n"
            "ailab_hotspot_history_recurring_total 0\n"
            "ailab_hotspot_history_drift_score 0\n"
            "ailab_hotspot_history_increasing_total 0\n"
            "ailab_hotspot_history_decreasing_total 0\n"
            "ailab_hotspot_history_unknowns_total 0\n"
            "ailab_hotspot_history_recommendations_total 0\n"
            "ailab_hotspot_history_persistence_enabled 0\n"
        )


def _history_payload(*, limit: int, top_n: int) -> dict[str, Any]:
    limit = _parse_limit(limit, 10, lo=1, hi=50)
    top_n = _parse_limit(top_n, 10, lo=1, hi=25)

    # record a fresh snapshot on each query, but bounded by deque.
    record_hotspot_snapshot(top_n=top_n, scope="runtime_only", source="runtime")
    with _LOCK:
        snaps = list(_SNAPSHOTS)[-limit:]
        total = len(_SNAPSHOTS)
    return {
        "status": "ok",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/hotspot-history",
        "timestamp": _now(),
        "contract_version": GRAPH_HOTSPOT_HISTORY_CONTRACT_VERSION,
        "snapshots": snaps,
        "snapshots_total": total,
        "returned": len(snaps),
        "unknowns": ["insufficient_history"] if total < 2 else [],
    }


def get_hotspot_history_window(*, limit: int = 10, top_n: int = 10) -> dict[str, Any]:
    return _history_payload(limit=limit, top_n=top_n)
