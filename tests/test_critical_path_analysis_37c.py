"""FASE 37C: Critical Path Analysis tests.

Focus:
- deterministic severity classification
- bounded outputs
- fail-safe snapshot builder
- Prometheus metrics exposure
- endpoint handler behavior
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_severity_classification_is_deterministic() -> None:
    from runtime.critical_path.critical_path_analysis import _severity_from_score

    assert _severity_from_score(0.0) == "INFO"
    assert _severity_from_score(0.24) == "INFO"
    assert _severity_from_score(0.25) == "LOW"
    assert _severity_from_score(0.49) == "LOW"
    assert _severity_from_score(0.50) == "MEDIUM"
    assert _severity_from_score(0.69) == "MEDIUM"
    assert _severity_from_score(0.70) == "HIGH"
    assert _severity_from_score(0.84) == "HIGH"
    assert _severity_from_score(0.85) == "CRITICAL"


def test_snapshot_builder_is_fail_safe_and_bounded(monkeypatch) -> None:
    import runtime.critical_path.critical_path_analysis as cpa

    # Speed up test: scan fewer files.
    monkeypatch.setattr(cpa, "_MAX_SCAN_FILES", 60)

    snap = cpa.build_critical_path_snapshot(top_n=10)
    assert isinstance(snap, dict)
    assert snap.get("contract_version") == cpa.CRITICAL_PATH_CONTRACT_VERSION
    top = snap.get("top_files") or []
    assert isinstance(top, list)
    assert len(top) <= 10
    assert "domain_summary" in snap
    assert "recommendations" in snap


def test_unknowns_not_hidden_when_sources_missing(monkeypatch) -> None:
    import runtime.critical_path.critical_path_analysis as cpa

    monkeypatch.setattr(cpa, "_read_health", lambda: None)
    monkeypatch.setattr(cpa, "_read_graph_hotspots", lambda: None)
    snap = cpa.build_critical_path_snapshot(top_n=5)
    unk = set(snap.get("unknowns") or [])
    assert "cognitive_health_unavailable" in unk
    assert "graph_hotspots_unavailable" in unk


def test_prometheus_metrics_builder_has_expected_keys(monkeypatch) -> None:
    import runtime.critical_path.critical_path_analysis as cpa

    monkeypatch.setattr(cpa, "_MAX_SCAN_FILES", 60)
    text = cpa.build_critical_path_prometheus_metrics()
    for k in [
        "ailab_critical_path_score",
        "ailab_critical_path_top_modules_total",
        "ailab_critical_path_high_total",
        "ailab_critical_path_critical_total",
        "ailab_critical_path_unknowns_total",
        "ailab_critical_path_routes_critical_total",
        "ailab_critical_path_recommendations_total",
    ]:
        assert k in text


def test_dependencies_endpoint_normalizes_runtime_prefix(monkeypatch) -> None:
    import runtime.critical_path.critical_path_analysis as cpa

    monkeypatch.setattr(cpa, "_MAX_SCAN_FILES", 60)
    out = cpa.get_critical_path_dependencies(file_path="gateway/openai_gateway.py")
    assert out.get("status") in ("ok", "degraded")
    assert out.get("contract_version") == cpa.CRITICAL_PATH_CONTRACT_VERSION
    assert str(out.get("file_path") or "").startswith("runtime/")


def test_endpoint_handler_writes_json_200() -> None:
    from runtime.gateway.runtime_api_routes import handle_critical_path_routes

    class H:
        def __init__(self, path: str):
            self.path = path
            self.sent = None

        def _send_json(self, code, payload):
            self.sent = (code, payload)

    h = H("/runtime/critical-path/summary")
    assert handle_critical_path_routes(h) is True
    assert h.sent is not None
    assert h.sent[0] == 200
    assert isinstance(h.sent[1], dict)
