from __future__ import annotations

from dataclasses import dataclass
from typing import Any


FASTPATH_CONTRACT_VERSION = "35D"


@dataclass(frozen=True)
class OperationalSignal:
    domain: str
    severity: str  # critical|warning|info
    message: str
    evidence: list[str]
    confidence: str  # high|medium|low|unknown
    freshness: str  # fresh|partial|unavailable|unknown

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "severity": self.severity,
            "message": self.message,
            "evidence": list(self.evidence or []),
            "confidence": self.confidence,
            "freshness": self.freshness,
        }


@dataclass(frozen=True)
class OperationalSummary:
    mode: str  # minimal|operational|technical|deep
    lines: list[str]
    signals: list[dict[str, Any]]
    deterministic_signature: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "lines": list(self.lines or []),
            "signals": list(self.signals or []),
            "deterministic_signature": self.deterministic_signature,
        }


@dataclass(frozen=True)
class FastPathCache:
    cache_entries: int
    cache_hits: int
    cache_misses: int
    freshness: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "cache_entries": int(self.cache_entries),
            "cache_hits": int(self.cache_hits),
            "cache_misses": int(self.cache_misses),
            "freshness": self.freshness,
        }


@dataclass(frozen=True)
class FastPathRouting:
    classification: str
    intent: str
    deep_path: bool
    verbosity: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "intent": self.intent,
            "deep_path": bool(self.deep_path),
            "verbosity": self.verbosity,
        }


@dataclass(frozen=True)
class FastPathAuthoritySnapshot:
    contract_version: str
    freshness: dict[str, Any]
    gaps: list[str]
    prometheus_targets: dict[str, Any]
    deterministic_signature: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "freshness": self.freshness,
            "gaps": list(self.gaps or []),
            "prometheus_targets": self.prometheus_targets,
            "deterministic_signature": self.deterministic_signature,
        }


@dataclass(frozen=True)
class FastPathResponse:
    contract_version: str
    routing: dict[str, Any]
    summary: dict[str, Any]
    authority: dict[str, Any]
    cache: dict[str, Any]
    response_quality_score: float
    deterministic_signature: str
    generated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "routing": self.routing,
            "summary": self.summary,
            "authority": self.authority,
            "cache": self.cache,
            "response_quality_score": float(self.response_quality_score),
            "deterministic_signature": self.deterministic_signature,
            "generated_at": float(self.generated_at),
        }
