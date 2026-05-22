from __future__ import annotations

import sys
import time
from typing import Any

sys.path.insert(0, "/opt/ai-lab")

from runtime.entities.contracts import (
    ENTITY_CONTRACT_VERSION,
    ENTITY_STATES,
    ENTITY_TYPES,
    EntityContract,
    EntityStateContract,
    DiscoverabilityContract,
    OperationalEntityContract,
    InventoryEntityContract,
    RoutabilityContract,
)
from runtime.entities.entity_registry import (
    build_entity_registry,
    build_active_entities,
    build_inventory_entities,
    build_discoverable_entities,
    build_deprecated_entities,
    build_routability_summary,
    build_topology_preparation,
    classify_entity_state,
    classify_operational_state,
    classify_discoverability,
    classify_routability,
    detect_stale_entities,
    detect_inventory_only_entities,
    detect_deprecated_entities,
)


def _make_gpu_summary(gpu_id: str, *, active: bool = False, expected_offline: bool = False, confidence: str = "high") -> dict:
    summary = {
        "gpu_id": gpu_id,
        "name": gpu_id,
        "observed_state": "online" if active else ("expected_offline" if expected_offline else "unavailable"),
        "operational_state": "active" if active else ("inactive" if expected_offline else "down"),
        "inventory_expected_offline": expected_offline,
        "confidence": confidence,
        "freshness": {"status": "fresh" if active else "unknown"},
        "source_of_truth": ["sensor_fusion"],
    }
    return summary


def _make_model_entry(model_id: str, group: str = "active") -> dict:
    return {"id": model_id, "name": model_id}


# ── Tests ──────────────────────────────────────────────────────

def test_entity_contract_version():
    assert ENTITY_CONTRACT_VERSION == "31E"


def test_entity_states_defined():
    required = {"active", "loaded", "discoverable", "inventory", "expected_offline", "unobserved", "stale", "disabled", "deprecated", "unavailable"}
    assert required.issubset(ENTITY_STATES)


def test_entity_types_defined():
    required = {"gpu", "model", "host", "service", "storage", "topology_mode"}
    assert required.issubset(ENTITY_TYPES)


def test_entity_contract_to_dict():
    ec = EntityContract(entity_id="test-gpu", entity_type="gpu", operational_state="active", routable=True)
    d = ec.to_dict()
    assert d["entity_id"] == "test-gpu"
    assert d["entity_type"] == "gpu"
    assert d["operational_state"] == "active"
    assert d["routable"] is True
    assert d["contract_version"] == "31E"


def test_classify_entity_state_deprecated():
    assert classify_entity_state("inventory", None, None, deprecated=True) == "deprecated"


def test_classify_entity_state_disabled():
    assert classify_entity_state("inventory", None, None, disabled=True) == "disabled"


def test_classify_entity_state_expected_offline():
    assert classify_entity_state(None, None, None, inventory_expected_offline=True) == "expected_offline"


def test_classify_entity_state_active():
    assert classify_entity_state("inventory", "online", "active") == "active"


def test_classify_entity_state_loaded():
    assert classify_entity_state("inventory", "online", "idle") == "loaded"


def test_classify_entity_state_inventory():
    assert classify_entity_state("inventory", None, None) == "inventory"


def test_classify_entity_state_discoverable():
    assert classify_entity_state(None, "online", "inactive") == "discoverable"


def test_classify_entity_state_unavailable():
    assert classify_entity_state(None, "down", None) == "unavailable"


def test_classify_entity_state_unobserved():
    assert classify_entity_state(None, None, None) == "unobserved"


def test_classify_operational_state_active():
    assert classify_operational_state("online", has_recent_traffic=True) == "active"


def test_classify_operational_state_loaded():
    assert classify_operational_state("online", is_loaded_in_backend=True) == "loaded"


def test_classify_operational_state_idle():
    assert classify_operational_state("online") == "idle"


def test_classify_operational_state_expected_offline():
    assert classify_operational_state(None, expected_offline=True) == "inactive"


def test_classify_discoverability_endpoint():
    assert classify_discoverability(endpoint_responds=True) == "discoverable"


def test_classify_discoverability_observed():
    assert classify_discoverability(observed_state="online") == "discoverable"


def test_classify_discoverability_inventory():
    assert classify_discoverability(visible_in_inventory=True) == "inventory_visible"


def test_classify_routability_active():
    routable, reason = classify_routability("gpu", "rx9070", operational_state="active")
    assert routable is True
    assert reason == "operational"


def test_classify_routability_deprecated():
    routable, reason = classify_routability("model", "deprecated-model", deprecated=True)
    assert routable is False
    assert reason == "deprecated"


def test_classify_routability_disabled():
    routable, reason = classify_routability("model", "disabled-model", disabled=True)
    assert routable is False
    assert reason == "disabled"


def test_classify_routability_expected_offline():
    routable, reason = classify_routability("gpu", "rx7900xt", expected_offline=True)
    assert routable is False
    assert reason == "expected_offline"


def test_classify_routability_idle():
    routable, reason = classify_routability("gpu", "rx9070", operational_state="idle")
    assert routable is True
    assert reason == "idle_available"


def test_classify_routability_not_available():
    routable, reason = classify_routability("gpu", "unknown", operational_state="inactive")
    assert routable is False
    assert reason == "not_available"


def test_build_entity_registry_with_gpu_active():
    sensor = {"gpu_operational_summaries": [_make_gpu_summary("RX9070", active=True)]}
    registry = build_entity_registry(sensor_snapshot=sensor)
    assert len(registry) >= 1
    gpu_entity = next((e for e in registry if e["entity_id"] == "RX9070"), None)
    assert gpu_entity is not None
    assert gpu_entity["operational_state"] == "active"
    assert gpu_entity["routable"] is True


def test_build_entity_registry_with_gpu_expected_offline():
    sensor = {"gpu_operational_summaries": [_make_gpu_summary("RX7900XT", expected_offline=True)]}
    registry = build_entity_registry(sensor_snapshot=sensor)
    gpu_entity = next((e for e in registry if e["entity_id"] == "RX7900XT"), None)
    assert gpu_entity is not None
    assert gpu_entity["inventory_state"] == "expected_offline"
    assert gpu_entity["routable"] is False


def test_build_entity_registry_with_active_model():
    extra = {"models": {"active": [_make_model_entry("llama-3.1-8b-instruct")]}}
    registry = build_entity_registry(extra_ctx=extra)
    model_entity = next((e for e in registry if e["entity_id"] == "llama-3.1-8b-instruct"), None)
    assert model_entity is not None
    assert model_entity["operational_state"] == "active"
    assert model_entity["routable"] is True


def test_build_entity_registry_with_deprecated_model():
    extra = {"models": {"discovered": [_make_model_entry("lmstudio-community/qwen2.5-coder-14b-instruct")]}}
    registry = build_entity_registry(extra_ctx=extra)
    model_entity = next((e for e in registry if e["entity_id"] == "lmstudio-community/qwen2.5-coder-14b-instruct"), None)
    assert model_entity is not None
    assert model_entity["deprecated"] is True
    assert model_entity["routable"] is False


def test_build_entity_registry_with_disabled_model():
    extra = {"models": {"disabled": [_make_model_entry("qwen3.6-27b")]}}
    registry = build_entity_registry(extra_ctx=extra)
    model_entity = next((e for e in registry if e["entity_id"] == "qwen3.6-27b"), None)
    assert model_entity is not None
    assert model_entity["operational_state"] == "inactive"


def test_build_active_entities_separates_rx9070():
    sensor = {
        "gpu_operational_summaries": [
            _make_gpu_summary("RX9070", active=True),
            _make_gpu_summary("RX7900XT", expected_offline=True),
        ]
    }
    active = build_active_entities(sensor_snapshot=sensor)
    active_ids = [e["entity_id"] for e in active]
    assert "RX9070" in active_ids
    assert "RX7900XT" not in active_ids


def test_build_inventory_entities_separates_rx7900xt():
    sensor = {
        "gpu_operational_summaries": [
            _make_gpu_summary("RX9070", active=True),
            _make_gpu_summary("RX7900XT", expected_offline=True),
        ]
    }
    inventory = build_inventory_entities(sensor_snapshot=sensor)
    inv_ids = [e["entity_id"] for e in inventory]
    assert "RX7900XT" in inv_ids
    assert "RX9070" not in inv_ids


def test_build_discoverable_entities():
    sensor = {"gpu_operational_summaries": [_make_gpu_summary("RX9070", active=True)]}
    discoverable = build_discoverable_entities(sensor_snapshot=sensor)
    discoverable_ids = [e["entity_id"] for e in discoverable]
    assert "RX9070" in discoverable_ids


def test_build_deprecated_entities():
    extra = {"models": {"discovered": [_make_model_entry("lmstudio-community/qwen2.5-coder-14b-instruct")]}}
    deprecated = build_deprecated_entities(extra_ctx=extra)
    deprecated_ids = [e["entity_id"] for e in deprecated]
    assert "lmstudio-community/qwen2.5-coder-14b-instruct" in deprecated_ids


def test_build_routability_summary():
    sensor = {
        "gpu_operational_summaries": [
            _make_gpu_summary("RX9070", active=True),
            _make_gpu_summary("RX7900XT", expected_offline=True),
        ]
    }
    summary = build_routability_summary(sensor_snapshot=sensor)
    rx9070 = next((s for s in summary if s["entity_id"] == "RX9070"), None)
    rx7900xt = next((s for s in summary if s["entity_id"] == "RX7900XT"), None)
    assert rx9070 is not None and rx9070["routable"] is True
    assert rx7900xt is not None and rx7900xt["routable"] is False


def test_build_topology_preparation():
    sensor = {
        "gpu_operational_summaries": [
            _make_gpu_summary("RX9070", active=True),
            _make_gpu_summary("RX7900XT", expected_offline=True),
        ]
    }
    extra = {"models": {"discovered": [_make_model_entry("lmstudio-community/qwen2.5-coder-14b-instruct")]}}
    topo = build_topology_preparation(sensor_snapshot=sensor, extra_ctx=extra)
    assert "topology_active" in topo
    assert "topology_inventory" in topo
    assert "topology_deprecated" in topo
    assert "topology_discoverable" in topo
    active_ids = [e["entity_id"] for e in topo["topology_active"]]
    inv_ids = [e["entity_id"] for e in topo["topology_inventory"]]
    deprecated_ids = [e["entity_id"] for e in topo["topology_deprecated"]]
    assert "RX9070" in active_ids
    assert "RX7900XT" in inv_ids
    assert "lmstudio-community/qwen2.5-coder-14b-instruct" in deprecated_ids


def test_detect_stale_entities():
    sensor = {"gpu_operational_summaries": [_make_gpu_summary("RX9070", active=True)]}
    stale = detect_stale_entities(sensor_snapshot=sensor)
    assert isinstance(stale, list)


def test_detect_inventory_only_entities():
    sensor = {
        "gpu_operational_summaries": [
            _make_gpu_summary("RX9070", active=True),
            _make_gpu_summary("RX7900XT", expected_offline=True),
        ]
    }
    inventory = detect_inventory_only_entities(sensor_snapshot=sensor)
    inv_ids = [e["entity_id"] for e in inventory]
    assert "RX7900XT" in inv_ids
    assert "RX9070" not in inv_ids


def test_detect_deprecated_entities():
    extra = {"models": {"discovered": [_make_model_entry("lmstudio-community/qwen2.5-coder-14b-instruct")]}}
    deprecated = detect_deprecated_entities(extra_ctx=extra)
    deprecated_ids = [e["entity_id"] for e in deprecated]
    assert "lmstudio-community/qwen2.5-coder-14b-instruct" in deprecated_ids


def test_gpu_active_and_inventory_not_mixed_rule_31e1():
    """RULE-31E-1: Inventory != active — RX7900XT is inventory, not active."""
    sensor = {
        "gpu_operational_summaries": [
            _make_gpu_summary("RX9070", active=True),
            _make_gpu_summary("RX7900XT", expected_offline=True),
        ]
    }
    registry = build_entity_registry(sensor_snapshot=sensor)
    rx9070 = next(e for e in registry if e["entity_id"] == "RX9070")
    rx7900xt = next(e for e in registry if e["entity_id"] == "RX7900XT")
    assert rx9070["operational_state"] == "active"
    assert rx7900xt["operational_state"] != "active"
    assert rx7900xt["inventory_state"] == "expected_offline"
    assert rx9070["routable"] is True
    assert rx7900xt["routable"] is False


def test_discoverable_not_operational_rule_31e2():
    """RULE-31E-2: Discoverable != operational — discovered model is not routable."""
    extra = {"models": {"discovered": [_make_model_entry("lmstudio-community/qwen2.5-coder-14b-instruct")]}}
    registry = build_entity_registry(extra_ctx=extra)
    model = next(e for e in registry if e["entity_id"] == "lmstudio-community/qwen2.5-coder-14b-instruct")
    assert model["deprecated"] is True
    assert model["routable"] is False
    assert model["operational_state"] != "active"


def test_expected_offline_not_degraded_rule_31e3():
    """RULE-31E-3: Expected_offline != degraded — RX7900XT is expected offline, not an error."""
    sensor = {"gpu_operational_summaries": [_make_gpu_summary("RX7900XT", expected_offline=True)]}
    registry = build_entity_registry(sensor_snapshot=sensor)
    gpu = next(e for e in registry if e["entity_id"] == "RX7900XT")
    assert gpu["inventory_state"] == "expected_offline"
    assert gpu["operational_state"] != "active"


def test_deprecated_does_not_contaminate_active_topology_rule_31e4():
    """RULE-31E-4: Deprecated entities must NOT contaminate active topology."""
    sensor = {"gpu_operational_summaries": [_make_gpu_summary("RX9070", active=True)]}
    extra = {"models": {"discovered": [_make_model_entry("lmstudio-community/qwen2.5-coder-14b-instruct")]}}
    topo = build_topology_preparation(sensor_snapshot=sensor, extra_ctx=extra)
    active_ids = [e["entity_id"] for e in topo["topology_active"]]
    deprecated_ids = [e["entity_id"] for e in topo["topology_deprecated"]]
    assert "lmstudio-community/qwen2.5-coder-14b-instruct" in deprecated_ids
    assert "lmstudio-community/qwen2.5-coder-14b-instruct" not in active_ids


def test_empty_sensor_returns_empty_registry():
    registry = build_entity_registry()
    assert registry == []


def test_empty_sensor_detection_functions_return_empty():
    assert detect_stale_entities() == []
    assert detect_inventory_only_entities() == []
    assert detect_deprecated_entities() == []


if __name__ == "__main__":
    tests = [
        name for name in dir() if name.startswith("test_")
    ]
    passed = 0
    failed = 0
    for name in tests:
        try:
            globals()[name]()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}: {e}")
            failed += 1
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
