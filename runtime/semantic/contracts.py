from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SEMANTIC_CONTRACT_VERSION = "35B"


@dataclass(frozen=True)
class SemanticIdentity:
    identity: str
    identity_type: str  # ip/model/gpu/unknown

    def to_dict(self) -> dict[str, Any]:
        return {"identity": self.identity, "identity_type": self.identity_type}


@dataclass(frozen=True)
class SemanticClassification:
    identity: str
    semantic_state: str
    roles: list[str]
    authority: bool
    operational: bool
    routable: bool
    expected_offline: bool
    legacy: bool
    phantom: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "semantic_state": self.semantic_state,
            "roles": list(self.roles or []),
            "authority": bool(self.authority),
            "operational": bool(self.operational),
            "routable": bool(self.routable),
            "expected_offline": bool(self.expected_offline),
            "legacy": bool(self.legacy),
            "phantom": bool(self.phantom),
        }


@dataclass(frozen=True)
class LegacyEntity:
    identity: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"identity": self.identity, "reason": self.reason}


@dataclass(frozen=True)
class PhantomEntity:
    identity: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"identity": self.identity, "reason": self.reason}


@dataclass(frozen=True)
class SemanticContamination:
    contamination_type: str
    total: int
    examples: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contamination_type": self.contamination_type,
            "total": int(self.total),
            "examples": list(self.examples or []),
        }


@dataclass(frozen=True)
class OperationalTruth:
    contract_version: str
    authority_roots: list[str]
    operational_nodes: list[str]
    inventory_only_nodes: list[str]
    discoverable_nodes: list[str]
    classifications: list[dict[str, Any]]
    deterministic_signature: str
    generated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "authority_roots": list(self.authority_roots or []),
            "operational_nodes": list(self.operational_nodes or []),
            "inventory_only_nodes": list(self.inventory_only_nodes or []),
            "discoverable_nodes": list(self.discoverable_nodes or []),
            "classifications": list(self.classifications or []),
            "deterministic_signature": self.deterministic_signature,
            "generated_at": float(self.generated_at),
        }


@dataclass(frozen=True)
class SemanticSterilizationResult:
    contract_version: str
    operational_truth: dict[str, Any]
    legacy_entities: list[dict[str, Any]]
    phantom_entities: list[dict[str, Any]]
    contaminations: list[dict[str, Any]]
    deterministic_signature: str
    generated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "operational_truth": self.operational_truth,
            "legacy_entities": list(self.legacy_entities or []),
            "phantom_entities": list(self.phantom_entities or []),
            "contaminations": list(self.contaminations or []),
            "deterministic_signature": self.deterministic_signature,
            "generated_at": float(self.generated_at),
        }


@dataclass(frozen=True)
class SemanticIntegrityReport:
    contract_version: str
    semantic_integrity_score: float
    semantic_integrity_level: str
    phantom_entities_total: int
    legacy_leakage_total: int
    discoverable_contamination_total: int
    inventory_contamination_total: int
    unknown_operational_entities_total: int
    sterilized_operational_nodes_total: int
    issues: list[str]
    deterministic_signature: str
    generated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "semantic_integrity_score": float(self.semantic_integrity_score),
            "semantic_integrity_level": self.semantic_integrity_level,
            "phantom_entities_total": int(self.phantom_entities_total),
            "legacy_leakage_total": int(self.legacy_leakage_total),
            "discoverable_contamination_total": int(self.discoverable_contamination_total),
            "inventory_contamination_total": int(self.inventory_contamination_total),
            "unknown_operational_entities_total": int(self.unknown_operational_entities_total),
            "sterilized_operational_nodes_total": int(self.sterilized_operational_nodes_total),
            "issues": list(self.issues or []),
            "deterministic_signature": self.deterministic_signature,
            "generated_at": float(self.generated_at),
        }


@dataclass(frozen=True)
class IdentityHygieneSummary:
    contract_version: str
    authority_roots_ok: bool
    legacy_leakage_ok: bool
    phantom_ok: bool
    strict_state_separation_ok: bool
    issues: list[str]
    deterministic_signature: str
    generated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "authority_roots_ok": bool(self.authority_roots_ok),
            "legacy_leakage_ok": bool(self.legacy_leakage_ok),
            "phantom_ok": bool(self.phantom_ok),
            "strict_state_separation_ok": bool(self.strict_state_separation_ok),
            "issues": list(self.issues or []),
            "deterministic_signature": self.deterministic_signature,
            "generated_at": float(self.generated_at),
        }
