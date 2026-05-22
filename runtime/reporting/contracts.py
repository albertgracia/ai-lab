from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

REPORTING_CONTRACT_VERSION = "31C"

SEVERITIES = frozenset({"info", "notice", "warning", "degraded", "critical", "unknown", "expected_offline"})
OPERATIONAL_IMPACTS = frozenset({"none", "low", "moderate", "high", "critical"})
REPORT_MODES = frozenset({"compact", "operational", "technical", "executive", "governance"})
CONFIDENCE_LEVELS = frozenset({"high", "medium", "low"})


@dataclass
class OperationalReportContract:
    runtime_state: str = "unknown"
    confidence: str = "unknown"
    maturity_score: float = 0.0
    uncertainty_level: str = "unknown"
    operational_impact: str = "none"
    degraded_domains: list[str] = field(default_factory=list)
    unknown_domains: list[str] = field(default_factory=list)
    degradation_reason: list[str] = field(default_factory=list)
    freshness: str = "unknown"
    topology_mode: str = "unknown"
    timestamp: float = field(default_factory=time.time)
    contract_version: str = REPORTING_CONTRACT_VERSION
    mode: str = "compact"

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "timestamp": self.timestamp,
            "runtime_state": self.runtime_state,
            "confidence": self.confidence,
            "maturity_score": round(self.maturity_score, 2),
            "uncertainty_level": self.uncertainty_level,
            "operational_impact": self.operational_impact,
            "degraded_domains": list(self.degraded_domains),
            "unknown_domains": list(self.unknown_domains),
            "degradation_reason": list(self.degradation_reason),
            "freshness": self.freshness,
            "topology_mode": self.topology_mode,
            "mode": self.mode,
        }


@dataclass
class OperationalSummaryContract:
    overall_state: str = "unknown"
    active_gpus: int = 0
    inventory_gpus: int = 0
    degraded_domains: list[str] = field(default_factory=list)
    unknown_domains: list[str] = field(default_factory=list)
    expected_offline: list[str] = field(default_factory=list)
    unexpected_down: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    confidence: str = "unknown"
    freshness: str = "unknown"
    timestamp: float = field(default_factory=time.time)
    contract_version: str = REPORTING_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "timestamp": self.timestamp,
            "overall_state": self.overall_state,
            "active_gpus": self.active_gpus,
            "inventory_gpus": self.inventory_gpus,
            "degraded_domains": list(self.degraded_domains),
            "unknown_domains": list(self.unknown_domains),
            "expected_offline": list(self.expected_offline),
            "unexpected_down": list(self.unexpected_down),
            "risks": list(self.risks),
            "recommendations": list(self.recommendations),
            "confidence": self.confidence,
            "freshness": self.freshness,
        }


@dataclass
class GovernanceReportContract:
    governance_level: str = "unknown"
    blocked_actions: int = 0
    blocked_by_reason: dict[str, int] = field(default_factory=dict)
    evidence_guard_active: bool = False
    governance_issues: list[str] = field(default_factory=list)
    confidence: str = "unknown"
    freshness: str = "unknown"
    timestamp: float = field(default_factory=time.time)
    contract_version: str = REPORTING_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "timestamp": self.timestamp,
            "governance_level": self.governance_level,
            "blocked_actions": self.blocked_actions,
            "blocked_by_reason": dict(self.blocked_by_reason),
            "evidence_guard_active": self.evidence_guard_active,
            "governance_issues": list(self.governance_issues),
            "confidence": self.confidence,
            "freshness": self.freshness,
        }


@dataclass
class RuntimeHealthContract:
    runtime_state: str = "unknown"
    topology_mode: str = "unknown"
    active_backends: int = 0
    offline_backends: int = 0
    degraded_domains: list[str] = field(default_factory=list)
    confidence: str = "unknown"
    freshness: str = "unknown"
    timestamp: float = field(default_factory=time.time)
    contract_version: str = REPORTING_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "timestamp": self.timestamp,
            "runtime_state": self.runtime_state,
            "topology_mode": self.topology_mode,
            "active_backends": self.active_backends,
            "offline_backends": self.offline_backends,
            "degraded_domains": list(self.degraded_domains),
            "confidence": self.confidence,
            "freshness": self.freshness,
        }


@dataclass
class DomainHealthContract:
    domain: str = "unknown"
    state: str = "unknown"
    confidence: str = "unknown"
    freshness: str = "unknown"
    sources: list[str] = field(default_factory=list)
    operational_impact: str = "none"
    issues: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    contract_version: str = REPORTING_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "timestamp": self.timestamp,
            "domain": self.domain,
            "state": self.state,
            "confidence": self.confidence,
            "freshness": self.freshness,
            "sources": list(self.sources),
            "operational_impact": self.operational_impact,
            "issues": list(self.issues),
        }


@dataclass
class OperatorExplainabilityContract:
    degradation_summary: str = "informacion insuficiente"
    missing_evidence: list[str] = field(default_factory=list)
    affected_domains: list[str] = field(default_factory=list)
    confidence_breakdown: dict[str, str] = field(default_factory=dict)
    uncertainty_notes: list[str] = field(default_factory=list)
    valid_recommendations: list[str] = field(default_factory=list)
    stale_observability: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    contract_version: str = REPORTING_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "timestamp": self.timestamp,
            "degradation_summary": self.degradation_summary,
            "missing_evidence": list(self.missing_evidence),
            "affected_domains": list(self.affected_domains),
            "confidence_breakdown": dict(self.confidence_breakdown),
            "uncertainty_notes": list(self.uncertainty_notes),
            "valid_recommendations": list(self.valid_recommendations),
            "stale_observability": list(self.stale_observability),
        }


@dataclass
class ExecutiveSummaryContract:
    title: str = "AI-LAB Runtime Status"
    overall_state: str = "unknown"
    active_backends: int = 0
    degraded_domains: list[str] = field(default_factory=list)
    critical_issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    confidence: str = "unknown"
    freshness: str = "unknown"
    timestamp: float = field(default_factory=time.time)
    contract_version: str = REPORTING_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "timestamp": self.timestamp,
            "title": self.title,
            "overall_state": self.overall_state,
            "active_backends": self.active_backends,
            "degraded_domains": list(self.degraded_domains),
            "critical_issues": list(self.critical_issues),
            "recommendations": list(self.recommendations),
            "confidence": self.confidence,
            "freshness": self.freshness,
        }


@dataclass
class DegradationReportContract:
    degradation_level: str = "none"
    degraded_domains: list[str] = field(default_factory=list)
    degradation_reasons: list[str] = field(default_factory=list)
    operational_impact: str = "none"
    affected_services: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    confidence: str = "unknown"
    freshness: str = "unknown"
    timestamp: float = field(default_factory=time.time)
    contract_version: str = REPORTING_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "timestamp": self.timestamp,
            "degradation_level": self.degradation_level,
            "degraded_domains": list(self.degraded_domains),
            "degradation_reasons": list(self.degradation_reasons),
            "operational_impact": self.operational_impact,
            "affected_services": list(self.affected_services),
            "recommended_actions": list(self.recommended_actions),
            "confidence": self.confidence,
            "freshness": self.freshness,
        }
