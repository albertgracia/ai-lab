"""FEDERATION-TRUST-PROPAGATION-01: deterministic trust propagation between domains.

This is NOT AI reasoning.
It enforces bounded confidence via:
- attenuation
- freshness decay
- semantic TTL
- lineage depth limits
- recursive confidence risk marking

Hard rules:
- Deterministic, metadata-only.
- Fail-safe (never raise to caller).
- No runtime/state mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class TrustDecayReason(str, Enum):
    OK = "ok"
    STALE = "stale"
    TTL_EXPIRED = "ttl_expired"
    DEPTH_EXCEEDED = "depth_exceeded"
    RECURSIVE_RISK = "recursive_risk"
    UNKNOWN_DOMAIN = "unknown_domain"
    ERROR = "error"


@dataclass(frozen=True)
class TrustEvidence:
    evidence_type: str
    authority_backed: bool
    freshness_seconds: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_type": self.evidence_type,
            "authority_backed": bool(self.authority_backed),
            "freshness_seconds": int(self.freshness_seconds),
        }


@dataclass(frozen=True)
class TrustLineageNode:
    domain: str
    evidence_count: int

    def to_dict(self) -> dict[str, Any]:
        return {"domain": self.domain, "evidence_count": int(self.evidence_count)}


@dataclass(frozen=True)
class TrustAttenuationPolicy:
    max_depth: int = 3
    base_attenuation: float = 0.85
    recursive_penalty: float = 0.6
    stale_penalty: float = 0.7
    ttl_seconds_default: int = 120
    # Freshness windows by domain (seconds)
    freshness_authority: int = 30
    freshness_observability: int = 60
    freshness_infrastructure: int = 60
    freshness_semantic: int = 180
    freshness_memory: int = 120
    freshness_default: int = 90


@dataclass(frozen=True)
class TrustFreshnessState:
    freshness_seconds: int
    window_seconds: int
    stale: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "freshness_seconds": int(self.freshness_seconds),
            "window_seconds": int(self.window_seconds),
            "stale": bool(self.stale),
        }


@dataclass(frozen=True)
class TrustPropagationDecision:
    trust_score: float
    attenuation_factor: float
    semantic_ttl: int
    lineage_depth: int
    evidence_count: int
    authority_backed: bool
    stale: bool
    degraded: bool
    recursive_risk: bool
    reason: TrustDecayReason

    def to_dict(self) -> dict[str, Any]:
        return {
            "trust_score": float(self.trust_score),
            "attenuation_factor": float(self.attenuation_factor),
            "semantic_ttl": int(self.semantic_ttl),
            "lineage_depth": int(self.lineage_depth),
            "evidence_count": int(self.evidence_count),
            "authority_backed": bool(self.authority_backed),
            "stale": bool(self.stale),
            "degraded": bool(self.degraded),
            "recursive_risk": bool(self.recursive_risk),
            "reason": self.reason.value,
        }


@dataclass(frozen=True)
class TrustPropagationEnvelope:
    source_domain: str
    target_domain: str
    origin_domain: str
    lineage: list[TrustLineageNode]
    evidence: list[TrustEvidence]
    ttl_seconds: int
    policy: TrustAttenuationPolicy

    def lineage_depth(self) -> int:
        return int(len(self.lineage or []))

    def evidence_count(self) -> int:
        return int(len(self.evidence or []))


def build_trust_envelope(
    *,
    source_domain: str,
    target_domain: str,
    origin_domain: str,
    evidence: list[TrustEvidence] | None = None,
    lineage: list[TrustLineageNode] | None = None,
    ttl_seconds: int | None = None,
    policy: TrustAttenuationPolicy | None = None,
) -> TrustPropagationEnvelope:
    policy = policy or TrustAttenuationPolicy()
    if ttl_seconds is None:
        ttl_seconds = int(policy.ttl_seconds_default)
    return TrustPropagationEnvelope(
        source_domain=source_domain or "unknown",
        target_domain=target_domain or "unknown",
        origin_domain=origin_domain or (source_domain or "unknown"),
        lineage=list(lineage or []),
        evidence=list(evidence or []),
        ttl_seconds=int(ttl_seconds),
        policy=policy,
    )


def validate_lineage_depth(env: TrustPropagationEnvelope) -> tuple[bool, int]:
    depth = env.lineage_depth()
    return depth <= int(env.policy.max_depth), depth


def detect_recursive_confidence(env: TrustPropagationEnvelope) -> bool:
    # Simple deterministic detection: repeated domains in lineage or origin == target in multi-hop.
    seen: set[str] = set()
    for node in env.lineage:
        if node.domain in seen:
            return True
        seen.add(node.domain)
    if env.origin_domain and env.target_domain and env.origin_domain == env.target_domain and env.lineage_depth() > 0:
        return True
    return False


def _freshness_window_for_domain(domain: str, policy: TrustAttenuationPolicy) -> int:
    d = (domain or "").lower()
    if d == "authority":
        return int(policy.freshness_authority)
    if d == "observability":
        return int(policy.freshness_observability)
    if d == "infrastructure":
        return int(policy.freshness_infrastructure)
    if d == "semantic":
        return int(policy.freshness_semantic)
    if d == "memory":
        return int(policy.freshness_memory)
    return int(policy.freshness_default)


def apply_freshness_decay(env: TrustPropagationEnvelope) -> TrustFreshnessState:
    # Deterministic freshness: use maximum freshness_seconds in evidence as a conservative indicator.
    freshness = 0
    for e in env.evidence:
        freshness = max(freshness, int(e.freshness_seconds))
    window = _freshness_window_for_domain(env.origin_domain, env.policy)
    stale = freshness > window
    return TrustFreshnessState(freshness_seconds=int(freshness), window_seconds=int(window), stale=bool(stale))


def apply_trust_attenuation(*, base_trust: float, depth: int, stale: bool, recursive_risk: bool, policy: TrustAttenuationPolicy) -> tuple[float, float]:
    # Base attenuation per hop.
    attenuation = float(policy.base_attenuation) ** max(0, int(depth))
    if stale:
        attenuation *= float(policy.stale_penalty)
    if recursive_risk:
        attenuation *= float(policy.recursive_penalty)
    effective = max(0.0, min(1.0, float(base_trust) * attenuation))
    return effective, attenuation


def compute_effective_trust(env: TrustPropagationEnvelope) -> TrustPropagationDecision:
    """Compute deterministic trust decision.

    Base trust is derived only from evidence count and authority-backed flag.
    """

    try:
        ttl = int(env.ttl_seconds)
        ok_depth, depth = validate_lineage_depth(env)
        recursive_risk = detect_recursive_confidence(env)
        freshness = apply_freshness_decay(env)

        authority_backed = any(bool(e.authority_backed) for e in env.evidence)
        evidence_count = env.evidence_count()

        # Base trust (bounded, deterministic):
        # - authority-backed starts higher
        # - each evidence adds a small bounded increment
        base = 0.3
        if authority_backed:
            base = 0.6
        base += min(0.3, 0.05 * float(evidence_count))
        base = max(0.0, min(1.0, base))

        degraded = False
        reason = TrustDecayReason.OK

        if ttl <= 0:
            degraded = True
            reason = TrustDecayReason.TTL_EXPIRED

        if not ok_depth:
            degraded = True
            reason = TrustDecayReason.DEPTH_EXCEEDED

        if freshness.stale:
            degraded = True
            # Preserve more specific reason if already set.
            if reason == TrustDecayReason.OK:
                reason = TrustDecayReason.STALE

        if recursive_risk:
            degraded = True
            if reason == TrustDecayReason.OK:
                reason = TrustDecayReason.RECURSIVE_RISK

        effective, attenuation = apply_trust_attenuation(
            base_trust=base,
            depth=depth,
            stale=freshness.stale,
            recursive_risk=recursive_risk,
            policy=env.policy,
        )

        # If degraded, cap effective trust further deterministically.
        if degraded:
            effective = min(effective, 0.7)

        return TrustPropagationDecision(
            trust_score=effective,
            attenuation_factor=attenuation,
            semantic_ttl=ttl,
            lineage_depth=depth,
            evidence_count=evidence_count,
            authority_backed=bool(authority_backed),
            stale=bool(freshness.stale),
            degraded=bool(degraded),
            recursive_risk=bool(recursive_risk),
            reason=reason,
        )
    except Exception:
        return TrustPropagationDecision(
            trust_score=0.0,
            attenuation_factor=0.0,
            semantic_ttl=0,
            lineage_depth=0,
            evidence_count=0,
            authority_backed=False,
            stale=True,
            degraded=True,
            recursive_risk=False,
            reason=TrustDecayReason.ERROR,
        )


def propagate_trust(env: TrustPropagationEnvelope) -> TrustPropagationDecision:
    return compute_effective_trust(env)


def build_trust_summary(decision: TrustPropagationDecision) -> dict[str, Any]:
    return {
        "trust_score": float(decision.trust_score),
        "degraded": bool(decision.degraded),
        "stale": bool(decision.stale),
        "recursive_risk": bool(decision.recursive_risk),
        "ttl": int(decision.semantic_ttl),
        "depth": int(decision.lineage_depth),
        "attenuation": float(decision.attenuation_factor),
        "reason": decision.reason.value,
    }
