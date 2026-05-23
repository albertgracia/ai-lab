"""FEDERATION-OBSERVABILITY-01: federation propagation observability tests."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/ai-lab")

from runtime.federation.federation_observability import (
    FederationPropagationTrace,
    get_domain_hotspots,
    get_federation_observability_snapshot,
    get_overflow_summary,
    record_propagation_trace,
    reset_federation_observability_state,
)


def test_snapshot_starts_empty_and_is_deterministic():
    reset_federation_observability_state()
    s1 = get_federation_observability_snapshot().to_dict()
    s2 = get_federation_observability_snapshot().to_dict()
    assert s1 == s2
    assert s1["delegated_requests_total"] == 0


def test_record_trace_updates_counters_and_paths():
    reset_federation_observability_state()
    record_propagation_trace(
        FederationPropagationTrace(
            source_domain="gateway",
            target_domain="observability",
            authority_weight="high",
            budget_consumed={"chars": 100, "items": 5},
            overflow=False,
            truncated=False,
            degraded=False,
            rejected=False,
            path_depth=1,
        )
    )
    snap = get_federation_observability_snapshot().to_dict()
    assert snap["delegated_requests_total"] == 1
    assert snap["domain_calls_total"] == 1
    assert any(k.startswith("gateway->observability@") for k in snap["cross_domain_paths"].keys())


def test_hotspot_detection_is_deterministic_and_triggers_on_rejects():
    reset_federation_observability_state()
    # Create repeated reject traces for authority.
    for _ in range(3):
        record_propagation_trace(
            FederationPropagationTrace(
                source_domain="gateway",
                target_domain="authority",
                authority_weight="high",
                budget_consumed={"chars": 2000, "items": 50},
                overflow=True,
                truncated=False,
                degraded=True,
                rejected=True,
                path_depth=1,
            )
        )
    hs1 = [h.to_dict() for h in get_domain_hotspots(min_events=3)]
    hs2 = [h.to_dict() for h in get_domain_hotspots(min_events=3)]
    assert hs1 == hs2
    assert any(h["domain"] == "authority" and h["hotspot_type"] == "reject_overflow" for h in hs1)


def test_overflow_summary_counts_domains():
    reset_federation_observability_state()
    record_propagation_trace(
        FederationPropagationTrace(
            source_domain="gateway",
            target_domain="semantic",
            authority_weight="medium",
            budget_consumed={"chars": 999, "items": 99},
            overflow=True,
            truncated=True,
            degraded=True,
            rejected=False,
            path_depth=1,
        )
    )
    summary = get_overflow_summary()
    assert summary["budget_overflows_total"] == 1
    assert summary["overflow_by_domain"].get("semantic") == 1
