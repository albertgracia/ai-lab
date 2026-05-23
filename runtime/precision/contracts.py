from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class EvidenceStrength(str, Enum):
    CONFIRMED = "CONFIRMED"
    GROUNDED = "GROUNDED"
    PARTIAL = "PARTIAL"
    DISCOVERABLE = "DISCOVERABLE"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"
    CONFLICTING = "CONFLICTING"
    NON_ROUTABLE = "NON_ROUTABLE"


class OperationalCertainty(str, Enum):
    CONFIRMED = "confirmed"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class ConfidenceScore:
    score: float
    label: str
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PrecisionEvidence:
    evidence_type: str
    strength: EvidenceStrength
    source: str
    payload: dict[str, Any] = field(default_factory=dict)
    freshness: str = "unknown"
    confidence: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["strength"] = self.strength.value
        return d


@dataclass(frozen=True)
class AuthorityConflict:
    conflict_type: str
    severity: str
    description: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PartialState:
    domain: str
    missing: list[str]
    severity: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PrecisionSummary:
    lines: list[str]
    confidence: ConfidenceScore
    certainty: OperationalCertainty
    determinism_signature: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["certainty"] = self.certainty.value
        d["confidence"] = self.confidence.to_dict()
        return d


@dataclass(frozen=True)
class PrecisionDecision:
    classification: str
    certainty: OperationalCertainty
    confidence: ConfidenceScore
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["certainty"] = self.certainty.value
        d["confidence"] = self.confidence.to_dict()
        return d
