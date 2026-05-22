"""FASE OBS-31A.4: Observability Remediation Plan Contracts.

Defines dataclasses and enums for remediation planning:
- RemediationItem: individual remediation action
- RemediationPlan: full plan with grouped items
- RemediationSummary: summary statistics
- RemediationRisk: risk classification
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

REMEDIATION_CONTRACT_VERSION = "OBS-31A.4"


class RemediationSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class ProblemClass(str, Enum):
    RUNTIME_BLOCKING = "runtime_blocking"
    OBSERVABILITY_BLOCKING = "observability_blocking"
    COSMETIC = "cosmetic"
    LEGACY = "legacy"
    EXPECTED_OFFLINE = "expected_offline"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"
    TECHNICAL_DEBT = "technical_debt"


class RemediationPhase(str, Enum):
    PHASE_1 = "phase_1_safe_quick_wins"
    PHASE_2 = "phase_2_runtime_alignment"
    PHASE_3 = "phase_3_dashboard_modernization"
    PHASE_4 = "phase_4_legacy_cleanup"
    PHASE_5 = "phase_5_governance_hardening"


@dataclass
class RemediationRisk:
    severity: str = "low"
    runtime_impact: str = "none"
    operational_risk: str = "low"
    change_risk: str = "low"
    reversible: bool = True
    requires_restart: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "runtime_impact": self.runtime_impact,
            "operational_risk": self.operational_risk,
            "change_risk": self.change_risk,
            "reversible": self.reversible,
            "requires_restart": self.requires_restart,
        }


@dataclass
class RemediationItem:
    uid: str = ""
    title: str = ""
    description: str = ""
    domain: str = ""
    problem_class: str = "technical_debt"
    severity: str = "low"
    source: str = ""
    evidence: list[str] = field(default_factory=list)
    risk: RemediationRisk = field(default_factory=RemediationRisk)
    phase: str = "phase_4_legacy_cleanup"
    owner: str = "observability"
    safe_quick_win: bool = False
    high_risk_change: bool = False
    recommended_action: str = ""
    runtime_dependency: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "uid": self.uid,
            "title": self.title,
            "description": self.description,
            "domain": self.domain,
            "problem_class": self.problem_class,
            "severity": self.severity,
            "source": self.source,
            "evidence": self.evidence,
            "risk": self.risk.to_dict(),
            "phase": self.phase,
            "owner": self.owner,
            "safe_quick_win": self.safe_quick_win,
            "high_risk_change": self.high_risk_change,
            "recommended_action": self.recommended_action,
            "runtime_dependency": self.runtime_dependency,
        }


@dataclass
class RemediationPlan:
    items: list[RemediationItem] = field(default_factory=list)
    total_items: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    informational_count: int = 0
    quick_wins: list[RemediationItem] = field(default_factory=list)
    high_risk_changes: list[RemediationItem] = field(default_factory=list)
    phases: dict[str, list[RemediationItem]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": REMEDIATION_CONTRACT_VERSION,
            "timestamp": time.time(),
            "total_items": self.total_items,
            "classification": {
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
                "informational": self.informational_count,
            },
            "quick_wins": len(self.quick_wins),
            "high_risk_changes": len(self.high_risk_changes),
            "phase_summary": {k: len(v) for k, v in self.phases.items()},
            "items": [i.to_dict() for i in self.items],
        }


@dataclass
class RemediationSummary:
    total_findings: int = 0
    critical_findings: int = 0
    legacy_dashboards: int = 0
    stale_panels: int = 0
    orphan_datasources: int = 0
    runtime_drift_count: int = 0
    estimated_complexity: str = "unknown"
    quick_win_count: int = 0
    high_risk_count: int = 0
    remediation_score: float = 0.0
    phases_summary: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": REMEDIATION_CONTRACT_VERSION,
            "timestamp": time.time(),
            "total_findings": self.total_findings,
            "critical_findings": self.critical_findings,
            "legacy_dashboards": self.legacy_dashboards,
            "stale_panels": self.stale_panels,
            "orphan_datasources": self.orphan_datasources,
            "runtime_drift_count": self.runtime_drift_count,
            "estimated_complexity": self.estimated_complexity,
            "quick_win_count": self.quick_win_count,
            "high_risk_count": self.high_risk_count,
            "remediation_score": round(self.remediation_score, 2),
            "phases_summary": self.phases_summary,
        }


def build_remediation_item(
    uid: str = "",
    title: str = "",
    description: str = "",
    domain: str = "",
    problem_class: str = "technical_debt",
    severity: str = "low",
    source: str = "",
    evidence: list[str] | None = None,
    safe_quick_win: bool = False,
    high_risk_change: bool = False,
    phase: str = "phase_4_legacy_cleanup",
    owner: str = "observability",
    recommended_action: str = "",
    runtime_dependency: str = "",
) -> RemediationItem:
    return RemediationItem(
        uid=uid, title=title, description=description,
        domain=domain, problem_class=problem_class,
        severity=severity, source=source,
        evidence=evidence or [],
        safe_quick_win=safe_quick_win,
        high_risk_change=high_risk_change,
        phase=phase, owner=owner,
        recommended_action=recommended_action,
        runtime_dependency=runtime_dependency,
    )
