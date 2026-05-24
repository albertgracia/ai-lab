"""FEDERATION-EVIDENCE-LINEAGE-01 tests."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/ai-lab")

from runtime.federation.evidence_lineage import (
    EvidenceAuthorityBinding,
    EvidenceOrigin,
    EvidenceSourceType,
    EvidenceDecayReason,
    FreshnessState,
    ReplayRiskLevel,
    build_evidence_envelope,
    build_lineage_summary,
)


def _origin(domain: str) -> EvidenceOrigin:
    return EvidenceOrigin(
        source_domain=domain,
        source_role=domain,
        model_profile="coding",
        tool_name="",
        trust_scope="routing",
    )


def test_evidence_id_and_hash_are_deterministic_without_timestamps():
    canonical_payload = {"a": 1, "b": "x"}
    d1 = build_evidence_envelope(
        evidence_type="routing_metadata",
        source_type=EvidenceSourceType.ROUTING,
        canonical_payload=canonical_payload,
        origin=_origin("gateway"),
        created_at=123.0,
    ).envelope
    d2 = build_evidence_envelope(
        evidence_type="routing_metadata",
        source_type=EvidenceSourceType.ROUTING,
        canonical_payload=canonical_payload,
        origin=_origin("gateway"),
        created_at=999.0,
    ).envelope
    assert d1.evidence_id == d2.evidence_id
    assert d1.evidence_hash == d2.evidence_hash


def test_authority_precedence_has_high_base_confidence():
    env = build_evidence_envelope(
        evidence_type="authority_snapshot",
        source_type=EvidenceSourceType.AUTHORITY,
        canonical_payload={"x": "y"},
        origin=_origin("authority"),
        authority_binding=EvidenceAuthorityBinding(authority_bound=True, authority_domain="authority", binding_reason="test"),
        freshness_seconds=0,
        freshness_ttl=30,
    ).envelope
    assert env.effective_confidence >= 0.7
    assert env.degraded is False


def test_semantic_without_authority_degrades():
    env = build_evidence_envelope(
        evidence_type="semantic_state",
        source_type=EvidenceSourceType.SEMANTIC,
        canonical_payload={"k": "v"},
        origin=_origin("semantic"),
        authority_binding=EvidenceAuthorityBinding(authority_bound=False),
        freshness_seconds=0,
        freshness_ttl=120,
    ).envelope
    assert env.degraded is True
    assert env.decay_reason == EvidenceDecayReason.SEMANTIC_WITHOUT_AUTHORITY


def test_stale_evidence_degrades_automatically():
    env = build_evidence_envelope(
        evidence_type="obs",
        source_type=EvidenceSourceType.OBSERVABILITY,
        canonical_payload={"k": "v"},
        origin=_origin("observability"),
        freshness_seconds=999,
        freshness_ttl=60,
    ).envelope
    assert env.freshness.state in {FreshnessState.STALE, FreshnessState.EXPIRED}
    assert env.degraded is True


def test_reuse_tracking_is_deterministic_with_seen_counts():
    env1 = build_evidence_envelope(
        evidence_type="routing_metadata",
        source_type=EvidenceSourceType.ROUTING,
        canonical_payload={"q": "hello"},
        origin=_origin("gateway"),
        previous_seen_count=0,
    ).envelope
    env2 = build_evidence_envelope(
        evidence_type="routing_metadata",
        source_type=EvidenceSourceType.ROUTING,
        canonical_payload={"q": "hello"},
        origin=_origin("gateway"),
        previous_seen_count=1,
    ).envelope
    assert env2.reuse.reuse_count >= 1
    assert env2.replay_risk.level in {ReplayRiskLevel.LOW, ReplayRiskLevel.MEDIUM, ReplayRiskLevel.HIGH}


def test_recursive_ancestry_degrades():
    env = build_evidence_envelope(
        evidence_type="routing_metadata",
        source_type=EvidenceSourceType.ROUTING,
        canonical_payload={"x": 1},
        origin=_origin("gateway"),
        ancestry_chain=["a", "b", "a"],
        max_depth=3,
    ).envelope
    assert env.ancestry.recursive_ancestry is True
    assert env.degraded is True


def test_lineage_summary_contains_required_fields():
    env = build_evidence_envelope(
        evidence_type="routing_metadata",
        source_type=EvidenceSourceType.ROUTING,
        canonical_payload={"x": 1},
        origin=_origin("gateway"),
    ).envelope
    summary = build_lineage_summary(env).to_dict()
    for k in (
        "evidence_id",
        "source_domain",
        "authority_bound",
        "freshness_state",
        "replay_risk",
        "lineage_depth",
        "reuse_count",
        "propagation_count",
        "effective_confidence",
        "degraded",
        "decay_reason",
    ):
        assert k in summary
