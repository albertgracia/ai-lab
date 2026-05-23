from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any


INCIDENT_CONTRACT_VERSION = "36A"

INCIDENT_DOMAINS = [
    "authority", "observability", "validation", "governance",
    "topology", "semantic", "fastpath", "infrastructure",
    "performance", "storage", "gpu", "execution",
]

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

DOMAIN_DEPENDENCY_MAP: dict[str, list[str]] = {
    "authority": ["observability", "validation", "governance", "reporting"],
    "observability": ["validation", "governance", "reporting"],
    "validation": ["governance", "reporting"],
    "governance": ["reporting"],
    "topology": ["gpu", "routing", "fastpath"],
    "infrastructure": ["topology", "authority"],
    "semantic": ["reporting", "governance"],
    "fastpath": ["reporting"],
    "gpu": ["performance", "execution"],
    "performance": ["reporting"],
    "storage": ["performance"],
    "execution": ["reporting"],
}

CORRELATION_DOMAINS: dict[str, list[str]] = {
    "authority": ["observability"],
    "observability": ["authority"],
    "validation": ["governance"],
    "governance": ["validation"],
    "topology": ["infrastructure"],
    "infrastructure": ["topology"],
    "semantic": ["infrastructure"],
    "gpu": ["topology"],
    "performance": ["storage", "gpu"],
    "storage": ["performance"],
    "execution": ["performance"],
    "fastpath": ["observability", "authority"],
}


def _hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _now() -> float:
    return 0.0 if os.environ.get("STRICT_VALIDATION_MODE", "false").lower() in ("true", "1", "yes") else time.time()


import os


@dataclass(frozen=True)
class IncidentSignal:
    domain: str
    signal_type: str
    severity: str
    description: str
    evidence: list[str]
    confidence: str
    freshness: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "signal_type": self.signal_type,
            "severity": self.severity,
            "description": self.description,
            "evidence": list(self.evidence or []),
            "confidence": self.confidence,
            "freshness": self.freshness,
        }


@dataclass(frozen=True)
class BlastRadiusEntry:
    affected_domain: str
    severity: str
    dependency_path: list[str]
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "affected_domain": self.affected_domain,
            "severity": self.severity,
            "dependency_path": list(self.dependency_path or []),
            "description": self.description,
        }


@dataclass(frozen=True)
class IncidentHypothesis:
    hypothesis_type: str
    domain: str
    description: str
    evidence: list[str]
    confidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_type": self.hypothesis_type,
            "domain": self.domain,
            "description": self.description,
            "evidence": list(self.evidence or []),
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class IncidentRecommendation:
    priority: str
    domain: str
    description: str
    actionable: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority": self.priority,
            "domain": self.domain,
            "description": self.description,
            "actionable": bool(self.actionable),
        }


@dataclass(frozen=True)
class OperationalIncident:
    incident_id: str
    primary_domain: str
    severity: str
    title: str
    description: str
    signals: list[dict[str, Any]]
    correlated_signals: list[dict[str, Any]]
    blast_radius: list[dict[str, Any]]
    hypotheses: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    evidence: list[str]
    confidence: str
    deterministic_signature: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "primary_domain": self.primary_domain,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "signals": list(self.signals or []),
            "correlated_signals": list(self.correlated_signals or []),
            "blast_radius": list(self.blast_radius or []),
            "hypotheses": list(self.hypotheses or []),
            "recommendations": list(self.recommendations or []),
            "evidence": list(self.evidence or []),
            "confidence": self.confidence,
            "deterministic_signature": self.deterministic_signature,
        }


@dataclass(frozen=True)
class IncidentIntelligenceReport:
    contract_version: str
    active_incidents: list[dict[str, Any]]
    incident_count: int
    highest_severity: str
    affected_domains: list[str]
    total_signals_evaluated: int
    correlation_results: list[dict[str, Any]]
    blast_radius_summary: dict[str, Any]
    recommendations_total: int
    deterministic_signature: str
    generated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "active_incidents": list(self.active_incidents or []),
            "incident_count": int(self.incident_count),
            "highest_severity": self.highest_severity,
            "affected_domains": list(self.affected_domains or []),
            "total_signals_evaluated": int(self.total_signals_evaluated),
            "correlation_results": list(self.correlation_results or []),
            "blast_radius_summary": dict(self.blast_radius_summary or {}),
            "recommendations_total": int(self.recommendations_total),
            "deterministic_signature": self.deterministic_signature,
            "generated_at": float(self.generated_at),
        }
