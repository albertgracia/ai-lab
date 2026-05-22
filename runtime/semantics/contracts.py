"""FASE 31B: Runtime Semantic Maturity Contracts.

Defines contracts for runtime maturity assessment, degradation tracking,
confidence propagation, uncertainty semantics, and operational impact.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

SEMANTICS_CONTRACT_VERSION = "31B"

RUNTIME_STATES = frozenset({
    "healthy", "healthy_degraded", "degraded", "critical", "unknown",
    "partially_observed", "inventory_only", "stale", "expected_offline",
})

CONFIDENCE_LEVELS = frozenset({"high", "medium", "low", "unknown"})

UNCERTAINTY_TYPES = frozenset({
    "low_confidence", "mixed_confidence", "unknown_state",
    "stale_evidence", "partially_observed", "degraded_observability",
})

OPERATIONAL_IMPACTS = frozenset({
    "none", "low", "medium", "high", "critical",
})

DEGRADED_DOMAINS = frozenset({
    "gpu", "routing", "observability", "storage", "governance",
    "telemetry", "services", "grounding",
})


@dataclass
class RuntimeMaturityContract:
    runtime_state: str = "unknown"
    maturity_score: float = 0.0
    confidence: str = "unknown"
    freshness: str = "unknown"
    degraded_domains: list[str] = field(default_factory=list)
    unknown_domains: list[str] = field(default_factory=list)
    domain_states: dict[str, str] = field(default_factory=dict)
    uncertainty_level: str = "unknown"
    operational_impact: str = "unknown"
    degradation_reason: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    contract_version: str = SEMANTICS_CONTRACT_VERSION
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "timestamp": self.timestamp,
            "runtime_state": self.runtime_state,
            "maturity_score": round(self.maturity_score, 2),
            "confidence": self.confidence,
            "freshness": self.freshness,
            "degraded_domains": self.degraded_domains,
            "unknown_domains": self.unknown_domains,
            "domain_states": self.domain_states,
            "uncertainty_level": self.uncertainty_level,
            "operational_impact": self.operational_impact,
            "degradation_reason": self.degradation_reason,
            "recommended_actions": self.recommended_actions,
        }


@dataclass
class DegradationContract:
    domain: str = ""
    previous_state: str = "healthy"
    current_state: str = "healthy"
    reason: list[str] = field(default_factory=list)
    confidence_before: str = "high"
    confidence_after: str = "high"
    affected_subdomains: list[str] = field(default_factory=list)
    reversible: bool = True
    contract_version: str = SEMANTICS_CONTRACT_VERSION
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "timestamp": self.timestamp,
            "domain": self.domain,
            "previous_state": self.previous_state,
            "current_state": self.current_state,
            "reason": self.reason,
            "confidence_before": self.confidence_before,
            "confidence_after": self.confidence_after,
            "affected_subdomains": self.affected_subdomains,
            "reversible": self.reversible,
        }


@dataclass
class ConfidenceContract:
    domain: str = ""
    base_confidence: str = "high"
    freshness: str = "fresh"
    stale_sources: int = 0
    missing_sources: int = 0
    expected_offline: int = 0
    effective_confidence: str = "high"
    degradation_applied: bool = False
    reason: list[str] = field(default_factory=list)
    contract_version: str = SEMANTICS_CONTRACT_VERSION
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "timestamp": self.timestamp,
            "domain": self.domain,
            "base_confidence": self.base_confidence,
            "freshness": self.freshness,
            "stale_sources": self.stale_sources,
            "missing_sources": self.missing_sources,
            "expected_offline": self.expected_offline,
            "effective_confidence": self.effective_confidence,
            "degradation_applied": self.degradation_applied,
            "reason": self.reason,
        }


@dataclass
class UncertaintyContract:
    uncertainty_type: str = ""
    domain: str = ""
    description: str = ""
    severity: str = "info"
    evidence: list[str] = field(default_factory=list)
    operational_impact: str = "none"
    contract_version: str = SEMANTICS_CONTRACT_VERSION
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "timestamp": self.timestamp,
            "uncertainty_type": self.uncertainty_type,
            "domain": self.domain,
            "description": self.description,
            "severity": self.severity,
            "evidence": self.evidence,
            "operational_impact": self.operational_impact,
        }


@dataclass
class OperationalImpactContract:
    impact_level: str = "none"
    runtime_state: str = "healthy"
    confidence: str = "high"
    affected_operations: list[str] = field(default_factory=list)
    requires_attention: bool = False
    recommended_action: str = ""
    contract_version: str = SEMANTICS_CONTRACT_VERSION
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "timestamp": self.timestamp,
            "impact_level": self.impact_level,
            "runtime_state": self.runtime_state,
            "confidence": self.confidence,
            "affected_operations": self.affected_operations,
            "requires_attention": self.requires_attention,
            "recommended_action": self.recommended_action,
        }


def _filter_fields(cls: type, overrides: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in overrides.items() if k in cls.__dataclass_fields__}


def build_maturity_contract(**overrides: Any) -> dict[str, Any]:
    c = RuntimeMaturityContract(**_filter_fields(RuntimeMaturityContract, overrides))
    return c.to_dict()


def build_degradation_contract(**overrides: Any) -> dict[str, Any]:
    c = DegradationContract(**_filter_fields(DegradationContract, overrides))
    return c.to_dict()


def build_confidence_contract(**overrides: Any) -> dict[str, Any]:
    c = ConfidenceContract(**_filter_fields(ConfidenceContract, overrides))
    return c.to_dict()


def build_uncertainty_contract(**overrides: Any) -> dict[str, Any]:
    c = UncertaintyContract(**_filter_fields(UncertaintyContract, overrides))
    return c.to_dict()


def build_operational_impact_contract(**overrides: Any) -> dict[str, Any]:
    c = OperationalImpactContract(**_filter_fields(OperationalImpactContract, overrides))
    return c.to_dict()
