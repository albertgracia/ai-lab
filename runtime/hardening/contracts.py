from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any


HARDENING_CONTRACT_VERSION = "34A"


@dataclass
class WatchdogContract:
    watchdog: str
    state: str  # healthy|degraded|critical
    authority: str
    timeout_seconds: int
    last_success: float | None
    confidence: str
    escalation_level: str
    explainable: bool = True
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TimeoutGovernanceContract:
    component: str
    timeout_seconds: int
    state: str  # ok|warning|critical
    authority_degraded: bool
    confidence: str
    explainable: bool = True
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DegradedEscalationContract:
    escalation_state: str  # healthy|healthy_degraded|degraded|critical|containment_mode
    triggers: list[str]
    confidence: str
    explainable: bool = True
    last_transition: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FailureContainmentContract:
    containment_mode: bool
    policies: list[str]
    active_policies: list[str]
    explainable: bool = True
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OperationalSafeguardContract:
    safeguard: str
    state: str  # safe|restricted|blocked
    confidence: str
    explainable: bool = True
    derived_from: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RuntimeSurvivabilityContract:
    survivability_score: float
    survivability_level: str
    continuity: str
    authority_survivability: str
    observability_survivability: str
    governance_survivability: str
    reporting_survivability: str
    degraded_continuity: str
    explainable: bool = True
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RuntimeHardeningContract:
    hardening_score: float
    hardening_level: str
    watchdogs: list[dict[str, Any]]
    timeouts: list[dict[str, Any]]
    escalation: dict[str, Any]
    containment: dict[str, Any]
    safeguards: list[dict[str, Any]]
    survivability: dict[str, Any]
    instability: list[dict[str, Any]]
    strict_mode: bool
    contract_version: str = HARDENING_CONTRACT_VERSION
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
