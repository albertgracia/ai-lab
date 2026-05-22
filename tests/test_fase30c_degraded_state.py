"""FASE 30C: Single-Node Explicit Degraded Mode

Tests for DegradedModeState, TemporalTransition, integration with
DegradationManager, runtime state, builder, and endpoint.
"""

import time
import json
import pytest

from runtime.slo.degraded_state import (
    DegradedModeState,
    TemporalTransition,
    build_disabled_degraded_state,
)
from runtime.slo.degradation import DegradationManager


# ── TemporalTransition ──────────────────────────────────────────

def test_temporal_transition_defaults():
    t = TemporalTransition()
    assert t.timestamp == 0.0
    assert t.previous_level == 0
    assert t.current_level == 0
    assert t.reason == ""
    assert t.source == "runtime_slo"


def test_temporal_transition_with_values():
    now = time.time()
    t = TemporalTransition(
        timestamp=now,
        previous_level=0,
        current_level=1,
        reason="gpu_pressure_0.95",
        source="runtime_slo",
    )
    assert t.timestamp == now
    assert t.previous_level == 0
    assert t.current_level == 1
    assert t.reason == "gpu_pressure_0.95"
    assert t.source == "runtime_slo"


def test_temporal_transition_to_dict():
    t = TemporalTransition(
        timestamp=100.0,
        previous_level=0,
        current_level=2,
        reason="timeout_rate_0.10",
        source="runtime_slo",
    )
    d = t.to_dict()
    assert d["timestamp"] == 100.0
    assert d["previous_level"] == 0
    assert d["current_level"] == 2
    assert d["reason"] == "timeout_rate_0.10"
    assert d["source"] == "runtime_slo"


def test_temporal_transition_source_manual():
    t = TemporalTransition(
        timestamp=time.time(),
        previous_level=1,
        current_level=0,
        reason="manual_recovery",
        source="manual",
    )
    assert t.source == "manual"


def test_temporal_transition_source_startup():
    t = TemporalTransition(
        timestamp=time.time(),
        previous_level=0,
        current_level=0,
        reason="initialized",
        source="startup",
    )
    assert t.source == "startup"


# ── DegradedModeState: level 0 (normal) ────────────────────────

def test_degraded_state_init_normal():
    state = DegradedModeState()
    assert state.level == 0
    assert state.is_degraded is False
    assert state.reason == ""
    assert state.source == "startup"
    assert state.dry_run is True
    assert state.transition_count == 0
    assert state.previous_level == 0
    assert state.duration_seconds == 0.0
    assert state.cooldown_remaining == 0.0


def test_degraded_state_to_dict_normal():
    state = DegradedModeState(level=0, reason="normal", source="startup")
    d = state.to_dict()
    assert d["level"] == 0
    assert d["is_degraded"] is False
    assert d["reason"] == "normal"
    assert d["source"] == "startup"
    assert d["transitions"] == []
    assert d["health_checks"] == []


def test_degraded_state_serializable():
    state = DegradedModeState(level=0, reason="normal")
    json.dumps(state.to_dict())


# ── DegradedModeState: level > 0 (degraded) ────────────────────

def test_degraded_state_level_1():
    state = DegradedModeState(
        level=1,
        reason="gpu_pressure_0.95",
        source="runtime_slo",
        dry_run=True,
    )
    assert state.is_degraded is True
    assert state.level == 1
    assert state.reason == "gpu_pressure_0.95"
    assert state.source == "runtime_slo"


def test_degraded_state_level_2():
    state = DegradedModeState(
        level=2,
        reason="vram_pressure_0.98",
        source="runtime_slo",
        dry_run=False,
    )
    assert state.is_degraded is True
    assert state.level == 2
    assert state.dry_run is False


def test_degraded_state_level_3():
    state = DegradedModeState(level=3, reason="emergency", source="runtime_slo")
    assert state.is_degraded is True
    assert state.level == 3


def test_degraded_state_level_0_is_not_degraded():
    state = DegradedModeState(level=0)
    assert state.is_degraded is False


# ── DegradedModeState: transitions ──────────────────────────────

def test_degraded_state_record_transition():
    state = DegradedModeState()
    state.record_transition(0, 1, "gpu_pressure_0.95", "runtime_slo")
    assert state.level == 1
    assert state.previous_level == 0
    assert state.transition_count == 1
    assert state.is_degraded is True
    assert state.reason == "gpu_pressure_0.95"
    assert state.source == "runtime_slo"


def test_degraded_state_transition_history():
    state = DegradedModeState()
    state.record_transition(0, 1, "gpu_pressure", "runtime_slo")
    state.record_transition(1, 2, "timeout_rate", "runtime_slo")
    state.record_transition(2, 0, "recovered", "runtime_slo")
    assert state.transition_count == 3
    assert len(state.transitions) == 3
    assert state.transitions[0].previous_level == 0
    assert state.transitions[0].current_level == 1
    assert state.transitions[1].previous_level == 1
    assert state.transitions[1].current_level == 2
    assert state.transitions[2].previous_level == 2
    assert state.transitions[2].current_level == 0


def test_degraded_state_transition_source_manual():
    state = DegradedModeState()
    state.record_transition(1, 0, "operator_recovery", "manual")
    assert state.source == "manual"
    assert state.transitions[0].source == "manual"


def test_degraded_state_transition_source_startup():
    state = DegradedModeState(source="startup")
    state.record_transition(0, 0, "initialized", "startup")
    assert state.source == "startup"


# ── DegradedModeState: health checks ────────────────────────────

def test_health_checks_deque():
    state = DegradedModeState()
    state.record_health_check(True)
    state.record_health_check(True)
    state.record_health_check(False)
    assert len(state.health_checks) == 3
    assert list(state.health_checks) == [True, True, False]


def test_health_checks_maxlen_20():
    state = DegradedModeState()
    for _ in range(25):
        state.record_health_check(True)
    assert len(state.health_checks) == 20


# ── DegradedModeState: duration and cooldown ────────────────────

def test_duration_zeros_when_level_0():
    state = DegradedModeState(level=0)
    assert state.duration_seconds == 0.0


def test_duration_increases_when_degraded():
    state = DegradedModeState(level=1, started_at=time.time() - 10)
    assert state.duration_seconds >= 9.0


def test_duration_zeros_when_not_started():
    state = DegradedModeState(level=1, started_at=0.0)
    assert state.duration_seconds == 0.0


def test_cooldown_remaining_when_level_0_and_healthy():
    state = DegradedModeState(
        level=0, healthy_since=time.time() - 5, cooldown_seconds=30.0
    )
    assert 24.0 <= state.cooldown_remaining <= 26.0


def test_cooldown_zero_when_degraded():
    state = DegradedModeState(level=2, healthy_since=0.0, cooldown_seconds=30.0)
    assert state.cooldown_remaining == 0.0


def test_cooldown_zero_when_healthy_since_zero():
    state = DegradedModeState(level=0, healthy_since=0.0, cooldown_seconds=30.0)
    assert state.cooldown_remaining == 0.0


# ── DegradedModeState: update_from_degradation ──────────────────

def test_update_from_degradation_transition():
    state = DegradedModeState()
    state.update_from_degradation(
        level=1,
        dry_run=True,
        reason="gpu_pressure_0.95",
        trigger_metric="gpu_util",
        trigger_value=0.95,
        threshold=0.92,
        source="runtime_slo",
    )
    assert state.level == 1
    assert state.previous_level == 0
    assert state.transition_count == 1
    assert state.trigger_metric == "gpu_util"
    assert state.trigger_value == 0.95
    assert state.threshold == 0.92


def test_update_from_degradation_recovery():
    state = DegradedModeState(
        level=2, started_at=time.time(), trigger_metric="vram_pressure"
    )
    state.update_from_degradation(
        level=0,
        dry_run=False,
        reason="recovered",
        source="runtime_slo",
    )
    assert state.level == 0
    assert state.previous_level == 2
    assert state.transition_count == 1
    assert state.trigger_metric == ""
    assert state.trigger_value == 0.0
    assert state.started_at == 0.0


def test_update_from_degradation_multiple_transitions():
    state = DegradedModeState()
    state.update_from_degradation(level=1, dry_run=True, reason="gpu", source="runtime_slo")
    state.update_from_degradation(level=2, dry_run=True, reason="vram", source="runtime_slo")
    state.update_from_degradation(level=0, dry_run=True, reason="recovered", source="runtime_slo")
    assert state.transition_count == 3
    assert len(state.transitions) == 3


# ── build_disabled_degraded_state (RULE-30C-7) ──────────────────

def test_build_disabled_degraded_state():
    state = build_disabled_degraded_state()
    assert state.level == 0
    assert state.is_degraded is False
    assert state.reason == "slo_enforcement_disabled"
    assert state.source == "startup"
    assert state.dry_run is True


def test_build_disabled_degraded_state_to_dict():
    state = build_disabled_degraded_state()
    d = state.to_dict()
    assert d["level"] == 0
    assert d["is_degraded"] is False
    assert d["reason"] == "slo_enforcement_disabled"


# ── DegradationManager integration ─────────────────────────────

def test_deg_manager_initial_state():
    mgr = DegradationManager()
    state = mgr.get_degraded_state()
    assert state.level == 0
    assert state.is_degraded is False
    assert state.reason == "normal"
    assert state.source == "startup"
    assert state.transition_count == 0


def test_deg_manager_get_degraded_state_isolation():
    mgr1 = DegradationManager()
    mgr2 = DegradationManager()
    s1 = mgr1.get_degraded_state()
    s2 = mgr2.get_degraded_state()
    assert s1.level == s2.level
    assert s1.reason == s2.reason
    # Different instances should not share state
    s1.record_transition(0, 1, "test", "manual")
    assert mgr1.get_degraded_state().transition_count == 1
    # mgr2 is a different instance
    assert mgr2.get_degraded_state().transition_count == 0


def test_deg_manager_record_health_check():
    mgr = DegradationManager()
    mgr.record_health_check(True)
    mgr.record_health_check(False)
    state = mgr.get_degraded_state()
    assert len(state.health_checks) == 2
    assert list(state.health_checks) == [True, False]


# ── Runtime state integration ──────────────────────────────────

def test_runtime_state_includes_degraded():
    from runtime.state.runtime_state import get_runtime_state
    state = get_runtime_state()
    assert "degraded_mode" in state
    dm = state["degraded_mode"]
    assert dm is not None
    assert isinstance(dm, dict)
    assert "level" in dm
    assert "is_degraded" in dm
    assert "reason" in dm


# ── Builder integration ─────────────────────────────────────────

def test_builder_includes_degraded_mode():
    from runtime.maturity.builder import build_runtime_descriptor
    descriptor = build_runtime_descriptor()
    d = descriptor.to_dict()
    assert "degraded_mode" in d
    dm = d["degraded_mode"]
    assert dm is not None
    assert "level" in dm
    assert "is_degraded" in dm
    assert dm["level"] == 0
    assert dm["is_degraded"] is False


def test_builder_phase_current():
    from runtime.maturity.builder import build_runtime_descriptor
    descriptor = build_runtime_descriptor()
    d = descriptor.to_dict()
    assert d["runtime_generation"]["phase"] in ("30C", "30D", "30E", "30F", "30G", "30H")


# ── Endpoint integration ────────────────────────────────────────

def test_runtime_phase_has_30C():
    from runtime.maturity.descriptor import RuntimePhase
    assert RuntimePhase.PHASE_30C.value == "30C"


def test_runtime_phase_includes_30C():
    from runtime.maturity.descriptor import RuntimePhase
    expected = {"28.1", "28.2", "28.3", "29.2", "29.3", "29.4", "30A", "30C"}
    actual = {p.value for p in RuntimePhase}
    assert expected.issubset(actual)
