from __future__ import annotations

import time
from typing import Any

from runtime.entities.contracts import (
    ENTITY_CONTRACT_VERSION,
    EntityContract,
    EntityStateContract,
    OperationalEntityContract,
    InventoryEntityContract,
    RoutabilityContract,
    DiscoverabilityContract,
)


def _ensure_list(val: Any) -> list:
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [val]
    return []


# ── State classification ───────────────────────────────────────────

def classify_entity_state(
    inventory_state: str | None,
    observed_state: str | None,
    operational_state: str | None,
    *,
    inventory_expected_offline: bool = False,
    deprecated: bool = False,
    disabled: bool = False,
) -> str:
    if deprecated:
        return "deprecated"
    if disabled:
        return "disabled"
    if inventory_expected_offline or inventory_state == "expected_offline":
        return "expected_offline"
    if operational_state == "active":
        return "active"
    if observed_state == "online" and operational_state == "idle":
        return "loaded"
    if inventory_state == "inventory" and not observed_state:
        return "inventory"
    if observed_state == "online":
        return "discoverable"
    if observed_state in ("unavailable", "down"):
        return "unavailable"
    if observed_state is None and inventory_state is None:
        return "unobserved"
    return "unknown"


def classify_operational_state(
    observed_state: str | None,
    *,
    has_recent_traffic: bool = False,
    is_loaded_in_backend: bool = False,
    expected_offline: bool = False,
) -> str:
    if expected_offline:
        return "inactive"
    if has_recent_traffic and observed_state == "online":
        return "active"
    if is_loaded_in_backend and observed_state == "online":
        return "loaded"
    if observed_state == "online":
        return "idle"
    if observed_state in ("unavailable", "down"):
        return "down"
    return "inactive"


def classify_discoverability(
    *,
    endpoint_responds: bool = False,
    visible_in_inventory: bool = False,
    observed_state: str | None = None,
) -> str:
    if endpoint_responds:
        return "discoverable"
    if observed_state == "online":
        return "discoverable"
    if visible_in_inventory:
        return "inventory_visible"
    return "undiscovered"


def classify_routability(
    entity_type: str,
    entity_id: str,
    *,
    deprecated: bool = False,
    disabled: bool = False,
    operational_state: str | None = None,
    expected_offline: bool = False,
) -> tuple[bool, str]:
    if deprecated:
        return False, "deprecated"
    if disabled:
        return False, "disabled"
    if expected_offline:
        return False, "expected_offline"
    if operational_state == "active":
        return True, "operational"
    if operational_state == "loaded":
        return True, "loaded_available"
    if operational_state == "idle":
        return True, "idle_available"
    return False, "not_available"


# ── Entity registry builder ────────────────────────────────────────

def build_entity_registry(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    registry: list[dict[str, Any]] = []
    if not sensor_snapshot and not extra_ctx:
        return registry

    gpu_summaries = []
    if sensor_snapshot:
        gpu_summaries = sensor_snapshot.get("gpu_operational_summaries", []) or []
    elif extra_ctx:
        gpu_summaries = extra_ctx.get("gpu_operational_summaries", []) or []

    for gpu in gpu_summaries:
        if not isinstance(gpu, dict):
            continue
        gpu_id = gpu.get("gpu_id", gpu.get("name", "?"))
        observed_state = gpu.get("observed_state", "unavailable")
        operational_state = gpu.get("operational_state", "inactive")
        inv_expected = gpu.get("inventory_expected_offline", False)
        confidence = gpu.get("confidence", "low")
        freshness = gpu.get("freshness", {})
        freshness_status = freshness.get("status", "unknown") if isinstance(freshness, dict) else "unknown"
        sources = gpu.get("source_of_truth", ["inventory"])

        entity = EntityContract(
            entity_id=gpu_id,
            entity_type="gpu",
            inventory_state="expected_offline" if inv_expected else "inventory",
            observed_state=observed_state,
            operational_state=operational_state,
            discoverability=classify_discoverability(
                visible_in_inventory=True,
                observed_state=observed_state,
            ),
            routable=operational_state == "active",
            deprecated=False,
            source_of_truth=sources,
            confidence=confidence,
            freshness=freshness_status,
        )

        registry.append(entity.to_dict())

    gpu_ids = {e["entity_id"] for e in registry}

    models_data = {}
    if extra_ctx:
        models_data = extra_ctx.get("models", {}) or {}
    if not models_data and sensor_snapshot:
        models_data = sensor_snapshot.get("models", {}) or {}

    seen_model_ids: set[str] = set()
    for model_group_key in ("active", "loaded", "disabled", "discovered"):
        for model in models_data.get(model_group_key, []):
            if not isinstance(model, dict):
                continue
            model_id = model.get("id", model.get("name", "?"))
            if model_id in seen_model_ids:
                continue
            seen_model_ids.add(model_id)

            model_deprecated = model_group_key == "discovered" or bool(model.get("deprecated"))
            model_disabled = model_group_key == "disabled" or bool(model.get("disabled"))
            exp_offline = bool(model.get("expected_offline"))
            is_active = model_group_key == "active" and not model_deprecated and not model_disabled

            entity = EntityContract(
                entity_id=model_id,
                entity_type="model",
                inventory_state=model_group_key,
                observed_state="online" if is_active else "inventory",
                operational_state="active" if is_active else "inactive",
                discoverability="discoverable" if is_active else "inventory_visible",
                routable=is_active and not model_deprecated,
                deprecated=model_deprecated,
                source_of_truth=["inventory", "code"],
                confidence="high",
                freshness="fresh",
            )
            registry.append(entity.to_dict())

    return registry


# ── Detection functions ────────────────────────────────────────────

def detect_stale_entities(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    stale: list[dict[str, Any]] = []
    registry = build_entity_registry(sensor_snapshot, extra_ctx)
    for entity in registry:
        if entity.get("freshness") in ("stale", "expired", "unavailable"):
            stale.append({
                "entity_id": entity["entity_id"],
                "entity_type": entity["entity_type"],
                "freshness": entity["freshness"],
                "confidence": entity["confidence"],
                "reason": f"freshness is {entity['freshness']}",
            })
    stale_sources = []
    if sensor_snapshot:
        stale_sources = sensor_snapshot.get("stale_sources", []) or []
    elif extra_ctx:
        stale_sources = extra_ctx.get("stale_sources", []) or []
    for src in stale_sources:
        if not any(s.get("entity_id") == str(src) for s in stale):
            stale.append({
                "entity_id": str(src),
                "entity_type": "domain",
                "freshness": "stale",
                "confidence": "low",
                "reason": "listed as stale source",
            })
    return stale


def detect_inventory_only_entities(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    registry = build_entity_registry(sensor_snapshot, extra_ctx)
    for entity in registry:
        etype = entity.get("entity_type", "")
        istate = entity.get("inventory_state", "")
        routable = entity.get("routable", False)
        if istate in ("inventory", "expected_offline") and not routable:
            inventory.append({
                "entity_id": entity["entity_id"],
                "entity_type": etype,
                "inventory_state": istate,
                "reason": "inventory only, not routable",
            })
    return inventory


def detect_deprecated_entities(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    deprecated: list[dict[str, Any]] = []
    registry = build_entity_registry(sensor_snapshot, extra_ctx)
    for entity in registry:
        if entity.get("deprecated"):
            deprecated.append({
                "entity_id": entity["entity_id"],
                "entity_type": entity["entity_type"],
                "reason": "marked as deprecated",
                "routable": entity.get("routable", False),
            })
    return deprecated


def build_active_entities(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    registry = build_entity_registry(sensor_snapshot, extra_ctx)
    return [e for e in registry if e.get("operational_state") == "active"]


def build_inventory_entities(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    registry = build_entity_registry(sensor_snapshot, extra_ctx)
    return [
        e for e in registry
        if e.get("inventory_state") in ("inventory", "expected_offline")
        and e.get("operational_state") != "active"
    ]


def build_discoverable_entities(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    registry = build_entity_registry(sensor_snapshot, extra_ctx)
    return [
        e for e in registry
        if e.get("discoverability") == "discoverable"
    ]


def build_deprecated_entities(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    registry = build_entity_registry(sensor_snapshot, extra_ctx)
    return [e for e in registry if e.get("deprecated")]


def build_routability_summary(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    registry = build_entity_registry(sensor_snapshot, extra_ctx)
    return [
        {
            "entity_id": e["entity_id"],
            "entity_type": e["entity_type"],
            "routable": e["routable"],
            "operational_state": e["operational_state"],
            "deprecated": e["deprecated"],
            "confidence": e.get("confidence", "unknown"),
        }
        for e in registry
    ]


def build_topology_preparation(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = build_entity_registry(sensor_snapshot, extra_ctx)
    return {
        "topology_active": [e for e in registry if e["operational_state"] == "active"],
        "topology_inventory": [
            e for e in registry
            if e["inventory_state"] in ("inventory", "expected_offline")
            and e["operational_state"] != "active"
        ],
        "topology_deprecated": [e for e in registry if e.get("deprecated")],
        "topology_discoverable": [
            e for e in registry
            if e["discoverability"] == "discoverable"
            and e["operational_state"] != "active"
        ],
    }
