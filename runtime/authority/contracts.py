from __future__ import annotations

from dataclasses import dataclass
from typing import Any


AUTHORITY_CONTRACT_VERSION = "35C"


@dataclass(frozen=True)
class AuthorityFreshness:
    status: str  # fresh/stale/aged/unavailable/partial
    confidence: str  # high/medium/low/unknown
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "confidence": self.confidence,
            "reasons": list(self.reasons or []),
        }


@dataclass(frozen=True)
class AuthoritySnapshot:
    contract_version: str
    prometheus: dict[str, Any]
    runtime: dict[str, Any]
    infrastructure: dict[str, Any]
    operational_truth: dict[str, Any]
    freshness: dict[str, Any]
    gaps: list[str]
    deterministic_signature: str
    generated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "prometheus": self.prometheus,
            "runtime": self.runtime,
            "infrastructure": self.infrastructure,
            "operational_truth": self.operational_truth,
            "freshness": self.freshness,
            "gaps": list(self.gaps or []),
            "deterministic_signature": self.deterministic_signature,
            "generated_at": float(self.generated_at),
        }


@dataclass(frozen=True)
class AuthorityQuery:
    query: str
    domain: str

    def to_dict(self) -> dict[str, Any]:
        return {"query": self.query, "domain": self.domain}


@dataclass(frozen=True)
class AuthorityEvidence:
    evidence_type: str
    source: str
    freshness: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_type": self.evidence_type,
            "source": self.source,
            "freshness": self.freshness,
            "payload": self.payload,
        }


@dataclass(frozen=True)
class AuthorityResponse:
    contract_version: str
    query: dict[str, Any]
    snapshot: dict[str, Any]
    evidence: list[dict[str, Any]]
    summary: dict[str, Any]
    deterministic_signature: str
    generated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "query": self.query,
            "snapshot": self.snapshot,
            "evidence": list(self.evidence or []),
            "summary": self.summary,
            "deterministic_signature": self.deterministic_signature,
            "generated_at": float(self.generated_at),
        }


@dataclass(frozen=True)
class AuthorityBackedCognition:
    contract_version: str
    snapshot: dict[str, Any]
    evidence: list[dict[str, Any]]
    grounded: bool
    confidence: str
    deterministic_signature: str
    generated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "snapshot": self.snapshot,
            "evidence": list(self.evidence or []),
            "grounded": bool(self.grounded),
            "confidence": self.confidence,
            "deterministic_signature": self.deterministic_signature,
            "generated_at": float(self.generated_at),
        }


@dataclass(frozen=True)
class AuthorityCacheEntry:
    key: str
    value: dict[str, Any]
    freshness: str
    ts: float
    ttl_s: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "freshness": self.freshness,
            "ts": float(self.ts),
            "ttl_s": int(self.ttl_s),
        }


@dataclass(frozen=True)
class AuthorityValidationResult:
    ok: bool
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"ok": bool(self.ok), "reasons": list(self.reasons or [])}


@dataclass(frozen=True)
class AuthorityCognitionSummary:
    contract_version: str
    authority_freshness_score: float
    grounded_cognition_score: float
    stale_authority_total: int
    authority_gaps_total: int
    deterministic_signature: str
    generated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "authority_freshness_score": float(self.authority_freshness_score),
            "grounded_cognition_score": float(self.grounded_cognition_score),
            "stale_authority_total": int(self.stale_authority_total),
            "authority_gaps_total": int(self.authority_gaps_total),
            "deterministic_signature": self.deterministic_signature,
            "generated_at": float(self.generated_at),
        }
