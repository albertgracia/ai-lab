"""OBS-34B: Live Observability Diagnostics tests.

Focus: deterministic diagnostics, exporter classification, incidents,
non-authority rules, always-on APIs.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from http.server import ThreadingHTTPServer

sys.path.insert(0, "/opt/ai-lab")

from runtime.observability.live_diagnostics import (
    run_live_observability_diagnostics,
    diagnose_prometheus_authority,
    diagnose_exporters,
    detect_exporter_flapping,
    diagnose_scrape_health,
    diagnose_grafana_platform,
    diagnose_loki_platform,
    build_observability_incident_summary,
    detect_observability_incidents,
    calculate_live_observability_score,
)


def _assert_json_safe(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            assert isinstance(k, str)
            _assert_json_safe(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _assert_json_safe(v, f"{path}[{i}]")
    elif isinstance(obj, (str, int, float, bool)):
        return
    elif obj is None:
        return
    else:
        raise AssertionError(f"non-JSON-safe type {type(obj)} at {path}")


def _start_gateway_server():
    from runtime.gateway.openai_gateway import GatewayHandler

    server = ThreadingHTTPServer(("127.0.0.1", 0), GatewayHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, port


def _prom_targets_fixture():
    # Minimal Prometheus /api/v1/targets response.
    return {
        "status": "success",
        "data": {
            "activeTargets": [
                {
                    "labels": {"job": "ai-lab-gateway", "instance": "192.168.1.30:8008"},
                    "health": "up",
                    "scrapeInterval": "15s",
                    "lastScrapeDuration": 0.02,
                    "lastError": "",
                },
                {
                    "labels": {"job": "ai-lab-gpu-rx7900xt", "instance": "192.168.1.60:9182"},
                    "health": "down",
                    "scrapeInterval": "15s",
                    "lastScrapeDuration": 0.0,
                    "lastError": "HTTPConnectionPool(host='192.168.1.60', port=9182): Failed to establish a new connection: [Errno 113] No route to host",
                },
                {
                    "labels": {"job": "legacy-exporter", "instance": "192.168.1.250:9999"},
                    "health": "down",
                    "scrapeInterval": "15s",
                    "lastScrapeDuration": 0.0,
                    "lastError": "dial tcp 192.168.1.250:9999: connect: no route to host",
                },
            ],
            "droppedTargets": [],
        },
    }


def _grafana_health_fixture():
    return {"database": "ok", "version": "test"}


def _loki_ready_fixture_ok():
    return {"status": "ok"}


def test_live_diagnostics_generated():
    rep = run_live_observability_diagnostics(
        extra_ctx={"enable_network": False},
        live_prometheus_targets=_prom_targets_fixture(),
        live_prometheus_config={"status": "success", "data": ""},
        live_prometheus_runtimeinfo={"status": "success", "data": {"version": "v2"}},
        live_grafana_health=_grafana_health_fixture(),
        live_loki_ready=_loki_ready_fixture_ok(),
        flapping_changes={},
    )
    assert rep.get("contract_version") == "OBS-34B"
    assert rep.get("deterministic_signature")
    assert "prometheus" in rep and "exporters" in rep and "incidents" in rep


def test_prometheus_authority_diagnostics():
    p = diagnose_prometheus_authority(extra_ctx={"enable_network": False}, live_targets=_prom_targets_fixture(), live_config={}, live_runtimeinfo={})
    assert p["authority"]["absolute"] is True
    assert p["authority"]["type"] == "prometheus"


def test_exporter_classification():
    exp = diagnose_exporters(_prom_targets_fixture(), extra_ctx={}, flapping_changes={})
    cls = exp.get("classification", [])
    assert any(e.get("job") == "ai-lab-gateway" and e.get("status") == "ACTIVE_HEALTHY" for e in cls)


def test_expected_offline_not_incident():
    exp = diagnose_exporters(_prom_targets_fixture(), extra_ctx={}, flapping_changes={})
    rx = next(e for e in exp["classification"] if e.get("job") == "ai-lab-gpu-rx7900xt")
    assert rx.get("status") == "EXPECTED_OFFLINE"
    assert rx.get("runtime_impact") == "none"


def test_no_route_to_host_classified():
    exp = diagnose_exporters(_prom_targets_fixture(), extra_ctx={}, flapping_changes={})
    legacy = next(e for e in exp["classification"] if e.get("job") == "legacy-exporter")
    assert legacy.get("error_type") == "no_route_to_host"
    assert legacy.get("status") in ("UNREACHABLE", "LEGACY_DOWN")


def test_exporter_flapping_detection():
    flap = detect_exporter_flapping({"ai-lab-gateway|192.168.1.30:8008": 5}, threshold_changes=4)
    assert flap.get("flapping_total") == 1


def test_scrape_instability_detection():
    scrape = diagnose_scrape_health(_prom_targets_fixture())
    assert scrape.get("scrape_failures_total") >= 1


def test_grafana_diagnostics_generated():
    g = diagnose_grafana_platform(extra_ctx={"enable_network": False}, live_health=_grafana_health_fixture())
    assert g.get("authority", {}).get("state") == "non_authority"


def test_loki_diagnostics_generated():
    l = diagnose_loki_platform(extra_ctx={"enable_network": False}, live_ready=_loki_ready_fixture_ok())
    assert l.get("authority", {}).get("state") == "dependency"


def test_incident_summary_generated():
    prom = diagnose_prometheus_authority(extra_ctx={"enable_network": False}, live_targets=_prom_targets_fixture(), live_config={}, live_runtimeinfo={})
    exp = diagnose_exporters(_prom_targets_fixture(), extra_ctx={}, flapping_changes={})
    g = diagnose_grafana_platform(extra_ctx={"enable_network": False}, live_health=_grafana_health_fixture())
    l = diagnose_loki_platform(extra_ctx={"enable_network": False}, live_ready=_loki_ready_fixture_ok())
    inc = detect_observability_incidents(prom, exp, g, l)
    summ = build_observability_incident_summary(inc)
    assert "incidents_total" in summ


def test_authority_staleness_detection():
    prom = diagnose_prometheus_authority(extra_ctx={"enable_network": False}, live_targets=_prom_targets_fixture(), live_config={}, live_runtimeinfo={})
    rep = run_live_observability_diagnostics(extra_ctx={"enable_network": False}, live_prometheus_targets=_prom_targets_fixture(), live_grafana_health=_grafana_health_fixture(), live_loki_ready=_loki_ready_fixture_ok())
    st = rep.get("authority_staleness", {})
    assert "authority_freshness" in st


def test_survivability_generated():
    rep = run_live_observability_diagnostics(extra_ctx={"enable_network": False}, live_prometheus_targets=_prom_targets_fixture(), live_grafana_health=_grafana_health_fixture(), live_loki_ready=_loki_ready_fixture_ok())
    surv = rep.get("survivability", {})
    assert surv.get("explainable") is True


def test_governance_integration():
    # Should not raise even if live diagnostics disabled.
    from runtime.governance import build_runtime_governance_registry
    reg = build_runtime_governance_registry(extra_ctx={}, sensor_snapshot={})
    assert isinstance(reg, dict)


def test_validation_integration():
    from runtime.validation import build_runtime_invariants
    inv = build_runtime_invariants(sensor_snapshot={})
    names = {i.get("name") for i in inv}
    assert "INVARIANT-EXPORTER-STABILITY" in names


def test_reporting_integration():
    from runtime.reporting.reporting_engine import build_live_observability_summary
    s = build_live_observability_summary({"enable_network": False})
    assert "live_observability_score" in s


def test_cognitive_compression_integration():
    from runtime.context.cognitive_compression import compress_live_observability_signals
    sigs = compress_live_observability_signals({}, {"enable_network": False})
    assert isinstance(sigs, list)


def test_live_apis_200():
    import requests

    server, port = _start_gateway_server()
    try:
        base = f"http://127.0.0.1:{port}"
        paths = [
            "/runtime/observability/live",
            "/runtime/observability/live/prometheus",
            "/runtime/observability/live/grafana",
            "/runtime/observability/live/loki",
            "/runtime/observability/live/exporters",
            "/runtime/observability/live/incidents",
            "/runtime/observability/live/score",
        ]
        for p in paths:
            r = requests.get(base + p, timeout=5)
            assert r.status_code == 200
    finally:
        server.shutdown()


def test_live_diagnostics_json_safe():
    rep = run_live_observability_diagnostics(extra_ctx={"enable_network": False}, live_prometheus_targets=_prom_targets_fixture(), live_grafana_health=_grafana_health_fixture(), live_loki_ready=_loki_ready_fixture_ok())
    _assert_json_safe(rep)
    assert json.dumps(rep, ensure_ascii=False, default=str)


def test_deterministic_diagnostics():
    os.environ["STRICT_VALIDATION_MODE"] = "true"
    try:
        r1 = run_live_observability_diagnostics(extra_ctx={"enable_network": False}, live_prometheus_targets=_prom_targets_fixture(), live_grafana_health=_grafana_health_fixture(), live_loki_ready=_loki_ready_fixture_ok())
        r2 = run_live_observability_diagnostics(extra_ctx={"enable_network": False}, live_prometheus_targets=_prom_targets_fixture(), live_grafana_health=_grafana_health_fixture(), live_loki_ready=_loki_ready_fixture_ok())
        assert r1["deterministic_signature"] == r2["deterministic_signature"]
        assert r1["generated_at"] == 0.0
    finally:
        os.environ.pop("STRICT_VALIDATION_MODE", None)


def test_no_fake_healthy_states():
    rep = run_live_observability_diagnostics(extra_ctx={"enable_network": False})
    # With network disabled and no fixtures, authority must not claim healthy.
    assert rep["prometheus"]["authority"]["state"] != "healthy"


def test_inventory_down_no_runtime_impact():
    exp = diagnose_exporters(_prom_targets_fixture(), extra_ctx={}, flapping_changes={})
    rx = next(e for e in exp["classification"] if e.get("job") == "ai-lab-gpu-rx7900xt")
    assert rx.get("runtime_impact") == "none"


def test_observability_score_generated():
    prom = diagnose_prometheus_authority(extra_ctx={"enable_network": False}, live_targets=_prom_targets_fixture(), live_config={}, live_runtimeinfo={})
    exp = diagnose_exporters(_prom_targets_fixture(), extra_ctx={}, flapping_changes={})
    g = diagnose_grafana_platform(extra_ctx={"enable_network": False}, live_health=_grafana_health_fixture())
    l = diagnose_loki_platform(extra_ctx={"enable_network": False}, live_ready=_loki_ready_fixture_ok())
    ds = {"datasource_drift_total": 0}
    score = calculate_live_observability_score(prom, exp, ds, l)
    assert 0 <= score.get("live_observability_score", -1) <= 100


def test_runtime_impact_classification():
    exp = diagnose_exporters(_prom_targets_fixture(), extra_ctx={}, flapping_changes={})
    legacy = next(e for e in exp["classification"] if e.get("job") == "legacy-exporter")
    assert legacy.get("runtime_impact") in ("none", "low", "unknown")


def test_containment_policy_generation():
    rep = run_live_observability_diagnostics(extra_ctx={"enable_network": False}, live_prometheus_targets=_prom_targets_fixture(), live_grafana_health=_grafana_health_fixture(), live_loki_ready=_loki_ready_fixture_ok())
    incidents = (rep.get("incidents", {}) or {}).get("incidents", [])
    assert any("containment_policy" in i for i in incidents)


def test_pre_pilot_observability_safe():
    # Validation should remain JSON-safe and not hard-fail purely due to diagnostics being unavailable.
    from runtime.validation import build_runtime_validation_report
    rep = build_runtime_validation_report(sensor_snapshot={}, extra_ctx={})
    assert isinstance(rep.get("validation_score"), (int, float))
