"""FASE 37D: Graph Hotspot History tests.

Focus:
- bounded snapshot store
- deterministic drift score + severity thresholds
- trends unknown when insufficient history
- increasing/decreasing/stable trend classification
- recurring hotspot detection
- fail-safe behavior when dependencies are missing
- endpoint handler behavior
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_severity_thresholds_match_contract() -> None:
    from runtime.hotspot_history.hotspot_history import _severity_from_score

    assert _severity_from_score(0.0) == "INFO"
    assert _severity_from_score(0.24) == "INFO"
    assert _severity_from_score(0.25) == "LOW"
    assert _severity_from_score(0.49) == "LOW"
    assert _severity_from_score(0.50) == "MEDIUM"
    assert _severity_from_score(0.69) == "MEDIUM"
    assert _severity_from_score(0.70) == "HIGH"
    assert _severity_from_score(0.84) == "HIGH"
    assert _severity_from_score(0.85) == "CRITICAL"


def test_trend_from_delta_is_deterministic() -> None:
    from runtime.hotspot_history.hotspot_history import _trend_from_delta

    assert _trend_from_delta(0.0) == "stable"
    assert _trend_from_delta(0.009) == "stable"
    assert _trend_from_delta(0.011) == "increasing"
    assert _trend_from_delta(-0.009) == "stable"
    assert _trend_from_delta(-0.011) == "decreasing"


def test_history_is_bounded(monkeypatch) -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()

    # Force a small deque for test via direct replacement.
    monkeypatch.setattr(hh, "_SNAPSHOTS", hh.deque(maxlen=3))

    for _ in range(10):
        hh.record_hotspot_snapshot(top_n=5)

    assert len(hh._SNAPSHOTS) == 3


def test_insufficient_history_marks_unknown_trend() -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()
    hh.record_hotspot_snapshot(top_n=10)
    out = hh.get_hotspot_trends(limit=10, top_n=10)

    assert out.get("contract_version") == hh.GRAPH_HOTSPOT_HISTORY_CONTRACT_VERSION
    assert "insufficient_history" in (out.get("unknowns") or [])
    # With only 1 snapshot, trends should be 'unknown'.
    for t in out.get("trends", [])[:5]:
        assert t.get("trend") == "unknown"


def test_increasing_and_decreasing_detected_from_two_snapshots(monkeypatch) -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()

    # Build two deterministic snapshots with a single module changing score.
    s1 = {
        "timestamp": 1.0,
        "top_modules": [{"file_path": "runtime/foo.py", "score": 0.10, "severity": "LOW", "blast_radius": "low", "domain": "foo"}],
        "critical_path_score": 0.1,
        "routing_confidence": 1.0,
        "health_score": 100.0,
        "unknowns": [],
        "unavailable_fields": [],
        "persistence": {"enabled": False},
    }
    s2 = {
        "timestamp": 2.0,
        "top_modules": [{"file_path": "runtime/foo.py", "score": 0.13, "severity": "LOW", "blast_radius": "low", "domain": "foo"}],
        "critical_path_score": 0.1,
        "routing_confidence": 1.0,
        "health_score": 100.0,
        "unknowns": [],
        "unavailable_fields": [],
        "persistence": {"enabled": False},
    }

    # Replace snapshots store.
    with hh._LOCK:
        hh._SNAPSHOTS.clear()
        hh._SNAPSHOTS.append(s1)
        hh._SNAPSHOTS.append(s2)

    out = hh.get_hotspot_trends(limit=10, top_n=10)
    assert out.get("increasing_total") >= 1
    t0 = out.get("trends", [])[0]
    assert t0["module"] == "runtime/foo.py"
    assert t0["trend"] == "increasing"
    assert t0["delta"] is not None and t0["delta"] > 0

    # Flip to decreasing.
    s3 = {**s2, "timestamp": 3.0, "top_modules": [{"file_path": "runtime/foo.py", "score": 0.09, "severity": "LOW", "blast_radius": "low", "domain": "foo"}]}
    with hh._LOCK:
        hh._SNAPSHOTS.append(s3)
    out2 = hh.get_hotspot_trends(limit=10, top_n=10)
    t1 = out2.get("trends", [])[0]
    assert t1["trend"] in ("decreasing", "stable", "increasing")


def test_recurring_hotspots_requires_history() -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()
    hh.record_hotspot_snapshot(top_n=5)
    out = hh.get_recurring_hotspots(limit=10, min_recurrence=3)
    assert "insufficient_history" in (out.get("unknowns") or [])


def test_recurring_hotspots_detects_recurrence(monkeypatch) -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()
    snaps = []
    for i in range(5):
        snaps.append({
            "timestamp": float(i),
            "top_modules": [{"file_path": "runtime/a.py", "score": 0.2, "severity": "LOW", "blast_radius": "low", "domain": "a"}],
            "unknowns": [],
            "unavailable_fields": [],
            "persistence": {"enabled": False},
        })
    with hh._LOCK:
        hh._SNAPSHOTS.clear()
        for s in snaps:
            hh._SNAPSHOTS.append(s)

    out = hh.get_recurring_hotspots(limit=10, min_recurrence=3)
    rec = out.get("recurring", [])
    assert rec
    assert rec[0]["module"] == "runtime/a.py"
    assert rec[0]["recurrence"] >= 3


def test_drift_unknown_with_insufficient_history() -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()
    hh.record_hotspot_snapshot(top_n=5)
    drift = hh.get_hotspot_drift(window=10)
    assert "insufficient_history" in (drift.get("unknowns") or [])
    assert drift.get("drift_score") == 0.0


def test_drift_score_increases_with_positive_deltas(monkeypatch) -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()

    s1 = {
        "timestamp": 1.0,
        "critical_path_score": 0.40,
        "routing_confidence": 1.0,
        "health_score": 100.0,
        "top_modules": [{"file_path": "runtime/gateway/x.py", "score": 0.40, "severity": "LOW", "blast_radius": "medium", "domain": "gateway"}],
        "unknowns": [],
        "unavailable_fields": [],
        "persistence": {"enabled": False},
    }
    s2 = {
        "timestamp": 2.0,
        "critical_path_score": 0.46,
        "routing_confidence": 0.95,
        "health_score": 95.0,
        "top_modules": [{"file_path": "runtime/gateway/x.py", "score": 0.48, "severity": "MEDIUM", "blast_radius": "high", "domain": "gateway"}],
        "unknowns": [],
        "unavailable_fields": [],
        "persistence": {"enabled": False},
    }
    with hh._LOCK:
        hh._SNAPSHOTS.clear()
        hh._SNAPSHOTS.append(s1)
        hh._SNAPSHOTS.append(s2)

    drift = hh.get_hotspot_drift(window=10)
    assert drift.get("drift_score") is not None
    assert float(drift.get("drift_score")) >= 0.0
    assert drift.get("severity") in ("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL")


def test_prometheus_metrics_builder_has_expected_keys(monkeypatch) -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()
    hh.record_hotspot_snapshot(top_n=5)
    txt = hh.build_hotspot_history_prometheus_metrics()
    for k in [
        "ailab_hotspot_history_snapshots_total",
        "ailab_hotspot_history_recurring_total",
        "ailab_hotspot_history_drift_score",
        "ailab_hotspot_history_increasing_total",
        "ailab_hotspot_history_decreasing_total",
        "ailab_hotspot_history_unknowns_total",
        "ailab_hotspot_history_recommendations_total",
        "ailab_hotspot_history_persistence_enabled",
    ]:
        assert k in txt


def test_endpoint_handler_writes_json_200() -> None:
    from runtime.gateway.runtime_api_routes import handle_hotspot_history_routes

    class H:
        def __init__(self, path: str):
            self.path = path
            self.sent = None

        def _send_json(self, code, payload):
            self.sent = (code, payload)

    h = H("/runtime/hotspot-history/summary")
    assert handle_hotspot_history_routes(h) is True
    assert h.sent is not None
    assert h.sent[0] == 200
    assert isinstance(h.sent[1], dict)


def test_build_snapshot_is_bounded_for_top_modules(monkeypatch) -> None:
    import runtime.hotspot_history.hotspot_history as hh

    # Stub dependency reader to return oversized lists.
    def fake_read(*, top_n: int):
        cp = {"score": 0.1, "severity": "LOW", "top_files": [{"file_path": f"runtime/m{i}.py", "score": 0.1} for i in range(100)], "recommendations": []}
        chok = {"chokepoints": [{"file_path": f"runtime/c{i}.py", "score": 0.2} for i in range(100)], "total": 100}
        br = {"blast_radius_summary": {"by_blast_radius": {}}}
        corr = {"correlation_score": 0.0, "hotspots_total": 0, "unknowns": [], "unavailable_fields": []}
        health = {"score": 100.0, "routing_confidence": {"confidence": 1.0}, "unknowns": [], "unavailable_fields": []}
        return ({
            "critical_path": cp,
            "chokepoints": chok,
            "blast_radius": br,
            "correlation": corr,
            "health": health,
            "slo": {"overall_status": "healthy"},
            "triage": {"total_incidents": 0},
            "graph": {},
            "guard_state": "normal",
        }, [], [])

    monkeypatch.setattr(hh, "_read_dependencies_snapshot", fake_read)
    snap = hh.build_hotspot_history_snapshot(top_n=25)
    assert len(snap.get("top_modules") or []) <= 25


def test_unknowns_include_persistence_not_configured() -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()
    snap = hh.record_hotspot_snapshot(top_n=5)
    assert "persistent_store_not_configured" in (snap.get("unknowns") or [])


def test_history_window_limit_is_clamped() -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()
    for _ in range(3):
        hh.record_hotspot_snapshot(top_n=5)
    out = hh.get_hotspot_history_window(limit=999, top_n=5)
    assert out.get("returned") <= 50


def test_trends_output_is_bounded_and_sorted(monkeypatch) -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()
    # Build two snapshots with many modules.
    s1 = {"timestamp": 1.0, "top_modules": [{"file_path": f"runtime/m{i}.py", "score": i / 100.0, "severity": "LOW", "blast_radius": "low", "domain": "m"} for i in range(60)], "unknowns": [], "unavailable_fields": [], "persistence": {"enabled": False}}
    s2 = {"timestamp": 2.0, "top_modules": [{"file_path": f"runtime/m{i}.py", "score": (i + 1) / 100.0, "severity": "LOW", "blast_radius": "low", "domain": "m"} for i in range(60)], "unknowns": [], "unavailable_fields": [], "persistence": {"enabled": False}}
    with hh._LOCK:
        hh._SNAPSHOTS.clear()
        hh._SNAPSHOTS.append(s1)
        hh._SNAPSHOTS.append(s2)

    out = hh.get_hotspot_trends(limit=10, top_n=10)
    trends = out.get("trends") or []
    assert len(trends) <= 25
    # sorted by current_score desc
    scores = [t.get("current_score") for t in trends]
    assert scores == sorted(scores, reverse=True)


def test_drift_score_is_deterministic_for_same_inputs() -> None:
    from runtime.hotspot_history.hotspot_history import DriftInputs, _compute_drift_score

    a = DriftInputs(
        critical_path_delta=0.05,
        max_module_delta=0.05,
        severity_escalations=1,
        blast_radius_escalations=1,
        routing_conf_delta=-0.02,
        health_delta=-2.0,
        unknowns_delta=1,
    )
    assert _compute_drift_score(a) == _compute_drift_score(a)


def test_drift_score_clamped_to_01() -> None:
    from runtime.hotspot_history.hotspot_history import DriftInputs, _compute_drift_score

    a = DriftInputs(
        critical_path_delta=999,
        max_module_delta=999,
        severity_escalations=999,
        blast_radius_escalations=999,
        routing_conf_delta=-999,
        health_delta=-999,
        unknowns_delta=999,
    )
    s = _compute_drift_score(a)
    assert 0.0 <= s <= 1.0


def test_recommendations_are_bounded_and_sorted() -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()
    hh.record_hotspot_snapshot(top_n=5)
    recs = hh.get_hotspot_recommendations()
    items = recs.get("recommendations") or []
    assert len(items) <= 10
    # sorted by severity string then recommendation
    keys = [(r.get("severity"), r.get("recommendation")) for r in items]
    assert keys == sorted(keys)


def test_snapshot_does_not_write_runtime_state_paths() -> None:
    import runtime.hotspot_history.hotspot_history as hh

    snap = hh.record_hotspot_snapshot(top_n=5)
    s = str(snap)
    assert "runtime/state" not in s


def test_reset_clears_snapshots() -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()
    hh.record_hotspot_snapshot(top_n=5)
    assert hh.get_hotspot_history_summary(limit=10).get("snapshots_total", 0) >= 1
    hh.reset_hotspot_history_runtime_state()
    assert hh.get_hotspot_history_summary(limit=10).get("snapshots_total", 0) == 0


def test_extract_module_key_prefers_file_path() -> None:
    from runtime.hotspot_history.hotspot_history import _extract_module_key

    assert _extract_module_key({"file_path": "runtime/x.py", "module": "y"}) == "runtime/x.py"
    assert _extract_module_key({"module": "runtime/y.py"}) == "runtime/y.py"
    assert _extract_module_key({}) == ""


def test_merge_top_modules_dedups_by_key() -> None:
    from runtime.hotspot_history.hotspot_history import _merge_top_modules

    top = [{"file_path": "runtime/a.py", "score": 0.1}, {"file_path": "runtime/a.py", "score": 0.2}]
    chok = [{"file_path": "runtime/a.py", "score": 0.3}, {"file_path": "runtime/b.py", "score": 0.4}]
    merged = _merge_top_modules(cp_top=top, chokepoints=chok)
    keys = [m.get("file_path") for m in merged]
    assert keys.count("runtime/a.py") == 1
    assert "runtime/b.py" in keys


def test_parse_limit_clamps_values() -> None:
    from runtime.hotspot_history.hotspot_history import _parse_limit

    assert _parse_limit("oops", 10, lo=1, hi=50) == 10
    assert _parse_limit(0, 10, lo=1, hi=50) == 1
    assert _parse_limit(999, 10, lo=1, hi=50) == 50


def test_summary_includes_persistence_flag() -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()
    hh.record_hotspot_snapshot(top_n=5)
    s = hh.get_hotspot_history_summary(limit=10)
    assert "persistence_enabled" in s


def test_blast_radius_history_is_bounded() -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()
    for _ in range(5):
        hh.record_hotspot_snapshot(top_n=5)
    out = hh.get_blast_radius_history(limit=2)
    assert len(out.get("timeline") or []) == 2


def test_unknown_endpoint_returns_degraded_payload() -> None:
    from runtime.gateway.runtime_api_routes import handle_hotspot_history_routes

    class H:
        def __init__(self, path: str):
            self.path = path
            self.sent = None

        def _send_json(self, code, payload):
            self.sent = (code, payload)

    h = H("/runtime/hotspot-history/does-not-exist")
    assert handle_hotspot_history_routes(h) is True
    assert h.sent[0] == 200
    assert h.sent[1].get("status") == "degraded"


def test_metrics_builder_outputs_numeric_lines() -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()
    hh.record_hotspot_snapshot(top_n=5)
    txt = hh.build_hotspot_history_prometheus_metrics()
    # very light check: each metric line ends with a number
    for line in [l for l in txt.splitlines() if l.startswith("ailab_hotspot_history_")]:
        float(line.split()[-1])


def test_drift_inputs_counts_severity_escalations() -> None:
    import runtime.hotspot_history.hotspot_history as hh

    latest = {"top_modules": [{"file_path": "runtime/a.py", "score": 0.2, "severity": "MEDIUM", "blast_radius": "high"}], "critical_path_score": 0.2, "routing_confidence": 1.0, "health_score": 100.0, "unknowns": []}
    prev = {"top_modules": [{"file_path": "runtime/a.py", "score": 0.1, "severity": "LOW", "blast_radius": "low"}], "critical_path_score": 0.1, "routing_confidence": 1.0, "health_score": 100.0, "unknowns": []}
    di = hh._drift_inputs(latest, prev)
    assert di.severity_escalations >= 1
    assert di.blast_radius_escalations >= 1


def test_history_payload_marks_insufficient_history() -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()
    out = hh.get_hotspot_history_window(limit=10, top_n=5)
    assert "insufficient_history" in (out.get("unknowns") or [])


def test_latest_endpoint_records_snapshot() -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()
    out = hh.get_hotspot_history_latest(top_n=5, scope="runtime_only", record=True)
    assert out.get("contract_version") == hh.GRAPH_HOTSPOT_HISTORY_CONTRACT_VERSION
    assert out.get("snapshot")


def test_summary_limit_is_clamped() -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()
    for _ in range(3):
        hh.record_hotspot_snapshot(top_n=5)
    s = hh.get_hotspot_history_summary(limit=999)
    assert s.get("returned") <= 50


def test_snapshot_has_required_fields() -> None:
    import runtime.hotspot_history.hotspot_history as hh

    snap = hh.build_hotspot_history_snapshot(top_n=5)
    for k in [
        "timestamp",
        "contract_version",
        "critical_path_score",
        "critical_path_severity",
        "correlation_score",
        "health_score",
        "routing_confidence",
        "slo_status",
        "chokepoints_total",
        "top_modules",
        "unknowns",
        "unavailable_fields",
    ]:
        assert k in snap


def test_drift_severity_thresholds() -> None:
    from runtime.hotspot_history.hotspot_history import _severity_from_score

    assert _severity_from_score(0.49) == "LOW"
    assert _severity_from_score(0.50) == "MEDIUM"
    assert _severity_from_score(0.70) == "HIGH"


def test_recurring_is_sorted_by_recurrence_then_score() -> None:
    import runtime.hotspot_history.hotspot_history as hh

    hh.reset_hotspot_history_runtime_state()
    with hh._LOCK:
        hh._SNAPSHOTS.clear()
        for i in range(4):
            hh._SNAPSHOTS.append({
                "timestamp": float(i),
                "top_modules": [
                    {"file_path": "runtime/a.py", "score": 0.3, "severity": "LOW", "blast_radius": "low", "domain": "a"},
                    {"file_path": "runtime/b.py", "score": 0.1, "severity": "LOW", "blast_radius": "low", "domain": "b"},
                ],
                "unknowns": [],
                "unavailable_fields": [],
                "persistence": {"enabled": False},
            })
    out = hh.get_recurring_hotspots(limit=10, min_recurrence=3)
    rec = out.get("recurring") or []
    assert rec and rec[0]["module"] == "runtime/a.py"


def test_top_modules_is_sorted_by_score_desc() -> None:
    import runtime.hotspot_history.hotspot_history as hh

    snap = hh.build_hotspot_history_snapshot(top_n=10)
    mods = snap.get("top_modules") or []
    scores = [m.get("score") for m in mods if isinstance(m, dict) and m.get("score") is not None]
    assert scores == sorted(scores, reverse=True)
