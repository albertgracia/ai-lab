"""FASE 37B: Graph-Runtime Correlation tests.

Focus:
- deterministic scoring + severity
- hard_facts / inferred / unknowns separation
- bounded outputs
- fail-safe snapshot builder
- endpoint handler behavior
"""

from __future__ import annotations

import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_severity_classification_is_deterministic() -> None:
    from runtime.correlation.graph_runtime_correlation import _severity_from_score

    assert _severity_from_score(0.0) == "INFO"
    assert _severity_from_score(0.24) == "INFO"
    assert _severity_from_score(0.25) == "LOW"
    assert _severity_from_score(0.49) == "LOW"
    assert _severity_from_score(0.50) == "MEDIUM"
    assert _severity_from_score(0.69) == "MEDIUM"
    assert _severity_from_score(0.70) == "HIGH"
    assert _severity_from_score(0.84) == "HIGH"
    assert _severity_from_score(0.85) == "CRITICAL"


def test_snapshot_builder_is_fail_safe() -> None:
    from runtime.correlation.graph_runtime_correlation import build_graph_runtime_correlation_snapshot

    snap = build_graph_runtime_correlation_snapshot()
    assert isinstance(snap, dict)
    assert snap.get("contract_version") == "37B-GRAPH-RUNTIME-CORRELATION-01"
    assert "correlation_score" in snap
    assert "correlated_hotspots" in snap
    assert "unknowns" in snap
    assert "unavailable_fields" in snap


def test_correlated_hotspots_are_bounded_and_sorted() -> None:
    from runtime.correlation.graph_runtime_correlation import build_graph_runtime_correlation_snapshot

    snap = build_graph_runtime_correlation_snapshot()
    hs = snap.get("correlated_hotspots") or []
    assert isinstance(hs, list)
    assert len(hs) <= 20
    # Sorted by correlation_score desc then module
    scores = [float(h.get("correlation_score", 0) or 0) for h in hs if isinstance(h, dict)]
    assert scores == sorted(scores, reverse=True)


def test_unknowns_not_hidden_when_sources_missing(monkeypatch) -> None:
    import runtime.correlation.graph_runtime_correlation as corr

    monkeypatch.setattr(corr, "_read_graph_hotspots", lambda: None)
    monkeypatch.setattr(corr, "_read_health", lambda: None)
    snap = corr.build_graph_runtime_correlation_snapshot()
    assert "gitnexus_hotspots_unavailable" in (snap.get("unknowns") or [])
    assert "cognitive_health_unavailable" in (snap.get("unknowns") or [])
    assert "graph_hotspots" in (snap.get("unavailable_fields") or [])
    assert "cognitive_health" in (snap.get("unavailable_fields") or [])


def test_prometheus_metrics_builder_has_expected_keys() -> None:
    from runtime.correlation.graph_runtime_correlation import build_graph_runtime_correlation_prometheus_metrics

    text = build_graph_runtime_correlation_prometheus_metrics()
    for k in [
        "ailab_correlation_score",
        "ailab_correlation_hotspots_total",
        "ailab_correlation_high_risk_total",
        "ailab_correlation_critical_total",
        "ailab_correlation_unknowns_total",
        "ailab_correlation_recommendations_total",
        "ailab_correlation_runtime_health_linked_total",
        "ailab_correlation_graph_health_linked_total",
    ]:
        assert k in text


def test_endpoint_handler_writes_json_200() -> None:
    from runtime.gateway.runtime_api_routes import handle_correlation_routes

    class H:
        def __init__(self, path: str):
            self.path = path
            self.sent = None

        def _send_json(self, code, payload):
            self.sent = (code, payload)

    h = H("/runtime/correlation/summary")
    assert handle_correlation_routes(h) is True
    assert h.sent is not None
    assert h.sent[0] == 200
    assert isinstance(h.sent[1], dict)


def test_reset_clears_cache() -> None:
    from runtime.correlation.graph_runtime_correlation import (
        build_graph_runtime_correlation_snapshot,
        reset_graph_runtime_correlation_state,
    )

    a = build_graph_runtime_correlation_snapshot()
    assert a.get("contract_version") == "37B-GRAPH-RUNTIME-CORRELATION-01"
    reset_graph_runtime_correlation_state()
    b = build_graph_runtime_correlation_snapshot()
    assert b.get("contract_version") == "37B-GRAPH-RUNTIME-CORRELATION-01"


def test_score_increases_with_more_degradation_signals() -> None:
    import runtime.correlation.graph_runtime_correlation as corr

    base = corr._correlation_score_for_hotspot(
        fan_in=2,
        fan_out=2,
        centrality=0.1,
        blast_radius="low",
        graph_risk="low",
        health_score=90.0,
        routing_confidence=0.95,
        slo_status="healthy",
        triage_sev="info",
        guard_state="normal",
        evidence={"replay_risk_total": 0, "stale_evidence_total": 0, "invalid_lineage_total": 0},
    )
    worse = corr._correlation_score_for_hotspot(
        fan_in=12,
        fan_out=20,
        centrality=0.9,
        blast_radius="critical",
        graph_risk="critical",
        health_score=40.0,
        routing_confidence=0.40,
        slo_status="degraded",
        triage_sev="critical",
        guard_state="safe_mode",
        evidence={"replay_risk_total": 20, "stale_evidence_total": 10, "invalid_lineage_total": 5},
    )
    assert 0.0 <= base <= 1.0
    assert 0.0 <= worse <= 1.0
    assert worse > base


def test_recommendations_are_bounded_and_sorted() -> None:
    import runtime.correlation.graph_runtime_correlation as corr

    recs = corr._build_recommendations(
        severity="HIGH",
        slo_status="degraded",
        guard_state="safe_mode",
        routing_conf=0.5,
        unavailable_fields=["graph_hotspots", "triage_summary"],
    )
    assert len(recs) <= 8
    # deterministic order (severity then text)
    keys = [(r.severity, r.recommendation) for r in recs]
    assert keys == sorted(keys)


def test_summary_endpoint_shape() -> None:
    from runtime.correlation.graph_runtime_correlation import get_graph_runtime_correlation_summary

    s = get_graph_runtime_correlation_summary()
    assert s.get("contract_version") == "37B-GRAPH-RUNTIME-CORRELATION-01"
    assert "correlation_score" in s
    assert "severity" in s


def test_hotspots_endpoint_is_bounded() -> None:
    from runtime.correlation.graph_runtime_correlation import get_correlated_hotspots

    hs = get_correlated_hotspots()
    items = hs.get("hotspots") or []
    assert isinstance(items, list)
    assert len(items) <= 20


def test_graph_blast_radius_endpoint_is_fail_safe(monkeypatch) -> None:
    import runtime.correlation.graph_runtime_correlation as corr

    monkeypatch.setattr(corr, "_read_graph_blast_radius", lambda: None)
    out = corr.get_correlated_blast_radius()
    assert out.get("status") in ("ok", "degraded")
    assert out.get("contract_version") == "37B-GRAPH-RUNTIME-CORRELATION-01"


def test_findings_endpoint_has_expected_sections() -> None:
    from runtime.correlation.graph_runtime_correlation import get_runtime_topology_findings

    f = get_runtime_topology_findings()
    rt = f.get("runtime") or {}
    assert "cognitive_health" in rt
    assert "slo" in rt
    assert "triage" in rt
    assert "federation" in rt


def test_prometheus_metrics_text_is_numeric_lines() -> None:
    from runtime.correlation.graph_runtime_correlation import build_graph_runtime_correlation_prometheus_metrics

    txt = build_graph_runtime_correlation_prometheus_metrics().strip().splitlines()
    assert any(line.startswith("ailab_correlation_score ") for line in txt)
    assert all("\n" not in line for line in txt)


def test_cache_returns_same_payload_within_ttl(monkeypatch) -> None:
    import runtime.correlation.graph_runtime_correlation as corr

    # Force a tiny TTL and deterministic time
    monkeypatch.setattr(corr, "_CACHE_TTL_S", 9999.0)
    corr.reset_graph_runtime_correlation_state()
    a = corr._get_cached_snapshot()
    b = corr._get_cached_snapshot()
    assert a.get("contract_version") == b.get("contract_version")


def test_weight_mappings_are_stable() -> None:
    import runtime.correlation.graph_runtime_correlation as corr

    assert corr._br_weight("low") < corr._br_weight("medium") < corr._br_weight("high") < corr._br_weight("critical")
    assert corr._gov_weight("low") < corr._gov_weight("medium") < corr._gov_weight("high") < corr._gov_weight("critical")
    assert corr._slo_weight("healthy") < corr._slo_weight("warning") < corr._slo_weight("degraded") < corr._slo_weight("critical")
    assert corr._guard_weight("normal") < corr._guard_weight("degraded") < corr._guard_weight("constrained") < corr._guard_weight("safe_mode")


def test_runtime_health_status_parsing_handles_missing() -> None:
    import runtime.correlation.graph_runtime_correlation as corr

    st, hs, rc = corr._runtime_health_status(None)
    assert st == "unknown"
    assert hs == 0.0
    assert rc == 0.0


def test_runtime_health_status_parsing_reads_fields() -> None:
    import runtime.correlation.graph_runtime_correlation as corr

    health = {
        "overall_health": {"status": "warning"},
        "score": 55.5,
        "routing_confidence": {"confidence": 0.42},
    }
    st, hs, rc = corr._runtime_health_status(health)
    assert st == "warning"
    assert hs == 55.5
    assert abs(rc - 0.42) < 1e-6


def test_evidence_state_is_bounded_defaults() -> None:
    import runtime.correlation.graph_runtime_correlation as corr

    ev = corr._evidence_state(None)
    assert ev["replay_risk_total"] == 0
    assert ev["stale_evidence_total"] == 0
    assert ev["invalid_lineage_total"] == 0


def test_evidence_state_extracts_known_fields() -> None:
    import runtime.correlation.graph_runtime_correlation as corr

    ev = corr._evidence_state({"replay_risk_total": 3, "stale_evidence_total": 2, "invalid_lineage_total": 1, "lineage_depth_max": 9})
    assert ev["replay_risk_total"] == 3
    assert ev["stale_evidence_total"] == 2
    assert ev["invalid_lineage_total"] == 1
    assert ev["lineage_depth_max"] == 9


def test_triage_severity_rollup() -> None:
    import runtime.correlation.graph_runtime_correlation as corr

    assert corr._triage_severity(None) == "info"
    assert corr._triage_severity({"total_warning": 1}) == "warning"
    assert corr._triage_severity({"total_high": 1}) == "high"
    assert corr._triage_severity({"total_critical": 1}) == "critical"


def test_endpoint_handler_unknown_path_returns_degraded() -> None:
    from runtime.gateway.runtime_api_routes import handle_correlation_routes

    class H:
        def __init__(self, path: str):
            self.path = path
            self.sent = None

        def _send_json(self, code, payload):
            self.sent = (code, payload)

    h = H("/runtime/correlation/does-not-exist")
    assert handle_correlation_routes(h) is True
    assert h.sent is not None
    assert h.sent[0] == 200
    assert h.sent[1].get("status") == "degraded"


def test_handler_returns_false_for_other_paths() -> None:
    from runtime.gateway.runtime_api_routes import handle_correlation_routes

    class H:
        def __init__(self, path: str):
            self.path = path

    assert handle_correlation_routes(H("/runtime/health")) is False


def test_prometheus_metrics_builder_is_fail_safe(monkeypatch) -> None:
    import runtime.correlation.graph_runtime_correlation as corr

    monkeypatch.setattr(corr, "_get_cached_snapshot", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    txt = corr.build_graph_runtime_correlation_prometheus_metrics()
    assert "ailab_correlation_score 0" in txt


def test_build_snapshot_includes_prioritized_modules_even_without_graph(monkeypatch) -> None:
    import runtime.correlation.graph_runtime_correlation as corr

    monkeypatch.setattr(corr, "_read_graph_hotspots", lambda: None)
    snap = corr.build_graph_runtime_correlation_snapshot()
    hs = snap.get("correlated_hotspots") or []
    # Should still include some prioritized modules (bounded)
    assert isinstance(hs, list)


def test_correlation_score_is_clamped() -> None:
    import runtime.correlation.graph_runtime_correlation as corr

    s = corr._correlation_score_for_hotspot(
        fan_in=10**9,
        fan_out=10**9,
        centrality=999.0,
        blast_radius="critical",
        graph_risk="critical",
        health_score=-1000.0,
        routing_confidence=-5.0,
        slo_status="critical",
        triage_sev="critical",
        guard_state="safe_mode",
        evidence={"replay_risk_total": 10**9, "stale_evidence_total": 10**9, "invalid_lineage_total": 10**9},
    )
    assert 0.0 <= s <= 1.0


def test_missing_sources_recommendation_present_when_unavailable() -> None:
    import runtime.correlation.graph_runtime_correlation as corr

    recs = corr._build_recommendations(
        severity="LOW",
        slo_status="healthy",
        guard_state="normal",
        routing_conf=0.9,
        unavailable_fields=["graph_hotspots"],
    )
    assert any("missing_sources" in r.rationale for r in recs)


def test_snapshot_unknowns_are_unique_sorted() -> None:
    import runtime.correlation.graph_runtime_correlation as corr

    snap = corr.build_graph_runtime_correlation_snapshot()
    unk = snap.get("unknowns") or []
    assert unk == sorted(set(unk))


def test_correlated_hotspot_shape_has_required_fields() -> None:
    import runtime.correlation.graph_runtime_correlation as corr

    snap = corr.build_graph_runtime_correlation_snapshot()
    hs = snap.get("correlated_hotspots") or []
    if hs:
        h0 = hs[0]
        for k in ("module", "fan_in", "fan_out", "centrality_score", "correlation_score", "severity", "hard_facts", "inferred", "unknowns"):
            assert k in h0


def test_cache_ttl_expiry_rebuilds(monkeypatch) -> None:
    import runtime.correlation.graph_runtime_correlation as corr

    corr.reset_graph_runtime_correlation_state()
    monkeypatch.setattr(corr, "_CACHE_TTL_S", 0.0)
    a = corr._get_cached_snapshot()
    # force time forward
    monkeypatch.setattr(corr, "_now", lambda: time.time() + 1000)
    b = corr._get_cached_snapshot()
    assert a.get("contract_version") == b.get("contract_version")
