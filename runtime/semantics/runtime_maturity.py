"""FASE 31B: Runtime Semantic Maturity Engine.

Formalizes degraded behavior, confidence propagation, uncertainty semantics,
domain-level degradation, and operational impact classification.

RULE-31B-1: No toda degradacion es critica.
RULE-31B-2: expected_offline != degraded.
RULE-31B-3: confidence debe propagarse automaticamente.
RULE-31B-4: freshness afecta cognition.
RULE-31B-5: unknown > inventar.
RULE-31B-6: Ausencia parcial de observabilidad debe expresarse explicitamente.
RULE-31B-7: El runtime debe razonar diferente con confidence=high vs low.
RULE-31B-8: Summaries operacionales deben incluir degradation_reason,
            operational_impact, affected_domains, uncertainty_level.
"""

from __future__ import annotations

import time
from typing import Any

from runtime.semantics.contracts import (
    SEMANTICS_CONTRACT_VERSION,
    RUNTIME_STATES,
    CONFIDENCE_LEVELS,
    UNCERTAINTY_TYPES,
    DEGRADED_DOMAINS,
    RuntimeMaturityContract,
    DegradationContract,
    ConfidenceContract,
    UncertaintyContract,
    OperationalImpactContract,
    build_maturity_contract,
    build_degradation_contract,
    build_confidence_contract,
    build_uncertainty_contract,
    build_operational_impact_contract,
)

RUNTIME_MATURITY_CONTRACT_VERSION = "31B"

_STALE_THRESHOLD_SECONDS = 60
_EXPIRED_THRESHOLD_SECONDS = 300

_CONFIDENCE_WEIGHTS = {"high": 1.0, "medium": 0.6, "low": 0.2, "unknown": 0.0}


def _confidence_value(level: str) -> float:
    return _CONFIDENCE_WEIGHTS.get(level, 0.0)


def _weighted_confidence(domain_confs: dict[str, str]) -> float:
    if not domain_confs:
        return 0.0
    values = [_confidence_value(v) for v in domain_confs.values()]
    return round(sum(values) / len(values), 2)


def _aggregate_freshness(
    freshness: dict[str, Any],
) -> str:
    if not freshness:
        return "unavailable"
    statuses = []
    for v in freshness.values():
        if isinstance(v, dict):
            s = v.get("status", "")
        elif isinstance(v, str):
            s = v
        else:
            s = str(v)
        if s:
            statuses.append(s.lower())
    if not statuses:
        return "unavailable"
    if "expired" in statuses:
        return "expired"
    if "stale" in statuses:
        return "stale"
    if all(s == "fresh" for s in statuses):
        return "fresh"
    return "mixed"


def classify_runtime_state(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> str:
    domain_confidence = sensor_snapshot.get("domain_confidence", {}) or {}
    freshness = sensor_snapshot.get("freshness", {}) or {}
    obs_sources = sensor_snapshot.get("observed_sources", [])
    miss_sources = sensor_snapshot.get("missing_sources", [])
    stale_sources = sensor_snapshot.get("stale_sources", []) or []
    expected_offline = sensor_snapshot.get("expected_offline", [])
    unexpected_down = sensor_snapshot.get("unexpected_down", [])
    topology_mode = sensor_snapshot.get("topology", {}).get("mode", "unknown")

    total_sources = len(obs_sources) + len(miss_sources)
    observed_ratio = len(obs_sources) / total_sources if total_sources > 0 else 0

    conf_values = set(domain_confidence.values())
    has_low = "low" in conf_values
    has_medium = "medium" in conf_values
    freshness_agg = _aggregate_freshness(freshness)

    has_critical_missing = any(
        d in miss_sources
        for d in ("gpu_nodes", "gateway", "prometheus")
    )

    if total_sources == 0:
        return "unknown"
    if has_critical_missing and has_low:
        return "critical"
    if has_low and unexpected_down:
        return "degraded"
    if freshness_agg == "expired":
        return "stale"
    if observed_ratio == 0 and total_sources > 0:
        return "degraded"
    if 0 < observed_ratio < 0.3:
        return "partially_observed"
    if len(stale_sources) > 0 and freshness_agg == "stale":
        return "stale"
    if has_low and not has_critical_missing:
        if topology_mode == "degraded_single_gpu":
            return "healthy_degraded"
        return "degraded"
    if expected_offline and not has_low:
        if topology_mode == "degraded_single_gpu":
            return "healthy_degraded"
        return "healthy"
    if topology_mode == "degraded_single_gpu":
        return "healthy_degraded"
    if has_medium and not has_low:
        return "healthy_degraded"
    return "healthy"


def classify_operational_impact(
    runtime_state: str,
    confidence: str,
    degraded_domains: list[str],
) -> str:
    if runtime_state == "critical":
        return "critical"
    if runtime_state == "unknown":
        return "high"
    if runtime_state == "stale":
        return "medium"
    if runtime_state == "degraded" and confidence == "low":
        return "high"
    if runtime_state == "degraded":
        return "medium"
    if len(degraded_domains) >= 2:
        return "medium"
    if len(degraded_domains) == 1:
        return "low"
    if runtime_state == "healthy_degraded":
        return "low"
    return "none"


def calculate_operational_confidence(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> str:
    domain_confidence = sensor_snapshot.get("domain_confidence", {}) or {}
    freshness = sensor_snapshot.get("freshness", {}) or {}
    fresh_agg = _aggregate_freshness(freshness)

    conf_values = set(domain_confidence.values())
    if "low" in conf_values:
        return "low"
    if fresh_agg in ("expired", "stale"):
        return "low"
    if "medium" in conf_values:
        return "medium"
    if fresh_agg in ("unavailable", "mixed"):
        return "medium"
    return "high"


def calculate_observability_confidence(
    sensor_snapshot: dict[str, Any],
) -> str:
    obs_audit = sensor_snapshot.get("observability_audit", {}) or {}
    if not obs_audit:
        return "unknown"
    targets = obs_audit.get("prometheus_targets", {}) or {}
    healthy = targets.get("healthy", 0)
    total = targets.get("total", 0)
    alignment = obs_audit.get("critical_targets_alignment_pct", 0.0)

    if total == 0:
        return "unknown"
    if alignment >= 100.0 and healthy == total:
        return "high"
    if alignment >= 50.0 and healthy >= total * 0.5:
        return "medium"
    return "low"


def calculate_uncertainty_level(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> str:
    domain_confidence = sensor_snapshot.get("domain_confidence", {}) or {}
    freshness = sensor_snapshot.get("freshness", {}) or {}
    stale_sources = sensor_snapshot.get("stale_sources", []) or []
    miss_sources = sensor_snapshot.get("missing_sources", [])
    fresh_agg = _aggregate_freshness(freshness)

    conf_values = set(domain_confidence.values())
    if "low" in conf_values and fresh_agg == "expired":
        return "degraded_observability"
    if "low" in conf_values:
        return "low_confidence"
    if fresh_agg == "expired":
        return "stale_evidence"
    if len(stale_sources) > 0 and fresh_agg == "stale":
        return "stale_evidence"
    if conf_values == {"high", "medium"}:
        return "mixed_confidence"
    if conf_values == {"medium"}:
        return "mixed_confidence"
    if len(miss_sources) > 0:
        return "partially_observed"
    if fresh_agg == "mixed":
        return "partially_observed"
    return "low_confidence" if fresh_agg == "unavailable" else "unknown_state"


def propagate_degradation(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    domain_confidence = sensor_snapshot.get("domain_confidence", {}) or {}
    freshness = sensor_snapshot.get("freshness", {}) or {}
    stale = sensor_snapshot.get("stale_sources", []) or []
    miss = sensor_snapshot.get("missing_sources", [])

    for domain in DEGRADED_DOMAINS:
        base_conf = domain_confidence.get(domain, "unknown")
        found_in_stale = any(domain in s for s in stale)
        found_in_miss = any(domain in s for s in miss)

        reasons: list[str] = []
        effective = base_conf

        if found_in_miss:
            reasons.append(f"{domain}: missing source")
        if found_in_stale:
            reasons.append(f"{domain}: stale data")
            if effective == "high":
                effective = "medium"
            elif effective == "medium":
                effective = "low"

        freshness_status = "unknown"
        fresh_entry = freshness.get(domain, {})
        if isinstance(fresh_entry, dict):
            freshness_status = fresh_entry.get("status", "unknown")
        if freshness_status in ("expired", "stale"):
            if effective == "high":
                effective = "medium"
                reasons.append(f"freshness={freshness_status}")

        degraded = effective != base_conf or found_in_miss or found_in_stale
        contracts.append(build_confidence_contract(
            domain=domain,
            base_confidence=base_conf,
            freshness=freshness_status,
            stale_sources=1 if found_in_stale else 0,
            missing_sources=1 if found_in_miss else 0,
            effective_confidence=effective,
            degradation_applied=degraded,
            reason=reasons,
        ))
    return contracts


def build_degradation_summary(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime_state = classify_runtime_state(sensor_snapshot, extra_ctx)
    confidence = calculate_operational_confidence(sensor_snapshot, extra_ctx)
    obs_conf = calculate_observability_confidence(sensor_snapshot)
    uncertainty = calculate_uncertainty_level(sensor_snapshot, extra_ctx)
    prop_contracts = propagate_degradation(sensor_snapshot, extra_ctx)

    degraded_domains: list[str] = []
    unknown_domains: list[str] = []
    domain_states: dict[str, str] = {}
    for c in prop_contracts:
        d = c.get("domain", "")
        eff = c.get("effective_confidence", "unknown")
        base = c.get("base_confidence", "unknown")
        domain_states[d] = eff
        if eff == "low":
            degraded_domains.append(d)
        elif eff == "unknown":
            unknown_domains.append(d)
        elif eff != base and base == "high":
            degraded_domains.append(d)

    operational_impact = classify_operational_impact(
        runtime_state, confidence, degraded_domains,
    )

    freshness = sensor_snapshot.get("freshness", {}) or {}
    fresh_agg = _aggregate_freshness(freshness)

    degradation_reason: list[str] = []
    if runtime_state in ("critical", "degraded", "stale"):
        for c in prop_contracts:
            if c.get("degradation_applied"):
                reasons = c.get("reason", [])
                degradation_reason.extend(reasons)
    if obs_conf == "low":
        degradation_reason.append("observabilidad degradada")
    if runtime_state == "healthy_degraded":
        degradation_reason.append("topology=degraded_single_gpu")

    recommended: list[str] = []
    if runtime_state == "critical":
        recommended.append("intervencion inmediata: fuentes criticas no accesibles")
    if runtime_state == "stale":
        recommended.append("verificar conectividad Prometheus y exporters")
    if degraded_domains:
        recommended.append(f"investigar degradacion en: {', '.join(degraded_domains[:3])}")
    if runtime_state == "unknown":
        recommended.append("verificar sensor fusion - sin fuentes de datos")
    if not recommended:
        recommended.append("ninguna accion necesaria - runtime estable")

    return build_maturity_contract(
        runtime_state=runtime_state,
        confidence=confidence,
        freshness=fresh_agg,
        degraded_domains=sorted(set(degraded_domains)),
        unknown_domains=sorted(set(unknown_domains)),
        domain_states=domain_states,
        uncertainty_level=uncertainty,
        operational_impact=operational_impact,
        degradation_reason=degradation_reason,
        recommended_actions=recommended,
    )


def calculate_maturity_score(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> float:
    domain_confidence = sensor_snapshot.get("domain_confidence", {}) or {}
    freshness = sensor_snapshot.get("freshness", {}) or {}
    stale = sensor_snapshot.get("stale_sources", []) or []
    miss = sensor_snapshot.get("missing_sources", [])
    obs_sources = sensor_snapshot.get("observed_sources", [])
    total_sources = len(obs_sources) + len(miss)

    runtime_state = classify_runtime_state(sensor_snapshot, extra_ctx)
    confidence_val = _weighted_confidence(domain_confidence)
    fresh_agg = _aggregate_freshness(freshness)

    state_scores = {
        "healthy": 100, "healthy_degraded": 85, "degraded": 60,
        "partially_observed": 50, "stale": 35, "inventory_only": 30,
        "expected_offline": 25, "critical": 15, "unknown": 0,
    }
    base = state_scores.get(runtime_state, 0)

    stale_penalty = len(stale) * 5
    miss_penalty = len(miss) * 3
    conf_penalty = int((1.0 - confidence_val) * 25)

    if total_sources == 0:
        fresh_penalty = 20
    elif fresh_agg == "expired":
        fresh_penalty = 15
    elif fresh_agg == "stale":
        fresh_penalty = 8
    elif fresh_agg == "unavailable":
        fresh_penalty = 10
    else:
        fresh_penalty = 0

    score = max(0, min(100, base - stale_penalty - miss_penalty - conf_penalty - fresh_penalty))
    return float(score)


def calculate_runtime_maturity(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not sensor_snapshot:
        return build_maturity_contract(
            runtime_state="unknown",
            maturity_score=0.0,
            confidence="unknown",
            freshness="unavailable",
            degradation_reason=["sensor snapshot empty"],
            recommended_actions=["verificar sensor fusion"],
        )

    maturity_score = calculate_maturity_score(sensor_snapshot, extra_ctx)
    degradation_summary = build_degradation_summary(sensor_snapshot, extra_ctx)
    degradation_summary["maturity_score"] = round(maturity_score, 2)
    return degradation_summary


class RuntimeMaturityEngine:

    CONTRACT_VERSION = RUNTIME_MATURITY_CONTRACT_VERSION

    def __init__(self) -> None:
        self._last_maturity: dict[str, Any] | None = None

    def evaluate(
        self,
        sensor_snapshot: dict[str, Any],
        extra_ctx: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._last_maturity = calculate_runtime_maturity(sensor_snapshot, extra_ctx)
        return dict(self._last_maturity)

    def get_degraded_domains(self) -> list[str]:
        if not self._last_maturity:
            return []
        return self._last_maturity.get("degraded_domains", [])

    def get_unknown_domains(self) -> list[str]:
        if not self._last_maturity:
            return []
        return self._last_maturity.get("unknown_domains", [])

    def get_operational_impact(self) -> str:
        if not self._last_maturity:
            return "unknown"
        return self._last_maturity.get("operational_impact", "unknown")

    def get_recommended_actions(self) -> list[str]:
        if not self._last_maturity:
            return ["evaluar runtime maturity primero"]
        return self._last_maturity.get("recommended_actions", [])

    def needs_attention(self) -> bool:
        if not self._last_maturity:
            return True
        state = self._last_maturity.get("runtime_state", "unknown")
        return state in ("critical", "degraded", "unknown", "stale")
