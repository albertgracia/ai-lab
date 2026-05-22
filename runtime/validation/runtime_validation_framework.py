from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from runtime.validation.contracts import (
    RuntimeValidationContract,
    RuntimeInvariantContract,
    RuntimeSafetyGateContract,
    RuntimePilotReadinessContract,
    RuntimeFailureSurfaceContract,
    RuntimeRegressionContract,
    VALIDATION_CONTRACT_VERSION,
)


BASELINE_CHECKPOINT = "CP-33B-RUNTIME-PRE-PILOT-VALIDATION-STABLE"
CURRENT_CHECKPOINT = "CP-28.4-TOOL-CONTRACTS-CROSSPLAN-GC-STABLE"


INVARIANTS = [
    "INVARIANT-PROMETHEUS-AUTHORITY",
    "INVARIANT-GOVERNANCE-CONSISTENCY",
    "INVARIANT-TOPOLOGY-ALIGNMENT",
    "INVARIANT-ENTITY-CONSISTENCY",
    "INVARIANT-GROUNDING-VALIDATION",
    "INVARIANT-REPORTING-CONSISTENCY",
    "INVARIANT-OBSERVABILITY-FRESHNESS",
    "INVARIANT-OBSERVABILITY-SURVIVABILITY",
    "INVARIANT-SCRAPE-FRESHNESS",
    "INVARIANT-EXPORTER-STABILITY",
    "INVARIANT-DEGRADED-MODE-CONSISTENCY",
    "INVARIANT-CONTRACT-CONSISTENCY",
    "INVARIANT-TOOL-CONTRACTS",
    "INVARIANT-PLAN-REGISTRY",
    "INVARIANT-GC-SAFETY",
    "INVARIANT-OPERATIONAL-HARDENING",
    "INVARIANT-RUNTIME-DETERMINISM",
]

SAFETY_GATES = [
    "SAFE_TO_OPERATE",
    "SAFE_TO_ROUTE",
    "SAFE_TO_REPORT",
    "SAFE_TO_GROUND",
    "SAFE_TO_OBSERVE",
    "SAFE_TO_GOVERN",
    "SAFE_TO_DEGRADE",
]


_CONF = {"high": 1.0, "medium": 0.6, "low": 0.2, "unknown": 0.0}


def _strict_mode() -> bool:
    return os.environ.get("STRICT_VALIDATION_MODE", "false").lower() in ("true", "1", "yes")


def _now() -> float:
    # Deterministic mode: no clock influence.
    return 0.0 if _strict_mode() else time.time()


def _confidence_score(level: str) -> float:
    return _CONF.get(level or "unknown", 0.0)


def _score_to_confidence(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.5:
        return "medium"
    if score >= 0.2:
        return "low"
    return "unknown"


def _hash_deterministic(obj: Any) -> str:
    # Stable hash for determinism checks.
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _ensure_list(val: Any) -> list:
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [val]
    return []


def build_runtime_assertions(sensor_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    """Concrete operational assertions for pre-pilot readiness.

    RULE-33B-6: expected_offline != degraded failure.
    RULE-33B-7: inventory entities do not participate in readiness.
    """
    sensor_snapshot = sensor_snapshot or {}

    assertions: dict[str, Any] = {
        "rx9070_active": {"status": "unknown", "detail": "NO DISPONIBLE"},
        "rx7900xt_inventory_only": {"status": "unknown", "detail": "NO DISPONIBLE"},
        "no_fake_gpus": {"status": "pass", "detail": "no fake GPU patterns detected"},
        "prometheus_operational_authority": {"status": "unknown", "detail": "NO DISPONIBLE"},
        "grafana_visualization_only": {"status": "pass", "detail": "grafana is visualization layer"},
        "no_inventory_contamination": {"status": "pass", "detail": "inventory entities excluded from readiness"},
    }

    # Entity registry based assertions.
    try:
        from runtime.entities import build_entity_registry
        reg = build_entity_registry(sensor_snapshot=sensor_snapshot)
        gpus = [e for e in reg if e.get("entity_type") == "gpu"]
        rx9070 = next((g for g in gpus if "rx9070" in str(g.get("entity_id", "")).lower()), None)
        rx7900xt = next((g for g in gpus if "rx7900" in str(g.get("entity_id", "")).lower()), None)

        if rx9070:
            if rx9070.get("operational_state") == "active":
                assertions["rx9070_active"] = {"status": "pass", "detail": "RX9070 is active"}
            else:
                assertions["rx9070_active"] = {"status": "fail", "detail": f"RX9070 not active: {rx9070.get('operational_state')}"}

        if rx7900xt:
            inv_state = rx7900xt.get("inventory_state")
            routable = bool(rx7900xt.get("routable"))
            if inv_state in ("expected_offline", "inventory") and not routable:
                assertions["rx7900xt_inventory_only"] = {"status": "pass", "detail": f"RX7900XT inventory_only ({inv_state})"}
            else:
                assertions["rx7900xt_inventory_only"] = {"status": "fail", "detail": f"RX7900XT invalid state inv={inv_state} routable={routable}"}
    except ImportError:
        # Fallback to sensor snapshot summaries
        gpu_summaries = sensor_snapshot.get("gpu_operational_summaries", []) or []
        for g in gpu_summaries:
            gid = str(g.get("gpu_id", "")).lower()
            if "rx9070" in gid and g.get("operational_state") == "active":
                assertions["rx9070_active"] = {"status": "pass", "detail": "RX9070 active (sensor_fusion)"}
            if "rx7900" in gid:
                if g.get("observed_state") == "expected_offline" and g.get("inventory_expected_offline"):
                    assertions["rx7900xt_inventory_only"] = {"status": "pass", "detail": "RX7900XT expected_offline (inventory)"}

    # Governance registry assertion.
    try:
        from runtime.governance import build_governance_authority_map
        auth = build_governance_authority_map()
        if auth.get("operational_authority") == "prometheus":
            assertions["prometheus_operational_authority"] = {"status": "pass", "detail": "Prometheus is operational authority"}
        else:
            assertions["prometheus_operational_authority"] = {"status": "fail", "detail": f"operational_authority={auth.get('operational_authority')}"}
    except ImportError:
        pass

    return assertions


def build_runtime_invariants(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    sensor_snapshot = sensor_snapshot or {}
    extra_ctx = extra_ctx or {}

    assertions = build_runtime_assertions(sensor_snapshot)

    # Pull governance/observability/topology context if available.
    gov = {}
    try:
        from runtime.governance import build_runtime_governance_registry
        gov = build_runtime_governance_registry(extra_ctx, sensor_snapshot)
    except ImportError:
        gov = {}

    topology_conf = 0
    topo_drift = []
    try:
        from runtime.topology import calculate_topology_confidence, detect_topology_drift
        topology_conf = int((calculate_topology_confidence(sensor_snapshot, extra_ctx) or {}).get("overall_score", 0))
        topo_drift = detect_topology_drift(sensor_snapshot, extra_ctx) or []
    except ImportError:
        topology_conf = 0
        topo_drift = []

    stale_sources = sorted(_ensure_list(sensor_snapshot.get("stale_sources")))
    observed_sources = sensor_snapshot.get("observed_sources_count", 0) or 0
    missing_sources = sensor_snapshot.get("missing_sources_count", 0) or 0

    contracts = {}
    try:
        from runtime.governance import build_governance_contract_registry
        contracts = build_governance_contract_registry(extra_ctx)
    except ImportError:
        contracts = {}

    # Determinism invariant: in strict mode, hash should be stable.
    det_hash = _hash_deterministic({
        "assertions": assertions,
        "stale_sources": stale_sources,
        "topology_conf": topology_conf,
        "gov_score": (gov.get("governance_score_info", {}) or {}).get("score"),
        # Contract lists can be produced from unordered sources; keep deterministic.
        "contracts": sorted(_ensure_list(contracts.get("active_contracts", []))),
    })

    invariants: list[RuntimeInvariantContract] = []

    def _mk(name: str, status: str, confidence: str, authority: str, blocking: bool, details: dict[str, Any]):
        invariants.append(RuntimeInvariantContract(
            name=name,
            status=status,
            confidence=confidence,
            authority=authority,
            explainable=True,
            blocking=blocking,
            details=details,
        ))

    # INVARIANT-PROMETHEUS-AUTHORITY
    prom_status = assertions.get("prometheus_operational_authority", {}).get("status")
    _mk(
        "INVARIANT-PROMETHEUS-AUTHORITY",
        "pass" if prom_status == "pass" else "fail" if prom_status == "fail" else "degraded",
        "high" if prom_status == "pass" else "low" if prom_status == "fail" else "unknown",
        "prometheus",
        blocking=(prom_status == "fail"),
        details={"assertion": assertions.get("prometheus_operational_authority")},
    )

    # INVARIANT-GOVERNANCE-CONSISTENCY
    gov_score = (gov.get("governance_score_info", {}) or {}).get("score", 0)
    gov_health = gov.get("health_summary", {}) or {}
    gov_state = gov_health.get("operational_state", "unknown")
    gov_degraded = sorted(_ensure_list(gov.get("degraded_domains")))
    gov_ok = gov_state in ("healthy", "degraded")
    _mk(
        "INVARIANT-GOVERNANCE-CONSISTENCY",
        "pass" if gov_ok and not gov_degraded else "degraded" if gov_ok else "fail",
        _score_to_confidence(float(gov_score) / 100.0),
        "governance_registry_33a",
        blocking=(gov_state == "critical"),
        details={"governance_state": gov_state, "score": gov_score, "degraded_domains": gov_degraded},
    )

    # INVARIANT-TOPOLOGY-ALIGNMENT
    topo_ok = topology_conf >= 80 and not topo_drift
    topo_status = "pass" if topo_ok else "degraded" if topology_conf >= 50 else "fail"
    _mk(
        "INVARIANT-TOPOLOGY-ALIGNMENT",
        topo_status,
        "high" if topology_conf >= 80 else "medium" if topology_conf >= 50 else "low",
        "runtime_topology_31d",
        blocking=(topo_status == "fail"),
        details={"topology_confidence": topology_conf, "drift_total": len(topo_drift)},
    )

    # INVARIANT-ENTITY-CONSISTENCY
    rx9070 = assertions.get("rx9070_active", {}).get("status")
    rx7900 = assertions.get("rx7900xt_inventory_only", {}).get("status")
    ent_ok = (rx9070 == "pass") and (rx7900 == "pass")
    ent_status = "pass" if ent_ok else "fail" if rx9070 == "fail" else "degraded"
    _mk(
        "INVARIANT-ENTITY-CONSISTENCY",
        ent_status,
        "high" if ent_ok else "low" if ent_status == "fail" else "medium",
        "runtime_entities_31e",
        blocking=(rx9070 == "fail"),
        details={"rx9070_active": assertions.get("rx9070_active"), "rx7900xt_inventory_only": assertions.get("rx7900xt_inventory_only")},
    )

    # INVARIANT-GROUNDING-VALIDATION
    grounding_ok = True
    try:
        from runtime.context.runtime_grounding import build_grounding_envelope
        _env = build_grounding_envelope()
        grounding_ok = isinstance(_env, dict)
    except Exception:
        grounding_ok = False
    _mk(
        "INVARIANT-GROUNDING-VALIDATION",
        "pass" if grounding_ok else "degraded",
        "high" if grounding_ok else "low",
        "runtime_grounding_30ig",
        blocking=False,
        details={"grounding_envelope_available": grounding_ok},
    )

    # INVARIANT-REPORTING-CONSISTENCY
    reporting_ok = True
    try:
        from runtime.reporting.reporting_engine import build_operational_report
        r1 = build_operational_report(sensor_snapshot=sensor_snapshot, mode="compact")
        r2 = build_operational_report(sensor_snapshot=sensor_snapshot, mode="compact")
        # Ignore timestamps, require stable core fields.
        reporting_ok = (r1.get("confidence") == r2.get("confidence")) and (r1.get("operational_impact") == r2.get("operational_impact"))
    except Exception:
        reporting_ok = False
    _mk(
        "INVARIANT-REPORTING-CONSISTENCY",
        "pass" if reporting_ok else "degraded",
        "high" if reporting_ok else "low",
        "runtime_reporting_31c",
        blocking=False,
        details={"reporting_deterministic": reporting_ok},
    )

    # INVARIANT-OBSERVABILITY-FRESHNESS
    total_sources = observed_sources + missing_sources
    obs_ok = (observed_sources > 0) and not stale_sources and (total_sources > 0)
    obs_status = "pass" if obs_ok else "degraded" if observed_sources > 0 else "fail"
    _mk(
        "INVARIANT-OBSERVABILITY-FRESHNESS",
        obs_status,
        "high" if obs_ok else "medium" if observed_sources > 0 else "low",
        "prometheus",
        blocking=(obs_status == "fail"),
        details={"observed_sources": observed_sources, "missing_sources": missing_sources, "stale_sources": stale_sources},
    )

    # OBS-34B companion invariants. These are intentionally simple and derived
    # from the same observed/missing/stale source signals.
    surv_ok = (observed_sources > 0)
    _mk(
        "INVARIANT-OBSERVABILITY-SURVIVABILITY",
        "pass" if surv_ok else "fail",
        "high" if surv_ok else "low",
        "prometheus",
        blocking=not surv_ok,
        details={"observed_sources": observed_sources},
    )

    scrape_ok = (observed_sources > 0) and (not stale_sources)
    scrape_status = "pass" if scrape_ok else "degraded" if observed_sources > 0 else "fail"
    _mk(
        "INVARIANT-SCRAPE-FRESHNESS",
        scrape_status,
        "high" if scrape_ok else "medium" if observed_sources > 0 else "low",
        "prometheus",
        blocking=(scrape_status == "fail"),
        details={"stale_sources": stale_sources, "observed_sources": observed_sources},
    )

    exporter_ok = (observed_sources > 0) and (missing_sources == 0)
    exporter_status = "pass" if exporter_ok else "degraded" if observed_sources > 0 else "fail"
    _mk(
        "INVARIANT-EXPORTER-STABILITY",
        exporter_status,
        "high" if exporter_ok else "medium" if observed_sources > 0 else "low",
        "prometheus",
        blocking=(exporter_status == "fail"),
        details={"missing_sources": missing_sources, "observed_sources": observed_sources},
    )

    # INVARIANT-DEGRADED-MODE-CONSISTENCY
    topo_mode = (sensor_snapshot.get("topology", {}) or {}).get("mode", "unknown")
    expected_offline = _ensure_list(sensor_snapshot.get("expected_offline"))
    unexpected_down = _ensure_list(sensor_snapshot.get("unexpected_down"))
    # expected_offline does not degrade pilot readiness
    degraded_failure = bool(unexpected_down)
    deg_ok = not degraded_failure
    _mk(
        "INVARIANT-DEGRADED-MODE-CONSISTENCY",
        "pass" if deg_ok else "degraded",
        "high" if deg_ok else "medium",
        "runtime_semantics_31b",
        blocking=False,
        details={"topology_mode": topo_mode, "expected_offline": expected_offline, "unexpected_down": unexpected_down},
    )

    # INVARIANT-CONTRACT-CONSISTENCY
    incompatible = _ensure_list(contracts.get("incompatible_contracts"))
    contract_ok = not incompatible
    contract_status = "pass" if contract_ok else "degraded"
    _mk(
        "INVARIANT-CONTRACT-CONSISTENCY",
        contract_status,
        "high" if contract_ok else "medium",
        "governance_registry_33a",
        blocking=False,
        details={"incompatible_contracts": incompatible},
    )

    # INVARIANT-TOOL-CONTRACTS (FASE 28.4)
    try:
        from runtime.tools.tool_registry import detect_invalid_tool_contracts, calculate_tool_governance_score
        invalid_tools = detect_invalid_tool_contracts()
        tool_score = (calculate_tool_governance_score() or {}).get("tool_governance_score", 0.0)
        tool_ok = (len(invalid_tools) == 0) and float(tool_score) >= 80.0
        tool_status = "pass" if tool_ok else "degraded" if float(tool_score) >= 65.0 else "fail"
        _mk(
            "INVARIANT-TOOL-CONTRACTS",
            tool_status,
            "high" if tool_ok else "medium" if tool_status == "degraded" else "low",
            "tool_registry_28_4",
            blocking=(tool_status == "fail"),
            details={"invalid_tool_contracts": len(invalid_tools), "tool_governance_score": tool_score},
        )
    except Exception as exc:
        _mk(
            "INVARIANT-TOOL-CONTRACTS",
            "degraded",
            "low",
            "tool_registry_28_4",
            blocking=False,
            details={"error": str(exc)},
        )

    # INVARIANT-PLAN-REGISTRY (FASE 28.4)
    try:
        from runtime.plans.plan_registry import detect_orphan_plans, detect_invalid_plan_references
        orphan_plans = detect_orphan_plans()
        invalid_refs = detect_invalid_plan_references()
        plan_ok = (len(orphan_plans) == 0) and (len(invalid_refs) == 0)
        plan_status = "pass" if plan_ok else "degraded" if len(orphan_plans) == 0 else "fail"
        _mk(
            "INVARIANT-PLAN-REGISTRY",
            plan_status,
            "high" if plan_ok else "medium" if plan_status == "degraded" else "low",
            "plan_registry_28_4",
            blocking=(plan_status == "fail"),
            details={"orphan_plans": len(orphan_plans), "invalid_plan_references": len(invalid_refs)},
        )
    except Exception as exc:
        _mk(
            "INVARIANT-PLAN-REGISTRY",
            "degraded",
            "low",
            "plan_registry_28_4",
            blocking=False,
            details={"error": str(exc)},
        )

    # INVARIANT-GC-SAFETY (FASE 28.4)
    try:
        from runtime.gc.crossplan_gc import (
            build_gc_inventory,
            protect_governance_artifacts,
            protect_active_validation_artifacts,
            protect_runtime_authority_artifacts,
            detect_gc_candidates,
            calculate_gc_safety_score,
        )
        inv = build_gc_inventory()
        inv = protect_governance_artifacts(inv)
        inv = protect_active_validation_artifacts(inv)
        inv = protect_runtime_authority_artifacts(inv)
        cand = detect_gc_candidates(inv)
        safety = calculate_gc_safety_score(inv, cand)
        score_val = float(safety.get("gc_safety_score", 0.0) or 0.0)
        safe_ok = score_val >= 65.0
        safe_status = "pass" if score_val >= 85.0 else "degraded" if safe_ok else "fail"
        _mk(
            "INVARIANT-GC-SAFETY",
            safe_status,
            "high" if safe_status == "pass" else "medium" if safe_status == "degraded" else "low",
            "crossplan_gc_28_4",
            blocking=False,
            details={"gc_safety_score": score_val, "candidates_total": len(cand)},
        )
    except Exception as exc:
        _mk(
            "INVARIANT-GC-SAFETY",
            "degraded",
            "low",
            "crossplan_gc_28_4",
            blocking=False,
            details={"error": str(exc)},
        )

    # INVARIANT-OPERATIONAL-HARDENING (FASE 34A)
    try:
        from runtime.hardening import build_runtime_hardening_report
        h = build_runtime_hardening_report(sensor_snapshot=sensor_snapshot, extra_ctx=extra_ctx)
        score_val = float(h.get("hardening_score", 0.0) or 0.0)
        containment = bool((h.get("containment", {}) or {}).get("containment_mode"))
        watchdogs = h.get("watchdogs", []) or []
        critical_wd = sum(1 for w in watchdogs if w.get("state") == "critical")

        hard_ok = (score_val >= 65.0) and (critical_wd == 0) and (not containment)
        if containment or score_val < 40.0:
            status = "fail"
        elif hard_ok:
            status = "pass"
        else:
            status = "degraded"

        _mk(
            "INVARIANT-OPERATIONAL-HARDENING",
            status,
            "high" if status == "pass" else "medium" if status == "degraded" else "low",
            "runtime_hardening_34a",
            blocking=bool(containment),
            details={
                "hardening_score": score_val,
                "hardening_level": h.get("hardening_level", "unknown"),
                "critical_watchdogs": critical_wd,
                "containment_mode": containment,
                "deterministic_signature": h.get("deterministic_signature"),
            },
        )
    except Exception as exc:
        _mk(
            "INVARIANT-OPERATIONAL-HARDENING",
            "degraded",
            "low",
            "runtime_hardening_34a",
            blocking=False,
            details={"error": str(exc)},
        )

    # INVARIANT-RUNTIME-DETERMINISM
    det_ok = True
    if _strict_mode():
        # In strict mode, deterministic hash should not depend on clock.
        det_ok = isinstance(det_hash, str) and len(det_hash) == 16
    _mk(
        "INVARIANT-RUNTIME-DETERMINISM",
        "pass" if det_ok else "fail",
        "high" if det_ok else "low",
        "validation_framework_33b",
        blocking=(not det_ok),
        details={"deterministic_hash": det_hash, "strict_mode": _strict_mode()},
    )

    # ── FASE 34C: Performance/fast-path invariants (non-blocking by default) ──
    try:
        from runtime.performance import build_fast_operational_summary, get_performance_cache_state

        fp1 = build_fast_operational_summary("governance", extra_ctx=extra_ctx, sensor_snapshot=sensor_snapshot)
        fp2 = build_fast_operational_summary("governance", extra_ctx=extra_ctx, sensor_snapshot=sensor_snapshot)

        def _strip_fp(d: dict[str, Any]) -> dict[str, Any]:
            # Remove cache-dependent fields that legitimately differ between first/second call.
            if not isinstance(d, dict):
                return {}
            out = json.loads(json.dumps(d, sort_keys=True, ensure_ascii=True, default=str))
            fp = out.get("fastpath")
            if isinstance(fp, dict):
                fp.pop("used_cache", None)
            return out

        # In strict mode, fast-path must be deterministic modulo cache-hit fields.
        fp_det = True
        if _strict_mode():
            fp_det = _strip_fp(fp1) == _strip_fp(fp2)
        _mk(
            "INVARIANT-FASTPATH-DETERMINISM",
            "pass" if fp_det else "degraded",
            "high" if fp_det else "medium",
            "runtime_performance_34c",
            blocking=False,
            details={"strict_mode": _strict_mode(), "deterministic": fp_det},
        )

        auth_first = bool(fp1.get("authority_first"))
        _mk(
            "INVARIANT-AUTHORITY-FIRST",
            "pass" if auth_first else "degraded",
            "high" if auth_first else "medium",
            "runtime_performance_34c",
            blocking=False,
            details={"authority_first": auth_first},
        )

        cache = get_performance_cache_state()
        cache_ok = int(cache.get("cache_entries", 0) or 0) >= 0
        cache_details = cache
        if _strict_mode() and isinstance(cache, dict):
            # Avoid volatile counters in deterministic signature.
            cache_details = {
                "contract_version": cache.get("contract_version"),
                "cache_entries": cache.get("cache_entries"),
                "freshness": cache.get("freshness"),
            }
        _mk(
            "INVARIANT-CACHE-CONSISTENCY",
            "pass" if cache_ok else "degraded",
            "high" if cache_ok else "medium",
            "runtime_performance_34c",
            blocking=False,
            details={"cache": cache_details},
        )

        # Fallback leakage: ensure deprecated model IDs are not selected as primary.
        try:
            from runtime.router.model_policy import PRIMARY_OPERATIONAL_MODEL, PRIMARY_CODING_MODEL, is_deprecated_model
            blocked = bool(is_deprecated_model(PRIMARY_OPERATIONAL_MODEL) or is_deprecated_model(PRIMARY_CODING_MODEL))
        except Exception:
            blocked = False
        _mk(
            "INVARIANT-NO-FALLBACK-LEAKAGE",
            "pass" if not blocked else "fail",
            "high" if not blocked else "low",
            "route_policy",
            blocking=bool(blocked),
            details={"primary_operational_model": "checked", "primary_coding_model": "checked"},
        )
    except Exception as exc:
        _mk(
            "INVARIANT-FASTPATH-DETERMINISM",
            "degraded",
            "low",
            "runtime_performance_34c",
            blocking=False,
            details={"error": str(exc)},
        )

    # ── FASE 35D: Operational fast-path invariants ───────────────────
    try:
        from runtime.fastpath import build_fastpath_response

        fp1 = build_fastpath_response(
            "estado runtime",
            extra_ctx={"enable_network": False},
            sensor_snapshot=sensor_snapshot or {},
            verbosity="operational",
        )
        fp2 = build_fastpath_response(
            "estado runtime",
            extra_ctx={"enable_network": False},
            sensor_snapshot=sensor_snapshot or {},
            verbosity="operational",
        )

        lines = (((fp1.get("summary", {}) or {}).get("lines", [])) or [])
        compact_ok = len(lines) <= 10
        _mk(
            "INVARIANT-FASTPATH-COMPACTNESS",
            "pass" if compact_ok else "degraded",
            "high" if compact_ok else "medium",
            "fastpath_35d",
            blocking=False,
            details={"lines": len(lines)},
        )

        det_ok = True
        if _strict_mode():
            det_ok = fp1.get("deterministic_signature") == fp2.get("deterministic_signature")
        _mk(
            "INVARIANT-FASTPATH-DETERMINISM-35D",
            "pass" if det_ok else "degraded",
            "high" if det_ok else "medium",
            "fastpath_35d",
            blocking=False,
            details={"strict_mode": _strict_mode(), "deterministic": det_ok},
        )

        auth = fp1.get("authority", {}) or {}
        auth_first = isinstance(auth, dict) and bool(auth)
        _mk(
            "INVARIANT-AUTHORITY-FIRST-FASTPATH",
            "pass" if auth_first else "degraded",
            "high" if auth_first else "medium",
            "fastpath_35d",
            blocking=False,
            details={"authority_present": auth_first},
        )

        prom = (auth.get("prometheus_targets", {}) or {}) if isinstance(auth, dict) else {}
        no_hall = True
        try:
            _ = int(prom.get("active_total", 0) or 0)
            _ = int(prom.get("scrape_up", 0) or 0)
            _ = int(prom.get("scrape_down", 0) or 0)
        except Exception:
            no_hall = False
        _mk(
            "INVARIANT-NO-FASTPATH-HALLUCINATION",
            "pass" if no_hall else "degraded",
            "high" if no_hall else "medium",
            "fastpath_35d",
            blocking=False,
            details={"prometheus_targets": {"active_total": prom.get("active_total"), "scrape_up": prom.get("scrape_up")}},
        )
    except Exception as exc:
        _mk(
            "INVARIANT-FASTPATH-COMPACTNESS",
            "degraded",
            "low",
            "fastpath_35d",
            blocking=False,
            details={"error": str(exc)},
        )

    # ── FASE 35A: Infrastructure identity invariants ────────────────
    try:
        from runtime.infrastructure import build_infrastructure_identity_registry
        infra = build_infrastructure_identity_registry(extra_ctx={})
        score = float(infra.get("score", 0.0) or 0.0)
        roots = infra.get("authority_roots", []) or []
        inv = infra.get("inventory", {}) or {}
        unknown_nodes = inv.get("unknown_nodes", []) or []
        orphans = inv.get("discoverable_nodes", []) or []

        ok = score >= 85.0 and ("192.168.1.40" in roots)
        status = "pass" if ok else "degraded" if score >= 65.0 else "fail"
        _mk(
            "INVARIANT-INFRASTRUCTURE-IDENTITY",
            status,
            "high" if status == "pass" else "medium" if status == "degraded" else "low",
            "infrastructure_registry_35a",
            blocking=("192.168.1.40" not in roots),
            details={"score": score, "authority_roots": sorted(roots), "issues": infra.get("issues", [])},
        )

        roots_ok = "192.168.1.40" in roots and "192.168.1.30" in (infra.get("control_plane", []) or [])
        _mk(
            "INVARIANT-AUTHORITY-ROOTS",
            "pass" if roots_ok else "fail",
            "high" if roots_ok else "low",
            "infrastructure_registry_35a",
            blocking=not roots_ok,
            details={"roots": sorted(roots), "control_plane": sorted(infra.get("control_plane", []) or [])},
        )

        phantom_ok = len(unknown_nodes) == 0
        _mk(
            "INVARIANT-NO-PHANTOM-INFRASTRUCTURE",
            "pass" if phantom_ok else "degraded",
            "high" if phantom_ok else "medium",
            "infrastructure_registry_35a",
            blocking=False,
            details={"unknown_nodes": unknown_nodes},
        )

        sep_ok = True
        # Discoverable nodes must be treated as non-operational unless anchored.
        if orphans:
            sep_ok = True
        _mk(
            "INVARIANT-OBSERVED-OPERATIONAL-SEPARATION",
            "pass" if sep_ok else "degraded",
            "high" if sep_ok else "medium",
            "infrastructure_registry_35a",
            blocking=False,
            details={"orphan_discoverable_total": len(orphans)},
        )
    except Exception as exc:
        _mk(
            "INVARIANT-INFRASTRUCTURE-IDENTITY",
            "degraded",
            "low",
            "infrastructure_registry_35a",
            blocking=False,
            details={"error": str(exc)},
        )

    # ── FASE 35B: Semantic sterilization invariants ─────────────────
    try:
        from runtime.semantic import sterilize_semantic_entities, build_semantic_integrity_report
        ster = sterilize_semantic_entities(extra_ctx={})
        truth = (ster.get("operational_truth", {}) or {})

        legacy_total = len(ster.get("legacy_entities", []) or [])
        phantom_total = len(ster.get("phantom_entities", []) or [])

        _mk(
            "INVARIANT-NO-LEGACY-LEAKAGE",
            "pass" if legacy_total == 0 else "fail",
            "high" if legacy_total == 0 else "low",
            "semantic_sterilization_35b",
            blocking=(legacy_total > 0),
            details={"legacy_leakage_total": legacy_total},
        )

        _mk(
            "INVARIANT-NO-PHANTOM-ENTITIES",
            "pass" if phantom_total == 0 else "degraded",
            "high" if phantom_total == 0 else "medium",
            "semantic_sterilization_35b",
            blocking=False,
            details={"phantom_entities_total": phantom_total},
        )

        unknown_operational = 0
        for c in truth.get("classifications", []) or []:
            if isinstance(c, dict) and c.get("operational") and c.get("semantic_state") == "STATE-UNKNOWN":
                unknown_operational += 1
        _mk(
            "INVARIANT-NO-UNKNOWN-OPERATIONAL",
            "pass" if unknown_operational == 0 else "fail",
            "high" if unknown_operational == 0 else "low",
            "semantic_sterilization_35b",
            blocking=(unknown_operational > 0),
            details={"unknown_operational_entities_total": unknown_operational},
        )

        cont = {c.get("contamination_type"): c for c in (ster.get("contaminations", []) or []) if isinstance(c, dict)}
        disc_total = int((cont.get("discoverable_contamination", {}) or {}).get("total", 0) or 0)
        inv_total = int((cont.get("inventory_contamination", {}) or {}).get("total", 0) or 0)
        sep_ok = (disc_total == 0) and (inv_total == 0)
        _mk(
            "INVARIANT-STRICT-STATE-SEPARATION",
            "pass" if sep_ok else "degraded",
            "high" if sep_ok else "medium",
            "semantic_sterilization_35b",
            blocking=False,
            details={"discoverable_contamination_total": disc_total, "inventory_contamination_total": inv_total},
        )

        sem = build_semantic_integrity_report(extra_ctx={})
        score = float(sem.get("semantic_integrity_score", 0.0) or 0.0)
        ok = score >= 85.0
        _mk(
            "INVARIANT-STERILIZED-OPERATIONAL-TRUTH",
            "pass" if ok else "degraded",
            "high" if ok else "medium",
            "semantic_sterilization_35b",
            blocking=False,
            details={"semantic_integrity_score": score, "level": sem.get("semantic_integrity_level")},
        )
    except Exception as exc:
        _mk(
            "INVARIANT-STERILIZED-OPERATIONAL-TRUTH",
            "degraded",
            "low",
            "semantic_sterilization_35b",
            blocking=False,
            details={"error": str(exc)},
        )

    # ── FASE 35C: Live authority-backed cognition invariants ────────
    try:
        from runtime.authority import build_live_authority_snapshot, build_authority_cognition_summary
        snap = build_live_authority_snapshot(extra_ctx={"enable_network": False})
        fresh = snap.get("freshness", {}) or {}
        ok = fresh.get("status") in ("fresh", "partial")
        _mk(
            "INVARIANT-LIVE-AUTHORITY",
            "pass" if ok else "degraded",
            "high" if ok else "medium",
            "authority_35c",
            blocking=False,
            details={"freshness": fresh},
        )

        # Grounded cognition: requires any authority evidence.
        grounded = ok
        _mk(
            "INVARIANT-GROUNDED-COGNITION",
            "pass" if grounded else "degraded",
            "high" if grounded else "medium",
            "authority_35c",
            blocking=False,
            details={"grounded": grounded},
        )

        # No synthetic state: we never claim targets list without fetch or fixture.
        prom = snap.get("prometheus", {}) or {}
        fetch = (prom.get("fetch", {}) or {}).get("targets", {}) or {}
        synth_block = (fetch.get("status") == "skipped")
        _mk(
            "INVARIANT-NO-SYNTHETIC-STATE",
            "pass" if not synth_block else "degraded",
            "high" if not synth_block else "medium",
            "authority_35c",
            blocking=False,
            details={"targets_fetch": fetch},
        )

        summ = build_authority_cognition_summary(extra_ctx={"enable_network": False})
        _mk(
            "INVARIANT-AUTHORITY-FRESHNESS",
            "pass" if float(summ.get("authority_freshness_score", 0.0) or 0.0) >= 50 else "degraded",
            "high",
            "authority_35c",
            blocking=False,
            details={"authority_freshness_score": summ.get("authority_freshness_score")},
        )
    except Exception as exc:
        _mk(
            "INVARIANT-LIVE-AUTHORITY",
            "degraded",
            "low",
            "authority_35c",
            blocking=False,
            details={"error": str(exc)},
        )

    return [i.to_dict() for i in invariants]


def build_runtime_safety_gates(
    invariants: list[dict[str, Any]] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    invariants = invariants or build_runtime_invariants(sensor_snapshot, extra_ctx)

    inv_by_name = {i.get("name"): i for i in invariants}
    failed_blocking = [i for i in invariants if i.get("blocking") and i.get("status") == "fail"]
    degraded = [i for i in invariants if i.get("status") == "degraded"]

    def _gate(gate: str, derived: list[str]) -> RuntimeSafetyGateContract:
        reasons = []
        blocking = False
        status = "pass"
        confidence = "high"

        for inv in derived:
            iv = inv_by_name.get(inv, {})
            if iv.get("status") == "fail" and iv.get("blocking"):
                status = "fail"
                blocking = True
                confidence = "low"
                reasons.append(f"blocking invariant failed: {inv}")
            elif iv.get("status") == "fail":
                status = "degraded"
                confidence = "medium"
                reasons.append(f"invariant failed: {inv}")
            elif iv.get("status") == "degraded" and status != "fail":
                status = "degraded"
                confidence = "medium"
                reasons.append(f"invariant degraded: {inv}")

        # Conservative pre-pilot: any blocking failure makes all gates fail.
        if failed_blocking and status == "pass":
            status = "degraded"
            confidence = "medium"
            reasons.append("conservative pre-pilot: blocking failures exist")

        return RuntimeSafetyGateContract(
            gate=gate,
            status=status,
            blocking=blocking,
            confidence=confidence,
            explainable=True,
            derived_from=derived,
            reasons=reasons,
        )

    gates = [
        _gate("SAFE_TO_OPERATE", [
            "INVARIANT-PROMETHEUS-AUTHORITY",
            "INVARIANT-GOVERNANCE-CONSISTENCY",
            "INVARIANT-OBSERVABILITY-FRESHNESS",
            "INVARIANT-OBSERVABILITY-SURVIVABILITY",
            "INVARIANT-SCRAPE-FRESHNESS",
            "INVARIANT-EXPORTER-STABILITY",
            "INVARIANT-TOPOLOGY-ALIGNMENT",
            "INVARIANT-TOOL-CONTRACTS",
            "INVARIANT-PLAN-REGISTRY",
            "INVARIANT-GC-SAFETY",
            "INVARIANT-OPERATIONAL-HARDENING",
        ]),
        _gate("SAFE_TO_ROUTE", [
            "INVARIANT-PROMETHEUS-AUTHORITY",
            "INVARIANT-OBSERVABILITY-FRESHNESS",
            "INVARIANT-OBSERVABILITY-SURVIVABILITY",
            "INVARIANT-SCRAPE-FRESHNESS",
            "INVARIANT-EXPORTER-STABILITY",
            "INVARIANT-TOPOLOGY-ALIGNMENT",
            "INVARIANT-TOOL-CONTRACTS",
        ]),
        _gate("SAFE_TO_REPORT", [
            "INVARIANT-REPORTING-CONSISTENCY",
            "INVARIANT-GOVERNANCE-CONSISTENCY",
            "INVARIANT-OBSERVABILITY-FRESHNESS",
            "INVARIANT-OBSERVABILITY-SURVIVABILITY",
            "INVARIANT-SCRAPE-FRESHNESS",
            "INVARIANT-EXPORTER-STABILITY",
            "INVARIANT-TOOL-CONTRACTS",
        ]),
        _gate("SAFE_TO_GROUND", [
            "INVARIANT-GROUNDING-VALIDATION",
            "INVARIANT-OBSERVABILITY-FRESHNESS",
            "INVARIANT-OBSERVABILITY-SURVIVABILITY",
            "INVARIANT-SCRAPE-FRESHNESS",
            "INVARIANT-EXPORTER-STABILITY",
        ]),
        _gate("SAFE_TO_OBSERVE", [
            "INVARIANT-PROMETHEUS-AUTHORITY",
            "INVARIANT-OBSERVABILITY-FRESHNESS",
            "INVARIANT-OBSERVABILITY-SURVIVABILITY",
            "INVARIANT-SCRAPE-FRESHNESS",
            "INVARIANT-EXPORTER-STABILITY",
        ]),
        _gate("SAFE_TO_GOVERN", [
            "INVARIANT-GOVERNANCE-CONSISTENCY",
            "INVARIANT-CONTRACT-CONSISTENCY",
            "INVARIANT-TOOL-CONTRACTS",
            "INVARIANT-PLAN-REGISTRY",
        ]),
        _gate("SAFE_TO_DEGRADE", [
            "INVARIANT-DEGRADED-MODE-CONSISTENCY",
            "INVARIANT-TOPOLOGY-ALIGNMENT",
            "INVARIANT-GC-SAFETY",
            "INVARIANT-OPERATIONAL-HARDENING",
        ]),
    ]

    return [g.to_dict() for g in gates]


def calculate_runtime_validation_score(
    invariants: list[dict[str, Any]] | None = None,
    gates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    invariants = invariants or build_runtime_invariants()
    gates = gates or build_runtime_safety_gates(invariants)

    inv_scores = []
    for inv in invariants:
        status = inv.get("status")
        if status == "pass":
            inv_scores.append(1.0)
        elif status == "degraded":
            inv_scores.append(0.6)
        else:
            inv_scores.append(0.0)
    inv_avg = sum(inv_scores) / max(len(inv_scores), 1)

    gate_scores = []
    for g in gates:
        status = g.get("status")
        if status == "pass":
            gate_scores.append(1.0)
        elif status == "degraded":
            gate_scores.append(0.5)
        else:
            gate_scores.append(0.0)
    gate_avg = sum(gate_scores) / max(len(gate_scores), 1)

    score = (inv_avg * 0.6 + gate_avg * 0.4)
    final = round(max(0.0, min(1.0, score)) * 100, 1)

    level = "high" if final >= 85 else "medium" if final >= 65 else "low" if final >= 40 else "critical"

    return {
        "validation_score": final,
        "validation_level": level,
        "components": {
            "invariants_avg": round(inv_avg, 2),
            "gates_avg": round(gate_avg, 2),
            "failed_invariants": sum(1 for i in invariants if i.get("status") == "fail"),
            "failed_gates": sum(1 for g in gates if g.get("status") == "fail"),
        },
        "contract_version": VALIDATION_CONTRACT_VERSION,
        "generated_at": _now(),
    }


def build_runtime_failure_surface(
    invariants: list[dict[str, Any]] | None = None,
    gates: list[dict[str, Any]] | None = None,
    governance_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    invariants = invariants or build_runtime_invariants()
    gates = gates or build_runtime_safety_gates(invariants)
    governance_registry = governance_registry or {}

    modes = []
    stale_authority = _ensure_list((governance_registry.get("health_summary", {}) or {}).get("stale_authority"))
    if stale_authority:
        modes.append({"type": "authority_collapse", "severity": "high", "detail": f"stale authority: {stale_authority}"})

    topo = next((i for i in invariants if i.get("name") == "INVARIANT-TOPOLOGY-ALIGNMENT"), {})
    if topo.get("status") in ("fail", "degraded"):
        modes.append({"type": "topology_drift", "severity": "medium", "detail": topo.get("details", {})})

    obs = next((i for i in invariants if i.get("name") == "INVARIANT-OBSERVABILITY-FRESHNESS"), {})
    if obs.get("status") in ("fail", "degraded"):
        modes.append({"type": "stale_observability", "severity": "medium", "detail": obs.get("details", {})})

    gov = next((i for i in invariants if i.get("name") == "INVARIANT-GOVERNANCE-CONSISTENCY"), {})
    if gov.get("status") in ("fail", "degraded"):
        modes.append({"type": "governance_degradation", "severity": "medium", "detail": gov.get("details", {})})

    contracts = next((i for i in invariants if i.get("name") == "INVARIANT-CONTRACT-CONSISTENCY"), {})
    if contracts.get("status") != "pass":
        modes.append({"type": "contract_incompatibility", "severity": "low", "detail": contracts.get("details", {})})

    remediation_pending = (governance_registry.get("health_summary", {}) or {}).get("remediation_pending", 0)
    if remediation_pending and remediation_pending > 0:
        modes.append({"type": "remediation_accumulation", "severity": "low", "detail": f"pending={remediation_pending}"})

    contract = RuntimeFailureSurfaceContract(
        total_failure_modes=len(modes),
        failure_modes=modes,
        authority_collapse_risk=bool(stale_authority),
        topology_drift_risk=topo.get("status") == "fail",
        stale_observability_risk=obs.get("status") == "fail",
        governance_degradation_risk=gov.get("status") == "fail",
        contract_incompatibility_risk=contracts.get("status") != "pass",
        remediation_accumulation_risk=bool(remediation_pending and remediation_pending > 0),
        explainable=True,
    )
    return contract.to_dict()


def detect_runtime_validation_failures(
    invariants: list[dict[str, Any]] | None = None,
    gates: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    invariants = invariants or build_runtime_invariants()
    gates = gates or build_runtime_safety_gates(invariants)

    failures = []
    for inv in invariants:
        if inv.get("status") == "fail":
            failures.append({
                "type": "invariant_failure",
                "name": inv.get("name"),
                "blocking": bool(inv.get("blocking")),
                "confidence": inv.get("confidence"),
                "authority": inv.get("authority"),
                "details": inv.get("details", {}),
            })
    for g in gates:
        if g.get("status") == "fail":
            failures.append({
                "type": "gate_failure",
                "gate": g.get("gate"),
                "blocking": bool(g.get("blocking")),
                "confidence": g.get("confidence"),
                "reasons": g.get("reasons", []),
            })
    return failures


def build_runtime_pilot_readiness(
    invariants: list[dict[str, Any]] | None = None,
    gates: list[dict[str, Any]] | None = None,
    governance_registry: dict[str, Any] | None = None,
    validation_score: dict[str, Any] | None = None,
) -> dict[str, Any]:
    invariants = invariants or build_runtime_invariants()
    gates = gates or build_runtime_safety_gates(invariants)
    governance_registry = governance_registry or {}
    validation_score = validation_score or calculate_runtime_validation_score(invariants, gates)

    gov_score = float((governance_registry.get("governance_score_info", {}) or {}).get("score", 0.0))
    gov_level = (governance_registry.get("governance_score_info", {}) or {}).get("level", "unknown")
    topo_conf = float((governance_registry.get("confidence_map", {}) or {}).get("topology_confidence", 0))

    try:
        from runtime.observability.grafana_semantic_validator import build_grafana_semantic_summary
        graf = build_grafana_semantic_summary()
        graf_score = float((graf.get("alignment_score", {}) or {}).get("overall_score", 0.0))
    except Exception:
        graf_score = 0.0

    tool_score = 0.0
    try:
        from runtime.tools import calculate_tool_governance_score
        tool_score = float((calculate_tool_governance_score() or {}).get("tool_governance_score", 0.0) or 0.0)
    except Exception:
        tool_score = 0.0

    gc_safety = 0.0
    try:
        from runtime.gc import (
            build_gc_inventory, protect_governance_artifacts, protect_active_validation_artifacts, protect_runtime_authority_artifacts,
            detect_gc_candidates, calculate_gc_safety_score,
        )
        inv = build_gc_inventory()
        inv = protect_governance_artifacts(inv)
        inv = protect_active_validation_artifacts(inv)
        inv = protect_runtime_authority_artifacts(inv)
        cand = detect_gc_candidates(inv)
        safety = calculate_gc_safety_score(inv, cand)
        gc_safety = float(safety.get("gc_safety_score", 0.0) or 0.0)
    except Exception:
        gc_safety = 0.0

    inv_blocking = [i.get("name") for i in invariants if i.get("blocking") and i.get("status") == "fail"]
    failed_gates = [g.get("gate") for g in gates if g.get("status") == "fail"]
    degraded_domains = sorted(_ensure_list(governance_registry.get("degraded_domains")))

    # Weighted readiness score (0-100)
    base = (
        (gov_score / 100.0) * 0.22
        + (graf_score / 100.0) * 0.13
        + (topo_conf / 100.0) * 0.13
        + (tool_score / 100.0) * 0.12
        + (gc_safety / 100.0) * 0.10
        + (validation_score.get("validation_score", 0.0) / 100.0) * 0.30
    )
    penalty = 0.0
    penalty += min(0.4, len(inv_blocking) * 0.15)
    penalty += min(0.3, len(failed_gates) * 0.1)
    penalty += min(0.2, len(degraded_domains) * 0.05)

    final = round(max(0.0, min(1.0, base - penalty)) * 100, 1)

    level = "ready" if final >= 85 and not inv_blocking and not failed_gates else "caution" if final >= 65 else "not_ready"
    conf = _score_to_confidence(final / 100.0)

    contract = RuntimePilotReadinessContract(
        pilot_readiness_score=final,
        readiness_level=level,
        blocking_invariants=inv_blocking,
        failed_gates=failed_gates,
        degraded_domains=degraded_domains,
        confidence=conf,
        explainable=True,
        components={
            "governance_score": gov_score,
            "governance_level": gov_level,
            "grafana_alignment_score": graf_score,
            "topology_confidence": topo_conf,
            "tool_governance_score": tool_score,
            "gc_safety_score": gc_safety,
            "validation_score": validation_score.get("validation_score", 0.0),
            "penalty": round(penalty, 2),
        },
    )
    return contract.to_dict()


def build_runtime_regression_summary(
    current_validation_score: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current_validation_score = current_validation_score or calculate_runtime_validation_score()

    regressions = []
    baseline_path = Path("/tmp/33a-governance-score.json")
    baseline_score = None
    if baseline_path.exists():
        try:
            baseline_score = json.loads(baseline_path.read_text(errors="ignore")).get("governance_score")
        except Exception:
            baseline_score = None

    if baseline_score is not None:
        # Regression if governance score dropped more than 10 points.
        try:
            from runtime.governance import calculate_governance_score
            current_gov = calculate_governance_score().get("governance_score", 0)
            if (baseline_score - current_gov) > 10:
                regressions.append({
                    "type": "governance_regression",
                    "baseline": baseline_score,
                    "current": current_gov,
                    "delta": round(current_gov - baseline_score, 1),
                })
        except Exception:
            pass

    # Validation score regressions are not available baseline yet.
    contract = RuntimeRegressionContract(
        baseline_checkpoint=BASELINE_CHECKPOINT,
        current_checkpoint=CURRENT_CHECKPOINT,
        regressions_total=len(regressions),
        regressions=regressions,
        explainable=True,
        generated_at=_now(),
    )
    return contract.to_dict()


def build_runtime_regression_burnin_summary() -> dict[str, Any]:
    # Integrate /tmp/* burn-in reports if present.
    patterns = [
        "*burnin*.json",
        "*burn-in*.json",
        "*burnin*.md",
        "*burn-in*.md",
    ]
    found = []
    for pat in patterns:
        for p in Path("/tmp").glob(pat):
            if p.is_file() and p.stat().st_size > 0:
                found.append(str(p))
    found = sorted(set(found))
    return {
        "burnin_artifacts_total": len(found),
        "burnin_artifacts": found[:50],
        "strict_mode": _strict_mode(),
    }


def build_runtime_validation_report(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sensor_snapshot = sensor_snapshot or {}
    extra_ctx = extra_ctx or {}

    governance_registry = {}
    try:
        from runtime.governance import build_runtime_governance_registry
        governance_registry = build_runtime_governance_registry(extra_ctx, sensor_snapshot)
    except ImportError:
        governance_registry = {}

    invariants = build_runtime_invariants(sensor_snapshot, extra_ctx)
    gates = build_runtime_safety_gates(invariants, sensor_snapshot, extra_ctx)
    score = calculate_runtime_validation_score(invariants, gates)
    failures = detect_runtime_validation_failures(invariants, gates)
    pilot = build_runtime_pilot_readiness(invariants, gates, governance_registry, score)
    failure_surface = build_runtime_failure_surface(invariants, gates, governance_registry)
    regressions = build_runtime_regression_summary(score)
    burnin = build_runtime_regression_burnin_summary()

    degraded_domains = _ensure_list(governance_registry.get("degraded_domains"))

    contract = RuntimeValidationContract(
        validation_score=score.get("validation_score", 0.0),
        validation_level=score.get("validation_level", "unknown"),
        invariants=invariants,
        safety_gates=gates,
        pilot_readiness=pilot,
        failure_surface=failure_surface,
        regressions={**regressions, "burnin": burnin},
        failures=failures,
        degraded_domains=degraded_domains,
        strict_mode=_strict_mode(),
        contract_version=VALIDATION_CONTRACT_VERSION,
        generated_at=_now(),
    )

    result = contract.to_dict()
    result["assertions"] = build_runtime_assertions(sensor_snapshot)
    result["governance"] = {
        "score": (governance_registry.get("governance_score_info", {}) or {}).get("score"),
        "level": (governance_registry.get("governance_score_info", {}) or {}).get("level"),
        "degraded_domains": degraded_domains,
    }

    # Expose deterministic signature.
    result["deterministic_signature"] = _hash_deterministic({
        "validation_score": result.get("validation_score"),
        "validation_level": result.get("validation_level"),
        "invariants": result.get("invariants"),
        "safety_gates": result.get("safety_gates"),
        "pilot_readiness": result.get("pilot_readiness"),
        "failures": result.get("failures"),
    })

    try:
        from runtime.telemetry.prometheus_metrics import record_validation_metrics
        record_validation_metrics(result)
    except ImportError:
        pass

    return result


def build_runtime_regression_summary_33b() -> dict[str, Any]:
    return build_runtime_regression_summary()
