"""FEDERATION-TRUST-PROPAGATION-01 tests."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/ai-lab")

from runtime.federation.trust_propagation import (
    TrustEvidence,
    TrustLineageNode,
    TrustDecayReason,
    build_trust_envelope,
    propagate_trust,
)


def test_valid_propagation_is_deterministic_and_bounded():
    env = build_trust_envelope(
        source_domain="gateway",
        target_domain="observability",
        origin_domain="gateway",
        evidence=[TrustEvidence(evidence_type="x", authority_backed=False, freshness_seconds=0)],
        lineage=[TrustLineageNode(domain="gateway", evidence_count=1)],
        ttl_seconds=120,
    )
    d1 = propagate_trust(env)
    d2 = propagate_trust(env)
    assert d1.to_dict() == d2.to_dict()
    assert 0.0 <= d1.trust_score <= 1.0


def test_ttl_expiration_degrades():
    env = build_trust_envelope(
        source_domain="gateway",
        target_domain="semantic",
        origin_domain="gateway",
        evidence=[TrustEvidence(evidence_type="x", authority_backed=False, freshness_seconds=0)],
        lineage=[TrustLineageNode(domain="gateway", evidence_count=1)],
        ttl_seconds=0,
    )
    d = propagate_trust(env)
    assert d.degraded is True
    assert d.reason in {TrustDecayReason.TTL_EXPIRED, TrustDecayReason.DEPTH_EXCEEDED, TrustDecayReason.STALE, TrustDecayReason.RECURSIVE_RISK, TrustDecayReason.ERROR}


def test_excessive_depth_degrades():
    env = build_trust_envelope(
        source_domain="gateway",
        target_domain="semantic",
        origin_domain="gateway",
        evidence=[TrustEvidence(evidence_type="x", authority_backed=False, freshness_seconds=0)],
        lineage=[
            TrustLineageNode(domain="gateway", evidence_count=1),
            TrustLineageNode(domain="semantic", evidence_count=1),
            TrustLineageNode(domain="memory", evidence_count=1),
            TrustLineageNode(domain="semantic", evidence_count=1),
        ],
        ttl_seconds=120,
    )
    d = propagate_trust(env)
    assert d.degraded is True
    assert d.lineage_depth >= 3


def test_recursive_lineage_marks_recursive_risk():
    env = build_trust_envelope(
        source_domain="gateway",
        target_domain="semantic",
        origin_domain="gateway",
        evidence=[TrustEvidence(evidence_type="x", authority_backed=False, freshness_seconds=0)],
        lineage=[TrustLineageNode(domain="semantic", evidence_count=1), TrustLineageNode(domain="semantic", evidence_count=1)],
        ttl_seconds=120,
    )
    d = propagate_trust(env)
    assert d.recursive_risk is True
    assert d.degraded is True


def test_freshness_decay_marks_stale():
    # Authority has strict freshness window; a high freshness_seconds should mark stale.
    env = build_trust_envelope(
        source_domain="authority",
        target_domain="semantic",
        origin_domain="authority",
        evidence=[TrustEvidence(evidence_type="auth", authority_backed=True, freshness_seconds=999)],
        lineage=[TrustLineageNode(domain="authority", evidence_count=1)],
        ttl_seconds=120,
    )
    d = propagate_trust(env)
    assert d.stale is True
    assert d.degraded is True
