"""FEDERATION-EVIDENCE-LINEAGE-01: deterministic evidence lineage/provenance.

Goal: every propagated trust can trace evidence origin, authority binding, freshness,
reuse, lineage depth, and replay/recursive risk.

Hard rules:
- Metadata-only.
- Deterministic IDs/hashes from stable fields (NO timestamps in ID/hash).
- Fail-safe (never raise to caller).
- Bounded lineage chains (small max depth).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


EVIDENCE_SCHEMA_VERSION = "EVID-01"


class EvidenceSourceType(str, Enum):
    ROUTING = "routing"
    AUTHORITY = "authority"
    OBSERVABILITY = "observability"
    SEMANTIC = "semantic"
    MEMORY = "memory"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"


class FreshnessState(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    EXPIRED = "expired"


class ReplayRiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LineageValidationResult(str, Enum):
    OK = "ok"
    INVALID = "invalid"
    DEPTH_EXCEEDED = "depth_exceeded"


class EvidenceDecayReason(str, Enum):
    OK = "ok"
    STALE = "stale"
    TTL_EXPIRED = "ttl_expired"
    DEPTH_EXCEEDED = "depth_exceeded"
    REPLAYED = "replayed"
    RECURSIVE_ANCESTRY = "recursive_ancestry"
    SEMANTIC_WITHOUT_AUTHORITY = "semantic_without_authority"
    ERROR = "error"


@dataclass(frozen=True)
class EvidenceAuthorityBinding:
    authority_bound: bool
    authority_domain: str = ""
    binding_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "authority_bound": bool(self.authority_bound),
            "authority_domain": self.authority_domain,
            "binding_reason": self.binding_reason,
        }


@dataclass(frozen=True)
class EvidenceOrigin:
    source_domain: str
    source_role: str
    model_profile: str
    tool_name: str
    trust_scope: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_domain": self.source_domain,
            "source_role": self.source_role,
            "model_profile": self.model_profile,
            "tool_name": self.tool_name,
            "trust_scope": self.trust_scope,
        }


@dataclass(frozen=True)
class EvidenceFreshness:
    freshness_ttl: int
    freshness_seconds: int
    state: FreshnessState

    def to_dict(self) -> dict[str, Any]:
        return {
            "freshness_ttl": int(self.freshness_ttl),
            "freshness_seconds": int(self.freshness_seconds),
            "state": self.state.value,
        }


@dataclass(frozen=True)
class EvidenceReuseState:
    propagation_count: int
    reuse_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "propagation_count": int(self.propagation_count),
            "reuse_count": int(self.reuse_count),
        }


@dataclass(frozen=True)
class EvidenceReplayRisk:
    level: ReplayRiskLevel
    replayed: bool

    def to_dict(self) -> dict[str, Any]:
        return {"level": self.level.value, "replayed": bool(self.replayed)}


@dataclass(frozen=True)
class EvidenceAncestry:
    parent_evidence_ids: list[str]
    ancestry_chain: list[str]
    lineage_depth: int
    recursive_ancestry: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "parent_evidence_ids": list(self.parent_evidence_ids or []),
            "ancestry_chain": list(self.ancestry_chain or []),
            "lineage_depth": int(self.lineage_depth),
            "recursive_ancestry": bool(self.recursive_ancestry),
        }


@dataclass(frozen=True)
class EvidenceLineageNode:
    evidence_id: str
    source_domain: str
    effective_confidence: float
    freshness: dict[str, Any]
    replay_risk: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_domain": self.source_domain,
            "effective_confidence": float(self.effective_confidence),
            "freshness": dict(self.freshness),
            "replay_risk": dict(self.replay_risk),
        }


@dataclass(frozen=True)
class EvidenceEnvelope:
    evidence_id: str
    evidence_hash: str
    evidence_type: str
    source_type: EvidenceSourceType
    origin: EvidenceOrigin
    authority_binding: EvidenceAuthorityBinding
    canonical_payload_hash: str
    created_at: float
    freshness: EvidenceFreshness
    ancestry: EvidenceAncestry
    reuse: EvidenceReuseState
    replay_risk: EvidenceReplayRisk
    effective_confidence: float
    degraded: bool
    decay_reason: EvidenceDecayReason
    validation: LineageValidationResult

    def to_summary(self) -> dict[str, Any]:
        return {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "evidence_id": self.evidence_id,
            "evidence_hash": self.evidence_hash,
            "evidence_type": self.evidence_type,
            "source_domain": self.origin.source_domain,
            "source_type": self.source_type.value,
            "authority_binding": self.authority_binding.to_dict(),
            "created_at": float(self.created_at),
            "canonical_payload_hash": self.canonical_payload_hash,
            "freshness": self.freshness.to_dict(),
            "lineage_depth": int(self.ancestry.lineage_depth),
            "ancestry_chain": list(self.ancestry.ancestry_chain or []),
            "propagation_count": int(self.reuse.propagation_count),
            "reuse_count": int(self.reuse.reuse_count),
            "replay_risk": self.replay_risk.to_dict(),
            "effective_confidence": float(self.effective_confidence),
            "degraded": bool(self.degraded),
            "decay_reason": self.decay_reason.value,
            "validation": self.validation.value,
        }


@dataclass(frozen=True)
class EvidenceLineageDecision:
    envelope: EvidenceEnvelope

    def to_dict(self) -> dict[str, Any]:
        return self.envelope.to_summary()


@dataclass(frozen=True)
class EvidenceLineageSummary:
    evidence_id: str
    source_domain: str
    authority_bound: bool
    freshness_state: str
    replay_risk: str
    lineage_depth: int
    reuse_count: int
    propagation_count: int
    effective_confidence: float
    degraded: bool
    decay_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_domain": self.source_domain,
            "authority_bound": bool(self.authority_bound),
            "freshness_state": self.freshness_state,
            "replay_risk": self.replay_risk,
            "lineage_depth": int(self.lineage_depth),
            "reuse_count": int(self.reuse_count),
            "propagation_count": int(self.propagation_count),
            "effective_confidence": float(self.effective_confidence),
            "degraded": bool(self.degraded),
            "decay_reason": self.decay_reason,
        }


def _canonical_json(obj: Any) -> str:
    # Stable canonicalization: sorted keys, no whitespace.
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def compute_lineage_depth(ancestry_chain: list[str]) -> int:
    return int(len(ancestry_chain or []))


def validate_evidence_lineage(*, ancestry_chain: list[str], max_depth: int = 3) -> LineageValidationResult:
    depth = compute_lineage_depth(ancestry_chain)
    if depth > int(max_depth):
        return LineageValidationResult.DEPTH_EXCEEDED
    # Empty lineage is allowed for origin evidence.
    return LineageValidationResult.OK


def detect_evidence_reuse(*, previous_seen_count: int) -> tuple[int, int, bool]:
    """Return (propagation_count, reuse_count, replayed)."""

    prev = int(previous_seen_count or 0)
    propagation_count = prev + 1
    reuse_count = prev
    replayed = prev > 0
    return propagation_count, reuse_count, replayed


def detect_replay_risk(*, replayed: bool, reuse_count: int) -> EvidenceReplayRisk:
    if not replayed:
        return EvidenceReplayRisk(level=ReplayRiskLevel.NONE, replayed=False)
    # Deterministic tiers.
    if reuse_count >= 10:
        return EvidenceReplayRisk(level=ReplayRiskLevel.HIGH, replayed=True)
    if reuse_count >= 3:
        return EvidenceReplayRisk(level=ReplayRiskLevel.MEDIUM, replayed=True)
    return EvidenceReplayRisk(level=ReplayRiskLevel.LOW, replayed=True)


def _default_ttl_for_source(source: EvidenceSourceType) -> int:
    if source == EvidenceSourceType.AUTHORITY:
        return 30
    if source in {EvidenceSourceType.OBSERVABILITY, EvidenceSourceType.INFRASTRUCTURE}:
        return 60
    if source == EvidenceSourceType.MEMORY:
        return 90
    if source == EvidenceSourceType.SEMANTIC:
        return 120
    if source == EvidenceSourceType.ROUTING:
        return 120
    return 90


def apply_evidence_decay(
    *,
    source: EvidenceSourceType,
    authority_bound: bool,
    freshness_seconds: int,
    freshness_ttl: int,
    lineage_depth: int,
    max_depth: int,
    replayed: bool,
    recursive_ancestry: bool,
) -> tuple[float, bool, EvidenceDecayReason, FreshnessState]:
    """Return (effective_confidence, degraded, reason, freshness_state)."""

    degraded = False
    reason = EvidenceDecayReason.OK

    # Base confidence by source type.
    base = 0.35
    if source == EvidenceSourceType.AUTHORITY:
        base = 0.85
    elif source == EvidenceSourceType.OBSERVABILITY:
        base = 0.65
    elif source == EvidenceSourceType.SEMANTIC:
        base = 0.50
    elif source == EvidenceSourceType.MEMORY:
        base = 0.30
    elif source == EvidenceSourceType.ROUTING:
        base = 0.40

    # Semantic evidence without authority must degrade.
    if source == EvidenceSourceType.SEMANTIC and not authority_bound:
        degraded = True
        reason = EvidenceDecayReason.SEMANTIC_WITHOUT_AUTHORITY
        base = min(base, 0.35)

    # Freshness
    freshness_state = FreshnessState.FRESH
    if freshness_ttl <= 0:
        freshness_state = FreshnessState.EXPIRED
        degraded = True
        reason = EvidenceDecayReason.TTL_EXPIRED
    elif freshness_seconds > freshness_ttl:
        freshness_state = FreshnessState.STALE
        degraded = True
        if reason == EvidenceDecayReason.OK:
            reason = EvidenceDecayReason.STALE
        base *= 0.7

    # Lineage depth attenuation
    if lineage_depth > int(max_depth):
        degraded = True
        reason = EvidenceDecayReason.DEPTH_EXCEEDED
        base *= 0.6
    elif lineage_depth > 0:
        base *= 0.85 ** int(lineage_depth)

    # Replay / reuse
    if replayed:
        degraded = True
        if reason == EvidenceDecayReason.OK:
            reason = EvidenceDecayReason.REPLAYED
        base *= 0.7

    if recursive_ancestry:
        degraded = True
        if reason == EvidenceDecayReason.OK:
            reason = EvidenceDecayReason.RECURSIVE_ANCESTRY
        base *= 0.6

    base = max(0.0, min(1.0, float(base)))
    return base, degraded, reason, freshness_state


def compute_lineage_confidence(envelope: EvidenceEnvelope) -> float:
    return float(envelope.effective_confidence)


def invalidate_stale_lineage(envelope: EvidenceEnvelope) -> EvidenceEnvelope:
    # Deterministic invalidation: if stale/expired, force degraded and cap confidence.
    if envelope.freshness.state in {FreshnessState.STALE, FreshnessState.EXPIRED}:
        return EvidenceEnvelope(
            **{**envelope.__dict__, "effective_confidence": min(envelope.effective_confidence, 0.4), "degraded": True}
        )
    return envelope


def propagate_evidence_lineage(
    *,
    envelope: EvidenceEnvelope,
    new_parent_ids: list[str] | None = None,
    max_depth: int = 3,
) -> EvidenceEnvelope:
    """Create a new envelope for propagation (increments propagation_count, bounded ancestry)."""

    parent_ids = list(new_parent_ids or [])
    ancestry = list(envelope.ancestry.ancestry_chain or [])
    ancestry.extend(parent_ids)
    ancestry = ancestry[-(max_depth + 1) :]  # bounded
    recursive = len(set(ancestry)) != len(ancestry)
    lineage_depth = compute_lineage_depth(ancestry)

    reuse = EvidenceReuseState(
        propagation_count=int(envelope.reuse.propagation_count) + 1,
        reuse_count=int(envelope.reuse.reuse_count),
    )

    return EvidenceEnvelope(
        **{
            **envelope.__dict__,
            "ancestry": EvidenceAncestry(
                parent_evidence_ids=parent_ids,
                ancestry_chain=ancestry,
                lineage_depth=lineage_depth,
                recursive_ancestry=recursive,
            ),
            "reuse": reuse,
        }
    )


def build_lineage_summary(envelope: EvidenceEnvelope) -> EvidenceLineageSummary:
    return EvidenceLineageSummary(
        evidence_id=envelope.evidence_id,
        source_domain=envelope.origin.source_domain,
        authority_bound=envelope.authority_binding.authority_bound,
        freshness_state=envelope.freshness.state.value,
        replay_risk=envelope.replay_risk.level.value,
        lineage_depth=int(envelope.ancestry.lineage_depth),
        reuse_count=int(envelope.reuse.reuse_count),
        propagation_count=int(envelope.reuse.propagation_count),
        effective_confidence=float(envelope.effective_confidence),
        degraded=bool(envelope.degraded),
        decay_reason=envelope.decay_reason.value,
    )


def build_evidence_envelope(
    *,
    evidence_type: str,
    source_type: EvidenceSourceType,
    canonical_payload: dict[str, Any],
    origin: EvidenceOrigin,
    parent_evidence_ids: list[str] | None = None,
    ancestry_chain: list[str] | None = None,
    authority_binding: EvidenceAuthorityBinding | None = None,
    freshness_seconds: int = 0,
    freshness_ttl: int | None = None,
    created_at: float = 0.0,
    previous_seen_count: int = 0,
    max_depth: int = 3,
) -> EvidenceLineageDecision:
    """Build deterministic evidence envelope.

    evidence_id and evidence_hash are deterministic from stable identity fields.
    created_at is observability-only and MUST NOT participate in hashing.
    """

    try:
        parent_ids = list(parent_evidence_ids or [])
        ancestry = list(ancestry_chain or [])
        # bounded ancestry
        ancestry = ancestry[-(max_depth + 1) :]
        lineage_depth = compute_lineage_depth(ancestry)
        recursive_ancestry = len(set(ancestry)) != len(ancestry)

        canonical = _canonical_json(canonical_payload)
        canonical_payload_hash = _sha256_hex(canonical)

        identity_fields = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "evidence_type": evidence_type,
            "canonical_payload_hash": canonical_payload_hash,
            "source_role": origin.source_role,
            "model_profile": origin.model_profile,
            "tool_name": origin.tool_name,
            "parent_evidence_ids": list(parent_ids),
            "trust_scope": origin.trust_scope,
            "source_domain": origin.source_domain,
        }
        identity_str = _canonical_json(identity_fields)
        evidence_hash = _sha256_hex(identity_str)
        evidence_id = evidence_hash[:24]

        propagation_count, reuse_count, replayed = detect_evidence_reuse(previous_seen_count=int(previous_seen_count))
        replay_risk = detect_replay_risk(replayed=replayed, reuse_count=reuse_count)

        if freshness_ttl is None:
            freshness_ttl = _default_ttl_for_source(source_type)

        # Authority binding
        authority_binding = authority_binding or EvidenceAuthorityBinding(
            authority_bound=bool(source_type == EvidenceSourceType.AUTHORITY),
            authority_domain="authority" if source_type == EvidenceSourceType.AUTHORITY else "",
            binding_reason="source_type" if source_type == EvidenceSourceType.AUTHORITY else "",
        )

        effective_conf, degraded, decay_reason, freshness_state = apply_evidence_decay(
            source=source_type,
            authority_bound=authority_binding.authority_bound,
            freshness_seconds=int(freshness_seconds),
            freshness_ttl=int(freshness_ttl),
            lineage_depth=int(lineage_depth),
            max_depth=int(max_depth),
            replayed=replayed,
            recursive_ancestry=bool(recursive_ancestry),
        )

        validation = validate_evidence_lineage(ancestry_chain=ancestry, max_depth=max_depth)
        if validation != LineageValidationResult.OK:
            degraded = True
            if validation == LineageValidationResult.DEPTH_EXCEEDED:
                decay_reason = EvidenceDecayReason.DEPTH_EXCEEDED

        envelope = EvidenceEnvelope(
            evidence_id=evidence_id,
            evidence_hash=evidence_hash,
            evidence_type=evidence_type,
            source_type=source_type,
            origin=origin,
            authority_binding=authority_binding,
            canonical_payload_hash=canonical_payload_hash,
            created_at=float(created_at),
            freshness=EvidenceFreshness(
                freshness_ttl=int(freshness_ttl),
                freshness_seconds=int(freshness_seconds),
                state=freshness_state,
            ),
            ancestry=EvidenceAncestry(
                parent_evidence_ids=parent_ids,
                ancestry_chain=ancestry,
                lineage_depth=int(lineage_depth),
                recursive_ancestry=bool(recursive_ancestry),
            ),
            reuse=EvidenceReuseState(propagation_count=propagation_count, reuse_count=reuse_count),
            replay_risk=replay_risk,
            effective_confidence=float(effective_conf),
            degraded=bool(degraded),
            decay_reason=decay_reason,
            validation=validation,
        )
        return EvidenceLineageDecision(envelope=envelope)
    except Exception:
        # Fail-safe invalid envelope.
        origin = origin
        envelope = EvidenceEnvelope(
            evidence_id="",
            evidence_hash="",
            evidence_type=evidence_type,
            source_type=EvidenceSourceType.UNKNOWN,
            origin=origin,
            authority_binding=EvidenceAuthorityBinding(authority_bound=False),
            canonical_payload_hash="",
            created_at=float(created_at),
            freshness=EvidenceFreshness(freshness_ttl=0, freshness_seconds=int(freshness_seconds), state=FreshnessState.EXPIRED),
            ancestry=EvidenceAncestry(parent_evidence_ids=[], ancestry_chain=[], lineage_depth=0, recursive_ancestry=False),
            reuse=EvidenceReuseState(propagation_count=0, reuse_count=0),
            replay_risk=EvidenceReplayRisk(level=ReplayRiskLevel.HIGH, replayed=False),
            effective_confidence=0.0,
            degraded=True,
            decay_reason=EvidenceDecayReason.ERROR,
            validation=LineageValidationResult.INVALID,
        )
        return EvidenceLineageDecision(envelope=envelope)
