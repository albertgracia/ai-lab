"""FEDERATION-ROLE-EXECUTION-01: federated role routing tests.

These tests validate minimal delegation metadata without introducing:
- remediation execution
- loops
- forbidden coupling
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/ai-lab")

from runtime.federation.contracts import DelegationReason, FederatedExecutionIntent
from runtime.federation.role_router import build_routing_metadata, resolve_role


def test_routes_observability_on_metrics_keywords():
    intent = FederatedExecutionIntent(user_text="prometheus targets down y latencia p95", route_family="unknown")
    decision = resolve_role(intent)
    assert decision.domain == "observability"
    assert decision.reason == DelegationReason.KEYWORD_MATCH
    assert decision.context_budget.max_chars <= 1200


def test_routes_authority_on_operational_truth_keywords():
    intent = FederatedExecutionIntent(user_text="operational truth y freshness de authority", route_family="unknown")
    decision = resolve_role(intent)
    assert decision.domain == "authority"
    assert decision.delegated_to == "authority"


def test_routes_semantic_on_discoverable_keywords():
    intent = FederatedExecutionIntent(user_text="discoverable-only vs operational y stale", route_family="unknown")
    decision = resolve_role(intent)
    assert decision.domain == "semantic"


def test_routes_incidents_on_incident_keywords():
    intent = FederatedExecutionIntent(user_text="RCA del incidente P1 con timeline", route_family="unknown")
    decision = resolve_role(intent)
    assert decision.domain == "incidents"


def test_routes_infrastructure_on_systemd_time_keywords():
    intent = FederatedExecutionIntent(user_text="time semantics NTP y systemd services", route_family="unknown")
    decision = resolve_role(intent)
    assert decision.domain == "infrastructure"


def test_remediation_markers_are_safety_blocked_to_operator_intent():
    intent = FederatedExecutionIntent(user_text="haz systemctl restart ailab-gateway", route_family="unknown")
    decision = resolve_role(intent)
    assert decision.domain == "operator_intent"
    assert decision.reason == DelegationReason.SAFETY_BLOCK


def test_metadata_is_non_invasive_and_has_required_keys():
    intent = FederatedExecutionIntent(user_text="prometheus metrics", route_family="observe", request_id="req-1")
    meta = build_routing_metadata(intent)
    # Metadata is allowed to grow, but must include the non-invasive core keys.
    for k in (
        "_federation",
        "_domain",
        "_role",
        "_delegated_to",
        "_reasoning_scope",
        "_context_budget",
    ):
        assert k in meta
    assert meta["_federation"]["domain"] == meta["_domain"]
    assert meta["_federation"]["delegated_to"] == meta["_delegated_to"]
    assert meta["_delegated_to"] != "remediation"
