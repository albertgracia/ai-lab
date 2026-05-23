"""CORE-HARDENING-FEDERATION-GUARDS-01: federation guard tests."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/ai-lab")

from runtime.federation.federation_guards import (
    build_guard_summary,
    validate_federation_metadata,
)


def _valid_meta(domain: str = "observability") -> dict:
    return {
        "_federation": {
            "contract_version": "BOOTSTRAP-01",
            "domain": domain,
            "role": domain,
            "delegated_to": domain,
            "reason": "keyword_match",
            "authority_weight": "medium",
        },
        "_domain": domain,
        "_role": domain,
        "_delegated_to": domain,
        "_reasoning_scope": "bounded",
        "_context_budget": {"max_chars": 900, "max_items": 10, "overflow_policy": "truncate"},
        "_budget_consumed": {domain: {"chars": 10, "items": 2}},
        "_budget_remaining": {domain: {"chars": 890, "items": 8}},
        "_budget_overflow": {domain: {"chars": 0, "items": 0}},
        "_truncated_domains": [],
    }


def test_valid_metadata_is_ok():
    res = validate_federation_metadata(_valid_meta())
    assert res.ok is True
    assert res.degraded is False
    assert res.status == "ok"
    summary = build_guard_summary(res)
    assert summary["status"] == "ok"
    assert summary["violations_total"] == 0


def test_unknown_domain_degrades_safely():
    meta = _valid_meta(domain="unknown_domain")
    res = validate_federation_metadata(meta)
    assert res.ok is False
    assert res.degraded is True
    assert "unknown_domain" in " ".join(res.reason_codes)


def test_delegation_to_remediation_is_critical():
    meta = _valid_meta(domain="observability")
    meta["_delegated_to"] = "remediation"
    meta["_federation"]["delegated_to"] = "remediation"
    res = validate_federation_metadata(meta)
    assert res.degraded is True
    assert any(v.code == "delegation_to_remediation_forbidden" for v in res.violations)


def test_missing_budget_metadata_is_detected():
    meta = _valid_meta(domain="authority")
    meta.pop("_context_budget", None)
    res = validate_federation_metadata(meta)
    assert res.degraded is True
    assert any(v.code == "missing_context_budget" for v in res.violations)


def test_overflow_not_marked_is_detected():
    meta = _valid_meta(domain="semantic")
    meta["_budget_overflow"]["semantic"] = {"chars": 10, "items": 0}
    meta["_truncated_domains"] = []
    res = validate_federation_metadata(meta)
    assert res.degraded is True
    assert any(v.code == "overflow_not_marked" for v in res.violations)


def test_guard_never_raises_on_malformed_input():
    # Meta is wrong types but guard must return degraded, not raise.
    res = validate_federation_metadata({"_budget_overflow": "oops"})
    assert res.degraded is True
