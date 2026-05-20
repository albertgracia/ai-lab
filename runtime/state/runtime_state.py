from datetime import datetime


def _current_runtime_mode() -> str:
    try:
        from runtime.modes.mode_manager import current_mode

        return current_mode()
    except Exception:
        return RUNTIME_STATE["mode"]

RUNTIME_STATE = {
    "runtime": "AI-LAB Cognitive Runtime",
    "status": "online",
    "mode": "distributed-cognitive",
    "started_at": datetime.utcnow().isoformat(),
    "active_sessions": 0,
    "active_streams": 0,
    "executions": 0,
    "last_model": None,
    "last_task": None,
}


def update_runtime_state(
    model=None,
    task=None,
    streams=None,
):
    if model:
        RUNTIME_STATE["last_model"] = model

    if task:
        RUNTIME_STATE["last_task"] = task

    if streams is not None:
        RUNTIME_STATE["active_streams"] = streams

    RUNTIME_STATE["executions"] += 1


def get_runtime_state():
    state = dict(RUNTIME_STATE)
    state["mode"] = _current_runtime_mode()
    try:
        from runtime.maturity import build_runtime_descriptor
        descriptor = build_runtime_descriptor()
        state["maturity"] = descriptor.to_dict()
    except Exception:
        state["maturity"] = None
    try:
        from runtime.state.lmstudio_state import get_model_tracker
        tracker = get_model_tracker()
        tracker.rebuild_from_nodes()
        state["model_state"] = tracker.to_dict()
    except Exception:
        state["model_state"] = None
    try:
        from runtime.slo.degradation import DegradationManager
        from runtime.slo.runtime_slo import is_slo_enabled
        _dummy_mgr = DegradationManager()
        state["degraded_mode"] = _dummy_mgr.get_degraded_state().to_dict()
        state["slo_enabled"] = is_slo_enabled()
    except Exception:
        state["degraded_mode"] = None
        state["slo_enabled"] = False
    return state
