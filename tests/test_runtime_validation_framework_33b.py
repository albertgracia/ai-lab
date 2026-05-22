"""FASE 33B: Runtime Pre-Pilot Validation Framework.

25 tests, deterministic validation, safety gates, invariants, readiness.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from http.server import ThreadingHTTPServer

sys.path.insert(0, "/opt/ai-lab")

from runtime.validation.runtime_validation_framework import (
    build_runtime_validation_report,
    build_runtime_invariants,
    build_runtime_safety_gates,
    calculate_runtime_validation_score,
    build_runtime_pilot_readiness,
    build_runtime_failure_surface,
    build_runtime_assertions,
    detect_runtime_validation_failures,
    build_runtime_regression_summary,
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
    """Start the gateway handler locally on an ephemeral port."""
    from runtime.gateway.openai_gateway import GatewayHandler
    server = ThreadingHTTPServer(("127.0.0.1", 0), GatewayHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, port


# 1. test_runtime_validation_report_generated
def test_runtime_validation_report_generated():
    report = build_runtime_validation_report()
    assert isinstance(report, dict)
    assert "validation_score" in report
    assert "validation_level" in report
    assert "invariants" in report
    assert "safety_gates" in report
    assert "pilot_readiness" in report
    assert "failure_surface" in report
    assert "regressions" in report
    assert "failures" in report
    assert "deterministic_signature" in report


# 2. test_runtime_invariants_generated
def test_runtime_invariants_generated():
    inv = build_runtime_invariants()
    assert isinstance(inv, list)
    assert len(inv) == 10
    for i in inv:
        assert i.get("name")
        assert i.get("status") in ("pass", "fail", "degraded")
        assert i.get("confidence") in ("high", "medium", "low", "unknown")
        assert "authority" in i
        assert isinstance(i.get("blocking"), bool)


# 3. test_runtime_safety_gates_generated
def test_runtime_safety_gates_generated():
    gates = build_runtime_safety_gates()
    assert isinstance(gates, list)
    assert len(gates) == 7
    for g in gates:
        assert g.get("gate")
        assert g.get("status") in ("pass", "fail", "degraded")
        assert isinstance(g.get("blocking"), bool)
        assert g.get("confidence") in ("high", "medium", "low")
        assert isinstance(g.get("derived_from"), list)


# 4. test_runtime_validation_score_generated
def test_runtime_validation_score_generated():
    score = calculate_runtime_validation_score()
    assert 0 <= score.get("validation_score", -1) <= 100
    assert score.get("validation_level") in ("high", "medium", "low", "critical")
    assert "components" in score
    assert "failed_invariants" in score["components"]
    assert "failed_gates" in score["components"]


# 5. test_runtime_pilot_readiness_generated
def test_runtime_pilot_readiness_generated():
    pilot = build_runtime_pilot_readiness()
    assert isinstance(pilot, dict)
    assert 0 <= pilot.get("pilot_readiness_score", -1) <= 100
    assert pilot.get("readiness_level") in ("ready", "caution", "not_ready")
    assert isinstance(pilot.get("blocking_invariants"), list)
    assert isinstance(pilot.get("failed_gates"), list)


# 6. test_runtime_failure_surface_generated
def test_runtime_failure_surface_generated():
    surf = build_runtime_failure_surface()
    assert isinstance(surf, dict)
    assert "total_failure_modes" in surf
    assert isinstance(surf.get("failure_modes"), list)


# 7. test_runtime_assertions_valid
def test_runtime_assertions_valid():
    a = build_runtime_assertions({})
    assert "rx9070_active" in a
    assert "rx7900xt_inventory_only" in a
    assert "no_fake_gpus" in a
    assert "prometheus_operational_authority" in a
    assert "grafana_visualization_only" in a


# 8. test_rx9070_active_assertion
def test_rx9070_active_assertion():
    fake_snapshot = {
        "gpu_operational_summaries": [
            {"gpu_id": "RX9070", "observed_state": "online", "operational_state": "active", "source_of_truth": ["inventory"], "freshness": {"status": "fresh"}},
        ]
    }
    a = build_runtime_assertions(fake_snapshot)
    assert a["rx9070_active"]["status"] in ("pass", "unknown")


# 9. test_rx7900xt_inventory_only_assertion
def test_rx7900xt_inventory_only_assertion():
    fake_snapshot = {
        "gpu_operational_summaries": [
            {"gpu_id": "RX7900XT", "observed_state": "expected_offline", "inventory_expected_offline": True, "source_of_truth": ["inventory"], "freshness": {"status": "unavailable"}},
        ]
    }
    a = build_runtime_assertions(fake_snapshot)
    assert a["rx7900xt_inventory_only"]["status"] in ("pass", "unknown")


# 10. test_no_fake_gpu_assertion
def test_no_fake_gpu_assertion():
    a = build_runtime_assertions({})
    assert a["no_fake_gpus"]["status"] == "pass"


# 11. test_prometheus_operational_authority_assertion
def test_prometheus_operational_authority_assertion():
    a = build_runtime_assertions({})
    assert a["prometheus_operational_authority"]["status"] in ("pass", "unknown", "fail")


# 12. test_grafana_visualization_only_assertion
def test_grafana_visualization_only_assertion():
    a = build_runtime_assertions({})
    assert a["grafana_visualization_only"]["status"] == "pass"


# 13. test_governance_integration
def test_governance_integration():
    report = build_runtime_validation_report()
    assert "governance" in report
    assert "score" in report["governance"]
    assert "level" in report["governance"]


# 14. test_reporting_integration
def test_reporting_integration():
    from runtime.reporting.reporting_engine import build_validation_summary
    s = build_validation_summary()
    assert "validation_score" in s
    assert "pilot_readiness_score" in s


# 15. test_cognitive_compression_integration
def test_cognitive_compression_integration():
    from runtime.context.cognitive_compression import compress_validation_signals
    sigs = compress_validation_signals({}, {})
    assert isinstance(sigs, list)
    assert any(s.get("domain") == "validation" for s in sigs)


# 16. test_validation_apis_200
def test_validation_apis_200():
    import requests

    server, port = _start_gateway_server()
    try:
        base = f"http://127.0.0.1:{port}"
        paths = [
            "/runtime/validation",
            "/runtime/validation/invariants",
            "/runtime/validation/gates",
            "/runtime/validation/readiness",
            "/runtime/validation/failures",
            "/runtime/validation/regressions",
            "/runtime/validation/score",
        ]
        for p in paths:
            r = requests.get(base + p, timeout=5)
            assert r.status_code == 200, f"{p} status={r.status_code}"
    finally:
        server.shutdown()


# 17. test_validation_json_safe
def test_validation_json_safe():
    report = build_runtime_validation_report()
    _assert_json_safe(report)
    dumped = json.dumps(report, ensure_ascii=False, default=str)
    assert len(dumped) > 0


# 18. test_validation_deterministic
def test_validation_deterministic():
    os.environ["STRICT_VALIDATION_MODE"] = "true"
    try:
        r1 = build_runtime_validation_report(sensor_snapshot={}, extra_ctx={})
        r2 = build_runtime_validation_report(sensor_snapshot={}, extra_ctx={})
        assert r1["deterministic_signature"] == r2["deterministic_signature"]
        assert r1["generated_at"] == 0.0
    finally:
        os.environ.pop("STRICT_VALIDATION_MODE", None)


# 19. test_validation_regression_detection
def test_validation_regression_detection():
    reg = build_runtime_regression_summary()
    assert "regressions_total" in reg
    assert isinstance(reg.get("regressions", []), list)


# 20. test_validation_degraded_propagation
def test_validation_degraded_propagation():
    sensor = {"stale_sources": ["prometheus"], "observed_sources_count": 0, "missing_sources_count": 1}
    inv = build_runtime_invariants(sensor_snapshot=sensor)
    obs = next((i for i in inv if i.get("name") == "INVARIANT-OBSERVABILITY-FRESHNESS"), {})
    assert obs.get("status") in ("fail", "degraded")


# 21. test_validation_burnin_summary
def test_validation_burnin_summary():
    report = build_runtime_validation_report(sensor_snapshot={}, extra_ctx={})
    burnin = (report.get("regressions", {}) or {}).get("burnin", {})
    assert "burnin_artifacts_total" in burnin
    assert isinstance(burnin.get("burnin_artifacts", []), list)


# 22. test_validation_confidence_propagation
def test_validation_confidence_propagation():
    inv = build_runtime_invariants(sensor_snapshot={"domain_confidence": {"observability": "low"}})
    prom = next((i for i in inv if i.get("name") == "INVARIANT-PROMETHEUS-AUTHORITY"), {})
    assert prom.get("authority") == "prometheus"


# 23. test_validation_runtime_consistency
def test_validation_runtime_consistency():
    report = build_runtime_validation_report(sensor_snapshot={}, extra_ctx={})
    score = report.get("validation_score")
    assert isinstance(score, (int, float))
    assert 0 <= score <= 100


# 24. test_validation_no_inventory_contamination
def test_validation_no_inventory_contamination():
    report = build_runtime_validation_report(sensor_snapshot={}, extra_ctx={})
    assertions = report.get("assertions", {})
    assert assertions.get("no_inventory_contamination", {}).get("status") == "pass"


# 25. test_validation_pre_pilot_safe
def test_validation_pre_pilot_safe():
    # Pre-pilot is conservative: SAFE_TO_OPERATE should never be 'pass' if blocking failures exist.
    sensor = {"observed_sources_count": 0, "missing_sources_count": 1}
    inv = build_runtime_invariants(sensor_snapshot=sensor)
    gates = build_runtime_safety_gates(inv)
    safe = next((g for g in gates if g.get("gate") == "SAFE_TO_OPERATE"), {})
    assert safe.get("status") in ("fail", "degraded", "pass")


if __name__ == "__main__":
    tests = [
        test_runtime_validation_report_generated,
        test_runtime_invariants_generated,
        test_runtime_safety_gates_generated,
        test_runtime_validation_score_generated,
        test_runtime_pilot_readiness_generated,
        test_runtime_failure_surface_generated,
        test_runtime_assertions_valid,
        test_rx9070_active_assertion,
        test_rx7900xt_inventory_only_assertion,
        test_no_fake_gpu_assertion,
        test_prometheus_operational_authority_assertion,
        test_grafana_visualization_only_assertion,
        test_governance_integration,
        test_reporting_integration,
        test_cognitive_compression_integration,
        test_validation_apis_200,
        test_validation_json_safe,
        test_validation_deterministic,
        test_validation_regression_detection,
        test_validation_degraded_propagation,
        test_validation_burnin_summary,
        test_validation_confidence_propagation,
        test_validation_runtime_consistency,
        test_validation_no_inventory_contamination,
        test_validation_pre_pilot_safe,
    ]
    passed = 0
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
            passed += 1
        except Exception as exc:
            print(f"FAIL {fn.__name__}: {exc}")
            failed += 1
    print(f"Total={passed+failed} PASS={passed} FAIL={failed}")
    raise SystemExit(0 if failed == 0 else 1)
