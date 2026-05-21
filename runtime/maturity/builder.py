import time
import os

from runtime.maturity.descriptor import (
    RuntimePhase,
    RuntimeMaturityLevel,
    RuntimeMode,
    TopologyRole,
    FailureDomain,
    GovernanceLevel,
    GovVisibility,
    RouteFamilyStatus,
    RouteSemantics,
    RuntimeStateDescriptor,
    TemporalState,
    ModelStatus,
)


_DESCRIPTOR_CACHE: RuntimeStateDescriptor | None = None
_DESCRIPTOR_CACHE_TS: float = 0
_CACHE_TTL: float = 2.0


def build_runtime_descriptor() -> RuntimeStateDescriptor:
    global _DESCRIPTOR_CACHE, _DESCRIPTOR_CACHE_TS

    now = time.time()
    if _DESCRIPTOR_CACHE is not None and (now - _DESCRIPTOR_CACHE_TS) < _CACHE_TTL:
        return _DESCRIPTOR_CACHE

    temporal = TemporalState()
    temporal.touch()

    maturity = _resolve_maturity_level()
    mode = _resolve_mode()
    role = _resolve_topology_role()
    failure_domain = _resolve_failure_domain()
    generation_phase = _resolve_generation_phase()

    degraded_mode = _resolve_degraded_mode()
    gov_level = _resolve_governance_level()
    gov_visibility = build_governance_visibility()

    descriptor = RuntimeStateDescriptor(
        phase=generation_phase,
        maturity=maturity,
        topology_mode="single-node",
        scheduler_mode="static",
        governance_level=gov_level.value,
        mode=mode,
        topology_role=role,
        failure_domain=failure_domain,
        temporal=temporal,
        generation_ts=now,
        degraded_mode=degraded_mode,
        gov_visibility=gov_visibility,
    )

    _DESCRIPTOR_CACHE = descriptor
    _DESCRIPTOR_CACHE_TS = now
    return descriptor


def build_model_status_map() -> dict[str, str]:
    try:
        from runtime.state.lmstudio_state import get_model_tracker
        tracker = get_model_tracker()
        tracker.rebuild_from_nodes()
        raw = tracker.to_dict()
        return {k: v["status"] for k, v in raw.items()}
    except Exception:
        return {}


def _resolve_maturity_level() -> RuntimeMaturityLevel:
    try:
        from runtime.slo.degradation import get_deg_manager

        mgr = get_deg_manager()
        if mgr is None:
            return RuntimeMaturityLevel.OPERATIONAL
        level = mgr.get_current_level()
        if level == 3:
            return RuntimeMaturityLevel.EMERGENCY
        if level == 2:
            return RuntimeMaturityLevel.DEGRADED
        if level == 1:
            return RuntimeMaturityLevel.STABILIZING
        return RuntimeMaturityLevel.OPERATIONAL
    except Exception:
        pass

    try:
        from runtime.slo import DegradationManager
        _tmp = DegradationManager()
        level = _tmp.get_current_level()
        if level == 3:
            return RuntimeMaturityLevel.EMERGENCY
        if level == 2:
            return RuntimeMaturityLevel.DEGRADED
        if level == 1:
            return RuntimeMaturityLevel.STABILIZING
    except Exception:
        pass

    return RuntimeMaturityLevel.OPERATIONAL


def _resolve_mode() -> RuntimeMode:
    try:
        from runtime.agentic.execution_context import CURRENT_EXECUTION_MODE

        mode_str = CURRENT_EXECUTION_MODE.value if hasattr(CURRENT_EXECUTION_MODE, "value") else str(CURRENT_EXECUTION_MODE)
        mode_map = {
            "simulation": RuntimeMode.COGNITIVE,
            "readonly": RuntimeMode.EXECUTE,
            "sandbox_write": RuntimeMode.TOOL,
            "autonomous": RuntimeMode.EXECUTE,
        }
        return mode_map.get(mode_str.lower(), RuntimeMode.COGNITIVE)
    except Exception:
        pass
    return RuntimeMode.COGNITIVE


def _resolve_topology_role() -> TopologyRole:
    try:
        from runtime.distributed.runtime_topology import get_topology
        topo = get_topology()
        role_str = topo.get("role", "").lower()
        if "control" in role_str or "primary" in role_str:
            return TopologyRole.PRIMARY_CONTROL_PLANE
        if "backend" in role_str or "inference" in role_str:
            return TopologyRole.INFERENCE_BACKEND
        if "offline" in role_str or "inventory" in role_str:
            return TopologyRole.INVENTORY_OFFLINE
        if "observability" in role_str:
            return TopologyRole.OBSERVABILITY_NODE
        return TopologyRole.PRIMARY_CONTROL_PLANE
    except Exception:
        pass

    gateway_port = os.environ.get("AI_LAB_GATEWAY_PORT", "8008")
    if gateway_port == "8008":
        return TopologyRole.PRIMARY_CONTROL_PLANE
    return TopologyRole.INFERENCE_BACKEND


def _resolve_failure_domain() -> FailureDomain:
    role = _resolve_topology_role()
    mapping = {
        TopologyRole.PRIMARY_CONTROL_PLANE: FailureDomain.CONTROL_PLANE,
        TopologyRole.INFERENCE_BACKEND: FailureDomain.INFERENCE_GPU,
        TopologyRole.INVENTORY_OFFLINE: FailureDomain.INFERENCE_GPU,
        TopologyRole.OBSERVABILITY_NODE: FailureDomain.OBSERVABILITY,
        TopologyRole.EXTERNAL_GATEWAY: FailureDomain.EXTERNAL,
    }
    return mapping.get(role, FailureDomain.CONTROL_PLANE)


def build_topology_snapshot() -> dict:
    try:
        from runtime.distributed.runtime_topology import get_topology
        return get_topology()
    except Exception:
        return {
            "role": "unknown",
            "failure_domain": "unknown",
            "nodes": [],
        }


def _resolve_generation_phase() -> str:
    return "30G"


def _resolve_governance_level() -> GovernanceLevel:
    try:
        from runtime.control.control_plane import get_governance_state
        op_state = get_governance_state()
        mapping = {
            "NORMAL": GovernanceLevel.ENFORCED,
            "ELEVATED": GovernanceLevel.ENFORCED,
            "DEGRADED": GovernanceLevel.DEGRADED,
            "LOCKDOWN": GovernanceLevel.LOCKDOWN,
        }
        return mapping.get(op_state, GovernanceLevel.ENFORCED)
    except Exception:
        pass

    return GovernanceLevel.ENFORCED


def _resolve_governance_operational_state() -> str:
    try:
        from runtime.control.control_plane import get_governance_state
        return get_governance_state()
    except Exception:
        return "unavailable"


def _resolve_gateway_governance_counters() -> dict[str, int]:
    counters = {}
    try:
        from runtime.gateway.openai_gateway import (
            BLOCKED_PROMPTS, SANITIZATIONS, RATE_LIMIT_HITS,
            CONTEXT_OVERFLOWS, HALLUCINATION_GUARDS, PARSER_FAILURES,
        )
        counters["blocked_prompts"] = BLOCKED_PROMPTS
        counters["sanitizations"] = SANITIZATIONS
        counters["rate_limit_hits"] = RATE_LIMIT_HITS
        counters["context_overflows"] = CONTEXT_OVERFLOWS
        counters["hallucination_guards"] = HALLUCINATION_GUARDS
        counters["parser_failures"] = PARSER_FAILURES
    except Exception:
        pass
    try:
        from runtime.telemetry.prometheus_metrics import (
            GOVERNANCE_BLOCKED, GOVERNANCE_BLOCKED_BY_REASON,
        )
        counters["governance_blocked_total"] = int(GOVERNANCE_BLOCKED._value.get())
        for label in GOVERNANCE_BLOCKED_BY_REASON._metrics:
            v = int(GOVERNANCE_BLOCKED_BY_REASON.labels(label)._value.get())
            if v:
                counters[f"blocked_reason_{label}"] = v
    except Exception:
        pass
    return counters


def _resolve_active_policies() -> list[str]:
    policies = []
    try:
        from pathlib import Path
        policy_dir = Path("/opt/ai-lab/runtime/policies")
        if policy_dir.exists():
            for f in sorted(policy_dir.iterdir()):
                if f.suffix in (".py", ".md") and f.name != "__init__.py":
                    policies.append(f.name)
        memory_dir = policy_dir / "memory"
        if memory_dir.exists():
            for f in sorted(memory_dir.iterdir()):
                if f.suffix in (".py", ".md", ".json"):
                    policies.append(f"memory/{f.name}")
        tools_dir = policy_dir / "tools"
        if tools_dir.exists():
            for f in sorted(tools_dir.iterdir()):
                if f.suffix in (".py", ".md", ".json"):
                    policies.append(f"tools/{f.name}")
    except Exception:
        pass
    return policies


def build_governance_visibility() -> GovVisibility | None:
    try:
        op_state = _resolve_governance_operational_state()
        level = _resolve_governance_level()
        counters = _resolve_gateway_governance_counters()
        policies = _resolve_active_policies()

        blocked_total = sum(counters.values())

        temporal = TemporalState()
        temporal.touch()

        return GovVisibility(
            level=level,
            operational_state=op_state,
            source="control_plane",
            blocked_total=blocked_total,
            blocks_by_reason=counters,
            active_policies=policies,
            temporal=temporal,
        )
    except Exception:
        pass
    return GovVisibility(
        level=GovernanceLevel.ENFORCED,
        operational_state="unavailable",
        source="fallback",
        blocked_total=0,
        blocks_by_reason={},
        active_policies=[],
    )


_KNOWN_ROUTE_FAMILIES = (
    "minimal", "observe", "tool_fastpath", "cognitive", "learning", "report",
)


def build_route_semantics_snapshot() -> dict:
    try:
        from runtime.telemetry.prometheus_metrics import (
            ROUTE_FAMILY_TOTAL,
            ROUTE_FAMILY_ERRORS,
            ROUTE_FAMILY_BLOCKED,
            ROUTE_FAMILY_LATENCY,
        )
    except Exception:
        return {
            "source": "fallback",
            "generated_at": time.time(),
            "families": {f: RouteSemantics(family=f, status=RouteFamilyStatus.UNKNOWN, status_source="fallback", reason="prometheus_unavailable").to_dict() for f in _KNOWN_ROUTE_FAMILIES},
        }

    now = time.time()
    families: dict[str, RouteSemantics] = {}

    for family in _KNOWN_ROUTE_FAMILIES:
        try:
            total = int(ROUTE_FAMILY_TOTAL.labels(family=family)._value.get())
            errors = int(ROUTE_FAMILY_ERRORS.labels(family=family)._value.get())
            blocked = int(ROUTE_FAMILY_BLOCKED.labels(family=family)._value.get())
        except Exception:
            families[family] = RouteSemantics(family=family, status=RouteFamilyStatus.UNKNOWN, reason="metric_read_failed")
            continue

        if total == 0:
            status = RouteFamilyStatus.UNUSED
            reason = "no traffic observed"
        elif blocked > 0:
            status = RouteFamilyStatus.BLOCKED
            reason = f"{blocked} governance block(s)"
        elif total > 0 and (errors / total) > 0.1:
            status = RouteFamilyStatus.DEGRADED
            reason = f"error_rate={errors}/{total}={errors/total:.1%}"
        else:
            status = RouteFamilyStatus.ACTIVE
            reason = f"{total} request(s), no degradation"

        try:
            latency_samples = list(ROUTE_FAMILY_LATENCY.labels(family=family)._buckets.values())
            total_weight = sum(v for v in latency_samples if isinstance(v, (int, float)))
            lat = float(total_weight / total) if total > 0 and total_weight > 0 else 0.0
        except Exception:
            lat = 0.0

        families[family] = RouteSemantics(
            family=family,
            status=status,
            status_source="lifetime_metrics",
            total_requests=total,
            error_count=errors,
            blocked_count=blocked,
            avg_latency_ms=round(lat, 2),
            reason=reason,
        )

    return {
        "source": "gateway_metrics",
        "generated_at": now,
        "families": {k: v.to_dict() for k, v in families.items()},
    }


def _resolve_degraded_mode() -> dict | None:
    try:
        from runtime.slo.degradation import DegradationManager
        mgr = DegradationManager()
        return mgr.get_degraded_state().to_dict()
    except Exception:
        pass
    return None


def _is_model_actively_serving(model_info: dict) -> bool:
    _ = model_info.get("id", "") or model_info.get("model", "")
    return True
