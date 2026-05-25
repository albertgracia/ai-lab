"""FASE 37E: GOVERNANCE-DRIFT-DETECTION-01

Bounded, deterministic, metadata-only governance drift detection for AI-LAB.

Goals:
- Consume 37B/37C/37D internally (Python function calls, not HTTP).
- Compute per-domain governance drift scores from correlation, critical-path,
  hotspot history, SLO, and triage signals.
- Maintain a bounded in-memory store of drift events (no persistence).
- Provide recommendations when governance expectations drift from runtime reality.

Non-goals:
- No routing mutation, no remediation, no background loops/daemons.
- No writes to runtime/state/* or snapshots/*.
- No unbounded persistence.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from typing import Any


GOVERNANCE_DRIFT_CONTRACT_VERSION = "37E-GOVERNANCE-DRIFT-DETECTION-01"

_EVENTS_LOCK = Lock()
_EVENTS: deque[dict[str, Any]] = deque(maxlen=128)

_SNAPSHOT_CACHE_LOCK = Lock()
_SNAPSHOT_CACHE: dict[str, Any] | None = None
_SNAPSHOT_CACHE_TS = 0.0
_SNAPSHOT_CACHE_TTL_S = 15.0

_MAX_DOMAINS = 20
_MAX_EVENTS_PER_ENDPOINT = 25
_MAX_RECOMMENDATIONS = 10


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


def _parse_limit(q: Any, default: int, *, lo: int, hi: int) -> int:
    try:
        v = int(q)
    except Exception:
        v = int(default)
    return int(max(lo, min(hi, v)))


def _expectation_key(domain: str) -> str:
    return f"gov_expectation::{domain}"


@dataclass(frozen=True)
class GovernanceDriftEvent:
    domain: str
    drift_score: float
    previous_score: float | None
    signal_sources: list[str]
    severity: str
    inferred: list[str]
    unknowns: list[str]
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "drift_score": round(float(self.drift_score), 3),
            "previous_score": round(float(self.previous_score), 3) if self.previous_score is not None else None,
            "signal_sources": list(self.signal_sources),
            "severity": self.severity,
            "inferred": list(self.inferred),
            "unknowns": sorted(set(self.unknowns)),
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class DomainDriftResult:
    domain: str
    current_score: float
    governance_risk: str
    blast_radius: str
    correlation_hotspot: bool
    health_delta: float
    slo_impact: float
    triage_count: int
    chokepoint_count: int
    drift_score: float
    severity: str
    signal_sources: list[str]
    inferred: list[str]
    unknowns: list[str]


def _read_signal_bundle() -> tuple[dict[str, Any], list[str], list[str]]:
    """Read inputs from 37B/37C/37D + SLO + Triage.

    Returns (bundle, unknowns, unavailable_fields).
    """
    unknowns: list[str] = []
    unavailable_fields: list[str] = []

    # 37B: correlation
    try:
        from runtime.correlation.graph_runtime_correlation import (
            build_graph_runtime_correlation_snapshot,
            get_correlated_hotspots,
        )
        corr = build_graph_runtime_correlation_snapshot()
        corr_hotspots = get_correlated_hotspots()
    except Exception:
        corr = {"status": "degraded", "correlation_score": 0.0, "unknowns": ["correlation_unavailable"], "unavailable_fields": ["correlation_unavailable"]}
        corr_hotspots = {"status": "degraded", "hotspots": [], "unknowns": ["correlation_hotspots_unavailable"]}
        unknowns.append("correlation_unavailable")
        unavailable_fields.append("correlation")

    # 37C: critical-path
    try:
        from runtime.critical_path.critical_path_analysis import (
            build_critical_path_snapshot,
            get_critical_path_chokepoints,
        )
        cp = build_critical_path_snapshot(top_n=10)
        chok = get_critical_path_chokepoints(top_n=10)
    except Exception:
        cp = {"status": "degraded", "score": 0.0, "severity": "INFO", "top_files": [], "unknowns": ["critical_path_unavailable"], "unavailable_fields": ["critical_path"]}
        chok = {"status": "degraded", "chokepoints": [], "unknowns": ["chokepoints_unavailable"]}
        unknowns.append("critical_path_unavailable")
        unavailable_fields.append("critical_path")

    # 37D: hotspot history
    try:
        from runtime.hotspot_history.hotspot_history import (
            get_hotspot_drift,
            get_hotspot_trends,
            get_recurring_hotspots,
        )
        drift_37d = get_hotspot_drift(window=10)
        trends = get_hotspot_trends(limit=10, top_n=10)
        recurring = get_recurring_hotspots(limit=10, min_recurrence=3)
    except Exception:
        drift_37d = {"drift_score": 0.0, "unknowns": ["hotspot_drift_unavailable"]}
        trends = {"trends": [], "unknowns": ["hotspot_trends_unavailable"]}
        recurring = {"recurring": [], "unknowns": ["hotspot_recurring_unavailable"]}
        unknowns.append("hotspot_history_unavailable")
        unavailable_fields.append("hotspot_history")

    # SLO
    try:
        from runtime.slo.cognitive_slo import get_slo_status
        slo = get_slo_status() or {}
    except Exception:
        slo = {"overall_status": "unknown", "violations_total": 0}
        unknowns.append("slo_unavailable")

    # Triage
    try:
        from runtime.triage.autonomous_triage import get_triage_summary
        triage = get_triage_summary() or {}
    except Exception:
        triage = {"total_incidents": 0, "total_critical": 0, "total_high": 0}
        unknowns.append("triage_unavailable")

    # Architecture governance
    try:
        from runtime.governance.architecture_governance import get_architecture_summary
        arch = get_architecture_summary() or {}
    except Exception:
        arch = {"status": "degraded", "unknowns": ["architecture_unavailable"]}
        unknowns.append("architecture_unavailable")

    bundle = {
        "correlation": corr,
        "correlation_hotspots": corr_hotspots,
        "critical_path": cp,
        "chokepoints": chok,
        "hotspot_drift": drift_37d,
        "hotspot_trends": trends,
        "hotspot_recurring": recurring,
        "slo": slo,
        "triage": triage,
        "architecture": arch,
    }
    return bundle, sorted(set(unknowns)), sorted(set(unavailable_fields))


def _extract_domain_score(d: dict[str, Any]) -> float:
    return _safe_float(d.get("score"), _safe_float(d.get("current_score"), _safe_float(d.get("max_score"), 0.0)))


def _domain_from_item(item: dict[str, Any]) -> str:
    fp = item.get("file_path")
    if isinstance(fp, str) and fp:
        parts = fp.split("/")
        if len(parts) >= 2 and parts[0] == "runtime":
            return parts[1]
    dom = item.get("domain")
    if isinstance(dom, str) and dom:
        return dom
    mod = item.get("module")
    if isinstance(mod, str) and mod:
        return mod
    return "other"


def _analyze_domains(
    bundle: dict[str, Any],
    global_unknowns: list[str],
) -> tuple[list[DomainDriftResult], list[str]]:
    """Per-domain drift analysis from signal bundle.

    Returns (results, inferred).
    """
    corr = bundle["correlation"]
    corr_hotspots_list = (bundle["correlation_hotspots"].get("hotspots") if isinstance(bundle["correlation_hotspots"], dict) else []) or []
    cp_top = (bundle["critical_path"].get("top_files") if isinstance(bundle["critical_path"], dict) else []) or []
    chok_list = (bundle["chokepoints"].get("chokepoints") if isinstance(bundle["chokepoints"], dict) else []) or []
    trends_list = (bundle["hotspot_trends"].get("trends") if isinstance(bundle["hotspot_trends"], dict) else []) or []
    recurring_list = (bundle["hotspot_recurring"].get("recurring") if isinstance(bundle["hotspot_recurring"], dict) else []) or []
    slo = bundle["slo"]
    triage = bundle["triage"]
    arch = bundle["architecture"]

    cp_score = _safe_float(cp_top[0].get("score") if cp_top else 0.0, 0.0)
    corr_score = _safe_float(corr.get("correlation_score"), 0.0)
    slo_status = str(slo.get("overall_status") or "unknown")
    triage_critical = _safe_int(triage.get("total_critical"), 0)
    triage_high = _safe_int(triage.get("total_high"), 0)
    violations = (arch.get("governance_violations") if isinstance(arch, dict) else []) or []
    arch_hotspots = (arch.get("hotspots") if isinstance(arch, dict) else []) or []

    # Gather domain -> signals mapping
    domain_signals: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "cp_files": [], "chokepoints": [], "trends": [], "recurring": [],
        "correlation_hotspot": False, "governance_violation": False,
        "arch_hotspot": False, "max_severity": "INFO",
    })

    for f in cp_top:
        if not isinstance(f, dict):
            continue
        dom = _domain_from_item(f)
        domain_signals[dom]["cp_files"].append(f)
        sev = str(f.get("severity") or "INFO")
        order = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        if order.get(sev, 0) > order.get(domain_signals[dom]["max_severity"], 0):
            domain_signals[dom]["max_severity"] = sev

    for c in chok_list:
        if not isinstance(c, dict):
            continue
        dom = _domain_from_item(c)
        domain_signals[dom]["chokepoints"].append(c)
        sev = str(c.get("severity") or "INFO")
        order = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        if order.get(sev, 0) > order.get(domain_signals[dom]["max_severity"], 0):
            domain_signals[dom]["max_severity"] = sev

    for t in trends_list:
        if not isinstance(t, dict):
            continue
        dom = t.get("module")
        if isinstance(dom, str) and dom:
            dom = _domain_from_item({"file_path": dom})
            domain_signals[dom]["trends"].append(t)

    for r in recurring_list:
        if not isinstance(r, dict):
            continue
        dom = r.get("module")
        if isinstance(dom, str) and dom:
            dom = _domain_from_item({"file_path": dom})
            domain_signals[dom]["recurring"].append(r)

    for h in corr_hotspots_list:
        if not isinstance(h, dict):
            continue
        dom = _domain_from_item(h)
        domain_signals[dom]["correlation_hotspot"] = True

    for v in violations:
        if not isinstance(v, dict):
            continue
        dom = str(v.get("module") or "")
        if dom:
            domain_signals[dom]["governance_violation"] = True

    for h in arch_hotspots:
        if not isinstance(h, dict):
            continue
        dom = str(h.get("module") or "")
        if dom:
            domain_signals[dom]["arch_hotspot"] = True

    # Compute per-domain drift
    results: list[DomainDriftResult] = []
    global_inferred: list[str] = []
    domain_order = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    br_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    for domain, signals in sorted(domain_signals.items()):
        if not domain:
            continue

        cp_files = signals["cp_files"]
        chokepoints = signals["chokepoints"]
        trend_count = len(signals["trends"])
        recurring_count = len(signals["recurring"])
        is_corr_hotspot = signals["correlation_hotspot"]
        has_violation = signals["governance_violation"]
        is_arch_hotspot = signals["arch_hotspot"]
        max_sev = signals["max_severity"]

        # Domain current score: average of CP scores + correlation boost
        domain_cp_scores = [_extract_domain_score(f) for f in cp_files] + [_safe_float(c.get("score"), 0.0) for c in chokepoints]
        domain_cp_avg = sum(domain_cp_scores) / max(len(domain_cp_scores), 1)

        # Governance risk from architecture violations
        gov_risk: str = "low"
        if has_violation:
            gov_risk = "critical"
        elif is_arch_hotspot:
            gov_risk = "high"
        elif is_corr_hotspot:
            gov_risk = "medium"

        # Blast radius: max across CP files
        br: str = "low"
        for f in cp_files:
            fbr = str(f.get("blast_radius") or "low").lower()
            if br_order.get(fbr, 0) > br_order.get(br, 0):
                br = fbr
        for c in chokepoints:
            cbr = str(c.get("blast_radius") or "low").lower()
            if br_order.get(cbr, 0) > br_order.get(br, 0):
                br = cbr

        # Health delta: CP score vs correlation expectation
        health_delta = _clamp01(abs(domain_cp_avg - corr_score))

        # SLO impact
        slo_impact: float = 0.0
        if str(slo_status).lower() == "critical":
            slo_impact = 0.30
        elif str(slo_status).lower() == "degraded":
            slo_impact = 0.15
        elif str(slo_status).lower() == "warning":
            slo_impact = 0.05

        # Triage count for domain (best-effort: if domain in any triage incident)
        triage_count = triage_critical + triage_high

        # Chokepoint count
        chokepoint_count = len(chokepoints)

        # Signal sources
        signal_sources: list[str] = []
        if cp_files:
            signal_sources.append("critical_path")
        if chokepoints:
            signal_sources.append("chokepoints")
        if trend_count > 0:
            signal_sources.append("hotspot_trends")
        if recurring_count > 0:
            signal_sources.append("recurring_hotspots")
        if is_corr_hotspot:
            signal_sources.append("correlation_hotspot")
        if has_violation:
            signal_sources.append("governance_violation")
        if is_arch_hotspot:
            signal_sources.append("architecture_hotspot")

        # Drift score components
        drift_components = 0.0
        drift_components += 0.25 * _clamp01(domain_cp_avg)
        drift_components += 0.15 * health_delta
        drift_components += 0.10 * _clamp01(chokepoint_count / 5.0)
        drift_components += 0.10 * _clamp01(recurring_count / 3.0)
        drift_components += 0.10 * _clamp01(trend_count / 5.0)
        drift_components += 0.10 * _br_weight(br)
        drift_components += 0.10 * _gov_weight(gov_risk)
        drift_components += 0.10 * slo_impact
        drift_score = _clamp01(drift_components)
        severity = _severity_from_score(drift_score)

        inferred: list[str] = []
        if drift_score >= 0.70:
            inferred.append("drift_risk_elevated")
        if is_corr_hotspot:
            inferred.append("correlation_hotspot_active")
        if has_violation:
            inferred.append("governance_violation_detected")
        if health_delta > 0.15:
            inferred.append("health_expectation_mismatch")
        if chokepoint_count > 0:
            inferred.append("chokepoints_present")
        if recurring_count > 0:
            inferred.append("recurring_hotspot_active")
        if slo_impact > 0.0:
            inferred.append("slo_impact_detected")
        if is_arch_hotspot:
            inferred.append("architecture_hotspot_active")

        domain_unknowns: list[str] = []
        if str(cp_score) == "0.0" and not cp_files:
            domain_unknowns.append("no_critical_path_data")
        if corr_score == 0.0 and not is_corr_hotspot:
            domain_unknowns.append("no_correlation_signals")

        current_score = round(domain_cp_avg, 3)

        results.append(DomainDriftResult(
            domain=domain,
            current_score=current_score,
            governance_risk=gov_risk,
            blast_radius=br,
            correlation_hotspot=is_corr_hotspot,
            health_delta=round(health_delta, 3),
            slo_impact=round(slo_impact, 3),
            triage_count=triage_count,
            chokepoint_count=chokepoint_count,
            drift_score=drift_score,
            severity=severity,
            signal_sources=sorted(set(signal_sources)),
            inferred=sorted(set(inferred)),
            unknowns=sorted(set(domain_unknowns + global_unknowns)),
        ))

    results.sort(key=lambda r: (-r.drift_score, r.domain))
    results = results[:_MAX_DOMAINS]

    global_inferred_total: list[str] = []
    if any(r.drift_score >= 0.70 for r in results):
        global_inferred_total.append("critical_drift_detected")
    if any(r.drift_score >= 0.50 for r in results):
        global_inferred_total.append("elevated_drift_detected")
    if any(r.correlation_hotspot for r in results):
        global_inferred_total.append("correlation_hotspots_present")
    if any(r.governance_risk in {"high", "critical"} for r in results):
        global_inferred_total.append("governance_risk_elevated")
    if triage_critical > 0:
        global_inferred_total.append("critical_triage_active")

    return results, sorted(set(global_inferred_total))


def _br_weight(br: str) -> float:
    v = str(br or "").lower()
    return {"low": 0.05, "medium": 0.15, "high": 0.30, "critical": 0.45}.get(v, 0.0)


def _gov_weight(risk: str) -> float:
    v = str(risk or "").lower()
    return {"low": 0.05, "medium": 0.12, "high": 0.25, "critical": 0.40}.get(v, 0.0)


def _compute_governance_confidence(domains: list[DomainDriftResult], unknowns: list[str]) -> float:
    if not domains:
        return 0.0
    penalty = 0.0
    penalty += 0.10 * min(1.0, len(unknowns) / 5.0)
    avg_drift = sum(d.drift_score for d in domains) / len(domains)
    confidence = _clamp01(1.0 - avg_drift - penalty)
    return round(confidence, 3)


def build_governance_drift_snapshot() -> dict[str, Any]:
    """Build a full governance drift snapshot."""
    bundle, unknowns, unavailable = _read_signal_bundle()
    domains, global_inferred = _analyze_domains(bundle, unknowns)

    drift_scores = [d.drift_score for d in domains]
    overall_drift = _clamp01(sum(drift_scores) / max(len(drift_scores), 1)) if drift_scores else 0.0
    overall_severity = _severity_from_score(overall_drift)

    critical_count = sum(1 for d in domains if d.severity in {"HIGH", "CRITICAL"})
    elevated_count = sum(1 for d in domains if d.severity in {"MEDIUM", "HIGH", "CRITICAL"})

    gov_confidence = _compute_governance_confidence(domains, unknowns)

    corr = bundle["correlation"]
    cp = bundle["critical_path"]
    drift_37d = bundle["hotspot_drift"]
    slo = bundle["slo"]

    hard_facts = [
        "governance_drift_snapshot",
        f"domains_total={len(domains)}",
        f"overall_drift={round(overall_drift,3)}",
        f"governance_confidence={round(gov_confidence,3)}",
    ]

    inferred = list(global_inferred)
    if overall_drift >= 0.50:
        inferred.append("governance_drift_elevated")
    if gov_confidence < 0.50:
        inferred.append("governance_confidence_low")

    return {
        "status": "ok",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/governance-drift",
        "timestamp": _now(),
        "contract_version": GOVERNANCE_DRIFT_CONTRACT_VERSION,
        "overall_drift": round(float(overall_drift), 3),
        "severity": overall_severity,
        "governance_confidence": gov_confidence,
        "domains": [{
            "domain": d.domain,
            "current_score": round(float(d.current_score), 3),
            "governance_risk": d.governance_risk,
            "blast_radius": d.blast_radius,
            "correlation_hotspot": d.correlation_hotspot,
            "health_delta": round(float(d.health_delta), 3),
            "slo_impact": round(float(d.slo_impact), 3),
            "triage_count": int(d.triage_count),
            "chokepoint_count": int(d.chokepoint_count),
            "drift_score": round(float(d.drift_score), 3),
            "severity": d.severity,
            "signal_sources": list(d.signal_sources),
            "inferred": list(d.inferred),
            "unknowns": list(d.unknowns),
        } for d in domains],
        "domains_total": len(domains),
        "critical_domains_total": critical_count,
        "elevated_domains_total": elevated_count,
        "correlation_score": round(_safe_float(corr.get("correlation_score"), 0.0), 3),
        "critical_path_score": round(_safe_float(cp.get("score"), 0.0), 3),
        "hotspot_drift_score": round(_safe_float(drift_37d.get("drift_score"), 0.0), 3),
        "slo_status": str(slo.get("overall_status") or "unknown"),
        "recommendations": _build_drift_recommendations(overall_drift, overall_severity, gov_confidence, domains, unknowns),
        "hard_facts": hard_facts,
        "inferred": sorted(set(inferred)),
        "unknowns": sorted(set(unknowns)),
        "unavailable_fields": sorted(set(unavailable)),
    }


def _build_drift_recommendations(
    overall_drift: float,
    severity: str,
    gov_confidence: float,
    domains: list[DomainDriftResult],
    unknowns: list[str],
) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []

    if unknowns:
        recs.append({
            "severity": "LOW",
            "recommendation": "Missing signal sources limit governance drift accuracy",
            "rationale": f"unknowns={sorted(set(unknowns))}",
            "confidence": "low",
        })

    if gov_confidence < 0.30:
        recs.append({
            "severity": "HIGH",
            "recommendation": "Governance confidence critically low; verify signal chain integrity before acting on drift data",
            "rationale": f"governance_confidence={round(gov_confidence,3)}",
            "confidence": "medium",
        })
    elif gov_confidence < 0.50:
        recs.append({
            "severity": "MEDIUM",
            "recommendation": "Governance confidence degraded; cross-check drift signals before operational decisions",
            "rationale": f"governance_confidence={round(gov_confidence,3)}",
            "confidence": "medium",
        })

    if overall_drift >= 0.85:
        recs.append({
            "severity": "CRITICAL",
            "recommendation": "Critical governance drift detected; review all domains before deployments or refactors",
            "rationale": f"overall_drift={round(overall_drift,3)}",
            "confidence": "high",
        })
    elif overall_drift >= 0.70:
        recs.append({
            "severity": "HIGH",
            "recommendation": "High governance drift; prioritize domain-level investigation before changes",
            "rationale": f"overall_drift={round(overall_drift,3)}",
            "confidence": "high",
        })
    elif overall_drift >= 0.50:
        recs.append({
            "severity": "MEDIUM",
            "recommendation": "Moderate governance drift; monitor correlated domains for escalation",
            "rationale": f"overall_drift={round(overall_drift,3)}",
            "confidence": "medium",
        })

    critical_domains = [d for d in domains if d.severity in {"HIGH", "CRITICAL"}]
    if critical_domains:
        for d in critical_domains[:_MAX_EVENTS_PER_ENDPOINT]:
            recs.append({
                "severity": d.severity,
                "recommendation": f"Investigate governance drift in domain '{d.domain}'",
                "rationale": f"drift_score={round(d.drift_score,3)}, risk={d.governance_risk}, sources={d.signal_sources}",
                "confidence": "high",
            })

    if not recs:
        recs.append({
            "severity": "INFO",
            "recommendation": "No governance drift action required",
            "rationale": f"overall_drift={round(overall_drift,3)}, governance_confidence={round(gov_confidence,3)}",
            "confidence": "medium",
        })

    recs = recs[:_MAX_RECOMMENDATIONS]
    recs.sort(key=lambda r: (r.get("severity", ""), r.get("recommendation", "")))
    return recs


def _record_drift_events_from_snapshot(snapshot: dict[str, Any]) -> None:
    """Record drift events for each domain in snapshot."""
    domains = snapshot.get("domains") or []
    for d in domains:
        if not isinstance(d, dict):
            continue
        event = GovernanceDriftEvent(
            domain=d.get("domain", "unknown"),
            drift_score=_safe_float(d.get("drift_score"), 0.0),
            previous_score=None,
            signal_sources=list(d.get("signal_sources") or []),
            severity=str(d.get("severity") or "INFO"),
            inferred=list(d.get("inferred") or []),
            unknowns=list(d.get("unknowns") or []),
            timestamp=_now(),
        )
        with _EVENTS_LOCK:
            _EVENTS.append(event.to_dict())


def get_governance_drift_summary() -> dict[str, Any]:
    """Drift summary (lighter than full snapshot)."""
    try:
        snap = _get_cached_snapshot()
    except Exception:
        snap = build_governance_drift_snapshot()

    domains = snap.get("domains") or []
    return {
        "status": "ok",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/governance-drift/summary",
        "timestamp": _now(),
        "contract_version": GOVERNANCE_DRIFT_CONTRACT_VERSION,
        "overall_drift": snap.get("overall_drift", 0.0),
        "severity": snap.get("severity", "INFO"),
        "governance_confidence": snap.get("governance_confidence", 0.0),
        "domains_total": len(domains),
        "critical_domains_total": snap.get("critical_domains_total", 0),
        "elevated_domains_total": snap.get("elevated_domains_total", 0),
        "correlation_score": snap.get("correlation_score", 0.0),
        "hotspot_drift_score": snap.get("hotspot_drift_score", 0.0),
        "slo_status": snap.get("slo_status", "unknown"),
        "recommendations_total": len(snap.get("recommendations") or []),
        "unknowns": list(snap.get("unknowns") or []),
    }


def get_governance_drift_events(*, limit: int = 10) -> dict[str, Any]:
    """Return recent drift events."""
    limit = _parse_limit(limit, 10, lo=1, hi=50)
    with _EVENTS_LOCK:
        events = list(_EVENTS)[-limit:]
        total = len(_EVENTS)
    return {
        "status": "ok",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/governance-drift/events",
        "timestamp": _now(),
        "contract_version": GOVERNANCE_DRIFT_CONTRACT_VERSION,
        "events": events,
        "events_total": total,
        "returned": len(events),
        "unknowns": ["empty"] if not events else [],
    }


def get_governance_drift_domains() -> dict[str, Any]:
    """Return per-domain drift details."""
    try:
        snap = _get_cached_snapshot()
    except Exception:
        snap = build_governance_drift_snapshot()

    domains = snap.get("domains") or []
    return {
        "status": "ok",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/governance-drift/domains",
        "timestamp": _now(),
        "contract_version": GOVERNANCE_DRIFT_CONTRACT_VERSION,
        "domains": domains,
        "domains_total": len(domains),
        "unknowns": list(snap.get("unknowns") or []),
    }


def get_governance_drift_recommendations() -> dict[str, Any]:
    """Return drift recommendations."""
    try:
        snap = _get_cached_snapshot()
    except Exception:
        snap = build_governance_drift_snapshot()

    recs = snap.get("recommendations") or []
    return {
        "status": "ok",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/governance-drift/recommendations",
        "timestamp": _now(),
        "contract_version": GOVERNANCE_DRIFT_CONTRACT_VERSION,
        "overall_drift": snap.get("overall_drift", 0.0),
        "severity": snap.get("severity", "INFO"),
        "governance_confidence": snap.get("governance_confidence", 0.0),
        "recommendations": recs,
        "total": len(recs),
        "unknowns": list(snap.get("unknowns") or []),
    }


def reset_governance_drift_state() -> dict[str, Any]:
    """Reset in-memory state."""
    global _SNAPSHOT_CACHE, _SNAPSHOT_CACHE_TS
    with _EVENTS_LOCK:
        _EVENTS.clear()
    with _SNAPSHOT_CACHE_LOCK:
        _SNAPSHOT_CACHE = None
        _SNAPSHOT_CACHE_TS = 0.0
    return {"reset": True, "timestamp": _now(), "contract_version": GOVERNANCE_DRIFT_CONTRACT_VERSION}


def _get_cached_snapshot() -> dict[str, Any]:
    global _SNAPSHOT_CACHE, _SNAPSHOT_CACHE_TS
    now = _now()
    with _SNAPSHOT_CACHE_LOCK:
        if _SNAPSHOT_CACHE and (now - float(_SNAPSHOT_CACHE_TS)) <= _SNAPSHOT_CACHE_TTL_S:
            return dict(_SNAPSHOT_CACHE)
    snap = build_governance_drift_snapshot()
    _record_drift_events_from_snapshot(snap)
    with _SNAPSHOT_CACHE_LOCK:
        _SNAPSHOT_CACHE = dict(snap)
        _SNAPSHOT_CACHE_TS = now
    return snap


def build_governance_drift_prometheus_metrics() -> str:
    """Render governance drift metrics as Prometheus text (fail-safe)."""
    try:
        try:
            snap = _get_cached_snapshot()
        except Exception:
            snap = build_governance_drift_snapshot()

        overall_drift = float(snap.get("overall_drift", 0) or 0)
        gov_confidence = float(snap.get("governance_confidence", 0) or 0)
        domains_total = float(snap.get("domains_total", 0) or 0)
        critical_total = float(snap.get("critical_domains_total", 0) or 0)
        unknowns_total = float(len(snap.get("unknowns", []) or []))
        recs_total = float(len(snap.get("recommendations", []) or []))
        events_total = 0.0
        with _EVENTS_LOCK:
            events_total = float(len(_EVENTS))

        health_delta_avg = 0.0
        domains = snap.get("domains") or []
        if domains:
            health_delta_avg = sum(float(d.get("health_delta", 0) or 0) for d in domains) / len(domains)

        return (
            f"ailab_governance_drift_score {overall_drift}\n"
            f"ailab_governance_drift_governance_confidence {gov_confidence}\n"
            f"ailab_governance_drift_events_total {events_total}\n"
            f"ailab_governance_drift_domains_total {domains_total}\n"
            f"ailab_governance_drift_critical_domains_total {critical_total}\n"
            f"ailab_governance_drift_unknowns_total {unknowns_total}\n"
            f"ailab_governance_drift_recommendations_total {recs_total}\n"
            f"ailab_governance_drift_health_delta_avg {health_delta_avg}\n"
        )
    except Exception:
        return (
            "ailab_governance_drift_score 0\n"
            "ailab_governance_drift_governance_confidence 0\n"
            "ailab_governance_drift_events_total 0\n"
            "ailab_governance_drift_domains_total 0\n"
            "ailab_governance_drift_critical_domains_total 0\n"
            "ailab_governance_drift_unknowns_total 0\n"
            "ailab_governance_drift_recommendations_total 0\n"
            "ailab_governance_drift_health_delta_avg 0\n"
        )
