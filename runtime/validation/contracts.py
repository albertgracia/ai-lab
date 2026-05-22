from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any


VALIDATION_CONTRACT_VERSION = "33B"


@dataclass
class RuntimeInvariantContract:
    name: str
    status: str  # pass|fail|degraded
    confidence: str
    authority: str
    explainable: bool = True
    blocking: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RuntimeSafetyGateContract:
    gate: str
    status: str  # pass|fail|degraded
    blocking: bool
    confidence: str
    explainable: bool = True
    derived_from: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RuntimePilotReadinessContract:
    pilot_readiness_score: float
    readiness_level: str
    blocking_invariants: list[str]
    failed_gates: list[str]
    degraded_domains: list[str]
    confidence: str
    explainable: bool = True
    components: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RuntimeFailureSurfaceContract:
    total_failure_modes: int
    failure_modes: list[dict[str, Any]]
    authority_collapse_risk: bool
    topology_drift_risk: bool
    stale_observability_risk: bool
    governance_degradation_risk: bool
    contract_incompatibility_risk: bool
    remediation_accumulation_risk: bool
    explainable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RuntimeRegressionContract:
    baseline_checkpoint: str
    current_checkpoint: str
    regressions_total: int
    regressions: list[dict[str, Any]]
    explainable: bool = True
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RuntimeValidationContract:
    validation_score: float
    validation_level: str
    invariants: list[dict[str, Any]]
    safety_gates: list[dict[str, Any]]
    pilot_readiness: dict[str, Any]
    failure_surface: dict[str, Any]
    regressions: dict[str, Any]
    failures: list[dict[str, Any]]
    degraded_domains: list[str]
    strict_mode: bool
    contract_version: str = VALIDATION_CONTRACT_VERSION
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
