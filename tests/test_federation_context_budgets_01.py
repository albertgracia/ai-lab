"""FEDERATION-CONTEXT-BUDGETS-01: deterministic budget enforcement tests."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/ai-lab")

from runtime.federation.context_budget import (
    ContextOverflowPolicy,
    compute_budget_consumption,
    default_domain_limits,
    enforce_context_budget,
)


def test_compute_budget_consumption_is_deterministic():
    payload = {"a": "x" * 10, "b": ["y", "z"], "c": {"k": "v"}}
    c1 = compute_budget_consumption(payload)
    c2 = compute_budget_consumption(payload)
    assert c1 == c2


def test_authority_overflow_is_rejected_and_degraded():
    limits = default_domain_limits()
    assert limits.authority.overflow_policy == ContextOverflowPolicy.REJECT
    env = enforce_context_budget(domain="authority", payload={"blob": "x" * 5000}, limits=limits)
    assert env.rejected is True
    assert env.degraded is True
    assert env.payload == {}
    assert env.overflow["chars"] > 0


def test_observability_overflow_is_truncated_deterministically():
    limits = default_domain_limits()
    env = enforce_context_budget(domain="observability", payload={"events": [str(i) for i in range(1000)]}, limits=limits)
    assert env.rejected is False
    assert env.truncated is True
    assert env.degraded is True
    assert len(env.payload["events"]) == limits.observability.max_items


def test_truncation_preserves_sorted_key_determinism():
    limits = default_domain_limits()
    payload = {"b": [str(i) for i in range(50)], "a": "y" * 5000}
    env1 = enforce_context_budget(domain="tests", payload=payload, limits=limits)
    env2 = enforce_context_budget(domain="tests", payload=payload, limits=limits)
    assert env1.payload == env2.payload
    assert env1.truncated == env2.truncated
