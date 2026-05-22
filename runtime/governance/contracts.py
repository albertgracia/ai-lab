from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any


GOVERNANCE_CONTRACT_VERSION = "33A"


@dataclass
class GovernanceRegistryContract:
    governance_score: float
    governance_level: str
    degraded_domains: list[str]
    risks: list[dict[str, Any]]
    authority_map: dict[str, Any]
    confidence_map: dict[str, Any]
    contract_registry: dict[str, Any]
    remediation: dict[str, Any]
    health_summary: dict[str, Any]
    freshness: str
    contract_version: str = GOVERNANCE_CONTRACT_VERSION
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GovernanceDomainContract:
    domain: str
    operational_state: str
    confidence: str
    authority: str
    source_of_truth: str
    freshness: str
    degraded: bool = False
    explainable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GovernanceAuthorityContract:
    domain: str
    authority_type: str
    source_of_truth: str
    confidence: str
    freshness: str
    valid: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GovernanceConfidenceContract:
    domain: str
    confidence: str
    freshness: str
    propagated_from: list[str] = field(default_factory=list)
    degraded: bool = False
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GovernanceRiskContract:
    risk_type: str
    severity: str
    domain: str
    description: str
    confidence: str
    explainable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GovernanceRemediationContract:
    phase: str
    domain: str
    status: str
    severity: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GovernanceHealthContract:
    operational_state: str
    governance_level: str
    degraded_domains: list[str]
    risks_total: int
    remediation_pending: int
    stale_authority: list[str]
    confidence: str
    freshness: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GovernanceContractRegistry:
    registered_phases: list[dict[str, Any]]
    active_contracts: list[str]
    deprecated_contracts: list[str]
    incompatible_contracts: list[str]
    stale_contracts: list[str]
    total_contracts: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
