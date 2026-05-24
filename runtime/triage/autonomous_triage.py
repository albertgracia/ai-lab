"""FASE 36D: Autonomous Observability Triage Engine.

Bounded, deterministic, metadata-only, fail-safe triage for AI-LAB.
Reads existing signals, correlates degradation, estimates impact,
determines severity, suggests root causes, and proposes remediation hints.

NO auto-remediation. NO mutations. NO background loops. Read-only.
"""

import json
import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Any

TRIAGE_CONTRACT_VERSION = "36D"
_RUNTIME_ROOT = os.environ.get("AI_LAB_ROOT", "/opt/ai-lab")
_STORE_TTL = int(os.environ.get("AI_LAB_TRIAGE_TTL_SECONDS", "300"))

# Bounded store limits
_MAX_INCIDENTS = 256
_MAX_SNAPSHOTS = 128
_MAX_RECOMMENDATIONS = 128
_MAX_EVENTS = 512


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class BlastRadius(Enum):
    LOCAL = "local"
    FEDERATION = "federation"
    RUNTIME = "runtime"
    PLATFORM = "platform"


@dataclass
class TriageIncident:
    incident_id: str
    severity: str
    category: str
    source: str
    created_at: float
    updated_at: float
    blast_radius: str
    confidence: float
    correlated_alerts: list[str] = field(default_factory=list)
    correlated_slos: list[str] = field(default_factory=list)
    correlated_guard_state: str = "unknown"
    architecture_hotspots: list[str] = field(default_factory=list)
    probable_root_causes: list[str] = field(default_factory=list)
    remediation_hints: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    degraded_components: list[str] = field(default_factory=list)
    federation_state: str = "unknown"
    registry_state: str = "unknown"
    lmstudio_state: str = "unknown"
    recommended_priority: int = 0
    escalation_required: bool = False
    operational_impact: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "severity": self.severity,
            "category": self.category,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "blast_radius": self.blast_radius,
            "confidence": self.confidence,
            "correlated_alerts": self.correlated_alerts,
            "correlated_slos": self.correlated_slos,
            "correlated_guard_state": self.correlated_guard_state,
            "architecture_hotspots": self.architecture_hotspots,
            "probable_root_causes": self.probable_root_causes,
            "remediation_hints": self.remediation_hints,
            "evidence_refs": self.evidence_refs,
            "degraded_components": self.degraded_components,
            "federation_state": self.federation_state,
            "registry_state": self.registry_state,
            "lmstudio_state": self.lmstudio_state,
            "recommended_priority": self.recommended_priority,
            "escalation_required": self.escalation_required,
            "operational_impact": self.operational_impact,
        }


@dataclass
class TriageSnapshot:
    snapshot_id: str
    timestamp: float
    total_incidents: int
    critical_count: int
    high_count: int
    warning_count: int
    info_count: int
    platform_blast_count: int
    federation_blast_count: int
    runtime_blast_count: int
    local_blast_count: int
    lmstudio_related_count: int
    registry_related_count: int
    severity_distribution: dict[str, int] = field(default_factory=dict)
    blast_radius_distribution: dict[str, int] = field(default_factory=dict)
    top_categories: list[str] = field(default_factory=list)
    guard_state: str = "unknown"
    governance_score: float = 0.0
    slo_status: str = "unknown"
    degradation_level: int = 0
    sources_available: list[str] = field(default_factory=list)
    sources_unavailable: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "total_incidents": self.total_incidents,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "platform_blast_count": self.platform_blast_count,
            "federation_blast_count": self.federation_blast_count,
            "runtime_blast_count": self.runtime_blast_count,
            "local_blast_count": self.local_blast_count,
            "lmstudio_related_count": self.lmstudio_related_count,
            "registry_related_count": self.registry_related_count,
            "severity_distribution": self.severity_distribution,
            "blast_radius_distribution": self.blast_radius_distribution,
            "top_categories": self.top_categories,
            "guard_state": self.guard_state,
            "governance_score": self.governance_score,
            "slo_status": self.slo_status,
            "degradation_level": self.degradation_level,
            "sources_available": self.sources_available,
            "sources_unavailable": self.sources_unavailable,
        }


# ── Bounded Stores ─────────────────────────────────────────────

_lock = Lock()
_incidents: deque[TriageIncident] = deque(maxlen=_MAX_INCIDENTS)
_snapshots: deque[TriageSnapshot] = deque(maxlen=_MAX_SNAPSHOTS)
_recommendations: deque[dict[str, Any]] = deque(maxlen=_MAX_RECOMMENDATIONS)
_events: deque[dict[str, Any]] = deque(maxlen=_MAX_EVENTS)

_total_incidents_created = 0
_total_critical = 0
_total_high = 0
_total_warning = 0
_total_info = 0
_last_prune_ts: float = 0.0


def _now() -> float:
    return time.time()


def _prune_stores(*, now: float | None = None) -> None:
    ts = now if now is not None else _now()
    global _last_prune_ts
    if ts - _last_prune_ts < 60.0:
        return
    _last_prune_ts = ts
    cutoff = ts - _STORE_TTL
    while _events and _events[0].get("timestamp", 0) < cutoff:
        _events.popleft()


def _incident_id() -> str:
    global _total_incidents_created
    _total_incidents_created += 1
    return f"TRIAGE-{int(_now())}-{_total_incidents_created}"


def _snapshot_id() -> str:
    return f"SNAP-{int(_now())}-{len(_snapshots)}"


# ── Signal Readers (fail-safe) ─────────────────────────────────

def _safe_read_guard_state() -> dict[str, Any]:
    try:
        from runtime.federation.federation_guards import get_federation_guard_summary
        return get_federation_guard_summary()
    except Exception:
        return {"state": "unknown", "state_transitions_total": 0, "replay_detections_total": 0, "storm_detections_total": 0}


def _safe_read_evidence_summary() -> dict[str, Any]:
    try:
        from runtime.federation.federation_observability import get_evidence_summary
        return get_evidence_summary()
    except Exception:
        return {"total_evidences": 0, "invalid_lineage_total": 0}


def _safe_read_slo_status() -> dict[str, Any]:
    try:
        from runtime.slo.cognitive_slo import get_slo_status
        return get_slo_status()
    except Exception:
        return {"slo_state": "unknown", "violations_total": 0, "degraded_total": 0, "safe_mode_total": 0}


def _safe_read_architecture_summary() -> dict[str, Any]:
    try:
        from runtime.governance.architecture_governance import get_architecture_summary
        return get_architecture_summary()
    except Exception:
        return {"hotspots": [], "violations": [], "total_hotspots": 0, "total_violations": 0}


def _safe_read_governance_registry() -> dict[str, Any]:
    try:
        from runtime.governance.runtime_governance_registry import build_runtime_governance_registry
        reg = build_runtime_governance_registry()
        return {
            "score": reg.get("governance_score", {}).get("score", 0),
            "degraded_domains": reg.get("governance_health", {}).get("degraded_domains", []),
            "risks": reg.get("governance_risks", []),
        }
    except Exception:
        return {"score": 0, "degraded_domains": [], "risks": []}


def _safe_read_model_registry() -> dict[str, Any]:
    try:
        from runtime.state.lmstudio_state import get_model_tracker
        tracker = get_model_tracker()
        raw = tracker.to_dict() if hasattr(tracker, "to_dict") else {}
        models = raw.get("models", {}) if raw else {}
        active = sum(1 for m in models.values() if isinstance(m, dict) and m.get("status") == "active") if models else 0
        errors = sum(1 for m in models.values() if isinstance(m, dict) and m.get("status") == "error") if models else 0
        return {"total_models": len(models), "models_active": active, "models_error": errors, "raw": raw}
    except Exception:
        return {"total_models": 0, "models_active": 0, "models_error": 0}


def _safe_read_observability_incidents() -> list[dict[str, Any]]:
    try:
        from runtime.incidents.incident_intelligence import build_incident_intelligence_report
        report = build_incident_intelligence_report()
        return report.get("active_incidents", [])
    except Exception:
        return []


def _safe_read_degradation_level() -> int:
    try:
        from runtime.slo.degradation import get_degraded_state
        state = get_degraded_state()
        if isinstance(state, dict):
            return int(state.get("current_level", 0))
        return 0
    except Exception:
        return 0


def _safe_read_topology_drift() -> list[dict[str, Any]]:
    try:
        from runtime.topology.runtime_topology import detect_topology_drift
        return detect_topology_drift()
    except Exception:
        return []


def _safe_read_observability_health() -> dict[str, Any]:
    try:
        from runtime.observability.live_diagnostics import calculate_live_observability_score
        return calculate_live_observability_score()
    except Exception:
        return {"observability_score": 0, "incidents": [], "flapping_exporters": []}


def _safe_read_evidence_hotspots() -> dict[str, Any]:
    try:
        from runtime.federation.federation_observability import get_evidence_hotspots
        return get_evidence_hotspots()
    except Exception:
        return {"top_reused": [], "deepest": [], "replay_hot": []}


def _safe_read_infrastructure_registry() -> dict[str, Any]:
    try:
        from runtime.infrastructure.infrastructure_identity_registry import build_infrastructure_identity_registry
        return build_infrastructure_identity_registry()
    except Exception:
        return {"operational_nodes": [], "inventory_only_nodes": []}


def _safe_read_architecture_violations() -> list[dict[str, Any]]:
    try:
        from runtime.governance.architecture_governance import get_architecture_violations
        violations = get_architecture_violations()
        if isinstance(violations, dict):
            return violations.get("violations", [])
        return []
    except Exception:
        return []


def _safe_read_guard_events() -> list[dict[str, Any]]:
    try:
        from runtime.federation.federation_guards import get_federation_guard_events
        events = get_federation_guard_events()
        if isinstance(events, dict):
            return events.get("events", [])
        return []
    except Exception:
        return []


def _safe_read_slo_violations() -> list[dict[str, Any]]:
    try:
        from runtime.slo.cognitive_slo import get_slo_violations
        violations = get_slo_violations()
        if isinstance(violations, dict):
            return violations.get("violations", [])
        return []
    except Exception:
        return []


def _safe_read_circuit_breaker_state() -> dict[str, Any]:
    try:
        from runtime.slo.circuit_breakers import get_all_states
        states = get_all_states()
        if isinstance(states, dict):
            return states
        return {"circuit_breakers": []}
    except Exception:
        return {"circuit_breakers": []}


def _safe_read_slo_runtime_health() -> dict[str, Any]:
    try:
        from runtime.slo.runtime_slo import get_runtime_health
        return get_runtime_health()
    except Exception:
        return {"state": "unknown", "degradation_level": 0, "ttfb_p50": 0, "timeout_rate": 0}


# ── Severity Scoring ────────────────────────────────────────────

def _calculate_severity(signals: dict[str, Any]) -> str:
    if signals.get("safe_mode_active"):
        return Severity.CRITICAL.value
    if signals.get("guard_state") in ("safe_mode", "constrained"):
        return Severity.HIGH.value
    if (signals.get("slo_violations", 0) > 5) or (signals.get("slo_degraded", 0) > 3):
        return Severity.HIGH.value
    if signals.get("gateway_down") or signals.get("lmstudio_down"):
        return Severity.CRITICAL.value
    if signals.get("replay_detections", 0) > 10:
        return Severity.CRITICAL.value
    if signals.get("storm_detections", 0) > 5:
        return Severity.CRITICAL.value
    if signals.get("invalid_lineage", 0) > 20:
        return Severity.HIGH.value
    if signals.get("registry_inconsistent"):
        return Severity.WARNING.value
    if signals.get("governance_violations", 0) > 0:
        return Severity.WARNING.value
    if signals.get("architecture_hotspots", 0) > 3:
        return Severity.WARNING.value
    if signals.get("slo_violations", 0) > 0:
        return Severity.WARNING.value
    return Severity.INFO.value


def _calculate_blast_radius(signals: dict[str, Any]) -> str:
    guard_state = signals.get("guard_state", "normal")
    if guard_state in ("safe_mode",):
        return BlastRadius.PLATFORM.value
    if guard_state in ("constrained",):
        return BlastRadius.RUNTIME.value
    if signals.get("replay_detections", 0) > 5 or signals.get("storm_detections", 0) > 3:
        return BlastRadius.FEDERATION.value
    if signals.get("gateway_down") or signals.get("lmstudio_down"):
        return BlastRadius.PLATFORM.value
    if signals.get("topology_drift_count", 0) > 0:
        return BlastRadius.RUNTIME.value
    if signals.get("governance_violations", 0) > 0:
        return BlastRadius.FEDERATION.value
    return BlastRadius.LOCAL.value


def _calculate_confidence(signals: dict[str, Any]) -> float:
    sources = 0
    total = 0
    for key in ("guard_state_available", "slo_available", "evidence_available", "architecture_available"):
        total += 1
        if signals.get(key):
            sources += 1
    if total == 0:
        return 0.3
    base = sources / total
    penalty = 0.0
    if signals.get("guard_state") in ("unknown",):
        penalty += 0.1
    if signals.get("slo_violations", 0) > 10:
        penalty += 0.1
    return max(0.1, min(1.0, base - penalty))


def _calculate_priority(severity: str, blast_radius: str, confidence: float) -> int:
    sev_map = {"critical": 5, "high": 4, "warning": 3, "info": 1}
    br_map = {"platform": 5, "runtime": 4, "federation": 3, "local": 1}
    base = sev_map.get(severity, 1) + br_map.get(blast_radius, 1)
    if confidence < 0.3:
        base = max(1, base - 1)
    return min(10, base)


def _needs_escalation(severity: str, blast_radius: str) -> bool:
    return severity in ("critical",) or (severity == "high" and blast_radius in ("platform", "runtime"))


# ── Root Cause Heuristics ───────────────────────────────────────

_ROOT_CAUSE_HEURISTICS: list[dict[str, Any]] = [
    {"id": "RC-REPLAY", "label": "replay amplification", "check": "replay_detections", "threshold": 5},
    {"id": "RC-STALE", "label": "stale evidence propagation", "check": "invalid_lineage", "threshold": 10},
    {"id": "RC-LMSTUDIO", "label": "LM Studio unavailable", "check": "lmstudio_down", "threshold": 1},
    {"id": "RC-REGISTRY", "label": "registry inconsistency", "check": "registry_inconsistent", "threshold": 1},
    {"id": "RC-COUPLING", "label": "excessive architecture coupling", "check": "architecture_hotspots", "threshold": 5},
    {"id": "RC-SAFEMODE", "label": "SAFE_MODE saturation", "check": "safe_mode_active", "threshold": 1},
    {"id": "RC-STORM", "label": "storm heuristic escalation", "check": "storm_detections", "threshold": 5},
    {"id": "RC-GATEWAY", "label": "gateway unavailable", "check": "gateway_down", "threshold": 1},
    {"id": "RC-GUARD", "label": "degraded federation recovery", "check": "guard_state", "threshold": 3},
    {"id": "RC-SLO", "label": "SLO violation accumulation", "check": "slo_violations", "threshold": 5},
]

_REMEDIATION_HINTS: dict[str, list[str]] = {
    "replay amplification": [
        "Inspect federation replay amplification in guard events",
        "Review evidence lineage depth and replay risk scores",
        "Consider increasing replay detection thresholds",
    ],
    "stale evidence propagation": [
        "Validate evidence freshness and decay configuration",
        "Inspect stale evidence hotspots in federation observability",
        "Review evidence lineage max depth and TTL settings",
    ],
    "LM Studio unavailable": [
        "Validate LM Studio availability on inference node",
        "Check LM Studio process and model loading status",
        "Inspect model status tracker for error states",
    ],
    "registry inconsistency": [
        "Review model registry consistency across nodes",
        "Validate canonical model registry against LM Studio state",
        "Check for deprecated aliases or missing models",
    ],
    "excessive architecture coupling": [
        "Review architecture governance violations",
        "Inspect hotspot modules with high coupling scores",
        "Consider refactoring critical modules (GOV-ARCH-001 to 006)",
    ],
    "SAFE_MODE saturation": [
        "Investigate federation guard SAFE_MODE triggers",
        "Review guard events for repeated authority escalations",
        "Consider increasing federation propagation caps",
    ],
    "storm heuristic escalation": [
        "Inspect storm detection events in federation guards",
        "Review federation propagation patterns and burst thresholds",
        "Consider tuning storm detection sensitivity",
    ],
    "gateway unavailable": [
        "Check gateway process and systemd service status",
        "Verify port 8008 is not occupied by rogue uvicorn",
        "Inspect gateway startup logs for boot failures",
    ],
    "degraded federation recovery": [
        "Review federation guard state transitions",
        "Inspect federation observability for recovery patterns",
        "Validate trust propagation and authority binding",
    ],
    "SLO violation accumulation": [
        "Review SLO violation timeline for patterns",
        "Inspect TTFB, timeout rate, and GPU pressure metrics",
        "Consider adjusting SLO thresholds or increasing resources",
    ],
}


def _detect_root_causes(signals: dict[str, Any]) -> list[str]:
    causes: list[str] = []
    for h in _ROOT_CAUSE_HEURISTICS:
        check_key = h["check"]
        raw = signals.get(check_key, 0)
        if isinstance(raw, str):
            if raw in ("safe_mode", "constrained", "degraded") and h["id"] == "RC-GUARD":
                causes.append(h["label"])
            continue
        try:
            if int(raw) >= int(h["threshold"]):
                causes.append(h["label"])
        except (ValueError, TypeError):
            if raw:
                causes.append(h["label"])
    return causes


def _build_remediation_hints(root_causes: list[str]) -> list[str]:
    hints: list[str] = []
    for cause in root_causes:
        for key, vals in _REMEDIATION_HINTS.items():
            if key in cause or cause in key:
                hints.extend(vals)
                break
    return hints[:8]


# ── Category Detection ──────────────────────────────────────────

def _detect_category(signals: dict[str, Any]) -> str:
    if signals.get("gateway_down"):
        return "gateway_availability"
    if signals.get("lmstudio_down"):
        return "lmstudio_availability"
    if signals.get("safe_mode_active"):
        return "federation_safe_mode"
    if signals.get("replay_detections", 0) > 5:
        return "replay_amplification"
    if signals.get("storm_detections", 0) > 3:
        return "storm_escalation"
    if signals.get("invalid_lineage", 0) > 10:
        return "evidence_corruption"
    if signals.get("registry_inconsistent"):
        return "registry_inconsistency"
    if signals.get("governance_violations", 0) > 0:
        return "governance_violation"
    if signals.get("architecture_hotspots", 0) > 3:
        return "architecture_coupling"
    if signals.get("slo_violations", 0) > 0:
        return "slo_degradation"
    if signals.get("guard_state") in ("constrained", "degraded"):
        return "guard_degradation"
    if signals.get("topology_drift_count", 0) > 0:
        return "topology_drift"
    return "observability_observation"


def _detect_degraded_components(signals: dict[str, Any]) -> list[str]:
    comps: list[str] = []
    if signals.get("guard_state") in ("safe_mode", "constrained", "degraded"):
        comps.append("federation_guards")
    if signals.get("gateway_down"):
        comps.append("gateway")
    if signals.get("lmstudio_down"):
        comps.append("lmstudio")
    if signals.get("registry_inconsistent"):
        comps.append("model_registry")
    if signals.get("topology_drift_count", 0) > 0:
        comps.append("topology")
    if signals.get("architecture_hotspots", 0) > 3:
        comps.append("architecture")
    return comps[:8]


# ── Main Triage Engine ──────────────────────────────────────────

def build_runtime_triage_snapshot(*, now: float | None = None) -> dict[str, Any]:
    ts = now if now is not None else _now()
    _prune_stores(now=ts)

    guard = _safe_read_guard_state()
    evidence = _safe_read_evidence_summary()
    slo = _safe_read_slo_status()
    arch = _safe_read_architecture_summary()
    governance = _safe_read_governance_registry()
    model_reg = _safe_read_model_registry()
    degradation_level = _safe_read_degradation_level()
    topology_drift = _safe_read_topology_drift()
    obs_health = _safe_read_observability_health()
    evidence_hotspots = _safe_read_evidence_hotspots()
    infra = _safe_read_infrastructure_registry()
    arch_violations = _safe_read_architecture_violations()
    guard_events = _safe_read_guard_events()
    slo_violations = _safe_read_slo_violations()
    circuit_breakers = _safe_read_circuit_breaker_state()
    slo_runtime = _safe_read_slo_runtime_health()
    observability_incidents = _safe_read_observability_incidents()

    guard_state = guard.get("state", "unknown")
    guard_state_available = guard_state != "unknown"
    replay_detections = int(guard.get("replay_detections_total", 0))
    storm_detections = int(guard.get("storm_detections_total", 0))
    safe_mode_active = guard_state == "safe_mode"

    total_evidences = int(evidence.get("total_evidences", 0))
    invalid_lineage = int(evidence.get("invalid_lineage_total", 0))
    evidence_available = total_evidences > 0

    slo_state = slo.get("slo_state", "unknown")
    slo_violations_total = int(slo.get("violations_total", 0))
    slo_degraded_total = int(slo.get("degraded_total", 0))
    slo_safe_mode_total = int(slo.get("safe_mode_total", 0))
    slo_available = slo_state != "unknown"

    total_hotspots = int(arch.get("total_hotspots", 0))
    total_violations = int(arch.get("total_violations", 0))
    architecture_available = total_hotspots > 0 or total_violations > 0

    governance_score = float(governance.get("score", 0))
    degraded_domains = governance.get("degraded_domains", [])
    risks = governance.get("risks", [])

    model_total = int(model_reg.get("total_models", 0))
    model_errors = int(model_reg.get("models_error", 0))
    lmstudio_down = model_total == 0 or model_errors > 2
    registry_inconsistent = model_errors > 0

    gateway_down = slo_runtime.get("state", "").lower() in ("down", "error", "unavailable")
    topology_drift_count = len(topology_drift)
    obs_score = float(obs_health.get("observability_score", 0))
    governance_violations = len(arch_violations)
    replay_hotspots_data = evidence_hotspots.get("top_reused", []) or []
    replay_hotspots_count = len(replay_hotspots_data)

    signals: dict[str, Any] = {
        "guard_state": guard_state,
        "guard_state_available": guard_state_available,
        "replay_detections": replay_detections,
        "storm_detections": storm_detections,
        "safe_mode_active": safe_mode_active,
        "total_evidences": total_evidences,
        "invalid_lineage": invalid_lineage,
        "evidence_available": evidence_available,
        "slo_state": slo_state,
        "slo_violations": slo_violations_total,
        "slo_degraded": slo_degraded_total,
        "slo_safe_mode": slo_safe_mode_total,
        "slo_available": slo_available,
        "total_hotspots": total_hotspots,
        "architecture_hotspots": total_hotspots,
        "total_violations": total_violations,
        "architecture_available": architecture_available,
        "governance_score": governance_score,
        "degraded_domains": degraded_domains,
        "governance_violations": governance_violations,
        "model_total": model_total,
        "model_errors": model_errors,
        "lmstudio_down": lmstudio_down,
        "registry_inconsistent": registry_inconsistent,
        "gateway_down": gateway_down,
        "topology_drift_count": topology_drift_count,
        "obs_score": obs_score,
        "replay_hotspots": replay_hotspots_count,
    }

    severity = _calculate_severity(signals)
    blast_radius = _calculate_blast_radius(signals)
    confidence = _calculate_confidence(signals)
    priority = _calculate_priority(severity, blast_radius, confidence)
    escalation = _needs_escalation(severity, blast_radius)
    root_causes = _detect_root_causes(signals)
    remediation_hints = _build_remediation_hints(root_causes)
    category = _detect_category(signals)
    degraded_components = _detect_degraded_components(signals)

    correlated_alerts = sorted(set(
        [f"guard:{e.get('event_type', 'unknown')}" for e in guard_events[:5]]
        + [f"violation:{v.get('id', 'unknown')}" for v in arch_violations[:3]]
        + [f"slo:{v.get('slo_name', 'unknown')}" for v in slo_violations[:3]]
    ))

    correlated_slos = sorted(set(
        [v.get("slo_name", "") for v in slo_violations[:5] if v.get("slo_name")]
    ))

    evidence_refs = sorted(set(
        [f"evidence:{h.get('evidence_id', 'unknown')}" for h in replay_hotspots_data[:5] if isinstance(h, dict)]
    ))

    incident = TriageIncident(
        incident_id=_incident_id(),
        severity=severity,
        category=category,
        source="autonomous_triage",
        created_at=ts,
        updated_at=ts,
        blast_radius=blast_radius,
        confidence=confidence,
        correlated_alerts=correlated_alerts,
        correlated_slos=correlated_slos,
        correlated_guard_state=guard_state,
        architecture_hotspots=[h.get("module", "") for h in (arch.get("hotspots", []) or [])[:5] if isinstance(h, dict)],
        probable_root_causes=root_causes,
        remediation_hints=remediation_hints,
        evidence_refs=evidence_refs,
        degraded_components=degraded_components,
        federation_state=guard_state,
        registry_state="inconsistent" if registry_inconsistent else "consistent",
        lmstudio_state="down" if lmstudio_down else "up",
        recommended_priority=priority,
        escalation_required=escalation,
        operational_impact=f"{category}: {blast_radius} blast radius, confidence {confidence:.2f}",
    )

    with _lock:
        _incidents.append(incident)
        global _total_critical, _total_high, _total_warning, _total_info
        if severity == "critical":
            _total_critical += 1
        elif severity == "high":
            _total_high += 1
        elif severity == "warning":
            _total_warning += 1
        else:
            _total_info += 1

        severity_dist = {
            "critical": _total_critical,
            "high": _total_high,
            "warning": _total_warning,
            "info": _total_info,
        }

        br_counts: dict[str, int] = defaultdict(int)
        for inc in _incidents:
            br_counts[inc.blast_radius] = br_counts.get(inc.blast_radius, 0) + 1

        cat_counts: dict[str, int] = defaultdict(int)
        for inc in _incidents:
            cat_counts[inc.category] = cat_counts.get(inc.category, 0) + 1
        top_cats = sorted(cat_counts, key=cat_counts.get, reverse=True)[:5]

        platforms = br_counts.get("platform", 0)
        federations = br_counts.get("federation", 0)
        runtimes = br_counts.get("runtime", 0)
        locals_c = br_counts.get("local", 0)

        lmstudio_related = sum(1 for i in _incidents if i.lmstudio_state == "down" or "lmstudio" in i.category)
        registry_related = sum(1 for i in _incidents if i.registry_state == "inconsistent" or "registry" in i.category)

        sources_available: list[str] = []
        sources_unavailable: list[str] = []
        if guard_state_available:
            sources_available.append("federation_guards")
        else:
            sources_unavailable.append("federation_guards")
        if slo_available:
            sources_available.append("cognitive_slo")
        else:
            sources_unavailable.append("cognitive_slo")
        if evidence_available:
            sources_available.append("evidence_lineage")
        else:
            sources_unavailable.append("evidence_lineage")
        if architecture_available:
            sources_available.append("architecture_governance")
        else:
            sources_unavailable.append("architecture_governance")
        if governance.get("score", 0) > 0:
            sources_available.append("governance_registry")
        else:
            sources_unavailable.append("governance_registry")
        if model_total > 0:
            sources_available.append("model_registry")
        else:
            sources_unavailable.append("model_registry")

        snapshot = TriageSnapshot(
            snapshot_id=_snapshot_id(),
            timestamp=ts,
            total_incidents=len(_incidents),
            critical_count=_total_critical,
            high_count=_total_high,
            warning_count=_total_warning,
            info_count=_total_info,
            platform_blast_count=platforms,
            federation_blast_count=federations,
            runtime_blast_count=runtimes,
            local_blast_count=locals_c,
            lmstudio_related_count=lmstudio_related,
            registry_related_count=registry_related,
            severity_distribution=dict(severity_dist),
            blast_radius_distribution=dict(br_counts),
            top_categories=top_cats,
            guard_state=guard_state,
            governance_score=governance_score,
            slo_status=slo_state,
            degradation_level=degradation_level,
            sources_available=sources_available,
            sources_unavailable=sources_unavailable,
        )
        _snapshots.append(snapshot)

    return {
        "snapshot": snapshot.to_dict(),
        "incident": incident.to_dict(),
        "signals": {k: v for k, v in signals.items() if not k.startswith("_")},
    }


def get_active_triage_incidents(*, now: float | None = None) -> list[dict[str, Any]]:
    _prune_stores(now=now)
    with _lock:
        return [i.to_dict() for i in _incidents]


def get_triage_summary(*, now: float | None = None) -> dict[str, Any]:
    _prune_stores(now=now)
    with _lock:
        severity_dist: dict[str, int] = defaultdict(int)
        br_dist: dict[str, int] = defaultdict(int)
        sorted_incidents = sorted(_incidents, key=lambda i: i.recommended_priority, reverse=True)

        for inc in _incidents:
            severity_dist[inc.severity] += 1
            br_dist[inc.blast_radius] += 1

        top_priority_incidents = [i.to_dict() for i in sorted_incidents[:5]]

        return {
            "total_incidents": len(_incidents),
            "severity_distribution": dict(severity_dist),
            "blast_radius_distribution": dict(br_dist),
            "top_priority_incidents": top_priority_incidents,
            "total_critical": severity_dist.get("critical", 0),
            "total_high": severity_dist.get("high", 0),
            "total_warning": severity_dist.get("warning", 0),
            "total_info": severity_dist.get("info", 0),
            "contract_version": TRIAGE_CONTRACT_VERSION,
            "snapshots_available": len(_snapshots),
        }


def get_triage_recommendations(*, now: float | None = None) -> list[dict[str, Any]]:
    _prune_stores(now=now)
    with _lock:
        if _recommendations:
            return list(_recommendations)

        recommendations: list[dict[str, Any]] = []
        for inc in sorted(_incidents, key=lambda i: i.recommended_priority, reverse=True)[:20]:
            for hint in inc.remediation_hints:
                recommendations.append({
                    "incident_id": inc.incident_id,
                    "severity": inc.severity,
                    "blast_radius": inc.blast_radius,
                    "recommendation": hint,
                    "category": inc.category,
                    "confidence": inc.confidence,
                    "timestamp": inc.updated_at,
                })

        if not recommendations:
            recommendations.append({
                "incident_id": "noop",
                "severity": "info",
                "blast_radius": "local",
                "recommendation": "No active incidents requiring remediation",
                "category": "healthy",
                "confidence": 1.0,
                "timestamp": now if now is not None else _now(),
            })

        _recommendations.extend(recommendations[:50])
        return recommendations


def get_triage_snapshots(*, limit: int = 10, now: float | None = None) -> list[dict[str, Any]]:
    _prune_stores(now=now)
    with _lock:
        return [s.to_dict() for s in list(_snapshots)[-int(max(1, min(limit, 128))):]]


def get_triage_metrics() -> dict[str, Any]:
    with _lock:
        return {
            "ailab_triage_incidents_total": float(len(_incidents)),
            "ailab_triage_critical_total": float(_total_critical),
            "ailab_triage_high_total": float(_total_high),
            "ailab_triage_warning_total": float(_total_warning),
            "ailab_triage_info_total": float(_total_info),
            "ailab_triage_snapshots_total": float(len(_snapshots)),
            "ailab_triage_recommendations_total": float(len(_recommendations)),
            "ailab_triage_lmstudio_related_total": float(sum(1 for i in _incidents if i.lmstudio_state == "down" or "lmstudio" in i.category)),
            "ailab_triage_registry_related_total": float(sum(1 for i in _incidents if i.registry_state == "inconsistent" or "registry" in i.category)),
        }


def record_triage_metrics() -> None:
    try:
        from runtime.telemetry.prometheus_metrics import record_triage_prometheus_metrics
        record_triage_prometheus_metrics(get_triage_metrics())
    except Exception:
        pass


def reset_triage_runtime(*, now: float | None = None) -> dict[str, Any]:
    global _incidents, _snapshots, _recommendations, _events
    global _total_incidents_created, _total_critical, _total_high, _total_warning, _total_info
    ts = now if now is not None else _now()
    with _lock:
        _incidents.clear()
        _snapshots.clear()
        _recommendations.clear()
        _events.clear()
        _total_incidents_created = 0
        _total_critical = 0
        _total_high = 0
        _total_warning = 0
        _total_info = 0
        _last_prune_ts = ts
    return {"status": "reset", "timestamp": ts, "contract_version": TRIAGE_CONTRACT_VERSION}
