from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

from runtime.hardening.contracts import (
    RuntimeHardeningContract,
    WatchdogContract,
    TimeoutGovernanceContract,
    DegradedEscalationContract,
    FailureContainmentContract,
    OperationalSafeguardContract,
    RuntimeSurvivabilityContract,
    HARDENING_CONTRACT_VERSION,
)


WATCHDOGS = [
    "WATCHDOG-PROMETHEUS",
    "WATCHDOG-GATEWAY",
    "WATCHDOG-REPORTING",
    "WATCHDOG-GROUNDING",
    "WATCHDOG-OBSERVABILITY",
    "WATCHDOG-TOPOLOGY",
    "WATCHDOG-GOVERNANCE",
    "WATCHDOG-VALIDATION",
]


def _strict_mode() -> bool:
    return os.environ.get("STRICT_VALIDATION_MODE", "false").lower() in ("true", "1", "yes")


def _now() -> float:
    return 0.0 if _strict_mode() else time.time()


def _hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_timeout_governance(sensor_snapshot: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Timeout governance: deterministic timeouts -> authority/confidence degradation.

    In this phase we don't execute timeouts, we model them.
    """
    sensor_snapshot = sensor_snapshot or {}

    timeouts: list[TimeoutGovernanceContract] = []

    # Defaults; can be overridden via env
    defaults = {
        "prometheus": int(os.environ.get("AI_LAB_PROMETHEUS_TIMEOUT", "5")),
        "grafana": int(os.environ.get("AI_LAB_GRAFANA_TIMEOUT", "5")),
        "gateway": int(os.environ.get("AI_LAB_GATEWAY_TIMEOUT", "30")),
        "reporting": int(os.environ.get("AI_LAB_REPORTING_TIMEOUT", "10")),
        "validation": int(os.environ.get("AI_LAB_VALIDATION_TIMEOUT", "10")),
        "tool_execution": int(os.environ.get("AI_LAB_TOOL_TIMEOUT", "30")),
        "plan_resolution": int(os.environ.get("AI_LAB_PLAN_TIMEOUT", "10")),
    }

    stale = sensor_snapshot.get("stale_sources", []) or []
    prom_state = "ok" if not stale else "warning"
    prom_conf = "high" if prom_state == "ok" else "medium"
    prom_deg = prom_state != "ok"
    timeouts.append(TimeoutGovernanceContract(
        component="prometheus",
        timeout_seconds=defaults["prometheus"],
        state=prom_state,
        authority_degraded=prom_deg,
        confidence=prom_conf,
        reasons=["stale_sources detected"] if stale else [],
    ))

    # Other components modeled as ok by default
    for comp in ("grafana", "gateway", "reporting", "validation", "tool_execution", "plan_resolution"):
        timeouts.append(TimeoutGovernanceContract(
            component=comp,
            timeout_seconds=defaults[comp],
            state="ok",
            authority_degraded=False,
            confidence="high" if defaults[comp] <= 60 else "medium",
            reasons=[],
        ))

    return [t.to_dict() for t in timeouts]


def build_runtime_watchdogs(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    sensor_snapshot = sensor_snapshot or {}
    extra_ctx = extra_ctx or {}

    timeouts = build_timeout_governance(sensor_snapshot)
    timeout_map = {t["component"]: t for t in timeouts}

    watchdogs: list[WatchdogContract] = []

    def _wd(name: str, authority: str, timeout_comp: str, last_success: float | None, state: str, confidence: str, triggers: list[str]):
        t = timeout_map.get(timeout_comp, {})
        watchdogs.append(WatchdogContract(
            watchdog=name,
            state=state,
            authority=authority,
            timeout_seconds=int(t.get("timeout_seconds", 10) or 10),
            last_success=last_success,
            confidence=confidence,
            escalation_level="none" if state == "healthy" else "warning" if state == "degraded" else "critical",
            explainable=True,
            reasons=triggers,
        ))

    stale = sensor_snapshot.get("stale_sources", []) or []
    observed = sensor_snapshot.get("observed_sources_count", 0) or 0
    missing = sensor_snapshot.get("missing_sources_count", 0) or 0

    # Prometheus watchdog is derived from stale/observed
    if observed == 0 and (observed + missing) > 0:
        prom_state = "critical"
        prom_conf = "low"
        triggers = ["no observed sources"]
    elif stale:
        prom_state = "degraded"
        prom_conf = "medium"
        triggers = [f"stale_sources={len(stale)}"]
    else:
        prom_state = "healthy"
        prom_conf = "high"
        triggers = []
    _wd("WATCHDOG-PROMETHEUS", "prometheus", "prometheus", last_success=None if stale else _now(), state=prom_state, confidence=prom_conf, triggers=triggers)

    # Gateway watchdog: we can only assert unknown here without probing.
    _wd("WATCHDOG-GATEWAY", "gateway", "gateway", last_success=None, state="degraded" if stale else "healthy", confidence="medium" if stale else "high", triggers=["derived from observability"] if stale else [])

    # Reporting watchdog: reporting depends on observability/governance.
    _wd("WATCHDOG-REPORTING", "reporting", "reporting", last_success=None, state="degraded" if stale else "healthy", confidence="medium" if stale else "high", triggers=["observability stale"] if stale else [])

    # Grounding watchdog: if sensor snapshot exists, grounding should be available.
    grounding_state = "healthy" if sensor_snapshot is not None else "degraded"
    _wd("WATCHDOG-GROUNDING", "grounding", "reporting", last_success=_now() if sensor_snapshot else None, state=grounding_state, confidence="high" if grounding_state == "healthy" else "low", triggers=[] if grounding_state == "healthy" else ["sensor_snapshot missing"])

    # Observability watchdog
    obs_state = "healthy" if observed > 0 and not stale else "degraded" if observed > 0 else "critical" if (observed + missing) > 0 else "degraded"
    obs_conf = "high" if obs_state == "healthy" else "medium" if obs_state == "degraded" else "low"
    _wd("WATCHDOG-OBSERVABILITY", "observability", "prometheus", last_success=None if stale else _now(), state=obs_state, confidence=obs_conf, triggers=["stale observability"] if stale else [])

    # Topology watchdog: use topology confidence if available
    topo_conf = 0
    try:
        from runtime.topology import calculate_topology_confidence
        topo_conf = int((calculate_topology_confidence(sensor_snapshot, extra_ctx) or {}).get("overall_score", 0))
    except Exception:
        topo_conf = 0
    topo_state = "healthy" if topo_conf >= 80 else "degraded" if topo_conf >= 50 else "critical"
    _wd("WATCHDOG-TOPOLOGY", "topology", "plan_resolution", last_success=_now() if topo_conf else None, state=topo_state, confidence="high" if topo_conf >= 80 else "medium" if topo_conf >= 50 else "low", triggers=[f"topology_confidence={topo_conf}"])

    # Governance watchdog: avoid importing governance here to prevent recursion.
    # If a caller wants a grounded score, pass it in extra_ctx.
    gov_score_raw = extra_ctx.get("governance_score")
    gov_score = float(gov_score_raw or 0.0)
    if gov_score_raw is None:
        gov_state = "degraded"
        gov_conf = "low"
        triggers = ["governance_score unavailable"]
        last_success = None
    else:
        gov_state = "healthy" if gov_score >= 85 else "degraded" if gov_score >= 65 else "critical"
        gov_conf = "high" if gov_state == "healthy" else "medium" if gov_state == "degraded" else "low"
        triggers = [f"governance_score={gov_score}"]
        last_success = _now()
    _wd(
        "WATCHDOG-GOVERNANCE",
        "governance",
        "validation",
        last_success=last_success,
        state=gov_state,
        confidence=gov_conf,
        triggers=triggers,
    )

    # Validation watchdog: avoid importing validation here to prevent recursion.
    # If a caller wants a grounded score, pass it in extra_ctx.
    val_score_raw = extra_ctx.get("validation_score")
    val_score = float(val_score_raw or 0.0)
    if val_score_raw is None:
        val_state = "degraded"
        val_conf = "low"
        triggers = ["validation_score unavailable"]
        last_success = None
    else:
        val_state = "healthy" if val_score >= 85 else "degraded" if val_score >= 65 else "critical"
        val_conf = "high" if val_state == "healthy" else "medium" if val_state == "degraded" else "low"
        triggers = [f"validation_score={val_score}"]
        last_success = _now()
    _wd(
        "WATCHDOG-VALIDATION",
        "validation",
        "validation",
        last_success=last_success,
        state=val_state,
        confidence=val_conf,
        triggers=triggers,
    )

    return [w.to_dict() for w in watchdogs]


def build_degraded_escalation(
    watchdogs: list[dict[str, Any]] | None = None,
    timeouts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    watchdogs = watchdogs or build_runtime_watchdogs()
    timeouts = timeouts or build_timeout_governance()

    critical = [w for w in watchdogs if w.get("state") == "critical"]
    degraded = [w for w in watchdogs if w.get("state") == "degraded"]
    timeout_deg = [t for t in timeouts if t.get("authority_degraded")]

    triggers = []
    if critical:
        triggers.append(f"critical_watchdogs={len(critical)}")
    if degraded:
        triggers.append(f"degraded_watchdogs={len(degraded)}")
    if timeout_deg:
        triggers.append(f"timeout_governance_degraded={len(timeout_deg)}")

    if critical and len(critical) >= 2:
        state = "containment_mode"
    elif critical:
        state = "critical"
    elif degraded or timeout_deg:
        state = "degraded"
    else:
        state = "healthy"

    if state == "healthy" and degraded:
        state = "healthy_degraded"

    confidence = "high" if state == "healthy" else "medium" if state in ("healthy_degraded", "degraded") else "low"
    contract = DegradedEscalationContract(
        escalation_state=state,
        triggers=triggers,
        confidence=confidence,
        explainable=True,
        last_transition=_now(),
    )
    return contract.to_dict()


def build_failure_containment_summary(escalation: dict[str, Any] | None = None) -> dict[str, Any]:
    escalation = escalation or build_degraded_escalation()
    state = escalation.get("escalation_state", "unknown")
    containment = state == "containment_mode"

    policies = [
        "routing_freeze",
        "report_downgrade",
        "observability_conservative_mode",
        "governance_restricted_mode",
        "validation_fallback_mode",
        "topology_uncertainty_mode",
    ]
    active = []
    reasons = []
    if state in ("critical", "containment_mode"):
        active = ["routing_freeze", "report_downgrade", "governance_restricted_mode"]
        reasons.append(f"escalation_state={state}")
    elif state == "degraded":
        active = ["report_downgrade", "observability_conservative_mode"]
        reasons.append("degraded escalation")

    contract = FailureContainmentContract(
        containment_mode=containment,
        policies=policies,
        active_policies=active,
        explainable=True,
        reasons=reasons,
    )
    return contract.to_dict()


def build_operational_safeguards(
    escalation: dict[str, Any] | None = None,
    watchdogs: list[dict[str, Any]] | None = None,
    timeouts: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    escalation = escalation or build_degraded_escalation(watchdogs, timeouts)
    state = escalation.get("escalation_state", "unknown")

    def _mk(name: str, derived: list[str], restricted: bool, blocked: bool, reasons: list[str]):
        if blocked:
            s = "blocked"
            conf = "low"
        elif restricted:
            s = "restricted"
            conf = "medium"
        else:
            s = "safe"
            conf = "high"
        return OperationalSafeguardContract(
            safeguard=name,
            state=s,
            confidence=conf,
            explainable=True,
            derived_from=derived,
            reasons=reasons,
        ).to_dict()

    blocked = state == "containment_mode"
    restricted = state in ("degraded", "critical")
    reasons = [f"escalation_state={state}"] if state != "healthy" else []

    return [
        _mk("SAFE_ROUTING_MODE", ["watchdogs", "timeouts", "escalation"], restricted, blocked, reasons),
        _mk("SAFE_REPORTING_MODE", ["watchdogs", "timeouts", "escalation"], restricted, blocked, reasons),
        _mk("SAFE_GROUNDING_MODE", ["watchdogs", "timeouts"], restricted, False, reasons),
        _mk("SAFE_OBSERVABILITY_MODE", ["watchdogs", "timeouts"], restricted, blocked, reasons),
        _mk("SAFE_GOVERNANCE_MODE", ["watchdogs", "escalation"], restricted, blocked, reasons),
        _mk("SAFE_VALIDATION_MODE", ["watchdogs", "timeouts"], restricted, False, reasons),
    ]


def build_runtime_survivability(
    watchdogs: list[dict[str, Any]] | None = None,
    escalation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    watchdogs = watchdogs or build_runtime_watchdogs()
    escalation = escalation or build_degraded_escalation(watchdogs)
    state = escalation.get("escalation_state", "unknown")

    # Inventory does not participate. Use watchdogs states.
    critical = sum(1 for w in watchdogs if w.get("state") == "critical")
    degraded = sum(1 for w in watchdogs if w.get("state") == "degraded")

    base = 1.0
    base -= min(0.6, critical * 0.2)
    base -= min(0.3, degraded * 0.05)
    if state == "containment_mode":
        base -= 0.2
    score = round(max(0.0, min(1.0, base)) * 100, 1)
    level = "high" if score >= 85 else "medium" if score >= 65 else "low" if score >= 40 else "critical"

    contract = RuntimeSurvivabilityContract(
        survivability_score=score,
        survivability_level=level,
        continuity="continuous" if score >= 65 else "at_risk",
        authority_survivability="stable" if critical == 0 else "degraded" if critical == 1 else "unstable",
        observability_survivability="stable" if not any(w.get("watchdog") == "WATCHDOG-OBSERVABILITY" and w.get("state") != "healthy" for w in watchdogs) else "degraded",
        governance_survivability="stable" if not any(w.get("watchdog") == "WATCHDOG-GOVERNANCE" and w.get("state") == "critical" for w in watchdogs) else "degraded",
        reporting_survivability="stable" if not any(w.get("watchdog") == "WATCHDOG-REPORTING" and w.get("state") == "critical" for w in watchdogs) else "degraded",
        degraded_continuity="supported" if state in ("healthy_degraded", "degraded", "critical", "containment_mode") else "unknown",
        explainable=True,
        details={"critical_watchdogs": critical, "degraded_watchdogs": degraded, "escalation_state": state},
    )
    return contract.to_dict()


def detect_operational_instability(
    watchdogs: list[dict[str, Any]] | None = None,
    timeouts: list[dict[str, Any]] | None = None,
    escalation: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    watchdogs = watchdogs or build_runtime_watchdogs()
    timeouts = timeouts or build_timeout_governance()
    escalation = escalation or build_degraded_escalation(watchdogs, timeouts)

    events = []
    if any(w.get("state") == "critical" for w in watchdogs):
        events.append({"type": "watchdog_critical", "count": sum(1 for w in watchdogs if w.get("state") == "critical")})
    if any(t.get("state") == "critical" for t in timeouts):
        events.append({"type": "timeout_critical", "count": sum(1 for t in timeouts if t.get("state") == "critical")})
    if escalation.get("escalation_state") == "containment_mode":
        events.append({"type": "containment_mode", "reason": "multiple critical watchdogs"})
    if not events:
        events.append({"type": "stable", "detail": "no operational instability detected"})
    return events


def calculate_hardening_score(
    watchdogs: list[dict[str, Any]] | None = None,
    timeouts: list[dict[str, Any]] | None = None,
    escalation: dict[str, Any] | None = None,
    survivability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    watchdogs = watchdogs or build_runtime_watchdogs()
    timeouts = timeouts or build_timeout_governance()
    escalation = escalation or build_degraded_escalation(watchdogs, timeouts)
    survivability = survivability or build_runtime_survivability(watchdogs, escalation)

    critical = sum(1 for w in watchdogs if w.get("state") == "critical")
    degraded = sum(1 for w in watchdogs if w.get("state") == "degraded")
    timeout_deg = sum(1 for t in timeouts if t.get("authority_degraded"))
    surv = float(survivability.get("survivability_score", 0.0) or 0.0)

    base = 1.0
    base -= min(0.6, critical * 0.15)
    base -= min(0.3, degraded * 0.05)
    base -= min(0.2, timeout_deg * 0.05)
    base = (base * 0.6) + ((surv / 100.0) * 0.4)
    score = round(max(0.0, min(1.0, base)) * 100, 1)
    level = "high" if score >= 85 else "medium" if score >= 65 else "low" if score >= 40 else "critical"
    return {
        "hardening_score": score,
        "hardening_level": level,
        "components": {
            "critical_watchdogs": critical,
            "degraded_watchdogs": degraded,
            "timeout_governance_degraded": timeout_deg,
            "survivability_score": surv,
        },
        "contract_version": HARDENING_CONTRACT_VERSION,
        "generated_at": _now(),
    }


def build_runtime_hardening_report(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sensor_snapshot = sensor_snapshot or {}
    extra_ctx = extra_ctx or {}

    timeouts = build_timeout_governance(sensor_snapshot)
    watchdogs = build_runtime_watchdogs(sensor_snapshot, extra_ctx)
    escalation = build_degraded_escalation(watchdogs, timeouts)
    containment = build_failure_containment_summary(escalation)
    safeguards = build_operational_safeguards(escalation, watchdogs, timeouts)
    survivability = build_runtime_survivability(watchdogs, escalation)
    instability = detect_operational_instability(watchdogs, timeouts, escalation)
    score = calculate_hardening_score(watchdogs, timeouts, escalation, survivability)

    contract = RuntimeHardeningContract(
        hardening_score=score.get("hardening_score", 0.0),
        hardening_level=score.get("hardening_level", "unknown"),
        watchdogs=watchdogs,
        timeouts=timeouts,
        escalation=escalation,
        containment=containment,
        safeguards=safeguards,
        survivability=survivability,
        instability=instability,
        strict_mode=_strict_mode(),
        contract_version=HARDENING_CONTRACT_VERSION,
        generated_at=_now(),
    )

    result = contract.to_dict()
    result["deterministic_signature"] = _hash({
        "hardening_score": result.get("hardening_score"),
        "hardening_level": result.get("hardening_level"),
        "watchdogs": result.get("watchdogs"),
        "timeouts": result.get("timeouts"),
        "escalation": result.get("escalation"),
        "containment": result.get("containment"),
        "safeguards": result.get("safeguards"),
        "survivability": result.get("survivability"),
    })

    try:
        from runtime.telemetry.prometheus_metrics import record_hardening_metrics
        record_hardening_metrics(result)
    except Exception:
        pass

    return result
