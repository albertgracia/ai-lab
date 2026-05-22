from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

ENTITY_CONTRACT_VERSION = "31E"

ENTITY_STATES = frozenset({
    "active", "loaded", "discoverable", "inventory",
    "expected_offline", "unobserved", "stale", "disabled",
    "deprecated", "unavailable",
})

ENTITY_TYPES = frozenset({
    "gpu", "model", "host", "service", "storage", "topology_mode",
})


@dataclass
class EntityContract:
    entity_id: str = "unknown"
    entity_type: str = "unknown"
    inventory_state: str = "unobserved"
    observed_state: str = "unavailable"
    operational_state: str = "inactive"
    discoverability: str = "unknown"
    routable: bool = False
    deprecated: bool = False
    source_of_truth: list[str] = field(default_factory=list)
    confidence: str = "unknown"
    freshness: str = "unknown"
    timestamp: float = field(default_factory=time.time)
    contract_version: str = ENTITY_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "inventory_state": self.inventory_state,
            "observed_state": self.observed_state,
            "operational_state": self.operational_state,
            "discoverability": self.discoverability,
            "routable": self.routable,
            "deprecated": self.deprecated,
            "source_of_truth": list(self.source_of_truth),
            "confidence": self.confidence,
            "freshness": self.freshness,
            "contract_version": self.contract_version,
        }


@dataclass
class EntityStateContract:
    entity_id: str = "unknown"
    entity_type: str = "unknown"
    state: str = "unknown"
    sub_state: str = ""
    confidence: str = "unknown"
    freshness: str = "unknown"
    source_of_truth: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    contract_version: str = ENTITY_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "state": self.state,
            "sub_state": self.sub_state,
            "confidence": self.confidence,
            "freshness": self.freshness,
            "source_of_truth": list(self.source_of_truth),
            "contract_version": self.contract_version,
        }


@dataclass
class DiscoverabilityContract:
    entity_id: str = "unknown"
    entity_type: str = "unknown"
    discoverable: bool = False
    endpoint_responds: bool = False
    visible_in_inventory: bool = False
    inventory_valid: bool = False
    confidence: str = "unknown"
    source_of_truth: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    contract_version: str = ENTITY_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "discoverable": self.discoverable,
            "endpoint_responds": self.endpoint_responds,
            "visible_in_inventory": self.visible_in_inventory,
            "inventory_valid": self.inventory_valid,
            "confidence": self.confidence,
            "source_of_truth": list(self.source_of_truth),
            "contract_version": self.contract_version,
        }


@dataclass
class OperationalEntityContract:
    entity_id: str = "unknown"
    entity_type: str = "unknown"
    operational_state: str = "inactive"
    routable: bool = False
    loaded: bool = False
    active: bool = False
    capacity: str = "unknown"
    confidence: str = "unknown"
    freshness: str = "unknown"
    source_of_truth: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    contract_version: str = ENTITY_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "operational_state": self.operational_state,
            "routable": self.routable,
            "loaded": self.loaded,
            "active": self.active,
            "capacity": self.capacity,
            "confidence": self.confidence,
            "freshness": self.freshness,
            "source_of_truth": list(self.source_of_truth),
            "contract_version": self.contract_version,
        }


@dataclass
class InventoryEntityContract:
    entity_id: str = "unknown"
    entity_type: str = "unknown"
    inventory_state: str = "unobserved"
    historical: bool = False
    expected_offline: bool = False
    deprecated: bool = False
    confidence: str = "unknown"
    source_of_truth: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    contract_version: str = ENTITY_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "inventory_state": self.inventory_state,
            "historical": self.historical,
            "expected_offline": self.expected_offline,
            "deprecated": self.deprecated,
            "confidence": self.confidence,
            "source_of_truth": list(self.source_of_truth),
            "contract_version": self.contract_version,
        }


@dataclass
class RoutabilityContract:
    entity_id: str = "unknown"
    entity_type: str = "unknown"
    routable: bool = False
    routing_reason: str = ""
    primary_for: list[str] = field(default_factory=list)
    deprecation_reason: str = ""
    confidence: str = "unknown"
    source_of_truth: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    contract_version: str = ENTITY_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "routable": self.routable,
            "routing_reason": self.routing_reason,
            "primary_for": list(self.primary_for),
            "deprecation_reason": self.deprecation_reason,
            "confidence": self.confidence,
            "source_of_truth": list(self.source_of_truth),
            "contract_version": self.contract_version,
        }
