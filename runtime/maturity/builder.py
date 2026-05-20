import time
import os

from runtime.maturity.descriptor import (
    RuntimePhase,
    RuntimeMaturityLevel,
    RuntimeMode,
    TopologyRole,
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
    generation_phase = _resolve_generation_phase()

    degraded_mode = _resolve_degraded_mode()

    descriptor = RuntimeStateDescriptor(
        phase=generation_phase,
        maturity=maturity,
        topology_mode="single-node",
        scheduler_mode="static",
        governance_level="enforced",
        mode=mode,
        topology_role=role,
        temporal=temporal,
        generation_ts=now,
        degraded_mode=degraded_mode,
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
        return TopologyRole.PRIMARY_CONTROL_PLANE
    except Exception:
        pass

    gateway_port = os.environ.get("AI_LAB_GATEWAY_PORT", "8008")
    if gateway_port == "8008":
        return TopologyRole.PRIMARY_CONTROL_PLANE
    return TopologyRole.INFERENCE_BACKEND


def _resolve_generation_phase() -> str:
    return "30C"


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
