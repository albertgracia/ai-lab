from __future__ import annotations

from dataclasses import dataclass
from typing import Any


INFRASTRUCTURE_CONTRACT_VERSION = "35A"


@dataclass(frozen=True)
class InfrastructureRole:
    role: str
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"role": self.role, "description": self.description}


@dataclass(frozen=True)
class AuthorityRoot:
    identity: str  # IP/hostname
    roles: list[str]
    criticality: str  # critical/high/medium/low
    authority_type: str  # operational/observability/visualization/control
    source_of_truth: str
    expected_offline: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "roles": list(self.roles or []),
            "criticality": self.criticality,
            "authority_type": self.authority_type,
            "source_of_truth": self.source_of_truth,
            "expected_offline": bool(self.expected_offline),
        }


@dataclass(frozen=True)
class OperationalNode:
    identity: str  # IP/hostname
    roles: list[str]
    operational_state: str  # operational/inventory_only/discoverable/unknown
    expected_offline: bool = False
    routable: bool = False
    notes: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "roles": list(self.roles or []),
            "operational_state": self.operational_state,
            "expected_offline": bool(self.expected_offline),
            "routable": bool(self.routable),
            "notes": list(self.notes or []),
        }


@dataclass(frozen=True)
class InfrastructureDependency:
    source: str
    depends_on: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "depends_on": self.depends_on, "reason": self.reason}


@dataclass(frozen=True)
class InfrastructureAuthorityMap:
    authority_roots: list[dict[str, Any]]
    dependencies: list[dict[str, Any]]
    contract_version: str = INFRASTRUCTURE_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "authority_roots": list(self.authority_roots or []),
            "dependencies": list(self.dependencies or []),
        }


@dataclass(frozen=True)
class InfrastructureInventory:
    operational_nodes: list[dict[str, Any]]
    inventory_only_nodes: list[dict[str, Any]]
    discoverable_nodes: list[dict[str, Any]]
    legacy_nodes: list[dict[str, Any]]
    unknown_nodes: list[str]
    contract_version: str = INFRASTRUCTURE_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "operational_nodes": list(self.operational_nodes or []),
            "inventory_only_nodes": list(self.inventory_only_nodes or []),
            "discoverable_nodes": list(self.discoverable_nodes or []),
            "legacy_nodes": list(self.legacy_nodes or []),
            "unknown_nodes": list(self.unknown_nodes or []),
        }


@dataclass(frozen=True)
class InfrastructureSemanticSummary:
    contract_version: str
    identity: str
    roles: list[str]
    summary: str
    authority_root: bool
    expected_offline: bool
    operational_state: str
    deterministic_signature: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "identity": self.identity,
            "roles": list(self.roles or []),
            "summary": self.summary,
            "authority_root": bool(self.authority_root),
            "expected_offline": bool(self.expected_offline),
            "operational_state": self.operational_state,
            "deterministic_signature": self.deterministic_signature,
        }


@dataclass(frozen=True)
class InfrastructureIdentity:
    contract_version: str
    registry_version: str
    authority_map: dict[str, Any]
    inventory: dict[str, Any]
    control_plane: list[str]
    authority_roots: list[str]
    score: float
    issues: list[str]
    generated_at: float
    deterministic_signature: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "registry_version": self.registry_version,
            "authority_map": self.authority_map,
            "inventory": self.inventory,
            "control_plane": list(self.control_plane or []),
            "authority_roots": list(self.authority_roots or []),
            "score": float(self.score),
            "issues": list(self.issues or []),
            "generated_at": float(self.generated_at),
            "deterministic_signature": self.deterministic_signature,
        }
