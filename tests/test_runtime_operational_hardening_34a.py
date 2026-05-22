"""FASE 34A: Runtime Operational Hardening.

Covers: hardening report, watchdogs, timeout governance, escalation/containment,
always-on APIs, metrics hook, determinism in STRICT_VALIDATION_MODE.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from http.server import ThreadingHTTPServer

sys.path.insert(0, "/opt/ai-lab")

from runtime.hardening.runtime_operational_hardening import (
    build_runtime_hardening_report,
    build_runtime_watchdogs,
    build_timeout_governance,
    build_degraded_escalation,
    build_failure_containment_summary,
    build_operational_safeguards,
    build_runtime_survivability,
    calculate_hardening_score,
    detect_operational_instability,
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


def test_hardening_report_generated():
    rep = build_runtime_hardening_report(sensor_snapshot={}, extra_ctx={})
    assert isinstance(rep, dict)
    assert rep.get("contract_version") == "34A"
    assert "hardening_score" in rep
    assert "hardening_level" in rep
    assert isinstance(rep.get("watchdogs"), list)
    assert isinstance(rep.get("timeouts"), list)
    assert isinstance(rep.get("escalation"), dict)
    assert isinstance(rep.get("containment"), dict)
    assert isinstance(rep.get("safeguards"), list)
    assert isinstance(rep.get("survivability"), dict)
    assert isinstance(rep.get("instability"), list)
    assert rep.get("deterministic_signature")


def test_hardening_components_generate():
    timeouts = build_timeout_governance({})
    assert isinstance(timeouts, list)
    assert any(t.get("component") == "prometheus" for t in timeouts)

    watchdogs = build_runtime_watchdogs({}, {})
    assert isinstance(watchdogs, list)
    assert len(watchdogs) >= 5

    esc = build_degraded_escalation(watchdogs, timeouts)
    assert esc.get("escalation_state") in ("healthy", "healthy_degraded", "degraded", "critical", "containment_mode")

    cont = build_failure_containment_summary(esc)
    assert isinstance(cont.get("policies"), list)
    assert isinstance(cont.get("active_policies"), list)

    sg = build_operational_safeguards(esc, watchdogs, timeouts)
    assert isinstance(sg, list)

    sv = build_runtime_survivability(watchdogs, esc)
    assert 0 <= float(sv.get("survivability_score", -1)) <= 100

    inst = detect_operational_instability(watchdogs, timeouts, esc)
    assert isinstance(inst, list)

    score = calculate_hardening_score(watchdogs, timeouts, esc, sv)
    assert 0 <= float(score.get("hardening_score", -1)) <= 100


def test_hardening_json_safe():
    rep = build_runtime_hardening_report(sensor_snapshot={}, extra_ctx={})
    _assert_json_safe(rep)
    dumped = json.dumps(rep, ensure_ascii=False, default=str)
    assert len(dumped) > 0


def test_hardening_deterministic_strict_mode():
    os.environ["STRICT_VALIDATION_MODE"] = "true"
    try:
        r1 = build_runtime_hardening_report(sensor_snapshot={}, extra_ctx={})
        r2 = build_runtime_hardening_report(sensor_snapshot={}, extra_ctx={})
        assert r1["deterministic_signature"] == r2["deterministic_signature"]
        assert r1["generated_at"] == 0.0
    finally:
        os.environ.pop("STRICT_VALIDATION_MODE", None)


def test_hardening_apis_200():
    import requests

    server, port = _start_gateway_server()
    try:
        base = f"http://127.0.0.1:{port}"
        paths = [
            "/runtime/hardening",
            "/runtime/hardening/watchdogs",
            "/runtime/hardening/timeouts",
            "/runtime/hardening/escalation",
            "/runtime/hardening/containment",
            "/runtime/hardening/safeguards",
            "/runtime/hardening/survivability",
            "/runtime/hardening/score",
        ]
        for p in paths:
            r = requests.get(base + p, timeout=5)
            assert r.status_code == 200, f"{p} status={r.status_code}"
            payload = r.json()
            assert payload.get("service") == "ai-lab-openai-gateway"
            assert payload.get("contract_version") in ("34A",)
    finally:
        server.shutdown()
