"""FASE 30A: Runtime State Foundation & Maturity Descriptors"""

import time
import json
import pytest
from unittest.mock import patch, MagicMock

from runtime.maturity.descriptor import (
    RuntimePhase, RuntimeMaturityLevel, RuntimeMode,
    TopologyRole, SchedulerState, GovernanceLevel,
    TemporalState, RuntimeStateDescriptor, ModelStatus,
)
from runtime.maturity.builder import build_runtime_descriptor, build_model_status_map


# ── RuntimePhase ────────────────────────────────────────────────

def test_runtime_phase_has_30A():
    assert RuntimePhase.PHASE_30A.value == "30A"


def test_runtime_phase_all_values_are_strings():
    for phase in RuntimePhase:
        assert isinstance(phase.value, str)


def test_runtime_phase_includes_previous_phases():
    expected = {"28.1", "28.2", "28.3", "29.2", "29.3", "29.4", "30A"}
    actual = {p.value for p in RuntimePhase}
    assert expected.issubset(actual)


# ── RuntimeMaturityLevel ────────────────────────────────────────

def test_maturity_level_values():
    assert RuntimeMaturityLevel.OPERATIONAL.value == "operational"
    assert RuntimeMaturityLevel.DEGRADED.value == "degraded"
    assert RuntimeMaturityLevel.EMERGENCY.value == "emergency"
    assert RuntimeMaturityLevel.BOOTING.value == "booting"
    assert RuntimeMaturityLevel.STABILIZING.value == "stabilizing"
    assert RuntimeMaturityLevel.SHUTDOWN.value == "shutdown"


def test_maturity_level_has_six_levels():
    assert len(RuntimeMaturityLevel) == 6


# ── RuntimeMode ─────────────────────────────────────────────────

def test_runtime_mode_values():
    assert RuntimeMode.COGNITIVE.value == "cognitive"
    assert RuntimeMode.OPERATIONAL.value == "operational"
    assert RuntimeMode.TOOL.value == "tool"
    assert RuntimeMode.EXECUTE.value == "execute"
    assert RuntimeMode.OBSERVE.value == "observe"


def test_runtime_mode_has_five_modes():
    assert len(RuntimeMode) == 5


# ── TopologyRole ────────────────────────────────────────────────

def test_topology_role_values():
    assert TopologyRole.PRIMARY_CONTROL_PLANE.value == "primary-control-plane"
    assert TopologyRole.INFERENCE_BACKEND.value == "inference-backend"
    assert TopologyRole.INVENTORY_OFFLINE.value == "inventory-offline"


# ── SchedulerState ──────────────────────────────────────────────

def test_scheduler_state_default():
    assert SchedulerState.STATIC.value == "static"


# ── GovernanceLevel ─────────────────────────────────────────────

def test_governance_level_values():
    assert GovernanceLevel.PASSIVE.value == "passive"
    assert GovernanceLevel.OBSERVABLE.value == "observable"
    assert GovernanceLevel.ENFORCED.value == "enforced"


# ── ModelStatus ─────────────────────────────────────────────────

def test_model_status_values():
    assert ModelStatus.LOADED.value == "loaded"
    assert ModelStatus.ACTIVE.value == "active"
    assert ModelStatus.DISCOVERABLE.value == "discoverable"
    assert ModelStatus.DISABLED.value == "disabled"
    assert ModelStatus.UNAVAILABLE.value == "unavailable"


def test_model_status_has_five_statuses():
    assert len(ModelStatus) == 5


# RULE-30A-1: active != loaded
def test_model_status_active_not_equal_loaded():
    assert ModelStatus.ACTIVE != ModelStatus.LOADED
    assert ModelStatus.ACTIVE.value != ModelStatus.LOADED.value


# ── TemporalState ───────────────────────────────────────────────

def test_temporal_state_defaults():
    ts = TemporalState()
    assert ts.last_seen == 0.0
    assert ts.last_routed == 0.0
    assert ts.last_health == "unknown"
    assert ts.last_error == ""
    assert ts.transition_count == 0
    assert ts.first_seen == 0.0


def test_temporal_state_touch_sets_first_seen():
    ts = TemporalState()
    time.sleep(0.001)
    ts.touch()
    assert ts.first_seen > 0
    assert ts.last_seen > 0
    assert ts.first_seen == ts.last_seen


def test_temporal_state_touch_preserves_first_seen():
    ts = TemporalState()
    ts.touch()
    first = ts.first_seen
    time.sleep(0.001)
    ts.touch()
    assert ts.first_seen == first
    assert ts.last_seen > first


def test_temporal_state_record_route():
    ts = TemporalState()
    assert ts.transition_count == 0
    ts.record_route()
    assert ts.transition_count == 1
    assert ts.last_routed > 0


def test_temporal_state_record_route_increments():
    ts = TemporalState()
    ts.record_route()
    ts.record_route()
    ts.record_route()
    assert ts.transition_count == 3


def test_temporal_state_record_health():
    ts = TemporalState()
    ts.record_health("healthy")
    assert ts.last_health == "healthy"
    assert ts.last_seen > 0


def test_temporal_state_record_error():
    ts = TemporalState()
    ts.record_error("timeout")
    assert ts.last_error == "timeout"
    assert ts.last_seen > 0


def test_temporal_state_to_dict():
    ts = TemporalState()
    ts.touch()
    ts.record_route()
    ts.record_health("healthy")
    d = ts.to_dict()
    assert "last_seen" in d
    assert "last_routed" in d
    assert "last_health" in d
    assert d["last_health"] == "healthy"
    assert d["transition_count"] == 1
    assert "first_seen" in d
    assert "last_error" in d


# RULE-30A-2: temporal awareness
def test_temporal_state_is_temporally_aware():
    ts = TemporalState()
    ts.touch()
    ts.record_route()
    ts.record_health("degraded")
    ts.record_error("vram_pressure")
    assert ts.last_seen > 0
    assert ts.last_routed > 0
    assert ts.last_health == "degraded"
    assert ts.last_error == "vram_pressure"
    assert ts.transition_count >= 1


# ── RuntimeStateDescriptor ──────────────────────────────────────

def test_descriptor_defaults():
    desc = RuntimeStateDescriptor(
        phase="30A",
        maturity=RuntimeMaturityLevel.OPERATIONAL,
        topology_mode="single-node",
        scheduler_mode="static",
        governance_level="enforced",
        mode=RuntimeMode.COGNITIVE,
        topology_role=TopologyRole.PRIMARY_CONTROL_PLANE,
    )
    assert desc.phase == "30A"
    assert desc.maturity == RuntimeMaturityLevel.OPERATIONAL
    assert desc.topology_mode == "single-node"
    assert desc.scheduler_mode == "static"
    assert desc.governance_level == "enforced"
    assert desc.mode == RuntimeMode.COGNITIVE
    assert desc.topology_role == TopologyRole.PRIMARY_CONTROL_PLANE


def test_descriptor_to_dict_includes_runtime_generation():
    desc = RuntimeStateDescriptor(
        phase="30A",
        maturity=RuntimeMaturityLevel.OPERATIONAL,
        topology_mode="single-node",
        scheduler_mode="static",
        governance_level="enforced",
        mode=RuntimeMode.COGNITIVE,
        topology_role=TopologyRole.PRIMARY_CONTROL_PLANE,
    )
    d = desc.to_dict()
    assert "runtime_generation" in d
    gen = d["runtime_generation"]
    assert gen["phase"] == "30A"
    assert gen["maturity"] == "operational"
    assert gen["topology_mode"] == "single-node"
    assert gen["scheduler_mode"] == "static"
    assert gen["governance_level"] == "enforced"


def test_descriptor_to_dict_includes_temporal():
    desc = RuntimeStateDescriptor(
        phase="30A",
        maturity=RuntimeMaturityLevel.OPERATIONAL,
        topology_mode="single-node",
        scheduler_mode="static",
        governance_level="enforced",
        mode=RuntimeMode.COGNITIVE,
        topology_role=TopologyRole.PRIMARY_CONTROL_PLANE,
    )
    d = desc.to_dict()
    assert "temporal" in d
    assert "last_seen" in d["temporal"]


def test_descriptor_to_dict_includes_mode_and_role():
    desc = RuntimeStateDescriptor(
        phase="30A",
        maturity=RuntimeMaturityLevel.OPERATIONAL,
        topology_mode="single-node",
        scheduler_mode="static",
        governance_level="enforced",
        mode=RuntimeMode.COGNITIVE,
        topology_role=TopologyRole.PRIMARY_CONTROL_PLANE,
    )
    d = desc.to_dict()
    assert d["mode"] == "cognitive"
    assert d["topology_role"] == "primary-control-plane"


def test_descriptor_to_dict_includes_generated_at():
    desc = RuntimeStateDescriptor(
        phase="30A",
        maturity=RuntimeMaturityLevel.OPERATIONAL,
        topology_mode="single-node",
        scheduler_mode="static",
        governance_level="enforced",
        mode=RuntimeMode.COGNITIVE,
        topology_role=TopologyRole.PRIMARY_CONTROL_PLANE,
    )
    d = desc.to_dict()
    assert "generated_at" in d
    assert isinstance(d["generated_at"], float)


# ── build_runtime_descriptor ────────────────────────────────────

def test_build_runtime_descriptor_returns_valid():
    desc = build_runtime_descriptor()
    assert isinstance(desc, RuntimeStateDescriptor)
    assert desc.phase == "30A"
    assert isinstance(desc.maturity, RuntimeMaturityLevel)
    assert isinstance(desc.mode, RuntimeMode)
    assert isinstance(desc.topology_role, TopologyRole)


def test_build_runtime_descriptor_to_dict_roundtrip():
    desc = build_runtime_descriptor()
    d = desc.to_dict()
    assert d["runtime_generation"]["phase"] == "30A"
    assert d["runtime_generation"]["maturity"] in (
        "booting", "stabilizing", "operational", "degraded", "emergency", "shutdown"
    )
    assert d["mode"] in ("cognitive", "operational", "tool", "execute", "observe")
    assert d["topology_role"] in (
        "primary-control-plane", "inference-backend", "inventory-offline"
    )
    assert d["temporal"]["last_seen"] > 0


def test_build_runtime_descriptor_caches():
    desc1 = build_runtime_descriptor()
    desc2 = build_runtime_descriptor()
    assert desc1 is desc2


def test_build_runtime_descriptor_json_serializable():
    desc = build_runtime_descriptor()
    d = desc.to_dict()
    json_str = json.dumps(d)
    assert json_str
    parsed = json.loads(json_str)
    assert parsed["runtime_generation"]["phase"] == "30A"


def test_build_runtime_descriptor_temporal_touched():
    desc = build_runtime_descriptor()
    assert desc.temporal.last_seen > 0


# ── model_status_map (FASE 30A foundation) ─────────────────────

def test_build_model_status_map_returns_dict():
    result = build_model_status_map()
    assert isinstance(result, dict)


def test_build_model_status_map_handles_missing_modules():
    result = build_model_status_map()
    assert isinstance(result, dict)


# ── enum serialization ──────────────────────────────────────────

def test_all_enums_json_serializable():
    for enum_cls in [RuntimePhase, RuntimeMaturityLevel, RuntimeMode,
                     TopologyRole, SchedulerState, GovernanceLevel, ModelStatus]:
        for member in enum_cls:
            d = {"value": member.value}
            json.dumps(d)


# ── governance_level defaults ───────────────────────────────────

def test_runtime_generation_structure():
    desc = RuntimeStateDescriptor(
        phase="30A",
        maturity=RuntimeMaturityLevel.OPERATIONAL,
        topology_mode="single-node",
        scheduler_mode="static",
        governance_level="enforced",
        mode=RuntimeMode.COGNITIVE,
        topology_role=TopologyRole.PRIMARY_CONTROL_PLANE,
    )
    gen = desc.to_dict()["runtime_generation"]
    assert set(gen.keys()) == {"phase", "maturity", "topology_mode", "scheduler_mode", "governance_level"}
