from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any

from runtime.incidents.contracts import (
    INCIDENT_CONTRACT_VERSION,
    INCIDENT_DOMAINS,
    SEVERITY_ORDER,
    DOMAIN_DEPENDENCY_MAP,
    CORRELATION_DOMAINS,
    IncidentSignal,
    BlastRadiusEntry,
    IncidentHypothesis,
    IncidentRecommendation,
    OperationalIncident,
    IncidentIntelligenceReport,
)


def _strict_mode() -> bool:
    return os.environ.get("STRICT_VALIDATION_MODE", "false").lower() in ("true", "1", "yes")


def _now() -> float:
    return 0.0 if _strict_mode() else time.time()


def _hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _ensure_list(val: Any) -> list:
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [val]
    return []


def _confidence_score(level: str) -> float:
    return {"high": 1.0, "medium": 0.6, "low": 0.2, "unknown": 0.0}.get(level, 0.0)


def _score_to_confidence(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.5:
        return "medium"
    if score >= 0.2:
        return "low"
    return "unknown"


def _worst_severity(severities: list[str]) -> str:
    ranked = [s for s in severities if s in SEVERITY_ORDER]
    if not ranked:
        return "info"
    return min(ranked, key=lambda s: SEVERITY_ORDER.get(s, 99))


def _worst_confidence(confs: list[str]) -> str:
    scores = [_confidence_score(c) for c in confs]
    return _score_to_confidence(min(scores) if scores else 0.0)


# ── Domain detection functions ────────────────────────────────────────


def detect_authority_incidents(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> list[IncidentSignal]:
    signals: list[IncidentSignal] = []
    extra_ctx = extra_ctx or {}
    sensor_snapshot = sensor_snapshot or {}

    try:
        from runtime.authority import build_live_authority_snapshot, build_authority_cognition_summary

        snap = build_live_authority_snapshot(extra_ctx=extra_ctx)
        fresh = snap.get("freshness", {}) or {}
        status = fresh.get("status", "unknown")
        gaps = snap.get("gaps", []) or []
        prom = snap.get("prometheus", {}) or {}
        targets = prom.get("targets", {}) or {}
        down = int(targets.get("scrape_down", 0) or 0)

        if status in ("stale", "unavailable"):
            signals.append(IncidentSignal(
                domain="authority",
                signal_type="authority_freshness",
                severity="high" if status == "unavailable" else "medium",
                description=f"authority freshness: {status}",
                evidence=["authority_35c"],
                confidence=str(fresh.get("confidence", "medium")),
                freshness=status,
            ))

        if gaps:
            signals.append(IncidentSignal(
                domain="authority",
                signal_type="authority_gaps",
                severity="medium",
                description=f"authority gaps: {', '.join(gaps[:3])}",
                evidence=["authority_35c"],
                confidence="high",
                freshness="fresh",
            ))

        if down > 0:
            signals.append(IncidentSignal(
                domain="authority",
                signal_type="prometheus_targets_down",
                severity="high" if down > 2 else "medium",
                description=f"{down} prometheus targets down",
                evidence=["prometheus"],
                confidence="high",
                freshness="fresh",
            ))

        summ = build_authority_cognition_summary(extra_ctx=extra_ctx)
        fresh_score = float(summ.get("authority_freshness_score", 100.0) or 100.0)
        if fresh_score < 50:
            signals.append(IncidentSignal(
                domain="authority",
                signal_type="authority_freshness_score_low",
                severity="high" if fresh_score < 30 else "medium",
                description=f"authority freshness score: {fresh_score}/100",
                evidence=["authority_35c"],
                confidence="high",
                freshness="fresh",
            ))

    except Exception:
        signals.append(IncidentSignal(
            domain="authority",
            signal_type="authority_module_error",
            severity="medium",
            description="authority module not available for incident detection",
            evidence=["code"],
            confidence="low",
            freshness="unavailable",
        ))

    return signals


def detect_observability_incidents(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> list[IncidentSignal]:
    signals: list[IncidentSignal] = []
    extra_ctx = extra_ctx or {}
    sensor_snapshot = sensor_snapshot or {}

    observed = int(sensor_snapshot.get("observed_sources_count", 0) or 0)
    missing = int(sensor_snapshot.get("missing_sources_count", 0) or 0)
    stale = _ensure_list(sensor_snapshot.get("stale_sources"))
    dc = sensor_snapshot.get("domain_confidence", {}) or {}

    total = observed + missing
    if total > 0:
        ratio = observed / total
        if ratio < 0.5:
            signals.append(IncidentSignal(
                domain="observability",
                signal_type="observability_coverage_low",
                severity="high" if ratio < 0.3 else "medium",
                description=f"observability coverage: {observed}/{total} sources up ({ratio:.0%})",
                evidence=["prometheus"],
                confidence="high",
                freshness="fresh",
            ))

    if stale:
        signals.append(IncidentSignal(
            domain="observability",
            signal_type="observability_stale_sources",
            severity="medium",
            description=f"stale observability sources: {', '.join(stale[:3])}",
            evidence=["prometheus"],
            confidence="medium",
            freshness="stale",
        ))

    if dc.get("observability") == "low":
        signals.append(IncidentSignal(
            domain="observability",
            signal_type="observability_confidence_low",
            severity="medium",
            description="observability domain confidence is low",
            evidence=["prometheus", "code"],
            confidence="low",
            freshness="unknown",
        ))

    # Live observability diagnostics (OBS-34B)
    try:
        if os.environ.get("AI_LAB_ENABLE_LIVE_OBSERVABILITY_DIAGNOSTICS", "false").lower() in ("true", "1", "yes"):
            from runtime.observability import run_live_observability_diagnostics
            rep = run_live_observability_diagnostics(extra_ctx=extra_ctx)
            score = rep.get("score", {}) or {}
            lvl = score.get("live_observability_level", "unknown")
            val = float(score.get("live_observability_score", 100.0) or 100.0)
            if lvl in ("critical", "low") or val < 65:
                signals.append(IncidentSignal(
                    domain="observability",
                    signal_type="live_observability_score_low",
                    severity="critical" if val < 40 else "high" if val < 65 else "medium",
                    description=f"live observability score: {val}/100 ({lvl})",
                    evidence=["obs-34b"],
                    confidence="medium",
                    freshness="fresh",
                ))
            incidents = rep.get("incidents", {}) or {}
            highest = incidents.get("highest_severity", "info")
            if highest in ("critical", "high"):
                signals.append(IncidentSignal(
                    domain="observability",
                    signal_type="observability_incidents_active",
                    severity="critical" if highest == "critical" else "high",
                    description=f"observability incidents active (highest={highest})",
                    evidence=["obs-34b"],
                    confidence="high",
                    freshness="fresh",
                ))
    except Exception:
        pass

    return signals


def detect_validation_incidents(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> list[IncidentSignal]:
    signals: list[IncidentSignal] = []
    extra_ctx = extra_ctx or {}
    sensor_snapshot = sensor_snapshot or {}

    try:
        from runtime.validation import build_runtime_validation_report
        rep = build_runtime_validation_report(sensor_snapshot=sensor_snapshot, extra_ctx=extra_ctx)
        score = float(rep.get("validation_score", 100.0) or 100.0)
        level = rep.get("validation_level", "unknown")
        failures = rep.get("failures", []) or []
        pilot = rep.get("pilot_readiness", {}) or {}
        pilot_score = float(pilot.get("pilot_readiness_score", 100.0) or 100.0)
        blocking = _ensure_list(pilot.get("blocking_invariants"))

        if score < 65:
            signals.append(IncidentSignal(
                domain="validation",
                signal_type="validation_score_low",
                severity="critical" if score < 40 else "high",
                description=f"validation score: {score}/100 ({level})",
                evidence=["validation_framework_33b"],
                confidence="high",
                freshness="fresh",
            ))

        if pilot_score < 65:
            signals.append(IncidentSignal(
                domain="validation",
                signal_type="pilot_readiness_low",
                severity="high" if pilot_score < 40 else "medium",
                description=f"pilot readiness: {pilot_score}/100 ({pilot.get('readiness_level', 'unknown')})",
                evidence=["validation_framework_33b"],
                confidence="medium",
                freshness="fresh",
            ))

        if blocking:
            signals.append(IncidentSignal(
                domain="validation",
                signal_type="blocking_invariants_failed",
                severity="high",
                description=f"blocking invariants: {', '.join(blocking[:3])}",
                evidence=["validation_framework_33b"],
                confidence="high",
                freshness="fresh",
            ))

        failed_gates = _ensure_list(pilot.get("failed_gates"))
        if failed_gates:
            signals.append(IncidentSignal(
                domain="validation",
                signal_type="safety_gates_failed",
                severity="high",
                description=f"failed safety gates: {', '.join(failed_gates[:3])}",
                evidence=["validation_framework_33b"],
                confidence="high",
                freshness="fresh",
            ))

        if failures:
            blocking_count = sum(1 for f in failures if f.get("blocking"))
            signals.append(IncidentSignal(
                domain="validation",
                signal_type="validation_failures",
                severity="high" if blocking_count > 0 else "medium",
                description=f"{len(failures)} validation failures ({blocking_count} blocking)",
                evidence=["validation_framework_33b"],
                confidence="high",
                freshness="fresh",
            ))

    except Exception:
        signals.append(IncidentSignal(
            domain="validation",
            signal_type="validation_module_error",
            severity="medium",
            description="validation framework not available for incident detection",
            evidence=["code"],
            confidence="low",
            freshness="unavailable",
        ))

    return signals


def detect_governance_incidents(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> list[IncidentSignal]:
    signals: list[IncidentSignal] = []
    extra_ctx = extra_ctx or {}
    sensor_snapshot = sensor_snapshot or {}

    try:
        from runtime.governance import build_runtime_governance_registry
        reg = build_runtime_governance_registry(extra_ctx=extra_ctx, sensor_snapshot=sensor_snapshot)
        score = float((reg.get("governance_score_info", {}) or {}).get("score", 100.0) or 100.0)
        level = (reg.get("governance_score_info", {}) or {}).get("level", "unknown")
        degraded = _ensure_list(reg.get("degraded_domains"))
        risks = reg.get("risks", []) or []

        if score < 65:
            signals.append(IncidentSignal(
                domain="governance",
                signal_type="governance_score_low",
                severity="critical" if score < 40 else "high",
                description=f"governance score: {score}/100 ({level})",
                evidence=["runtime_governance_33a"],
                confidence="high",
                freshness="fresh",
            ))

        if degraded:
            signals.append(IncidentSignal(
                domain="governance",
                signal_type="degraded_domains_active",
                severity="medium",
                description=f"degraded domains: {', '.join(degraded[:5])}",
                evidence=["runtime_governance_33a"],
                confidence="high",
                freshness="fresh",
            ))

        high_risks = [r for r in risks if r.get("severity") in ("high", "critical")]
        if high_risks:
            signals.append(IncidentSignal(
                domain="governance",
                signal_type="high_severity_risks",
                severity="high" if any(r.get("severity") == "critical" for r in high_risks) else "medium",
                description=f"{len(high_risks)} high-severity governance risks",
                evidence=["runtime_governance_33a"],
                confidence="high",
                freshness="fresh",
            ))

        drift = [d for d in _ensure_list(reg.get("drift")) if d.get("drift_type") != "no_drift"]
        if drift:
            signals.append(IncidentSignal(
                domain="governance",
                signal_type="governance_drift",
                severity="medium",
                description=f"{len(drift)} governance drift events",
                evidence=["runtime_governance_33a"],
                confidence="high",
                freshness="fresh",
            ))

    except Exception:
        signals.append(IncidentSignal(
            domain="governance",
            signal_type="governance_module_error",
            severity="medium",
            description="governance registry not available for incident detection",
            evidence=["code"],
            confidence="low",
            freshness="unavailable",
        ))

    return signals


def detect_topology_incidents(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> list[IncidentSignal]:
    signals: list[IncidentSignal] = []
    extra_ctx = extra_ctx or {}
    sensor_snapshot = sensor_snapshot or {}

    try:
        from runtime.topology import (
            detect_topology_drift,
            calculate_topology_confidence,
        )
        drift = detect_topology_drift(sensor_snapshot, extra_ctx) or []
        conf = calculate_topology_confidence(sensor_snapshot, extra_ctx) or {}
        score = int(conf.get("overall_score", 100) or 100)

        if drift:
            signals.append(IncidentSignal(
                domain="topology",
                signal_type="topology_drift",
                severity="medium",
                description=f"{len(drift)} topology drift events",
                evidence=["runtime_topology_31d"],
                confidence="high",
                freshness="fresh",
            ))

        if score < 50:
            signals.append(IncidentSignal(
                domain="topology",
                signal_type="topology_confidence_low",
                severity="high" if score < 30 else "medium",
                description=f"topology confidence: {score}/100",
                evidence=["runtime_topology_31d"],
                confidence="medium",
                freshness="fresh",
            ))

    except Exception:
        signals.append(IncidentSignal(
            domain="topology",
            signal_type="topology_module_error",
            severity="medium",
            description="topology module not available for incident detection",
            evidence=["code"],
            confidence="low",
            freshness="unavailable",
        ))

    return signals


def detect_semantic_incidents(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> list[IncidentSignal]:
    signals: list[IncidentSignal] = []
    extra_ctx = extra_ctx or {}
    _ = sensor_snapshot

    try:
        from runtime.semantic import build_semantic_integrity_report
        sem = build_semantic_integrity_report(extra_ctx=extra_ctx)
        score = float(sem.get("semantic_integrity_score", 100.0) or 100.0)
        legacy = int(sem.get("legacy_leakage_total", 0) or 0)
        phantom = int(sem.get("phantom_entities_total", 0) or 0)
        unknown_operational = int(sem.get("unknown_operational_entities_total", 0) or 0)

        if score < 65:
            signals.append(IncidentSignal(
                domain="semantic",
                signal_type="semantic_integrity_low",
                severity="critical" if score < 40 else "high",
                description=f"semantic integrity: {score}/100",
                evidence=["semantic_sterilization_35b"],
                confidence="high",
                freshness="fresh",
            ))

        if legacy > 0:
            signals.append(IncidentSignal(
                domain="semantic",
                signal_type="legacy_leakage",
                severity="high",
                description=f"legacy leakage: {legacy} entities",
                evidence=["semantic_sterilization_35b"],
                confidence="high",
                freshness="fresh",
            ))

        if phantom > 0:
            signals.append(IncidentSignal(
                domain="semantic",
                signal_type="phantom_entities",
                severity="medium",
                description=f"phantom entities: {phantom}",
                evidence=["semantic_sterilization_35b"],
                confidence="medium",
                freshness="fresh",
            ))

        if unknown_operational > 0:
            signals.append(IncidentSignal(
                domain="semantic",
                signal_type="unknown_operational_entities",
                severity="high",
                description=f"unknown operational entities: {unknown_operational}",
                evidence=["semantic_sterilization_35b"],
                confidence="medium",
                freshness="fresh",
            ))

    except Exception:
        signals.append(IncidentSignal(
            domain="semantic",
            signal_type="semantic_module_error",
            severity="medium",
            description="semantic module not available for incident detection",
            evidence=["code"],
            confidence="low",
            freshness="unavailable",
        ))

    return signals


def detect_fastpath_incidents(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> list[IncidentSignal]:
    signals: list[IncidentSignal] = []
    extra_ctx = extra_ctx or {}
    _ = sensor_snapshot

    try:
        from runtime.fastpath import build_fastpath_response
        fp = build_fastpath_response(
            "estado runtime",
            extra_ctx={"enable_network": False},
            sensor_snapshot={},
            verbosity="operational",
        )
        q = float(fp.get("response_quality_score", 100.0) or 100.0)
        deep = bool((fp.get("routing", {}) or {}).get("deep_path"))
        auth = fp.get("authority", {}) or {}
        auth_fresh = (auth.get("freshness", {}) or {}).get("status", "unknown") if isinstance(auth, dict) else "unknown"

        if q < 55:
            signals.append(IncidentSignal(
                domain="fastpath",
                signal_type="fastpath_quality_low",
                severity="high" if q < 30 else "medium",
                description=f"fastpath quality score: {q}/100",
                evidence=["fastpath_35d"],
                confidence="high",
                freshness="fresh",
            ))

        if auth_fresh in ("unavailable", "stale") and q < 80:
            signals.append(IncidentSignal(
                domain="fastpath",
                signal_type="fastpath_authority_degraded",
                severity="medium",
                description=f"fastpath authority: {auth_fresh}, quality: {q}/100",
                evidence=["fastpath_35d"],
                confidence="medium",
                freshness="fresh",
            ))

    except Exception:
        signals.append(IncidentSignal(
            domain="fastpath",
            signal_type="fastpath_module_error",
            severity="medium",
            description="fastpath module not available for incident detection",
            evidence=["code"],
            confidence="low",
            freshness="unavailable",
        ))

    return signals


def detect_infrastructure_incidents(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> list[IncidentSignal]:
    signals: list[IncidentSignal] = []
    extra_ctx = extra_ctx or {}
    _ = sensor_snapshot

    try:
        from runtime.infrastructure import build_infrastructure_identity_registry
        reg = build_infrastructure_identity_registry(extra_ctx=extra_ctx)
        score = float(reg.get("score", 100.0) or 100.0)
        roots = reg.get("authority_roots", []) or []
        inv = reg.get("inventory", {}) or {}
        unknown = inv.get("unknown_nodes", []) or []
        orphans = inv.get("discoverable_nodes", []) or []

        if score < 65:
            signals.append(IncidentSignal(
                domain="infrastructure",
                signal_type="infrastructure_identity_low",
                severity="critical" if score < 40 else "high",
                description=f"infrastructure identity score: {score}/100",
                evidence=["infrastructure_registry_35a"],
                confidence="high",
                freshness="fresh",
            ))

        if "192.168.1.40" not in roots:
            signals.append(IncidentSignal(
                domain="infrastructure",
                signal_type="authority_root_missing",
                severity="high",
                description="192.168.1.40 (prometheus) not in authority roots",
                evidence=["infrastructure_registry_35a"],
                confidence="high",
                freshness="fresh",
            ))

        if unknown:
            signals.append(IncidentSignal(
                domain="infrastructure",
                signal_type="unknown_infrastructure_nodes",
                severity="medium",
                description=f"{len(unknown)} unknown infrastructure nodes",
                evidence=["infrastructure_registry_35a"],
                confidence="medium",
                freshness="fresh",
            ))

        if orphans:
            signals.append(IncidentSignal(
                domain="infrastructure",
                signal_type="orphan_discoverable_nodes",
                severity="medium",
                description=f"{len(orphans)} orphan discoverable nodes",
                evidence=["infrastructure_registry_35a"],
                confidence="medium",
                freshness="fresh",
            ))

    except Exception:
        signals.append(IncidentSignal(
            domain="infrastructure",
            signal_type="infrastructure_module_error",
            severity="medium",
            description="infrastructure module not available for incident detection",
            evidence=["code"],
            confidence="low",
            freshness="unavailable",
        ))

    return signals


def detect_performance_incidents(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> list[IncidentSignal]:
    signals: list[IncidentSignal] = []
    extra_ctx = extra_ctx or {}
    _ = sensor_snapshot

    try:
        from runtime.performance import profile_runtime_latency, get_performance_cache_state
        rep = profile_runtime_latency(extra_ctx=extra_ctx, sensor_snapshot={})
        perf = rep.get("performance", {}) or {}
        score = float(perf.get("runtime_performance_score", 100.0) or 100.0)

        if score < 65:
            signals.append(IncidentSignal(
                domain="performance",
                signal_type="runtime_performance_low",
                severity="critical" if score < 40 else "high",
                description=f"runtime performance score: {score}/100",
                evidence=["runtime_performance_34c"],
                confidence="high",
                freshness="fresh",
            ))

        friction = perf.get("friction_detected", False)
        if friction:
            signals.append(IncidentSignal(
                domain="performance",
                signal_type="runtime_friction_detected",
                severity="medium",
                description="runtime friction detected (latency/overhead)",
                evidence=["runtime_performance_34c"],
                confidence="medium",
                freshness="fresh",
            ))

    except Exception:
        signals.append(IncidentSignal(
            domain="performance",
            signal_type="performance_module_error",
            severity="medium",
            description="performance module not available for incident detection",
            evidence=["code"],
            confidence="low",
            freshness="unavailable",
        ))

    return signals


def detect_storage_incidents(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> list[IncidentSignal]:
    signals: list[IncidentSignal] = []
    extra_ctx = extra_ctx or {}
    sensor_snapshot = sensor_snapshot or {}

    observed_data = sensor_snapshot.get("observed_data", {}) or {}
    system = observed_data.get("system_node", {}) or {}
    fs_usage = system.get("fs_usage_pct")
    if fs_usage is not None:
        fs = float(fs_usage)
        if fs > 85:
            signals.append(IncidentSignal(
                domain="storage",
                signal_type="disk_usage_high",
                severity="critical" if fs > 95 else "high",
                description=f"root disk usage: {fs}%",
                evidence=["prometheus"],
                confidence="high",
                freshness="fresh",
            ))

    return signals


def detect_gpu_incidents(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> list[IncidentSignal]:
    signals: list[IncidentSignal] = []
    extra_ctx = extra_ctx or {}
    sensor_snapshot = sensor_snapshot or {}
    gpu_summaries = sensor_snapshot.get("gpu_operational_summaries", []) or []

    for gpu in gpu_summaries:
        if not isinstance(gpu, dict):
            continue
        gpu_id = gpu.get("gpu_id", "?")
        observed = gpu.get("observed_state", "unknown")
        active = gpu.get("operational_state") == "active"
        metrics = gpu.get("observed_metrics", {}) or {}
        inv_expected = bool(gpu.get("inventory_expected_offline"))

        if not active and observed == "unavailable" and not inv_expected:
            signals.append(IncidentSignal(
                domain="gpu",
                signal_type="gpu_unexpectedly_down",
                severity="high",
                description=f"GPU {gpu_id} unexpectedly down",
                evidence=["sensor_fusion"],
                confidence="high",
                freshness="fresh",
            ))

        temp = metrics.get("temperature_c")
        if temp is not None and float(temp) > 85:
            signals.append(IncidentSignal(
                domain="gpu",
                signal_type="gpu_temperature_high",
                severity="high" if float(temp) > 95 else "medium",
                description=f"GPU {gpu_id} temperature: {temp}C",
                evidence=["sensor_fusion"],
                confidence="high",
                freshness="fresh",
            ))

        vram_free = metrics.get("vram_free_gb")
        if vram_free is not None and float(vram_free) < 0.5:
            signals.append(IncidentSignal(
                domain="gpu",
                signal_type="gpu_vram_pressure",
                severity="high" if float(vram_free) < 0.2 else "medium",
                description=f"GPU {gpu_id} VRAM critical: {vram_free}GB free",
                evidence=["sensor_fusion"],
                confidence="high",
                freshness="fresh",
            ))

    return signals


def detect_execution_incidents(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> list[IncidentSignal]:
    signals: list[IncidentSignal] = []
    extra_ctx = extra_ctx or {}
    _ = sensor_snapshot

    try:
        from runtime.tools import calculate_tool_governance_score, detect_invalid_tool_contracts
        score = float((calculate_tool_governance_score() or {}).get("tool_governance_score", 100.0) or 100.0)
        invalid = detect_invalid_tool_contracts()

        if score < 65:
            signals.append(IncidentSignal(
                domain="execution",
                signal_type="tool_governance_low",
                severity="critical" if score < 40 else "high",
                description=f"tool governance score: {score}/100",
                evidence=["tool_registry_28_4"],
                confidence="high",
                freshness="fresh",
            ))

        if invalid:
            signals.append(IncidentSignal(
                domain="execution",
                signal_type="invalid_tool_contracts",
                severity="high",
                description=f"{len(invalid)} invalid tool contracts",
                evidence=["tool_registry_28_4"],
                confidence="high",
                freshness="fresh",
            ))

    except Exception:
        signals.append(IncidentSignal(
            domain="execution",
            signal_type="execution_module_error",
            severity="medium",
            description="execution governance module not available for incident detection",
            evidence=["code"],
            confidence="low",
            freshness="unavailable",
        ))

    return signals


# ── Signal correlation engine ────────────────────────────────────────


def correlate_incident_signals(
    all_signals: list[IncidentSignal],
) -> tuple[list[IncidentSignal], list[dict[str, Any]]]:
    merged: dict[str, list[IncidentSignal]] = {}
    for sig in all_signals:
        key = (sig.domain, sig.severity, sig.signal_type)
        if key not in merged:
            merged[key] = []
        merged[key].append(sig)

    correlation_results: list[dict[str, Any]] = []
    correlated: list[IncidentSignal] = []

    for domain, related_domains in CORRELATION_DOMAINS.items():
        domain_signals = [s for s in all_signals if s.domain == domain and s.severity in ("high", "critical", "medium")]
        if not domain_signals:
            continue
        for related in related_domains:
            related_signals = [s for s in all_signals if s.domain == related and s.severity in ("high", "critical")]
            if related_signals:
                worst = _worst_severity([s.severity for s in domain_signals] + [s.severity for s in related_signals])
                correlation_results.append({
                    "primary_domain": domain,
                    "correlated_domain": related,
                    "primary_signals_total": len(domain_signals),
                    "correlated_signals_total": len(related_signals),
                    "worst_severity": worst,
                    "correlation_type": "domain_dependency",
                })
                # Merge related signals into domain
                for rs in related_signals:
                    if rs not in correlated:
                        correlated.append(rs)

    # Merge duplicate signals across domains via correlation map
    merged_list: list[IncidentSignal] = []
    seen_keys: set[str] = set()
    for sig in all_signals:
        dk = (sig.domain, sig.signal_type)
        if dk not in seen_keys:
            seen_keys.add(dk)
            merged_list.append(sig)
        else:
            # Update severity of existing
            for i, existing in enumerate(merged_list):
                if existing.domain == sig.domain and existing.signal_type == sig.signal_type:
                    if SEVERITY_ORDER.get(sig.severity, 99) < SEVERITY_ORDER.get(existing.severity, 99):
                        merged_list[i] = sig
                    break

    # Add correlated signals not already merged
    for cs in correlated:
        dk = (cs.domain, cs.signal_type)
        if dk not in seen_keys:
            seen_keys.add(dk)
            merged_list.append(cs)

    # Merge by severity: deduplicate same domain+severity+type
    final_signals: list[IncidentSignal] = []
    final_keys: set[str] = set()
    for sig in merged_list:
        fk = (sig.domain, sig.severity, sig.signal_type)
        if fk not in final_keys:
            final_keys.add(fk)
            final_signals.append(sig)

    return final_signals, correlation_results


# ── Blast radius engine ──────────────────────────────────────────────


def calculate_incident_blast_radius(
    incident: IncidentSignal,
    all_signals: list[IncidentSignal],
) -> list[BlastRadiusEntry]:
    entries: list[BlastRadiusEntry] = []
    domain = incident.domain
    affected = DOMAIN_DEPENDENCY_MAP.get(domain, [])

    for dep_domain in affected:
        dep_signals = [s for s in all_signals if s.domain == dep_domain]
        if dep_signals:
            dep_severity = _worst_severity([s.severity for s in dep_signals])
        else:
            dep_severity = "low"
        entries.append(BlastRadiusEntry(
            affected_domain=dep_domain,
            severity="high" if incident.severity in ("critical", "high") and dep_severity != "low" else dep_severity,
            dependency_path=[domain, dep_domain],
            description=f"{domain} incident may affect {dep_domain}",
        ))

    # Propagate blast radius one hop deeper
    for dep_domain in affected:
        deeper = DOMAIN_DEPENDENCY_MAP.get(dep_domain, [])
        for deep_domain in deeper:
            if deep_domain != domain and deep_domain not in affected:
                entries.append(BlastRadiusEntry(
                    affected_domain=deep_domain,
                    severity="medium",
                    dependency_path=[domain, dep_domain, deep_domain],
                    description=f"secondary impact: {domain} -> {dep_domain} -> {deep_domain}",
                ))

    return entries


def build_blast_radius_summary(
    all_entries: list[BlastRadiusEntry],
) -> dict[str, Any]:
    affected_totals: dict[str, int] = {}
    severity_counts: dict[str, int] = {}
    for e in all_entries:
        affected_totals[e.affected_domain] = affected_totals.get(e.affected_domain, 0) + 1
        sev = e.severity
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    return {
        "total_affected_domains": len(affected_totals),
        "affected_domains": sorted(affected_totals.keys()),
        "blast_radius_entries": len(all_entries),
        "by_severity": {sev: severity_counts.get(sev, 0) for sev in ("critical", "high", "medium", "low")},
    }


# ── Root cause hypothesis engine ─────────────────────────────────────


def build_incident_hypotheses(
    incident: IncidentSignal,
    all_signals: list[IncidentSignal],
    correlation_results: list[dict[str, Any]],
) -> list[IncidentHypothesis]:
    hypotheses: list[IncidentHypothesis] = []

    domain = incident.domain
    domain_signals = [s for s in all_signals if s.domain == domain]

    # Root cause: check if upstream domain has worse signals
    upstream = None
    for parent, children in DOMAIN_DEPENDENCY_MAP.items():
        if domain in children:
            upstream = parent
            break

    if upstream:
        upstream_signals = [s for s in all_signals if s.domain == upstream and s.severity in ("critical", "high")]
        if upstream_signals:
            worst_up = _worst_severity([s.severity for s in upstream_signals])
            hypotheses.append(IncidentHypothesis(
                hypothesis_type="root_cause",
                domain=upstream,
                description=f"root cause likely in {upstream} ({worst_up}), propagating to {domain}",
                evidence=[f"{upstream}_module", f"{domain}_module"],
                confidence="medium" if worst_up == "high" else "low",
            ))

    # Correlated: check cross-correlation results
    correlated_with = [
        cr for cr in correlation_results
        if cr.get("primary_domain") == domain or cr.get("correlated_domain") == domain
    ]
    if correlated_with:
        total = len(correlated_with)
        hypotheses.append(IncidentHypothesis(
            hypothesis_type="correlated",
            domain=domain,
            description=f"incident correlated with {total} other domain(s)",
            evidence=["incident_correlation_36a"],
            confidence="medium" if total > 1 else "low",
        ))

    # Contributing: check within-domain signal patterns
    if len(domain_signals) > 1:
        types = ", ".join(sorted(set(s.signal_type for s in domain_signals)))
        hypotheses.append(IncidentHypothesis(
            hypothesis_type="contributing",
            domain=domain,
            description=f"multiple signals in {domain}: {types}",
            evidence=[f"{domain}_module"],
            confidence="medium",
        ))

    if not hypotheses:
        hypotheses.append(IncidentHypothesis(
            hypothesis_type="root_cause",
            domain=domain,
            description=f"no upstream or correlated evidence — possible isolated {domain} incident",
            evidence=[f"{domain}_module"],
            confidence="low",
        ))

    return hypotheses


# ── Recommendation engine (grounded, no LLM) ─────────────────────────


def build_incident_recommendations(
    incident: IncidentSignal,
    blast_radius: list[BlastRadiusEntry],
    hypotheses: list[IncidentHypothesis],
) -> list[IncidentRecommendation]:
    recommendations: list[IncidentRecommendation] = []
    domain = incident.domain

    domain_recs: dict[str, tuple[str, str, bool]] = {
        "authority": ("high", "verify prometheus connectivity and authority sources", True),
        "observability": ("high", "check prometheus targets, scrape config, and exporter health", True),
        "validation": ("high", "review invariant failures and blocked safety gates", True),
        "governance": ("medium", "investigate degraded domains and high-severity risks", True),
        "topology": ("medium", "review topology drift and confidence score", True),
        "semantic": ("high", "investigate semantic contamination and legacy leakage", True),
        "fastpath": ("low", "monitor fastpath quality — may be transient", False),
        "infrastructure": ("high", "verify infrastructure registry and authority roots", True),
        "performance": ("medium", "profile runtime latency and check cache health", True),
        "storage": ("critical", "free disk space immediately — risk of data loss", True),
        "gpu": ("high", "check GPU temperature, VRAM, and connectivity", True),
        "execution": ("medium", "review tool contracts and invalid registrations", True),
    }

    prio, desc, actionable = domain_recs.get(domain, ("medium", f"investigate {domain} incident signals", True))
    recommendations.append(IncidentRecommendation(
        priority=prio,
        domain=domain,
        description=desc,
        actionable=actionable,
    ))

    # Secondary recommendations from blast radius
    for br in blast_radius:
        if br.severity in ("critical", "high"):
            rec = domain_recs.get(br.affected_domain)
            if rec and rec[2]:
                r_desc = rec[1]
                if not any(r.domain == br.affected_domain for r in recommendations):
                    recommendations.append(IncidentRecommendation(
                        priority=rec[0],
                        domain=br.affected_domain,
                        description=f"[blast radius] {r_desc}",
                        actionable=True,
                    ))

    # Confidence-aware recommendations
    if any(h.confidence == "low" for h in hypotheses):
        recommendations.append(IncidentRecommendation(
            priority="medium",
            domain=domain,
            description="low confidence in hypothesis — gather more evidence before action",
            actionable=False,
        ))

    return recommendations


# ── Main incident intelligence builder ───────────────────────────────


_INCIDENT_GUARD = threading.local()


def build_incident_intelligence_report(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # Re-entrance guard: prevent circular calls from governance or validation.
    if getattr(_INCIDENT_GUARD, "in_incidents", False):
        return {
            "contract_version": INCIDENT_CONTRACT_VERSION,
            "active_incidents": [],
            "incident_count": 0,
            "highest_severity": "info",
            "affected_domains": [],
            "total_signals_evaluated": 0,
            "correlation_results": [],
            "blast_radius_summary": {"contract_version": "36A", "total_entries": 0, "highest_severity": "info", "affected_domains": []},
            "recommendations_total": 0,
            "deterministic_signature": _hash({"re_entrant": True}),
            "generated_at": _now(),
        }

    _INCIDENT_GUARD.in_incidents = True
    try:
        return _build_incident_intelligence_report_inner(extra_ctx, sensor_snapshot)
    finally:
        _INCIDENT_GUARD.in_incidents = False


def _build_incident_intelligence_report_inner(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    sensor_snapshot = sensor_snapshot or {}

    start = _now()

    signals: list[IncidentSignal] = []
    signals.extend(detect_authority_incidents(extra_ctx, sensor_snapshot))
    signals.extend(detect_observability_incidents(extra_ctx, sensor_snapshot))
    signals.extend(detect_validation_incidents(extra_ctx, sensor_snapshot))
    signals.extend(detect_governance_incidents(extra_ctx, sensor_snapshot))
    signals.extend(detect_topology_incidents(extra_ctx, sensor_snapshot))
    signals.extend(detect_semantic_incidents(extra_ctx, sensor_snapshot))
    signals.extend(detect_fastpath_incidents(extra_ctx, sensor_snapshot))
    signals.extend(detect_infrastructure_incidents(extra_ctx, sensor_snapshot))
    signals.extend(detect_performance_incidents(extra_ctx, sensor_snapshot))
    signals.extend(detect_storage_incidents(extra_ctx, sensor_snapshot))
    signals.extend(detect_gpu_incidents(extra_ctx, sensor_snapshot))
    signals.extend(detect_execution_incidents(extra_ctx, sensor_snapshot))

    total_evaluated = len(signals)

    # Correlate signals
    correlated_signals, correlation_results = correlate_incident_signals(signals)

    # Build incidents from correlated signals
    non_info = [s for s in correlated_signals if s.severity not in ("info",)]
    incidents: list[OperationalIncident] = []
    all_blast_entries: list[BlastRadiusEntry] = []

    for sig in non_info:
        blast = calculate_incident_blast_radius(sig, correlated_signals)
        all_blast_entries.extend(blast)
        hyp = build_incident_hypotheses(sig, correlated_signals, correlation_results)
        recs = build_incident_recommendations(sig, blast, hyp)

        det_parts = {
            "domain": sig.domain,
            "signal_type": sig.signal_type,
            "severity": sig.severity,
            "description": sig.description,
            "blast_radius": [e.to_dict() for e in blast],
            "hypotheses": [h.to_dict() for h in hyp],
            "recommendations": [r.to_dict() for r in recs],
        }
        det_hash = _hash(det_parts)

        incident = OperationalIncident(
            incident_id=f"INC-{sig.domain.upper()}-{sig.signal_type.upper()}-{det_hash[:8]}",
            primary_domain=sig.domain,
            severity=sig.severity,
            title=sig.description[:80],
            description=sig.description,
            signals=[sig.to_dict()],
            correlated_signals=[s.to_dict() for s in correlated_signals if s.domain == sig.domain and s != sig][:5],
            blast_radius=[e.to_dict() for e in blast],
            hypotheses=[h.to_dict() for h in hyp],
            recommendations=[r.to_dict() for r in recs],
            evidence=sig.evidence,
            confidence=sig.confidence,
            deterministic_signature=det_hash,
        )
        incidents.append(incident)

    # Merge incidents with same domain and overlapping blast radius
    merged_incidents = _merge_related_incidents(incidents)

    # Determine highest severity
    all_sevs = [i.severity for i in merged_incidents]
    highest = _worst_severity(all_sevs) if all_sevs else "info"

    affected = sorted(set(i.primary_domain for i in merged_incidents))
    recs_total = sum(len(i.recommendations) for i in merged_incidents)

    blast_summary = build_blast_radius_summary(all_blast_entries)

    det_parts = {
        "incidents": [i.to_dict() for i in merged_incidents],
        "correlation_results": correlation_results,
        "blast_summary": blast_summary,
        "total_signals": total_evaluated,
    }
    det_hash = _hash(det_parts)

    report = IncidentIntelligenceReport(
        contract_version=INCIDENT_CONTRACT_VERSION,
        active_incidents=[i.to_dict() for i in merged_incidents],
        incident_count=len(merged_incidents),
        highest_severity=highest,
        affected_domains=affected,
        total_signals_evaluated=total_evaluated,
        correlation_results=correlation_results,
        blast_radius_summary=blast_summary,
        recommendations_total=recs_total,
        deterministic_signature=det_hash,
        generated_at=start,
    )

    result = report.to_dict()

    # Record metrics
    try:
        from runtime.telemetry.prometheus_metrics import record_incident_intelligence_metrics
        record_incident_intelligence_metrics(result)
    except Exception:
        pass

    return result


def _merge_related_incidents(
    incidents: list[OperationalIncident],
) -> list[OperationalIncident]:
    if len(incidents) <= 1:
        return incidents

    domain_incidents: dict[str, list[OperationalIncident]] = {}
    for inc in incidents:
        d = inc.primary_domain
        if d not in domain_incidents:
            domain_incidents[d] = []
        domain_incidents[d].append(inc)

    merged: list[OperationalIncident] = []
    for domain, group in domain_incidents.items():
        if len(group) == 1:
            merged.append(group[0])
        else:
            # Merge into highest severity incident
            group.sort(key=lambda x: SEVERITY_ORDER.get(x.severity, 99))
            primary = group[0]
            all_signals = [s for inc in group for s in inc.signals]
            all_corr = [s for inc in group for s in inc.correlated_signals]
            all_blast = [e for inc in group for e in inc.blast_radius]
            all_hyp = [h for inc in group for h in inc.hypotheses]
            all_recs = [r for inc in group for r in inc.recommendations]
            all_evidence = list(set(e for inc in group for e in inc.evidence))

            det = _hash({
                "domain": domain,
                "count": len(group),
                "merged_signals": len(all_signals),
                "merged_blast": len(all_blast),
            })
            merged.append(OperationalIncident(
                incident_id=f"INC-{domain.upper()}-MERGED-{det[:8]}",
                primary_domain=domain,
                severity=primary.severity,
                title=f"Multiple {domain} incidents merged",
                description=f"Merged {len(group)} incidents in {domain}",
                signals=all_signals,
                correlated_signals=all_corr,
                blast_radius=all_blast,
                hypotheses=all_hyp,
                recommendations=all_recs,
                evidence=all_evidence,
                confidence=_worst_confidence([inc.confidence for inc in group]),
                deterministic_signature=det,
            ))

    return merged
