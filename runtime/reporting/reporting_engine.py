from __future__ import annotations

import os
import time
from typing import Any

from runtime.reporting.contracts import (
    REPORTING_CONTRACT_VERSION,
    REPORT_MODES,
    CONFIDENCE_LEVELS,
    SEVERITIES,
    OperationalReportContract,
    OperationalSummaryContract,
    GovernanceReportContract,
    RuntimeHealthContract,
    DomainHealthContract,
    OperatorExplainabilityContract,
    ExecutiveSummaryContract,
    DegradationReportContract,
)
from runtime.reporting.compact import format_compact_report
from runtime.reporting.verbose import format_verbose_report


def _ensure_list(val: Any) -> list:
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [val]
    return []


def _confidence_from_set(confidences: set[str]) -> str:
    if "low" in confidences:
        return "low"
    if "medium" in confidences:
        return "medium"
    if "high" in confidences:
        return "high"
    return "unknown"


def _freshness_from_set(freshness_vals: set[str]) -> str:
    if "expired" in freshness_vals:
        return "expired"
    if "stale" in freshness_vals:
        return "stale"
    if "fresh" in freshness_vals:
        return "fresh"
    if "unavailable" in freshness_vals:
        return "unavailable"
    return "unknown"


def _record_maturity_metrics(maturity: dict[str, Any]) -> None:
    flag = os.environ.get("AI_LAB_ENABLE_MATURITY_METRICS", "true").lower()
    if flag not in ("true", "1", "yes"):
        return
    try:
        from runtime.telemetry.prometheus_metrics import record_runtime_maturity
        record_runtime_maturity(maturity)
    except ImportError:
        pass


def _record_reporting_metrics(report: dict[str, Any], mode: str) -> None:
    try:
        from runtime.telemetry.prometheus_metrics import (
            REPORTING_TOTAL, REPORTING_CONFIDENCE, REPORTING_DEGRADED_TOTAL,
            REPORTING_UNKNOWN_TOTAL, REPORTING_EXPLAINABILITY_SCORE,
            REPORTING_CONSISTENCY_SCORE, REPORTING_GOVERNANCE_TOTAL,
        )
        REPORTING_TOTAL.labels(mode=mode).inc()
        conf = report.get("confidence", "unknown")
        if conf in CONFIDENCE_LEVELS:
            REPORTING_CONFIDENCE.labels(level=conf).inc()
        degraded = report.get("degraded_domains", [])
        if degraded:
            REPORTING_DEGRADED_TOTAL.inc(len(degraded))
        unknowns = report.get("unknown_domains", [])
        if unknowns:
            REPORTING_UNKNOWN_TOTAL.inc(len(unknowns))
    except Exception:
        pass


def _record_governance_metrics(governance: dict[str, Any]) -> None:
    try:
        from runtime.telemetry.prometheus_metrics import REPORTING_GOVERNANCE_TOTAL
        REPORTING_GOVERNANCE_TOTAL.inc()
    except Exception:
        pass


def _fallback_maturity(sensor_snapshot: dict[str, Any] | None) -> dict[str, Any]:
    topology_mode = "unknown"
    if sensor_snapshot:
        topology = sensor_snapshot.get("topology", {}) or {}
        if isinstance(topology, dict):
            topology_mode = topology.get("mode", "unknown")
    return {
        "runtime_state": "unknown",
        "confidence": "unknown",
        "maturity_score": 0.0,
        "uncertainty_level": "unknown",
        "operational_impact": "none",
        "degraded_domains": [],
        "unknown_domains": [],
        "degradation_reason": ["sensor snapshot not available"],
        "freshness": "unavailable",
        "topology_mode": topology_mode,
    }


def _extract_maturity(
    sensor_snapshot: dict[str, Any] | None,
    maturity: dict[str, Any] | None,
) -> dict[str, Any]:
    if maturity is not None:
        return maturity
    if sensor_snapshot:
        try:
            from runtime.semantics.runtime_maturity import calculate_runtime_maturity
            return calculate_runtime_maturity(sensor_snapshot)
        except ImportError:
            return _fallback_maturity(sensor_snapshot)
    return _fallback_maturity(None)


# ── Core operational report (already exists, kept as primary) ──────

def build_operational_report(
    sensor_snapshot: dict[str, Any] | None = None,
    maturity: dict[str, Any] | None = None,
    mode: str = "compact",
) -> dict[str, Any]:
    if mode not in REPORT_MODES:
        mode = "compact"
    _mode_map = {"compact": "compact", "operational": "verbose", "technical": "verbose",
                 "executive": "compact", "governance": "compact"}
    fmt_mode = _mode_map.get(mode, "compact")

    maturity_data = _extract_maturity(sensor_snapshot, maturity)
    _record_maturity_metrics(maturity_data)

    contract = OperationalReportContract(
        runtime_state=maturity_data.get("runtime_state", "unknown"),
        confidence=maturity_data.get("confidence", "unknown"),
        maturity_score=maturity_data.get("maturity_score", 0.0),
        uncertainty_level=maturity_data.get("uncertainty_level", "unknown"),
        operational_impact=maturity_data.get("operational_impact", "none"),
        degraded_domains=_ensure_list(maturity_data.get("degraded_domains")),
        unknown_domains=_ensure_list(maturity_data.get("unknown_domains")),
        degradation_reason=_ensure_list(maturity_data.get("degradation_reason")),
        freshness=maturity_data.get("freshness", "unknown"),
        topology_mode=_extract_topology(sensor_snapshot, maturity_data),
        mode=mode,
    )

    text: str | None = None
    if fmt_mode in ("compact", "debug"):
        text = format_compact_report(contract)

    verbose_text: str | None = None
    if fmt_mode in ("verbose", "debug"):
        verbose_text = format_verbose_report(contract)

    result: dict[str, Any] = {
        "contract": contract.to_dict(),
        "mode": mode,
        "confidence": contract.confidence,
        "freshness": contract.freshness,
        "degraded_domains": contract.degraded_domains,
        "unknown_domains": contract.unknown_domains,
        "operational_impact": contract.operational_impact,
    }
    if text is not None:
        result["text"] = text
    if verbose_text is not None:
        result["verbose_text"] = verbose_text

    _record_reporting_metrics(result, mode)
    return result


def _extract_topology(
    sensor_snapshot: dict[str, Any] | None,
    maturity: dict[str, Any],
) -> str:
    topo = maturity.get("topology_mode")
    if topo and topo != "unknown":
        return topo
    if sensor_snapshot:
        topology = sensor_snapshot.get("topology", {}) or {}
        if isinstance(topology, dict):
            return topology.get("mode", "unknown")
        gpu_summaries = sensor_snapshot.get("gpu_operational_summaries", [])
        if gpu_summaries:
            roles = {g.get("topology_role", "") for g in gpu_summaries if isinstance(g, dict)}
            if roles:
                return "|".join(sorted(roles))
    return "unknown"


# ── Runtime health report ──────────────────────────────────────────

def build_runtime_health_report(
    sensor_snapshot: dict[str, Any] | None = None,
    maturity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    maturity_data = _extract_maturity(sensor_snapshot, maturity)
    topology_mode = _extract_topology(sensor_snapshot, maturity_data)
    gpu_summaries = []
    if sensor_snapshot:
        gpu_summaries = sensor_snapshot.get("gpu_operational_summaries", []) or []

    active = sum(1 for g in gpu_summaries if isinstance(g, dict) and g.get("operational_state") == "active")
    offline = sum(1 for g in gpu_summaries if isinstance(g, dict) and g.get("observed_state") in ("expected_offline", "unavailable", "down"))

    report = RuntimeHealthContract(
        runtime_state=maturity_data.get("runtime_state", "unknown"),
        topology_mode=topology_mode,
        active_backends=active,
        offline_backends=offline,
        degraded_domains=_ensure_list(maturity_data.get("degraded_domains")),
        confidence=maturity_data.get("confidence", "unknown"),
        freshness=maturity_data.get("freshness", "unknown"),
    )

    d = report.to_dict()
    _record_reporting_metrics(d, "health")
    return d


# ── Domain health report ───────────────────────────────────────────

def build_domain_health_report(
    domain: str,
    sensor_snapshot: dict[str, Any] | None = None,
    maturity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if domain == "gpu":
        return _build_gpu_domain_report(sensor_snapshot, maturity)

    maturity_data = _extract_maturity(sensor_snapshot, maturity)
    degraded = _ensure_list(maturity_data.get("degraded_domains", []))
    state = "degraded" if domain in degraded else "healthy"

    domain_conf = "unknown"
    if sensor_snapshot:
        dc = sensor_snapshot.get("domain_confidence", {}) or {}
        domain_conf = dc.get(domain, "unknown")

    boundaries = ["gpu", "routing", "storage", "grounding", "observability", "governance", "services", "telemetry"]
    if domain not in boundaries:
        domain = "unknown"

    report = DomainHealthContract(
        domain=domain,
        state=state,
        confidence=domain_conf,
        freshness=maturity_data.get("freshness", "unknown"),
        sources=maturity_data.get("source_of_truth", []),
        operational_impact=maturity_data.get("operational_impact", "none"),
        issues=[f"degraded domain: {domain}"] if domain in degraded else [],
    )
    return report.to_dict()


def _build_gpu_domain_report(
    sensor_snapshot: dict[str, Any] | None,
    maturity: dict[str, Any] | None,
) -> dict[str, Any]:
    if not sensor_snapshot:
        return DomainHealthContract(domain="gpu", state="unknown", confidence="low").to_dict()

    gpu_summaries = sensor_snapshot.get("gpu_operational_summaries", []) or []
    active = any(g.get("operational_state") == "active" for g in gpu_summaries if isinstance(g, dict))
    offline = any(g.get("observed_state") == "expected_offline" for g in gpu_summaries if isinstance(g, dict))

    if active:
        state = "healthy"
    elif offline:
        state = "expected_offline"
    else:
        state = "unavailable"

    issues = []
    for g in gpu_summaries:
        if isinstance(g, dict):
            m = g.get("observed_metrics", {}) or {}
            temp = m.get("temperature_c")
            if temp is not None and float(temp) > 80:
                issues.append(f"GPU {g.get('gpu_id', '?')} high temperature: {temp}C")
            vram_free = m.get("vram_free_gb")
            if vram_free is not None and float(vram_free) < 1:
                vram_used = m.get("vram_used_gb", "?")
                issues.append(f"GPU {g.get('gpu_id', '?')} VRAM pressure: {vram_used}GB used")

    confidence_set = {g.get("confidence", "low") for g in gpu_summaries if isinstance(g, dict)}
    confidence = _confidence_from_set(confidence_set)

    report = DomainHealthContract(
        domain="gpu",
        state=state,
        confidence=confidence,
        freshness=maturity.get("freshness", "unknown") if maturity else "unknown",
        sources=["lmstudio", "prometheus", "sensor_fusion"],
        operational_impact="none" if active else "low",
        issues=issues,
    )
    return report.to_dict()


# ── Governance summary ─────────────────────────────────────────────

def build_governance_summary(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blocked = 0
    blocked_by_reason: dict[str, int] = {}
    evidence_active = False

    if extra_ctx:
        blocked = extra_ctx.get("governance_blocked", 0) or 0
        blocked_by_reason = extra_ctx.get("governance_blocked_by_reason", {}) or {}
        evidence_active = bool(extra_ctx.get("evidence_catalog", {}))

    if sensor_snapshot:
        dc = sensor_snapshot.get("domain_confidence", {}) or {}
    else:
        dc = {}

    issues = []
    if blocked > 0:
        issues.append(f"{blocked} actions blocked by governance")
    for reason, count in blocked_by_reason.items():
        if count > 0:
            issues.append(f"blocked: {reason} ({count})")

    conf_set = set(dc.values()) if dc else {"unknown"}
    confidence = _confidence_from_set(conf_set)

    report = GovernanceReportContract(
        governance_level="enforced",
        blocked_actions=blocked,
        blocked_by_reason=blocked_by_reason,
        evidence_guard_active=evidence_active,
        governance_issues=issues,
        confidence=confidence,
        freshness="fresh",
    )
    d = report.to_dict()
    _record_governance_metrics(d)
    return d


# ── Executive summary ──────────────────────────────────────────────

def build_executive_summary(
    sensor_snapshot: dict[str, Any] | None = None,
    maturity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    maturity_data = _extract_maturity(sensor_snapshot, maturity)
    degraded = _ensure_list(maturity_data.get("degraded_domains"))
    reasons = _ensure_list(maturity_data.get("degradation_reason"))
    impact = maturity_data.get("operational_impact", "none")

    gpu_summaries = []
    if sensor_snapshot:
        gpu_summaries = sensor_snapshot.get("gpu_operational_summaries", []) or []
    active = sum(1 for g in gpu_summaries if isinstance(g, dict) and g.get("operational_state") == "active")

    critical = []
    if impact in ("high", "critical"):
        critical.append(f"operational impact: {impact}")
    for reason in reasons:
        if reason not in critical:
            critical.append(reason)

    recommendations = []
    if impact in ("high", "critical"):
        recommendations.append("intervencion inmediata requerida")
    if degraded:
        recommendations.append(f"revisar dominios degradados: {', '.join(degraded[:3])}")
    if not recommendations:
        recommendations.append("ninguna accion necesaria")

    report = ExecutiveSummaryContract(
        overall_state=maturity_data.get("runtime_state", "unknown"),
        active_backends=active,
        degraded_domains=degraded,
        critical_issues=critical,
        recommendations=recommendations,
        confidence=_confidence_from_set({maturity_data.get("confidence", "unknown")}),
        freshness=maturity_data.get("freshness", "unknown"),
    )
    return report.to_dict()


# ── Operator summary ───────────────────────────────────────────────

def build_operator_summary(
    sensor_snapshot: dict[str, Any] | None = None,
    maturity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    maturity_data = _extract_maturity(sensor_snapshot, maturity)
    gpu_summaries = []
    if sensor_snapshot:
        gpu_summaries = sensor_snapshot.get("gpu_operational_summaries", []) or []

    active_gpus = [g for g in gpu_summaries if isinstance(g, dict) and g.get("operational_state") == "active"]
    offline_gpus = [g for g in gpu_summaries if isinstance(g, dict) and g.get("observed_state") == "expected_offline"]
    unknown_gpus = [g for g in gpu_summaries if isinstance(g, dict) and g.get("observed_state") in ("unavailable", "down") and not g.get("inventory_expected_offline")]

    expected_offline = [g.get("gpu_id", "?") for g in offline_gpus]
    unexpected_down = [g.get("gpu_id", "?") for g in unknown_gpus]

    report = OperationalSummaryContract(
        overall_state=maturity_data.get("runtime_state", "unknown"),
        active_gpus=len(active_gpus),
        inventory_gpus=len(offline_gpus),
        degraded_domains=_ensure_list(maturity_data.get("degraded_domains")),
        unknown_domains=_ensure_list(maturity_data.get("unknown_domains")),
        expected_offline=expected_offline,
        unexpected_down=unexpected_down,
        risks=_ensure_list(maturity_data.get("degradation_reason")),
        recommendations=maturity_data.get("recommended_actions", []),
        confidence=maturity_data.get("confidence", "unknown"),
        freshness=maturity_data.get("freshness", "unknown"),
    )
    return report.to_dict()


# ── Degradation report ─────────────────────────────────────────────

def build_degradation_report(
    sensor_snapshot: dict[str, Any] | None = None,
    maturity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    maturity_data = _extract_maturity(sensor_snapshot, maturity)
    degraded = _ensure_list(maturity_data.get("degraded_domains"))
    impact = maturity_data.get("operational_impact", "none")
    reasons = _ensure_list(maturity_data.get("degradation_reason"))

    if not degraded and impact == "none":
        level = "none"
    elif impact in ("high", "critical"):
        level = "critical"
    elif impact == "moderate":
        level = "moderate"
    elif degraded:
        level = "degraded"
    else:
        level = "none"

    report = DegradationReportContract(
        degradation_level=level,
        degraded_domains=degraded,
        degradation_reasons=reasons,
        operational_impact=impact,
        affected_services=degraded,
        recommended_actions=maturity_data.get("recommended_actions", []),
        confidence=maturity_data.get("confidence", "unknown"),
        freshness=maturity_data.get("freshness", "unknown"),
    )
    return report.to_dict()


# ── Confidence report ──────────────────────────────────────────────

def build_confidence_report(
    sensor_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not sensor_snapshot:
        return {"confidence": "unknown", "freshness": "unknown", "domain_confidence": {}, "overall": "unknown"}

    domain_confidence = sensor_snapshot.get("domain_confidence", {}) or {}
    source_quality = sensor_snapshot.get("source_quality", {}) or {}
    freshness_by_domain: dict[str, str] = {}
    sources_by_domain: dict[str, list[str]] = {}

    for domain, quality in source_quality.items():
        if isinstance(quality, dict):
            f = quality.get("freshness", {}) or {}
            freshness_by_domain[domain] = f.get("status", "unknown") if isinstance(f, dict) else "unknown"
            src = quality.get("source_of_truth", [])
            sources_by_domain[domain] = src if isinstance(src, list) else []

    conf_set = set(domain_confidence.values())
    overall = _confidence_from_set(conf_set)

    return {
        "overall": overall,
        "domain_confidence": dict(domain_confidence),
        "freshness_by_domain": freshness_by_domain,
        "sources_by_domain": sources_by_domain,
    }


# ── Explainability summary ─────────────────────────────────────────

def build_explainability_summary(
    sensor_snapshot: dict[str, Any] | None = None,
    maturity: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    maturity_data = _extract_maturity(sensor_snapshot, maturity)
    degraded = _ensure_list(maturity_data.get("degraded_domains"))
    reasons = _ensure_list(maturity_data.get("degradation_reason"))
    unknowns = _ensure_list(maturity_data.get("unknown_domains"))
    confidence = maturity_data.get("confidence", "unknown")

    if not degraded and not unknowns:
        summary = "runtime opera sin degradacion detectada"
    elif degraded and not reasons:
        summary = f"runtime degradado en {', '.join(degraded)}, causas no determinadas"
    else:
        summary = f"runtime degradado en {', '.join(degraded)}: {'; '.join(reasons)}"

    domain_confidence = {}
    if sensor_snapshot:
        domain_confidence = sensor_snapshot.get("domain_confidence", {}) or {}

    stale = []
    if sensor_snapshot:
        stale = sensor_snapshot.get("stale_sources", [])
        if not stale and extra_ctx:
            stale = extra_ctx.get("stale_sources", [])

    recommendations = []
    if confidence == "low":
        recommendations.append("verificar conectividad Prometheus antes de operaciones")
    if degraded:
        recommendations.append(f"revisar dominios degradados: {', '.join(degraded[:3])}")
    if unknowns:
        recommendations.append(f"investigar dominios desconocidos: {', '.join(unknowns[:2])}")
    if stale:
        recommendations.append(f"refresh de sensores stale: {', '.join(stale[:3])}")
    if not recommendations:
        recommendations.append("ninguna accion necesaria")

    report = OperatorExplainabilityContract(
        degradation_summary=summary,
        missing_evidence=unknowns,
        affected_domains=degraded,
        confidence_breakdown=dict(domain_confidence),
        uncertainty_notes=[f"dominio desconocido: {d}" for d in unknowns] if unknowns else ["sin incertidumbre significativa"],
        valid_recommendations=recommendations,
        stale_observability=stale if isinstance(stale, list) else [],
    )
    return report.to_dict()


# ── Reporting score ────────────────────────────────────────────────

def build_reporting_score(
    sensor_snapshot: dict[str, Any] | None = None,
    maturity: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    maturity_data = _extract_maturity(sensor_snapshot, maturity)

    has_explainability = bool(maturity_data.get("degradation_reason")) or bool(maturity_data.get("degraded_domains"))
    has_consistency = maturity_data.get("runtime_state") != "unknown"
    has_evidence = bool(maturity_data.get("source_of_truth")) or bool(maturity_data.get("confidence") != "unknown")
    has_confidence = maturity_data.get("confidence") in CONFIDENCE_LEVELS
    has_semantic_alignment = maturity_data.get("topology_mode") != "unknown" or bool(
        sensor_snapshot and sensor_snapshot.get("topology")
    )
    has_determinism = bool(maturity_data)  # deterministic by construction

    scores = {
        "explainability": 1.0 if has_explainability else 0.0,
        "consistency": 1.0 if has_consistency else 0.0,
        "evidence_coverage": 1.0 if has_evidence else 0.0,
        "confidence_propagation": 1.0 if has_confidence else 0.0,
        "semantic_alignment": 1.0 if has_semantic_alignment else 0.0,
        "determinism": 1.0 if has_determinism else 0.0,
    }
    overall = round(sum(scores.values()) / len(scores) * 100, 1)

    return {
        "overall_score": overall,
        "components": scores,
        "contract_version": REPORTING_CONTRACT_VERSION,
    }
