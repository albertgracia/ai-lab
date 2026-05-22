from __future__ import annotations

import os
import time
from typing import Any

from runtime.governance.contracts import (
    GovernanceRegistryContract,
    GovernanceDomainContract,
    GovernanceAuthorityContract,
    GovernanceConfidenceContract,
    GovernanceRiskContract,
    GovernanceRemediationContract,
    GovernanceHealthContract,
    GovernanceContractRegistry,
    GOVERNANCE_CONTRACT_VERSION,
)

GOVERNANCE_DOMAINS = [
    "runtime", "topology", "observability", "reporting",
    "grounding", "routing", "gpu", "storage",
    "archive", "governance", "ui_alignment", "grafana",
    "prometheus", "loki", "entities",
    "tools", "plans", "gc",
]

DOMAIN_AUTHORITY = {
    "runtime": {"authority_type": "operational", "source_of_truth": "runtime_state", "confidence": "high"},
    "topology": {"authority_type": "dependency", "source_of_truth": "runtime_topology_31d", "confidence": "high"},
    "prometheus": {"authority_type": "operational", "source_of_truth": "prometheus", "confidence": "high"},
    "grafana": {"authority_type": "visualization", "source_of_truth": "grafana", "confidence": "high"},
    "observability": {"authority_type": "observational", "source_of_truth": "prometheus", "confidence": "high"},
    "reporting": {"authority_type": "derived_cognition", "source_of_truth": "runtime_reporting", "confidence": "medium"},
    "grounding": {"authority_type": "runtime_validation", "source_of_truth": "runtime_grounding_30ig", "confidence": "high"},
    "governance": {"authority_type": "governance", "source_of_truth": "runtime_governance_33a", "confidence": "high"},
    "gpu": {"authority_type": "operational", "source_of_truth": "sensor_fusion", "confidence": "high"},
    "routing": {"authority_type": "operational", "source_of_truth": "route_policy", "confidence": "high"},
    "ui_alignment": {"authority_type": "validation", "source_of_truth": "runtime_ui_alignment_32a", "confidence": "high"},
    "entities": {"authority_type": "taxonomy", "source_of_truth": "runtime_entities_31e", "confidence": "medium"},
    "storage": {"authority_type": "operational", "source_of_truth": "prometheus", "confidence": "medium"},
    "archive": {"authority_type": "storage_policy", "source_of_truth": "archive_policy", "confidence": "medium"},
    "loki": {"authority_type": "logging", "source_of_truth": "loki", "confidence": "low"},
    "tools": {"authority_type": "execution_surface", "source_of_truth": "tool_registry_28_4", "confidence": "high"},
    "plans": {"authority_type": "execution_surface", "source_of_truth": "plan_registry_28_4", "confidence": "high"},
    "gc": {"authority_type": "restricted", "source_of_truth": "crossplan_gc_28_4", "confidence": "high"},
}

DOMAIN_CONFIDENCE_DEFAULTS = {
    "runtime": "high", "topology": "high", "observability": "high",
    "reporting": "medium", "grounding": "high", "routing": "high",
    "gpu": "high", "storage": "medium", "archive": "medium",
    "governance": "high", "ui_alignment": "high", "grafana": "high",
    "prometheus": "high", "loki": "medium", "entities": "medium",
    "tools": "high", "plans": "high", "gc": "high",
}

DOMAIN_FRESHNESS_DEFAULTS = {
    d: "fresh" for d in GOVERNANCE_DOMAINS
}

REGISTERED_PHASES = [
    {"phase": "30I-D", "label": "Sensor Semantics Normalization", "domain": "gpu"},
    {"phase": "30I-E", "label": "Operational Response Formatting", "domain": "grounding"},
    {"phase": "30I-F", "label": "Runtime Cognitive Compression", "domain": "routing"},
    {"phase": "30I-F0", "label": "Runtime Model Routing Cleanup", "domain": "routing"},
    {"phase": "30I-G", "label": "Deterministic Runtime Grounding", "domain": "grounding"},
    {"phase": "OBS-31A", "label": "Observability Source-of-Truth Audit", "domain": "observability"},
    {"phase": "OBS-31A.1", "label": "Prometheus Authority Audit", "domain": "prometheus"},
    {"phase": "OBS-31A.2", "label": "Grafana Drift Audit", "domain": "grafana"},
    {"phase": "OBS-31A.3", "label": "Runtime-Observability Alignment", "domain": "observability"},
    {"phase": "OBS-31A.4", "label": "Observability Remediation Plan", "domain": "observability"},
    {"phase": "OBS-31A.5", "label": "Safe Quick Wins Execution", "domain": "observability"},
    {"phase": "31B", "label": "Runtime Semantic Maturity", "domain": "runtime"},
    {"phase": "31C", "label": "Operational Reporting Discipline", "domain": "reporting"},
    {"phase": "31E", "label": "Active/Inventory/Discoverable Separation", "domain": "entities"},
    {"phase": "31D", "label": "Runtime Topology Awareness", "domain": "topology"},
    {"phase": "32A", "label": "Runtime UI Alignment", "domain": "ui_alignment"},
    {"phase": "32B", "label": "Grafana Semantic Cleanup", "domain": "grafana"},
    {"phase": "33A", "label": "Runtime Governance Registry", "domain": "governance"},
    {"phase": "33B", "label": "Runtime Pre-Pilot Validation Framework", "domain": "governance"},
    {"phase": "28.4", "label": "Tool Contracts & Cross-Plan GC", "domain": "tools"},
]

ACTIVE_CONTRACTS = [
    "30I-D", "30I-E", "30I-F", "30I-G",
    "OBS-31A", "OBS-31A.1", "OBS-31A.5",
    "31B", "31C", "31D", "31E", "32A", "32B", "33A", "33B", "28.4",
]

DEPRECATED_CONTRACTS = [
    "30I-F0",
    "OBS-31A.2", "OBS-31A.3", "OBS-31A.4",
]

_CONFIDENCE_VALUE = {"high": 1.0, "medium": 0.6, "low": 0.2, "unknown": 0.0}


def _confidence_to_score(conf: str) -> float:
    return _CONFIDENCE_VALUE.get(conf, 0.0)


def _score_to_confidence(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.5:
        return "medium"
    if score >= 0.2:
        return "low"
    return "unknown"


def _ensure_list(val: Any) -> list:
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [val]
    return []


def _try_import_topology_confidence() -> dict[str, Any]:
    try:
        from runtime.topology import calculate_topology_confidence
        return calculate_topology_confidence()
    except ImportError:
        return {"overall_score": 0, "confidence_level": "unavailable"}


def _try_import_entity_confidence() -> float:
    try:
        from runtime.entities import build_entity_registry
        registry = build_entity_registry()
        if not registry:
            return 0.0
        confs = [e.get("confidence", "unknown") for e in registry]
        scores = [_confidence_to_score(c) for c in confs]
        return sum(scores) / max(len(scores), 1)
    except ImportError:
        return 0.0


def _try_import_observability_audit() -> dict[str, Any]:
    try:
        from runtime.observability import build_observability_audit
        return build_observability_audit()
    except ImportError:
        return {}


def _try_import_remediation() -> dict[str, Any]:
    result = {
        "total": 0,
        "critical": 0,
        "quick_wins": 0,
        "high_risk": 0,
        "technical_debt": [],
    }
    try:
        from runtime.observability import build_remediation_plan
        plan = build_remediation_plan()
        if isinstance(plan, dict):
            items = plan.get("items", [])
            result["total"] = len(items)
            result["critical"] = sum(1 for i in items if i.get("severity") == "critical")
            result["quick_wins"] = sum(1 for i in items if i.get("type") == "quick_win")
            result["high_risk"] = sum(1 for i in items if i.get("type") == "high_risk")
            domains = set()
            for i in items:
                d = i.get("domain")
                if d:
                    domains.add(d)
            result["technical_debt"] = sorted(domains)
    except ImportError:
        pass

    return result


def _try_import_observability_state() -> dict[str, Any]:
    try:
        from runtime.observability import build_observability_state
        return build_observability_state()
    except ImportError:
        return {"observability_freshness": "unknown", "observability_confidence": "unknown"}


def build_governance_domains(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if extra_ctx is None:
        extra_ctx = {}
    sensor_snapshot = sensor_snapshot or {}
    dc = sensor_snapshot.get("domain_confidence", {}) or {}
    domain_freshness = sensor_snapshot.get("freshness", {}) or {}

    domains = []
    for d in GOVERNANCE_DOMAINS:
        base_authority = DOMAIN_AUTHORITY.get(d, {})
        base_conf = dc.get(d, DOMAIN_CONFIDENCE_DEFAULTS.get(d, "unknown"))
        base_fresh = domain_freshness.get(d, "fresh")
        degraded = base_conf == "low" or False
        contract = GovernanceDomainContract(
            domain=d,
            operational_state="degraded" if degraded else "healthy",
            confidence=base_conf,
            authority=base_authority.get("authority_type", "unknown"),
            source_of_truth=base_authority.get("source_of_truth", "unknown"),
            freshness=base_fresh,
            degraded=degraded,
            explainable=True,
        )
        domains.append(contract.to_dict())
    return domains


def build_governance_authority_map(
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    authorities = {}
    for domain, info in DOMAIN_AUTHORITY.items():
        contract = GovernanceAuthorityContract(
            domain=domain,
            authority_type=info["authority_type"],
            source_of_truth=info["source_of_truth"],
            confidence=info["confidence"],
            freshness="fresh",
            valid=True,
        )
        authorities[domain] = contract.to_dict()

    prometheus_targets = False
    if extra_ctx:
        prometheus_targets = bool(extra_ctx.get("prometheus_targets"))
    if not prometheus_targets:
        authorities["prometheus"]["freshness"] = "stale"
        authorities["prometheus"]["valid"] = False
        authorities["observability"]["freshness"] = "stale"
        authorities["observability"]["confidence"] = "medium"

    return {
        "authorities": authorities,
        "operational_authority": "prometheus",
        "visualization_authority": "grafana",
        "dependency_authority": "topology",
        "validation_authority": "grounding",
        "fallback_authority": "inventory",
        "governance_authority": "governance",
    }


def build_governance_confidence_map(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sensor_snapshot = sensor_snapshot or {}
    dc = sensor_snapshot.get("domain_confidence", {}) or {}
    obs_fresh = sensor_snapshot.get("observability_freshness", "unknown")

    topology_conf = _try_import_topology_confidence()
    topo_score = topology_conf.get("overall_score", 0)

    entity_conf = _try_import_entity_confidence()

    domains = {}
    for d in GOVERNANCE_DOMAINS:
        base_conf = dc.get(d, DOMAIN_CONFIDENCE_DEFAULTS.get(d, "unknown"))
        propagated = []
        if d == "observability" and base_conf == "unknown":
            propagated.append("prometheus")
        if d == "reporting" and base_conf == "unknown":
            propagated.append("observability")
        if d == "governance" and base_conf == "unknown":
            propagated.append("topology")
            propagated.append("observability")

        fresh = "fresh"
        if d == "topology" and topo_score < 50:
            fresh = "stale"
        if d == "observability" and obs_fresh == "stale":
            fresh = "stale"
        if d == "governance" and fresh == "stale":
            fresh = "stale"

        score = _confidence_to_score(base_conf)
        degraded = base_conf == "low"

        contract = GovernanceConfidenceContract(
            domain=d,
            confidence=base_conf,
            freshness=fresh,
            propagated_from=propagated,
            degraded=degraded,
            score=score,
        )
        domains[d] = contract.to_dict()

    return {
        "domains": domains,
        "topology_confidence": topo_score,
        "entity_confidence_avg": round(entity_conf, 2),
        "overall_generated_at": time.time(),
    }


def build_governance_risk_summary(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    sensor_snapshot = sensor_snapshot or {}

    stale_sources = sensor_snapshot.get("stale_sources", [])
    if stale_sources:
        risks.append(GovernanceRiskContract(
            risk_type="stale_authority",
            severity="medium",
            domain="observability",
            description=f"stale observability sources: {', '.join(stale_sources[:3])}",
            confidence="medium",
        ).to_dict())

    domain_confidence = sensor_snapshot.get("domain_confidence", {}) or {}
    for domain, conf in domain_confidence.items():
        if conf == "low":
            risks.append(GovernanceRiskContract(
                risk_type="low_confidence",
                severity="medium",
                domain=domain,
                description=f"confidence baja en dominio: {domain}",
                confidence="high",
            ).to_dict())

    try:
        from runtime.topology import detect_topology_drift
        drift = detect_topology_drift()
        if drift:
            risks.append(GovernanceRiskContract(
                risk_type="topology_drift",
                severity="medium",
                domain="topology",
                description=f"{len(drift)} desviaciones topologicas detectadas",
                confidence="high",
            ).to_dict())
    except ImportError:
        pass

    try:
        from runtime.observability import build_observability_audit
        audit = build_observability_audit()
        if isinstance(audit, dict):
            broken = audit.get("broken_panels", 0) or 0
            stale_metrics = audit.get("stale_metrics", 0) or 0
            if broken > 0:
                risks.append(GovernanceRiskContract(
                    risk_type="broken_observability",
                    severity="high" if broken > 3 else "medium",
                    domain="observability",
                    description=f"{broken} broken panels en Grafana",
                    confidence="high",
                ).to_dict())
            if stale_metrics > 0:
                risks.append(GovernanceRiskContract(
                    risk_type="stale_observability",
                    severity="low",
                    domain="observability",
                    description=f"{stale_metrics} metricas stale en inventario",
                    confidence="medium",
                ).to_dict())
    except ImportError:
        pass

    if not risks:
        risks.append(GovernanceRiskContract(
            risk_type="no_risks",
            severity="info",
            domain="governance",
            description="ningun riesgo activo detectado en governance",
            confidence="high",
        ).to_dict())

    return risks


def build_governance_remediation_summary(
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    remediation_data = _try_import_remediation()

    items = []
    for phase_info in REGISTERED_PHASES:
        phase = phase_info["phase"]
        contract = GovernanceRemediationContract(
            phase=phase,
            domain=phase_info["domain"],
            status="completed" if phase in ACTIVE_CONTRACTS else "deprecated",
            severity="info",
            description=phase_info["label"],
        )
        items.append(contract.to_dict())

    return {
        "total_remediation": remediation_data.get("total", 0),
        "critical_items": remediation_data.get("critical", 0),
        "quick_wins": remediation_data.get("quick_wins", 0),
        "high_risk_changes": remediation_data.get("high_risk", 0),
        "technical_debt_domains": remediation_data.get("technical_debt", []),
        "registered_phases_total": len(items),
        "phases": items,
    }


def build_governance_contract_registry(
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stale_contracts = []
    incompatible_contracts = []

    for phase_info in REGISTERED_PHASES:
        phase = phase_info["phase"]
        if phase in DEPRECATED_CONTRACTS:
            if phase not in stale_contracts:
                stale_contracts.append(phase)

    for phase in ["30I-F0"]:
        if phase not in incompatible_contracts:
            incompatible_contracts.append(phase)

    registry = GovernanceContractRegistry(
        registered_phases=REGISTERED_PHASES,
        active_contracts=list(ACTIVE_CONTRACTS),
        deprecated_contracts=list(DEPRECATED_CONTRACTS),
        incompatible_contracts=incompatible_contracts,
        stale_contracts=stale_contracts,
        total_contracts=len(REGISTERED_PHASES),
    )
    return registry.to_dict()


def build_governance_health_summary(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
    domains: list[dict[str, Any]] | None = None,
    risks: list[dict[str, Any]] | None = None,
    remediation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if domains is None:
        domains = build_governance_domains(extra_ctx, sensor_snapshot)
    if risks is None:
        risks = build_governance_risk_summary(extra_ctx, sensor_snapshot)
    if remediation is None:
        remediation = build_governance_remediation_summary(extra_ctx)

    degraded = [d["domain"] for d in domains if d.get("degraded")]
    stale = []
    authority_map = build_governance_authority_map(extra_ctx)
    for domain, info in authority_map.get("authorities", {}).items():
        if isinstance(info, dict) and info.get("freshness") == "stale":
            stale.append(domain)

    confidence_values = {d.get("confidence", "unknown") for d in domains}
    if "low" in confidence_values:
        health_conf = "low"
    elif "medium" in confidence_values:
        health_conf = "medium"
    else:
        health_conf = "high"

    active_risks = [r for r in risks if r.get("severity") in ("high", "medium", "critical")]
    state = "degraded" if degraded else "healthy"
    if any(r.get("severity") == "critical" for r in risks):
        state = "critical"

    health = GovernanceHealthContract(
        operational_state=state,
        governance_level="enforced" if state != "unknown" else "passive",
        degraded_domains=degraded,
        risks_total=len(active_risks),
        remediation_pending=remediation.get("critical_items", 0) + remediation.get("high_risk_changes", 0),
        stale_authority=stale,
        confidence=health_conf,
        freshness="fresh",
    )
    return health.to_dict()


def calculate_governance_score(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
    domains: list[dict[str, Any]] | None = None,
    risks: list[dict[str, Any]] | None = None,
    health_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if domains is None:
        domains = build_governance_domains(extra_ctx, sensor_snapshot)
    if risks is None:
        risks = build_governance_risk_summary(extra_ctx, sensor_snapshot)
    if health_summary is None:
        health_summary = build_governance_health_summary(extra_ctx, sensor_snapshot, domains, risks)

    components = {}

    topology_conf = _try_import_topology_confidence()
    topo_score = topology_conf.get("overall_score", 0)
    components["topology_confidence_weighted"] = round(topo_score / 100.0, 2)

    confidence_values = [d.get("confidence", "unknown") for d in domains]
    conf_scores = [_confidence_to_score(c) for c in confidence_values]
    domain_conf = sum(conf_scores) / max(len(conf_scores), 1)
    components["domain_confidence_avg"] = round(domain_conf, 2)

    degraded = [d for d in domains if d.get("degraded")]
    degraded_penalty = len(degraded) * 0.05
    components["degraded_domain_penalty"] = round(degraded_penalty, 2)

    severity_penalty = sum(
        0.1 for r in risks if r.get("severity") == "high" or r.get("severity") == "critical"
    ) + sum(0.05 for r in risks if r.get("severity") == "medium")
    components["risk_severity_penalty"] = round(severity_penalty, 2)

    fresh_count = sum(1 for d in domains if d.get("freshness") == "fresh")
    stale_count = sum(1 for d in domains if d.get("freshness") in ("stale", "expired"))
    total_domains = len(domains)
    freshness_ratio = fresh_count / max(total_domains, 1) - (stale_count * 0.1 / max(total_domains, 1))
    components["freshness_score"] = round(max(0.0, freshness_ratio), 2)

    explainable = sum(1 for d in domains if d.get("explainable"))
    components["explainability_ratio"] = round(explainable / max(total_domains, 1), 2)

    base = domain_conf
    score_components = [
        components.get("topology_confidence_weighted", 0.5) * 0.2,
        base * 0.3,
        components.get("freshness_score", 0.5) * 0.2,
        components.get("explainability_ratio", 1.0) * 0.15,
        0.15,
    ]
    score = sum(score_components)

    score -= min(degraded_penalty, 0.5)
    score -= min(severity_penalty, 0.3)

    final_score = round(max(0.0, min(1.0, score)) * 100, 1)

    level = "degraded"
    if final_score >= 85:
        level = "high"
    elif final_score >= 65:
        level = "medium"
    elif final_score >= 40:
        level = "low"
    else:
        level = "critical"

    return {
        "governance_score": final_score,
        "governance_level": level,
        "components": components,
        "degraded_domains": [d["domain"] for d in degraded],
        "risks_total": len([r for r in risks if r.get("severity") in ("high", "medium", "critical")]),
        "contract_version": GOVERNANCE_CONTRACT_VERSION,
        "generated_at": time.time(),
    }


def detect_governance_drift(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    drift: list[dict[str, Any]] = []
    sensor_snapshot = sensor_snapshot or {}

    stale_sources = sensor_snapshot.get("stale_sources", [])
    if stale_sources:
        drift.append({
            "drift_type": "stale_observability",
            "severity": "medium",
            "description": f"stale sources: {', '.join(stale_sources[:3])}",
            "confidence": "medium",
        })

    try:
        from runtime.topology import detect_topology_drift
        topo_drift = detect_topology_drift()
        for d in topo_drift:
            drift.append({
                "drift_type": "topology_drift",
                "severity": d.get("severity", "medium"),
                "description": d.get("message", "topology drift detected"),
                "confidence": "high",
            })
    except ImportError:
        drift.append({
            "drift_type": "topology_module_missing",
            "severity": "low",
            "description": "topology drift detection module not available",
            "confidence": "low",
        })

    domain_confidence = sensor_snapshot.get("domain_confidence", {}) or {}
    for domain, conf in domain_confidence.items():
        if conf == "low":
            drift.append({
                "drift_type": "domain_confidence_drift",
                "severity": "medium",
                "description": f"confidence baja en dominio: {domain}",
                "confidence": "high",
            })

    if not drift:
        drift.append({
            "drift_type": "no_drift",
            "severity": "info",
            "description": "no governance drift detected",
            "confidence": "high",
        })

    return drift


def build_runtime_governance_registry(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if extra_ctx is None:
        extra_ctx = {}
    sensor_snapshot = sensor_snapshot or {}

    domains = build_governance_domains(extra_ctx, sensor_snapshot)
    authority_map = build_governance_authority_map(extra_ctx)
    confidence_map = build_governance_confidence_map(extra_ctx, sensor_snapshot)
    risks = build_governance_risk_summary(extra_ctx, sensor_snapshot)
    remediation = build_governance_remediation_summary(extra_ctx)
    contract_registry = build_governance_contract_registry(extra_ctx)
    health_summary = build_governance_health_summary(extra_ctx, sensor_snapshot, domains, risks, remediation)
    score_info = calculate_governance_score(extra_ctx, sensor_snapshot, domains, risks, health_summary)
    drift = detect_governance_drift(extra_ctx, sensor_snapshot)

    contract = GovernanceRegistryContract(
        governance_score=score_info["governance_score"],
        governance_level=score_info["governance_level"],
        degraded_domains=[d["domain"] for d in domains if d.get("degraded")],
        risks=risks,
        authority_map=authority_map,
        confidence_map=confidence_map,
        contract_registry=contract_registry,
        remediation=remediation,
        health_summary=health_summary,
        freshness="fresh",
        contract_version=GOVERNANCE_CONTRACT_VERSION,
        generated_at=time.time(),
    )

    result = contract.to_dict()
    result["domains"] = domains
    result["governance_score_info"] = {
        "score": score_info["governance_score"],
        "level": score_info["governance_level"],
        "components": score_info["components"],
        "contract_version": score_info["contract_version"],
    }
    result["drift"] = drift

    try:
        from runtime.telemetry.prometheus_metrics import record_governance_metrics
        record_governance_metrics(result)
    except ImportError:
        pass

    return result


def build_governance_executive_summary(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> str:
    registry = build_runtime_governance_registry(extra_ctx, sensor_snapshot)
    score = registry.get("governance_score_info", {}).get("score", 0)
    level = registry.get("governance_score_info", {}).get("level", "unknown")
    degraded = registry.get("degraded_domains", [])
    risks_total = len(registry.get("risks", []))
    health = registry.get("health_summary", {})

    lines = [
        f"=== GOVERNANCE EXECUTIVE SUMMARY ===",
        f"Governance score: {score}/100 ({level})",
        f"Degraded domains: {len(degraded)} — {', '.join(degraded) if degraded else 'none'}",
        f"Active risks: {risks_total}",
        f"Operational state: {health.get('operational_state', 'unknown')}",
        f"Remediation pending: {health.get('remediation_pending', 0)}",
        f"Stale authority: {health.get('stale_authority', [])}",
        f"Governance confidence: {health.get('confidence', 'unknown')}",
        f"Contract version: {GOVERNANCE_CONTRACT_VERSION}",
    ]
    return "\n".join(lines)


def build_governance_degradation_summary(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    domains = build_governance_domains(extra_ctx, sensor_snapshot)
    degraded = [d for d in domains if d.get("degraded")]
    health = build_governance_health_summary(extra_ctx, sensor_snapshot, domains)

    return {
        "degraded_domains": [d["domain"] for d in degraded],
        "degradation_details": degraded,
        "operational_state": health.get("operational_state", "unknown"),
        "total_degraded": len(degraded),
        "contract_version": GOVERNANCE_CONTRACT_VERSION,
    }


def build_governance_risk_executive(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> str:
    risks = build_governance_risk_summary(extra_ctx, sensor_snapshot)
    if not risks:
        return "No governance risks detected."

    lines = ["=== GOVERNANCE RISK REPORT ==="]
    for r in risks:
        lines.append(f"[{r.get('severity', 'info').upper()}] {r.get('domain')}: {r.get('description')}")
    return "\n".join(lines)
