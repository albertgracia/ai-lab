from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

TOPOLOGY_CONTRACT_VERSION = "31D"

TOPOLOGY_NODE_TYPES = frozenset({
    "runtime", "gpu", "model", "service", "exporter", "datasource",
    "storage", "gateway", "router", "observability", "governance",
    "inventory", "deprecated",
})


@dataclass
class TopologyNodeContract:
    node_id: str = "unknown"
    node_type: str = "unknown"
    operational_state: str = "inactive"
    active: bool = False
    discoverable: bool = False
    routable: bool = False
    confidence: str = "unknown"
    freshness: str = "unknown"
    authority: str = "none"
    inventory_only: bool = False
    entity_ref: str = ""
    timestamp: float = field(default_factory=time.time)
    contract_version: str = TOPOLOGY_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "operational_state": self.operational_state,
            "active": self.active,
            "discoverable": self.discoverable,
            "routable": self.routable,
            "confidence": self.confidence,
            "freshness": self.freshness,
            "authority": self.authority,
            "inventory_only": self.inventory_only,
            "entity_ref": self.entity_ref,
            "contract_version": self.contract_version,
        }


@dataclass
class TopologyEdgeContract:
    source_id: str = ""
    target_id: str = ""
    relationship: str = "unknown"
    direction: str = "forward"
    observed: bool = False
    confidence: str = "unknown"
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    contract_version: str = TOPOLOGY_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship": self.relationship,
            "direction": self.direction,
            "observed": self.observed,
            "confidence": self.confidence,
            "weight": self.weight,
            "metadata": dict(self.metadata),
            "contract_version": self.contract_version,
        }


@dataclass
class TopologyGraphContract:
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    degraded_paths: list[dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    contract_version: str = TOPOLOGY_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": list(self.nodes),
            "edges": list(self.edges),
            "degraded_paths": list(self.degraded_paths),
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "contract_version": self.contract_version,
        }


@dataclass
class DependencyContract:
    dependency_id: str = ""
    dependent: str = ""
    dependency: str = ""
    relationship_type: str = "requires"
    critical: bool = False
    observed: bool = False
    confidence: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    contract_version: str = TOPOLOGY_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "dependency_id": self.dependency_id,
            "dependent": self.dependent,
            "dependency": self.dependency,
            "relationship_type": self.relationship_type,
            "critical": self.critical,
            "observed": self.observed,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
            "contract_version": self.contract_version,
        }


@dataclass
class AuthorityChainContract:
    chain_id: str = ""
    source: str = ""
    target: str = ""
    authority_type: str = "derived"
    observed: bool = False
    confidence: str = "unknown"
    hops: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    contract_version: str = TOPOLOGY_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "source": self.source,
            "target": self.target,
            "authority_type": self.authority_type,
            "observed": self.observed,
            "confidence": self.confidence,
            "hops": list(self.hops),
            "metadata": dict(self.metadata),
            "contract_version": self.contract_version,
        }


@dataclass
class BlastRadiusContract:
    event_id: str = ""
    event_type: str = "degradation"
    source_node: str = ""
    source_type: str = "unknown"
    severity: str = "low"
    affected_nodes: list[str] = field(default_factory=list)
    affected_domains: list[str] = field(default_factory=list)
    impact_score: float = 0.0
    confidence: str = "unknown"
    propagation_path: list[dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    contract_version: str = TOPOLOGY_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source_node": self.source_node,
            "source_type": self.source_type,
            "severity": self.severity,
            "affected_nodes": list(self.affected_nodes),
            "affected_domains": list(self.affected_domains),
            "impact_score": self.impact_score,
            "confidence": self.confidence,
            "propagation_path": list(self.propagation_path),
            "contract_version": self.contract_version,
        }


@dataclass
class TopologyConfidenceContract:
    overall_score: float = 0.0
    observed_edges: int = 0
    total_edges: int = 0
    stale_entities: int = 0
    total_entities: int = 0
    inventory_only: int = 0
    degraded_observability: int = 0
    authority_valid: bool = False
    factors: dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    contract_version: str = TOPOLOGY_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "observed_edges": self.observed_edges,
            "total_edges": self.total_edges,
            "stale_entities": self.stale_entities,
            "total_entities": self.total_entities,
            "inventory_only": self.inventory_only,
            "degraded_observability": self.degraded_observability,
            "authority_valid": self.authority_valid,
            "factors": dict(self.factors),
            "contract_version": self.contract_version,
        }
