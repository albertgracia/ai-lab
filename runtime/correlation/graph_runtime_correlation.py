"""GRAPH-RUNTIME-CORRELATION-01 (FASE 37B)

Read-only, bounded, metadata-only correlation layer:
- correlates GitNexus graph hotspots with runtime degradation signals
- separates hard_facts / inferred / unknowns
- deterministic ordering, fail-safe

No routing mutation. No remediation. No runtime/state writes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any


GRAPH_RUNTIME_CORRELATION_CONTRACT_VERSION = "37B-GRAPH-RUNTIME-CORRELATION-01"

_CACHE_LOCK = Lock()
_CACHE: dict[str, Any] | None = None
_CACHE_TS = 0.0
_CACHE_TTL_S = 15.0


def _now() -> float:
    return time.time()


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


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


def _br_weight(br: str) -> float:
    v = str(br or "").lower()
    return {
        "low": 0.10,
        "medium": 0.20,
        "high": 0.35,
        "critical": 0.50,
    }.get(v, 0.0)


def _gov_weight(risk: str) -> float:
    v = str(risk or "").lower()
    return {
        "low": 0.05,
        "medium": 0.15,
        "high": 0.30,
        "critical": 0.45,
    }.get(v, 0.0)


def _slo_weight(status: str) -> float:
    v = str(status or "").lower()
    return {
        "healthy": 0.00,
        "warning": 0.10,
        "degraded": 0.25,
        "critical": 0.45,
    }.get(v, 0.15 if v else 0.15)


def _guard_weight(state: str) -> float:
    v = str(state or "").lower()
    # federation_guards uses NORMAL/DEGRADED/CONSTRAINED/SAFE_MODE
    return {
        "normal": 0.00,
        "degraded": 0.10,
        "constrained": 0.25,
        "safe_mode": 0.45,
    }.get(v, 0.10 if v else 0.10)


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


@dataclass
class CorrelatedMetric:
    name: str
    value: Any
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value, "source": self.source}


@dataclass
class CorrelatedHotspot:
    module: str
    file_path: str
    cluster: str = "unknown"
    fan_in: int = 0
    fan_out: int = 0
    centrality_score: float = 0.0
    blast_radius: str = "unknown"
    graph_risk: str = "unknown"
    runtime_health_status: str = "unknown"
    health_score: float = 0.0
    routing_confidence: float = 0.0
    slo_status: str = "unknown"
    triage_severity: str = "info"
    federation_state: str = "unknown"
    evidence_state: dict[str, Any] = field(default_factory=dict)
    correlated_metrics: list[CorrelatedMetric] = field(default_factory=list)
    hard_facts: list[str] = field(default_factory=list)
    inferred: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    confidence: str = "low"
    recommendation: str = ""
    severity: str = "INFO"
    correlation_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "file_path": self.file_path,
            "cluster": self.cluster,
            "fan_in": int(self.fan_in),
            "fan_out": int(self.fan_out),
            "centrality_score": round(float(self.centrality_score), 4),
            "blast_radius": self.blast_radius,
            "graph_risk": self.graph_risk,
            "runtime_health_status": self.runtime_health_status,
            "health_score": round(float(self.health_score), 1),
            "routing_confidence": round(float(self.routing_confidence), 3),
            "slo_status": self.slo_status,
            "triage_severity": self.triage_severity,
            "federation_state": self.federation_state,
            "evidence_state": self.evidence_state,
            "correlated_metrics": [m.to_dict() for m in self.correlated_metrics],
            "hard_facts": list(self.hard_facts),
            "inferred": list(self.inferred),
            "unknowns": sorted(set(self.unknowns)),
            "confidence": self.confidence,
            "recommendation": self.recommendation,
            "severity": self.severity,
            "correlation_score": round(float(self.correlation_score), 3),
        }


@dataclass
class CorrelationRecommendation:
    severity: str
    recommendation: str
    rationale: str
    confidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "recommendation": self.recommendation,
            "rationale": self.rationale,
            "confidence": self.confidence,
        }


@dataclass
class CorrelationSnapshot:
    timestamp: float
    contract_version: str
    correlation_score: float
    severity: str
    hotspots_total: int
    correlated_hotspots: list[CorrelatedHotspot]
    unknowns: list[str]
    unavailable_fields: list[str]
    recommendations: list[CorrelationRecommendation]
    hard_facts: list[str]
    inferred: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "ai-lab-openai-gateway",
            "endpoint": "runtime/correlation",
            "timestamp": float(self.timestamp),
            "contract_version": self.contract_version,
            "correlation_score": round(float(self.correlation_score), 3),
            "severity": self.severity,
            "hotspots_total": int(self.hotspots_total),
            "correlated_hotspots": [h.to_dict() for h in self.correlated_hotspots],
            "unknowns": sorted(set(self.unknowns)),
            "unavailable_fields": sorted(set(self.unavailable_fields)),
            "recommendations": [r.to_dict() for r in self.recommendations],
            "hard_facts": list(self.hard_facts),
            "inferred": list(self.inferred),
        }


def reset_graph_runtime_correlation_state() -> dict[str, Any]:
    global _CACHE, _CACHE_TS
    with _CACHE_LOCK:
        _CACHE = None
        _CACHE_TS = 0.0
    return {"reset": True, "timestamp": _now(), "contract_version": GRAPH_RUNTIME_CORRELATION_CONTRACT_VERSION}


def _get_cached_snapshot() -> dict[str, Any]:
    global _CACHE, _CACHE_TS
    now = _now()
    with _CACHE_LOCK:
        if _CACHE and (now - float(_CACHE_TS)) <= _CACHE_TTL_S:
            return dict(_CACHE)
    snap = build_graph_runtime_correlation_snapshot()
    with _CACHE_LOCK:
        _CACHE = dict(snap)
        _CACHE_TS = now
    return snap


def _read_graph_hotspots() -> dict[str, Any] | None:
    try:
        from runtime.graph_reasoning.gitnexus_graph_reasoning import get_graph_hotspots
        return get_graph_hotspots()
    except Exception:
        return None


def _read_graph_summary() -> dict[str, Any] | None:
    try:
        from runtime.graph_reasoning.gitnexus_graph_reasoning import get_graph_reasoning_summary
        return get_graph_reasoning_summary()
    except Exception:
        return None


def _read_graph_blast_radius() -> dict[str, Any] | None:
    try:
        from runtime.graph_reasoning.gitnexus_graph_reasoning import get_graph_blast_radius
        return get_graph_blast_radius()
    except Exception:
        return None


def _read_health() -> dict[str, Any] | None:
    try:
        from runtime.health.cognitive_health_layer import build_cognitive_health_snapshot
        return build_cognitive_health_snapshot(window_minutes=60)
    except Exception:
        return None


def _read_slo_status() -> dict[str, Any] | None:
    try:
        from runtime.slo.cognitive_slo import get_slo_status
        return get_slo_status()
    except Exception:
        return None


def _read_triage_summary() -> dict[str, Any] | None:
    try:
        from runtime.triage.autonomous_triage import get_triage_summary
        return get_triage_summary()
    except Exception:
        return None


def _read_guard_summary() -> dict[str, Any] | None:
    try:
        from runtime.federation.federation_guards import get_federation_guard_summary
        return get_federation_guard_summary()
    except Exception:
        return None


def _read_evidence_summary() -> dict[str, Any] | None:
    try:
        from runtime.federation.federation_observability import get_evidence_summary
        return get_evidence_summary()
    except Exception:
        return None


def _read_architecture_summary() -> dict[str, Any] | None:
    try:
        from runtime.governance.architecture_governance import get_architecture_summary
        return get_architecture_summary()
    except Exception:
        return None


def _read_graph_findings_for_module(module: str, graph_hotspots: dict[str, Any] | None) -> dict[str, Any]:
    if not graph_hotspots or not isinstance(graph_hotspots, dict):
        return {}
    items = (graph_hotspots.get("hotspots") or [])
    if not isinstance(items, list):
        return {}
    for it in items:
        if isinstance(it, dict) and str(it.get("module") or "") == module:
            return dict(it)
    return {}


def _triage_severity(summary: dict[str, Any] | None) -> str:
    if not summary:
        return "info"
    if _safe_int(summary.get("total_critical"), 0) > 0:
        return "critical"
    if _safe_int(summary.get("total_high"), 0) > 0:
        return "high"
    if _safe_int(summary.get("total_warning"), 0) > 0:
        return "warning"
    return "info"


def _runtime_health_status(health: dict[str, Any] | None) -> tuple[str, float, float]:
    if not health:
        return "unknown", 0.0, 0.0
    overall = health.get("overall_health") if isinstance(health.get("overall_health"), dict) else {}
    hs = _safe_float(health.get("score"), 0.0)
    rc = _safe_float((health.get("routing_confidence") or {}).get("confidence"), 0.0)
    status = str(overall.get("status") or health.get("status") or "unknown")
    return status, hs, rc


def _evidence_state(evidence: dict[str, Any] | None) -> dict[str, Any]:
    if not evidence:
        return {"replay_risk_total": 0, "stale_evidence_total": 0, "invalid_lineage_total": 0}
    return {
        "replay_risk_total": _safe_int(evidence.get("replay_risk_total"), 0),
        "stale_evidence_total": _safe_int(evidence.get("stale_evidence_total"), 0),
        "invalid_lineage_total": _safe_int(evidence.get("invalid_lineage_total"), 0),
        "lineage_depth_max": _safe_int(evidence.get("lineage_depth_max"), 0),
    }


def _correlation_score_for_hotspot(
    *,
    fan_in: int,
    fan_out: int,
    centrality: float,
    blast_radius: str,
    graph_risk: str,
    health_score: float,
    routing_confidence: float,
    slo_status: str,
    triage_sev: str,
    guard_state: str,
    evidence: dict[str, Any],
) -> float:
    # Graph side (bounded 0-1)
    graph_signal = _clamp01(0.55 * _clamp01(float(centrality)) + 0.25 * _clamp01(min(1.0, fan_in / 20.0)) + 0.20 * _clamp01(min(1.0, fan_out / 20.0)))
    graph_signal += _br_weight(blast_radius)
    graph_signal += _gov_weight(graph_risk)

    # Runtime side
    hs_norm = _clamp01(1.0 - (float(health_score) / 100.0))  # 0 good, 1 bad
    rc_norm = _clamp01(1.0 - float(routing_confidence))
    runtime_signal = 0.55 * hs_norm + 0.25 * rc_norm
    runtime_signal += _slo_weight(slo_status)

    triage_map = {"info": 0.0, "warning": 0.10, "high": 0.25, "critical": 0.45}
    runtime_signal += float(triage_map.get(str(triage_sev).lower(), 0.10))

    runtime_signal += _guard_weight(guard_state)

    # Evidence
    replay = _safe_int(evidence.get("replay_risk_total"), 0)
    stale = _safe_int(evidence.get("stale_evidence_total"), 0)
    invalid = _safe_int(evidence.get("invalid_lineage_total"), 0)
    ev_signal = _clamp01(min(1.0, replay / 10.0) * 0.5 + min(1.0, stale / 10.0) * 0.25 + min(1.0, invalid / 5.0) * 0.25)

    # Weighted sum, bounded
    score = 0.45 * _clamp01(graph_signal) + 0.45 * _clamp01(runtime_signal) + 0.10 * ev_signal
    return _clamp01(score)


def build_graph_runtime_correlation_snapshot() -> dict[str, Any]:
    unknowns: list[str] = []
    unavailable_fields: list[str] = []
    hard_facts: list[str] = []
    inferred: list[str] = []

    graph_hotspots = _read_graph_hotspots()
    if graph_hotspots is None:
        unavailable_fields.append("graph_hotspots")
        unknowns.append("gitnexus_hotspots_unavailable")
    graph_summary = _read_graph_summary()
    if graph_summary is None:
        unavailable_fields.append("graph_summary")
        unknowns.append("gitnexus_summary_unavailable")

    health = _read_health()
    if health is None:
        unavailable_fields.append("cognitive_health")
        unknowns.append("cognitive_health_unavailable")
    else:
        hard_facts.append("cognitive_health_snapshot")

    slo = _read_slo_status()
    if slo is None:
        unavailable_fields.append("slo_status")
        unknowns.append("slo_status_unavailable")
    else:
        hard_facts.append("slo_status")

    triage = _read_triage_summary()
    if triage is None:
        unavailable_fields.append("triage_summary")
        unknowns.append("triage_unavailable")
    else:
        hard_facts.append("triage_summary")

    guard = _read_guard_summary()
    if guard is None:
        unavailable_fields.append("federation_guard")
        unknowns.append("federation_guard_unavailable")
    else:
        hard_facts.append("federation_guard_summary")

    evidence = _read_evidence_summary()
    if evidence is None:
        unavailable_fields.append("evidence_summary")
        unknowns.append("evidence_summary_unavailable")
    else:
        hard_facts.append("evidence_summary")

    arch = _read_architecture_summary()
    if arch is None:
        unavailable_fields.append("architecture_summary")
        unknowns.append("architecture_summary_unavailable")
    else:
        hard_facts.append("architecture_summary")

    runtime_status, health_score, routing_conf = _runtime_health_status(health)
    slo_status = str((slo or {}).get("overall_status") or "unknown")
    triage_sev = _triage_severity(triage)
    guard_state = str(((guard or {}).get("state") or {}).get("state") or (guard or {}).get("state") or "unknown")
    ev_state = _evidence_state(evidence)

    # Hotspots candidates: graph hotspots + prioritized modules
    prioritized = [
        "runtime/gateway/openai_gateway.py",
        "runtime/gateway/runtime_api_routes.py",
        "runtime/federation/federation_guards.py",
        "runtime/federation/role_router.py",
        "runtime/health/cognitive_health_layer.py",
        "runtime/triage/autonomous_triage.py",
        "runtime/slo/cognitive_slo.py",
        "runtime/graph_reasoning/gitnexus_graph_reasoning.py",
        "runtime/telemetry/prometheus_metrics.py",
        "runtime/models/model_registry.py",
    ]

    graph_items = []
    if isinstance(graph_hotspots, dict):
        graph_items = graph_hotspots.get("hotspots") or []
    graph_mods = [it.get("module") for it in graph_items if isinstance(it, dict) and it.get("module")]
    candidates = []
    for m in prioritized:
        if m not in candidates:
            candidates.append(m)
    for m in graph_mods:
        if isinstance(m, str) and m not in candidates:
            candidates.append(m)

    correlated: list[CorrelatedHotspot] = []
    for module in candidates[:30]:
        # Module graph signal may be absent (unknowns preserved)
        g = _read_graph_findings_for_module(module, graph_hotspots)
        if not g:
            # Only include prioritized unknown modules; bounded.
            if module not in prioritized:
                continue
        fan_in = _safe_int(g.get("fan_in"), 0)
        fan_out = _safe_int(g.get("fan_out"), 0)
        cent = _safe_float(g.get("centrality_score"), 0.0)
        br = str(g.get("blast_radius") or "unknown")
        gr = str(g.get("governance_risk") or "unknown")
        cluster = str(g.get("domain") or "unknown")

        hard: list[str] = []
        inf: list[str] = []
        unk: list[str] = []

        if g:
            hard.append("graph_hotspot")
        else:
            unk.append("graph_data_missing_for_module")

        if health is None:
            unk.append("health_unavailable")
        if slo is None:
            unk.append("slo_unavailable")
        if triage is None:
            unk.append("triage_unavailable")
        if guard is None:
            unk.append("federation_guard_unavailable")
        if evidence is None:
            unk.append("evidence_unavailable")

        # Inference statements (bounded, explainable)
        if g and br in {"high", "critical"}:
            inf.append("high_graph_blast_radius")
        if g and fan_in >= 8:
            inf.append("high_fan_in")
        if g and gr in {"high", "critical"}:
            inf.append("high_governance_risk")
        if runtime_status in {"degraded", "critical"}:
            inf.append("runtime_health_degraded")
        if routing_conf and routing_conf < 0.70:
            inf.append("routing_confidence_degraded")
        if slo_status in {"degraded", "critical"}:
            inf.append("slo_not_healthy")
        if triage_sev in {"warning", "high", "critical"}:
            inf.append("triage_active")

        score = _correlation_score_for_hotspot(
            fan_in=fan_in,
            fan_out=fan_out,
            centrality=cent,
            blast_radius=br,
            graph_risk=gr,
            health_score=health_score,
            routing_confidence=routing_conf,
            slo_status=slo_status,
            triage_sev=triage_sev,
            guard_state=guard_state,
            evidence=ev_state,
        )
        sev = _severity_from_score(score)

        confidence = "high" if g and health and slo and triage and guard and evidence else "medium" if (g and health) else "low"

        recommendation = ""
        if sev in {"HIGH", "CRITICAL"}:
            recommendation = "Review this module for operational correlation: verify metrics, guard counters, and recent deploys"
        elif sev == "MEDIUM":
            recommendation = "Monitor this module; correlation signals present but not critical"
        else:
            recommendation = "No immediate action"

        metrics: list[CorrelatedMetric] = []
        metrics.append(CorrelatedMetric("cognitive_health_score", round(health_score, 1), "runtime/health"))
        metrics.append(CorrelatedMetric("routing_confidence", round(routing_conf, 3), "runtime/health"))
        metrics.append(CorrelatedMetric("slo_status", slo_status, "runtime/slo"))
        metrics.append(CorrelatedMetric("triage_severity", triage_sev, "runtime/triage"))
        metrics.append(CorrelatedMetric("federation_guard_state", guard_state, "runtime/federation"))
        metrics.append(CorrelatedMetric("evidence_replay_risk_total", ev_state.get("replay_risk_total"), "runtime/federation"))

        correlated.append(CorrelatedHotspot(
            module=module,
            file_path=module,
            cluster=cluster,
            fan_in=fan_in,
            fan_out=fan_out,
            centrality_score=cent,
            blast_radius=br,
            graph_risk=gr,
            runtime_health_status=runtime_status,
            health_score=health_score,
            routing_confidence=routing_conf,
            slo_status=slo_status,
            triage_severity=triage_sev,
            federation_state=guard_state,
            evidence_state=ev_state,
            correlated_metrics=metrics,
            hard_facts=hard,
            inferred=inf,
            unknowns=unk,
            confidence=confidence,
            recommendation=recommendation,
            severity=sev,
            correlation_score=score,
        ))

    # Deterministic ordering: highest score then module
    correlated.sort(key=lambda h: (-h.correlation_score, h.module))
    if len(correlated) > 20:
        correlated = correlated[:20]

    # Snapshot score: max correlated score, tempered by unknowns
    top = correlated[0].correlation_score if correlated else 0.0
    missing_penalty = 0.05 * min(5, len(unavailable_fields))
    corr_score = _clamp01(top + 0.20 * _slo_weight(slo_status) + 0.15 * _guard_weight(guard_state) - missing_penalty)
    sev = _severity_from_score(corr_score)

    if unavailable_fields:
        inferred.append("correlation_partial_due_to_missing_sources")

    recs = _build_recommendations(
        severity=sev,
        slo_status=slo_status,
        guard_state=guard_state,
        routing_conf=routing_conf,
        unavailable_fields=unavailable_fields,
    )

    snap = CorrelationSnapshot(
        timestamp=_now(),
        contract_version=GRAPH_RUNTIME_CORRELATION_CONTRACT_VERSION,
        correlation_score=corr_score,
        severity=sev,
        hotspots_total=int((graph_hotspots or {}).get("total_hotspots", 0) or 0) if isinstance(graph_hotspots, dict) else 0,
        correlated_hotspots=correlated,
        unknowns=unknowns,
        unavailable_fields=unavailable_fields,
        recommendations=recs,
        hard_facts=hard_facts,
        inferred=inferred,
    ).to_dict()

    # Fail-safe: never raise
    return snap


def _build_recommendations(
    *,
    severity: str,
    slo_status: str,
    guard_state: str,
    routing_conf: float,
    unavailable_fields: list[str],
) -> list[CorrelationRecommendation]:
    recs: list[CorrelationRecommendation] = []

    if unavailable_fields:
        recs.append(CorrelationRecommendation(
            severity="LOW",
            recommendation="Fill missing correlation sources (graph/health/slo/triage/federation) before acting",
            rationale=f"missing_sources={sorted(set(unavailable_fields))}",
            confidence="low",
        ))

    if str(slo_status).lower() in {"degraded", "critical"}:
        recs.append(CorrelationRecommendation(
            severity="HIGH",
            recommendation="Treat operational degradation as primary; use graph correlation to narrow suspects",
            rationale=f"slo_status={slo_status}",
            confidence="high",
        ))

    if str(guard_state).lower() in {"constrained", "safe_mode"}:
        recs.append(CorrelationRecommendation(
            severity="HIGH",
            recommendation="Investigate federation guard triggers and evidence replay/staleness before code refactors",
            rationale=f"guard_state={guard_state}",
            confidence="high",
        ))

    if routing_conf and float(routing_conf) < 0.70:
        recs.append(CorrelationRecommendation(
            severity="MEDIUM",
            recommendation="Routing confidence degraded (single-node or low avg score); prefer low-risk changes",
            rationale=f"routing_confidence={round(float(routing_conf), 3)}",
            confidence="medium",
        ))

    if not recs:
        recs.append(CorrelationRecommendation(
            severity="INFO",
            recommendation="No immediate correlation-driven action",
            rationale=f"severity={severity}",
            confidence="medium",
        ))

    # bounded + deterministic
    recs = recs[:8]
    recs.sort(key=lambda r: (r.severity, r.recommendation))
    return recs


def get_graph_runtime_correlation_summary() -> dict[str, Any]:
    snap = _get_cached_snapshot()
    return {
        "status": snap.get("status", "ok"),
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/correlation/summary",
        "timestamp": _now(),
        "contract_version": GRAPH_RUNTIME_CORRELATION_CONTRACT_VERSION,
        "correlation_score": snap.get("correlation_score", 0.0),
        "severity": snap.get("severity", "INFO"),
        "hotspots_total": snap.get("hotspots_total", 0),
        "unknowns": snap.get("unknowns", []),
        "unavailable_fields": snap.get("unavailable_fields", []),
        "recommendations_total": len(snap.get("recommendations", []) or []),
    }


def get_correlated_hotspots() -> dict[str, Any]:
    snap = _get_cached_snapshot()
    hs = snap.get("correlated_hotspots", []) or []
    return {
        "status": snap.get("status", "ok"),
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/correlation/hotspots",
        "timestamp": _now(),
        "contract_version": GRAPH_RUNTIME_CORRELATION_CONTRACT_VERSION,
        "hotspots": hs,
        "displayed": len(hs),
    }


def get_correlated_blast_radius() -> dict[str, Any]:
    br = _read_graph_blast_radius()
    return {
        "status": "ok" if br is not None else "degraded",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/correlation/blast-radius",
        "timestamp": _now(),
        "contract_version": GRAPH_RUNTIME_CORRELATION_CONTRACT_VERSION,
        "blast_radius": br or {"contract_version": "unknown", "blast_radius_analysis": [], "unknowns": ["blast_radius_unavailable"]},
    }


def get_runtime_topology_findings() -> dict[str, Any]:
    # Minimal: expose health + slo + triage + guard summary in one bounded payload.
    health = _read_health() or {"status": "degraded"}
    slo = _read_slo_status() or {"overall_status": "unknown"}
    triage = _read_triage_summary() or {"total_incidents": 0}
    guard = _read_guard_summary() or {"state": {"state": "unknown"}, "counters": {}}
    evidence = _read_evidence_summary() or {}
    return {
        "status": "ok",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/correlation/findings",
        "timestamp": _now(),
        "contract_version": GRAPH_RUNTIME_CORRELATION_CONTRACT_VERSION,
        "runtime": {
            "cognitive_health": {
                "score": health.get("score", 0.0),
                "overall_health": health.get("overall_health", {}),
                "routing_confidence": (health.get("routing_confidence") or {}).get("confidence", 0.0),
            },
            "slo": {
                "overall_status": slo.get("overall_status", "unknown"),
                "violations_total": slo.get("violations_total", 0),
                "safe_mode_total": slo.get("safe_mode_total", 0),
            },
            "triage": {
                "total_incidents": triage.get("total_incidents", 0),
                "total_critical": triage.get("total_critical", 0),
                "total_high": triage.get("total_high", 0),
            },
            "federation": {
                "guard_state": ((guard.get("state") or {}).get("state") if isinstance(guard.get("state"), dict) else guard.get("state")) or "unknown",
                "guard_counters": guard.get("counters", {}),
                "evidence_summary": _evidence_state(evidence),
            },
        },
    }


def get_correlation_recommendations() -> dict[str, Any]:
    snap = _get_cached_snapshot()
    recs = snap.get("recommendations", []) or []
    return {
        "status": snap.get("status", "ok"),
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/correlation/recommendations",
        "timestamp": _now(),
        "contract_version": GRAPH_RUNTIME_CORRELATION_CONTRACT_VERSION,
        "recommendations": recs,
        "total": len(recs),
    }


def build_graph_runtime_correlation_prometheus_metrics() -> str:
    """Render correlation metrics as Prometheus text (fail-safe)."""
    try:
        snap = _get_cached_snapshot()
        score = float(snap.get("correlation_score", 0) or 0)
        hotspots_total = float(snap.get("hotspots_total", 0) or 0)
        ch = snap.get("correlated_hotspots", []) or []
        high_risk = sum(1 for h in ch if isinstance(h, dict) and h.get("severity") in {"HIGH", "CRITICAL"})
        critical = sum(1 for h in ch if isinstance(h, dict) and h.get("severity") == "CRITICAL")
        unknowns_total = float(len(snap.get("unknowns", []) or []) + len(snap.get("unavailable_fields", []) or []))
        recs_total = float(len(snap.get("recommendations", []) or []))

        # linkage heuristics
        runtime_linked = sum(1 for h in ch if isinstance(h, dict) and ("runtime_health_degraded" in (h.get("inferred") or []) or "routing_confidence_degraded" in (h.get("inferred") or [])))
        graph_linked = sum(1 for h in ch if isinstance(h, dict) and ("graph_hotspot" in (h.get("hard_facts") or []) or "high_graph_blast_radius" in (h.get("inferred") or [])))

        return (
            f"ailab_correlation_score {score}\n"
            f"ailab_correlation_hotspots_total {hotspots_total}\n"
            f"ailab_correlation_high_risk_total {float(high_risk)}\n"
            f"ailab_correlation_critical_total {float(critical)}\n"
            f"ailab_correlation_unknowns_total {unknowns_total}\n"
            f"ailab_correlation_recommendations_total {recs_total}\n"
            f"ailab_correlation_runtime_health_linked_total {float(runtime_linked)}\n"
            f"ailab_correlation_graph_health_linked_total {float(graph_linked)}\n"
        )
    except Exception:
        return (
            "ailab_correlation_score 0\n"
            "ailab_correlation_hotspots_total 0\n"
            "ailab_correlation_high_risk_total 0\n"
            "ailab_correlation_critical_total 0\n"
            "ailab_correlation_unknowns_total 0\n"
            "ailab_correlation_recommendations_total 0\n"
            "ailab_correlation_runtime_health_linked_total 0\n"
            "ailab_correlation_graph_health_linked_total 0\n"
        )
