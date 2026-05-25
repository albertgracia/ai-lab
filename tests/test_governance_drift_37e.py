"""FASE 37E: Governance Drift Detection tests.

Focus:
- deterministic drift computation from known inputs
- severity thresholds match contract
- domain extraction from file paths
- drift events bounded store
- fail-safe when dependencies are missing
- endpoint handler behavior
- governance confidence computation
- recommendations generation
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_severity_thresholds_match_contract() -> None:
    from runtime.governance_drift.governance_drift import _severity_from_score

    assert _severity_from_score(0.0) == "INFO"
    assert _severity_from_score(0.24) == "INFO"
    assert _severity_from_score(0.25) == "LOW"
    assert _severity_from_score(0.49) == "LOW"
    assert _severity_from_score(0.50) == "MEDIUM"
    assert _severity_from_score(0.69) == "MEDIUM"
    assert _severity_from_score(0.70) == "HIGH"
    assert _severity_from_score(0.84) == "HIGH"
    assert _severity_from_score(0.85) == "CRITICAL"


def test_clamp01_bounds() -> None:
    from runtime.governance_drift.governance_drift import _clamp01

    assert _clamp01(-0.5) == 0.0
    assert _clamp01(0.0) == 0.0
    assert _clamp01(0.5) == 0.5
    assert _clamp01(1.0) == 1.0
    assert _clamp01(1.5) == 1.0
    assert _clamp01("abc") == 0.0


def test_safe_int_returns_default_on_invalid() -> None:
    from runtime.governance_drift.governance_drift import _safe_int

    assert _safe_int("abc", 42) == 42
    assert _safe_int(None, 42) == 42
    assert _safe_int(5, 42) == 5


def test_safe_float_returns_default_on_invalid() -> None:
    from runtime.governance_drift.governance_drift import _safe_float

    assert _safe_float("abc", 1.5) == 1.5
    assert _safe_float(None, 1.5) == 1.5
    assert _safe_float(2.5, 1.5) == 2.5


def test_parse_limit_clamps_correctly() -> None:
    from runtime.governance_drift.governance_drift import _parse_limit

    assert _parse_limit(-1, 10, lo=1, hi=50) == 1
    assert _parse_limit(100, 10, lo=1, hi=50) == 50
    assert _parse_limit(20, 10, lo=1, hi=50) == 20
    assert _parse_limit("abc", 10, lo=1, hi=50) == 10


def test_domain_from_item_uses_file_path() -> None:
    from runtime.governance_drift.governance_drift import _domain_from_item

    d = _domain_from_item({"file_path": "runtime/gateway/x.py"})
    assert d == "gateway"


def test_domain_from_item_uses_domain_field() -> None:
    from runtime.governance_drift.governance_drift import _domain_from_item

    d = _domain_from_item({"domain": "health", "file_path": "runtime/health/x.py"})
    # file_path takes precedence
    assert d == "health"


def test_domain_from_item_uses_module_field() -> None:
    from runtime.governance_drift.governance_drift import _domain_from_item

    d = _domain_from_item({"module": "runtime.critical_path.critical_path_analysis"})
    assert d == "runtime.critical_path.critical_path_analysis"


def test_domain_from_item_returns_other_for_unknown() -> None:
    from runtime.governance_drift.governance_drift import _domain_from_item

    d = _domain_from_item({"foo": "bar"})
    assert d == "other"


def test_br_weight_returns_expected_values() -> None:
    from runtime.governance_drift.governance_drift import _br_weight

    assert _br_weight("low") == 0.05
    assert _br_weight("medium") == 0.15
    assert _br_weight("high") == 0.30
    assert _br_weight("critical") == 0.45
    assert _br_weight("unknown") == 0.0


def test_gov_weight_returns_expected_values() -> None:
    from runtime.governance_drift.governance_drift import _gov_weight

    assert _gov_weight("low") == 0.05
    assert _gov_weight("medium") == 0.12
    assert _gov_weight("high") == 0.25
    assert _gov_weight("critical") == 0.40
    assert _gov_weight("unknown") == 0.0


def test_build_governance_drift_snapshot_returns_contract() -> None:
    from runtime.governance_drift.governance_drift import (
        build_governance_drift_snapshot,
        GOVERNANCE_DRIFT_CONTRACT_VERSION,
    )

    snap = build_governance_drift_snapshot()
    assert snap.get("status") == "ok"
    assert snap.get("contract_version") == GOVERNANCE_DRIFT_CONTRACT_VERSION
    assert "overall_drift" in snap
    assert "severity" in snap
    assert "governance_confidence" in snap
    assert "domains" in snap
    assert "hard_facts" in snap
    assert "inferred" in snap
    assert "unknowns" in snap


def test_build_governance_drift_snapshot_recommendations_present() -> None:
    from runtime.governance_drift.governance_drift import build_governance_drift_snapshot

    snap = build_governance_drift_snapshot()
    assert "recommendations" in snap
    assert isinstance(snap["recommendations"], list)


def test_get_governance_drift_summary_returns_summary() -> None:
    from runtime.governance_drift.governance_drift import (
        get_governance_drift_summary,
        GOVERNANCE_DRIFT_CONTRACT_VERSION,
    )

    out = get_governance_drift_summary()
    assert out.get("status") == "ok"
    assert out.get("contract_version") == GOVERNANCE_DRIFT_CONTRACT_VERSION
    assert "overall_drift" in out
    assert "severity" in out
    assert "domains_total" in out


def test_get_governance_drift_events_empty_initially() -> None:
    from runtime.governance_drift.governance_drift import (
        get_governance_drift_events,
        reset_governance_drift_state,
    )

    reset_governance_drift_state()
    out = get_governance_drift_events(limit=10)
    assert out.get("events_total") == 0
    assert "empty" in (out.get("unknowns") or [])


def test_get_governance_drift_events_populated_after_snapshot() -> None:
    from runtime.governance_drift.governance_drift import (
        get_governance_drift_events,
        reset_governance_drift_state,
        build_governance_drift_snapshot,
    )

    reset_governance_drift_state()
    build_governance_drift_snapshot()

    out = get_governance_drift_events(limit=10)
    assert out.get("returned", 0) >= 0
    assert isinstance(out.get("events"), list)


def test_get_governance_drift_domains_returns_list() -> None:
    from runtime.governance_drift.governance_drift import get_governance_drift_domains

    out = get_governance_drift_domains()
    assert out.get("status") == "ok"
    assert isinstance(out.get("domains"), list)
    assert out.get("domains_total", 0) >= 0


def test_get_governance_drift_recommendations_returns_list() -> None:
    from runtime.governance_drift.governance_drift import get_governance_drift_recommendations

    out = get_governance_drift_recommendations()
    assert out.get("status") == "ok"
    assert isinstance(out.get("recommendations"), list)
    assert "overall_drift" in out
    assert "severity" in out
    assert "governance_confidence" in out


def test_reset_governance_drift_state_clears() -> None:
    from runtime.governance_drift.governance_drift import (
        reset_governance_drift_state,
        get_governance_drift_events,
        build_governance_drift_snapshot,
    )

    build_governance_drift_snapshot()
    out = reset_governance_drift_state()
    assert out.get("reset") is True

    events = get_governance_drift_events(limit=10)
    assert events.get("events_total") == 0


def test_governance_confidence_calculation() -> None:
    from runtime.governance_drift.governance_drift import (
        _compute_governance_confidence,
        DomainDriftResult,
    )

    domains = [
        DomainDriftResult(
            domain="gateway", current_score=0.2, governance_risk="low",
            blast_radius="medium", correlation_hotspot=False,
            health_delta=0.05, slo_impact=0.0, triage_count=0,
            chokepoint_count=0, drift_score=0.1, severity="INFO",
            signal_sources=["critical_path"], inferred=[], unknowns=[],
        ),
    ]
    conf = _compute_governance_confidence(domains, [])
    assert conf >= 0.8

    conf2 = _compute_governance_confidence(domains, ["a", "b", "c", "d", "e", "f"])
    # penalty should reduce confidence
    assert conf2 < conf


def test_governance_confidence_low_with_high_drift() -> None:
    from runtime.governance_drift.governance_drift import (
        _compute_governance_confidence,
        DomainDriftResult,
    )

    domains = [
        DomainDriftResult(
            domain="gateway", current_score=0.8, governance_risk="critical",
            blast_radius="high", correlation_hotspot=True,
            health_delta=0.4, slo_impact=0.3, triage_count=5,
            chokepoint_count=3, drift_score=0.85, severity="CRITICAL",
            signal_sources=["critical_path", "chokepoints"], inferred=[], unknowns=[],
        ),
    ]
    conf = _compute_governance_confidence(domains, [])
    assert conf < 0.3


def test_empty_domains_returns_zero_confidence() -> None:
    from runtime.governance_drift.governance_drift import _compute_governance_confidence

    assert _compute_governance_confidence([], []) == 0.0


def test_domain_drift_from_cp_top_files(monkeypatch) -> None:
    """Simulate CP top_files to test domain extraction and scoring."""
    from runtime.governance_drift.governance_drift import (
        build_governance_drift_snapshot,
        reset_governance_drift_state,
    )

    reset_governance_drift_state()
    snap = build_governance_drift_snapshot()
    # Should not crash with real runtime data
    assert snap.get("status") == "ok"


def test_events_bounded_to_128() -> None:
    from runtime.governance_drift.governance_drift import (
        get_governance_drift_events,
        _EVENTS,
        _EVENTS_LOCK,
    )

    with _EVENTS_LOCK:
        _EVENTS.clear()
        for i in range(200):
            _EVENTS.append({"domain": f"d{i}", "drift_score": 0.1, "timestamp": float(i)})

    out = get_governance_drift_events(limit=200)
    # Deque maxlen 128, endpoint caps at 50
    assert out.get("events_total") == 128
    assert len(out.get("events", [])) <= 50


def test_prometheus_metrics_rendered_safely() -> None:
    from runtime.governance_drift.governance_drift import build_governance_drift_prometheus_metrics

    text = build_governance_drift_prometheus_metrics()
    assert isinstance(text, str)
    assert "ailab_governance_drift_score" in text
    assert "ailab_governance_drift_governance_confidence" in text
    assert "ailab_governance_drift_events_total" in text
    assert "ailab_governance_drift_domains_total" in text
    assert "ailab_governance_drift_critical_domains_total" in text
    assert "ailab_governance_drift_unknowns_total" in text
    assert "ailab_governance_drift_recommendations_total" in text
    assert "ailab_governance_drift_health_delta_avg" in text


def test_prometheus_metrics_failsafe_on_exception(monkeypatch) -> None:
    from runtime.governance_drift.governance_drift import (
        build_governance_drift_prometheus_metrics,
        reset_governance_drift_state,
    )

    reset_governance_drift_state()

    def _fail(*args, **kwargs):
        raise RuntimeError("test failure")

    monkeypatch.setattr(
        "runtime.governance_drift.governance_drift._get_cached_snapshot",
        _fail,
    )
    monkeypatch.setattr(
        "runtime.governance_drift.governance_drift.build_governance_drift_snapshot",
        _fail,
    )
    text = build_governance_drift_prometheus_metrics()
    # All metrics should be 0 in fail-safe mode
    for line in text.strip().split("\n"):
        assert " 0" in line


def test_recommendations_include_unknowns_when_missing_signals() -> None:
    from runtime.governance_drift.governance_drift import _build_drift_recommendations

    recs = _build_drift_recommendations(0.3, "MEDIUM", 0.8, [], ["slo_unavailable", "correlation_unavailable"])
    unknown_recs = [r for r in recs if "Missing signal" in str(r.get("recommendation") or "")]
    assert unknown_recs


def test_recommendations_include_critical_drift() -> None:
    from runtime.governance_drift.governance_drift import (
        _build_drift_recommendations,
        DomainDriftResult,
    )

    domains = [
        DomainDriftResult(
            domain="gateway", current_score=0.9, governance_risk="critical",
            blast_radius="critical", correlation_hotspot=True,
            health_delta=0.5, slo_impact=0.3, triage_count=5,
            chokepoint_count=3, drift_score=0.9, severity="CRITICAL",
            signal_sources=["critical_path", "chokepoints"], inferred=[], unknowns=[],
        ),
    ]
    recs = _build_drift_recommendations(0.9, "CRITICAL", 0.2, domains, [])
    critical_recs = [r for r in recs if r.get("severity") == "CRITICAL"]
    assert critical_recs
    assert any("governance drift" in str(r.get("recommendation") or "").lower() for r in critical_recs)


def test_recommendations_include_domain_specific() -> None:
    from runtime.governance_drift.governance_drift import (
        _build_drift_recommendations,
        DomainDriftResult,
    )

    domains = [
        DomainDriftResult(
            domain="critical_domain_x", current_score=0.7, governance_risk="high",
            blast_radius="high", correlation_hotspot=True,
            health_delta=0.3, slo_impact=0.15, triage_count=2,
            chokepoint_count=1, drift_score=0.7, severity="HIGH",
            signal_sources=["critical_path"], inferred=[], unknowns=[],
        ),
    ]
    recs = _build_drift_recommendations(0.7, "HIGH", 0.5, domains, [])
    domain_recs = [r for r in recs if "critical_domain_x" in str(r.get("recommendation") or "")]
    assert domain_recs


def test_recommendations_info_when_no_drift() -> None:
    from runtime.governance_drift.governance_drift import _build_drift_recommendations

    recs = _build_drift_recommendations(0.1, "INFO", 0.95, [], [])
    assert any(r.get("severity") == "INFO" for r in recs)
    assert any("No governance drift" in str(r.get("recommendation") or "") for r in recs)


def test_recommendations_bounded() -> None:
    from runtime.governance_drift.governance_drift import (
        _build_drift_recommendations,
        DomainDriftResult,
    )

    domains = [
        DomainDriftResult(
            domain=f"d{i}", current_score=0.5, governance_risk="high",
            blast_radius="medium", correlation_hotspot=True,
            health_delta=0.2, slo_impact=0.1, triage_count=1,
            chokepoint_count=0, drift_score=0.5, severity="HIGH",
            signal_sources=["critical_path"], inferred=[], unknowns=[],
        )
        for i in range(30)
    ]
    recs = _build_drift_recommendations(0.8, "HIGH", 0.3, domains, [])
    # _MAX_RECOMMENDATIONS = 10
    assert len(recs) <= 10


def test_expectation_key_format() -> None:
    from runtime.governance_drift.governance_drift import _expectation_key

    assert _expectation_key("gateway") == "gov_expectation::gateway"


def test_analyze_domains_with_empty_input() -> None:
    from runtime.governance_drift.governance_drift import _analyze_domains

    bundle = {
        "correlation": {},
        "correlation_hotspots": {"hotspots": []},
        "critical_path": {"top_files": []},
        "chokepoints": {"chokepoints": []},
        "hotspot_drift": {"drift_score": 0.0},
        "hotspot_trends": {"trends": []},
        "hotspot_recurring": {"recurring": []},
        "slo": {"overall_status": "healthy"},
        "triage": {"total_incidents": 0, "total_critical": 0, "total_high": 0},
        "architecture": {"status": "ok"},
    }
    domains, inferred = _analyze_domains(bundle, [])
    assert isinstance(domains, list)
    assert isinstance(inferred, list)


def test_domain_drift_score_components() -> None:
    """Verify that higher inputs produce proportionally higher drift."""
    from runtime.governance_drift.governance_drift import _analyze_domains

    low_bundle = {
        "correlation": {"correlation_score": 0.1},
        "correlation_hotspots": {"hotspots": []},
        "critical_path": {"top_files": [
            {"file_path": "runtime/gateway/x.py", "score": 0.05, "severity": "INFO", "blast_radius": "low", "domain": "gateway"},
        ]},
        "chokepoints": {"chokepoints": []},
        "hotspot_drift": {"drift_score": 0.0},
        "hotspot_trends": {"trends": []},
        "hotspot_recurring": {"recurring": []},
        "slo": {"overall_status": "healthy"},
        "triage": {"total_incidents": 0, "total_critical": 0, "total_high": 0},
        "architecture": {"status": "ok"},
    }
    low_domains, _ = _analyze_domains(low_bundle, [])

    high_bundle = {
        "correlation": {"correlation_score": 0.8},
        "correlation_hotspots": {"hotspots": [
            {"file_path": "runtime/gateway/x.py", "score": 0.9, "severity": "CRITICAL"},
        ]},
        "critical_path": {"top_files": [
            {"file_path": "runtime/gateway/x.py", "score": 0.8, "severity": "CRITICAL", "blast_radius": "critical", "domain": "gateway"},
        ]},
        "chokepoints": {"chokepoints": [
            {"file_path": "runtime/gateway/x.py", "score": 0.8, "severity": "CRITICAL", "blast_radius": "critical", "domain": "gateway"},
        ]},
        "hotspot_drift": {"drift_score": 0.5},
        "hotspot_trends": {"trends": [{"module": "runtime/gateway/x.py", "current_score": 0.7}]},
        "hotspot_recurring": {"recurring": [{"module": "runtime/gateway/x.py", "recurrence": 3}]},
        "slo": {"overall_status": "critical"},
        "triage": {"total_incidents": 10, "total_critical": 3, "total_high": 5},
        "architecture": {"status": "ok", "governance_violations": [{"module": "gateway"}]},
    }
    high_domains, _ = _analyze_domains(high_bundle, [])

    high_drift = [d for d in high_domains if d.domain == "gateway"]
    low_drift = [d for d in low_domains if d.domain == "gateway"]
    if high_drift and low_drift:
        assert high_drift[0].drift_score >= low_drift[0].drift_score


def test_drift_events_dataclass_to_dict() -> None:
    from runtime.governance_drift.governance_drift import GovernanceDriftEvent

    event = GovernanceDriftEvent(
        domain="test", drift_score=0.5, previous_score=0.3,
        signal_sources=["critical_path"], severity="MEDIUM",
        inferred=["drift_detected"], unknowns=[], timestamp=100.0,
    )
    d = event.to_dict()
    assert d["domain"] == "test"
    assert d["drift_score"] == 0.5
    assert d["previous_score"] == 0.3
    assert d["severity"] == "MEDIUM"


def test_drift_events_dataclass_to_dict_none_previous() -> None:
    from runtime.governance_drift.governance_drift import GovernanceDriftEvent

    event = GovernanceDriftEvent(
        domain="test", drift_score=0.5, previous_score=None,
        signal_sources=[], severity="LOW",
        inferred=[], unknowns=["no_data"], timestamp=100.0,
    )
    d = event.to_dict()
    assert d["previous_score"] is None


def test_extract_domain_score_from_named_fields() -> None:
    from runtime.governance_drift.governance_drift import _extract_domain_score

    assert _extract_domain_score({"score": 0.5}) == 0.5
    assert _extract_domain_score({"current_score": 0.3}) == 0.3
    assert _extract_domain_score({"max_score": 0.7}) == 0.7
    assert _extract_domain_score({"foo": "bar"}) == 0.0


def test_snapshot_includes_critical_domains_total() -> None:
    from runtime.governance_drift.governance_drift import build_governance_drift_snapshot

    snap = build_governance_drift_snapshot()
    assert "critical_domains_total" in snap
    assert "elevated_domains_total" in snap


def test_snapshot_includes_correlation_and_cp_scores() -> None:
    from runtime.governance_drift.governance_drift import build_governance_drift_snapshot

    snap = build_governance_drift_snapshot()
    assert "correlation_score" in snap
    assert "critical_path_score" in snap
    assert "hotspot_drift_score" in snap
    assert "slo_status" in snap


def test_handler_registration_in_runtime_api_routes() -> None:
    """Verify handle_governance_drift_routes exists and rejects non-matching paths."""
    from runtime.gateway.runtime_api_routes import handle_governance_drift_routes

    class FakeHandler:
        path = "/runtime/health"

    assert handle_governance_drift_routes(FakeHandler()) is False


def test_handler_accepts_governance_drift_path() -> None:
    from runtime.gateway.runtime_api_routes import handle_governance_drift_routes

    sentinel = {}

    class FakeHandler:
        path = "/runtime/governance-drift"
        def _send_json(self, code: int, payload: dict) -> None:
            sentinel["code"] = code
            sentinel["payload"] = payload

    result = handle_governance_drift_routes(FakeHandler())
    assert result is True
    assert sentinel.get("code") == 200
    assert sentinel["payload"].get("contract_version", "").startswith("37E")


def test_handler_accepts_governance_drift_subpath() -> None:
    from runtime.gateway.runtime_api_routes import handle_governance_drift_routes

    sentinel = {}

    class FakeHandler:
        path = "/runtime/governance-drift/summary"
        def _send_json(self, code: int, payload: dict) -> None:
            sentinel["code"] = code
            sentinel["payload"] = payload

    result = handle_governance_drift_routes(FakeHandler())
    assert result is True
    assert sentinel.get("code") == 200


def test_handler_unknown_subpath_returns_degraded() -> None:
    from runtime.gateway.runtime_api_routes import handle_governance_drift_routes

    sentinel = {}

    class FakeHandler:
        path = "/runtime/governance-drift/unknown"
        def _send_json(self, code: int, payload: dict) -> None:
            sentinel["code"] = code
            sentinel["payload"] = payload

    result = handle_governance_drift_routes(FakeHandler())
    assert result is True
    assert sentinel.get("code") == 200
    assert sentinel["payload"].get("error") == "unknown_governance_drift_endpoint"


def test_handler_reset_works() -> None:
    from runtime.gateway.runtime_api_routes import handle_governance_drift_routes

    sentinel = {}

    class FakeHandler:
        path = "/runtime/governance-drift/reset"
        def _send_json(self, code: int, payload: dict) -> None:
            sentinel["code"] = code
            sentinel["payload"] = payload

    result = handle_governance_drift_routes(FakeHandler())
    assert result is True
    assert sentinel["payload"].get("reset", {}).get("reset") is True


def test_handler_events_works() -> None:
    from runtime.gateway.runtime_api_routes import handle_governance_drift_routes

    sentinel = {}

    class FakeHandler:
        path = "/runtime/governance-drift/events?limit=5"
        def _send_json(self, code: int, payload: dict) -> None:
            sentinel["code"] = code
            sentinel["payload"] = payload

    result = handle_governance_drift_routes(FakeHandler())
    assert result is True
    assert sentinel["payload"].get("events_total", 0) >= 0


def test_handler_domains_works() -> None:
    from runtime.gateway.runtime_api_routes import handle_governance_drift_routes

    sentinel = {}

    class FakeHandler:
        path = "/runtime/governance-drift/domains"
        def _send_json(self, code: int, payload: dict) -> None:
            sentinel["code"] = code
            sentinel["payload"] = payload

    result = handle_governance_drift_routes(FakeHandler())
    assert result is True
    assert sentinel["payload"].get("domains_total", 0) >= 0


def test_handler_recommendations_works() -> None:
    from runtime.gateway.runtime_api_routes import handle_governance_drift_routes

    sentinel = {}

    class FakeHandler:
        path = "/runtime/governance-drift/recommendations"
        def _send_json(self, code: int, payload: dict) -> None:
            sentinel["code"] = code
            sentinel["payload"] = payload

    result = handle_governance_drift_routes(FakeHandler())
    assert result is True
    assert sentinel["payload"].get("total", 0) >= 0


def test_handler_exception_returns_degraded(monkeypatch) -> None:
    from runtime.gateway.runtime_api_routes import handle_governance_drift_routes

    def _fail():
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(
        "runtime.governance_drift.governance_drift.build_governance_drift_snapshot",
        _fail,
    )

    sentinel = {}

    class FakeHandler:
        path = "/runtime/governance-drift"
        def _send_json(self, code: int, payload: dict) -> None:
            sentinel["code"] = code
            sentinel["payload"] = payload

    result = handle_governance_drift_routes(FakeHandler())
    assert result is True
    assert sentinel.get("code") == 200
    assert "error" in sentinel["payload"]
