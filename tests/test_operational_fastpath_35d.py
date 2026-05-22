"""FASE 35D: Operational Fast Path tests."""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, "/opt/ai-lab")

from runtime.fastpath import (
    build_fastpath_response,
    build_fast_operational_summary,
    build_fast_observability_summary,
    build_fast_governance_summary,
    build_fast_validation_summary,
    build_fast_topology_summary,
    build_fast_gpu_summary,
    get_fastpath_cache_state,
)


def _start_gateway_server():
    from runtime.gateway.openai_gateway import GatewayHandler

    server = ThreadingHTTPServer(("127.0.0.1", 0), GatewayHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, port


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


def _lines(resp: dict) -> list[str]:
    return [str(x) for x in ((resp.get("summary", {}) or {}).get("lines", []) or [])]


def test_fastpath_operational_summary():
    s = build_fast_operational_summary(extra_ctx={"verbosity": "operational"})
    assert s.get("lines") and len(s["lines"]) <= 10


def test_fastpath_observability_summary():
    s = build_fast_observability_summary(extra_ctx={"verbosity": "operational"})
    assert s.get("lines") and "Observability" in s["lines"][0]


def test_fastpath_governance_summary():
    s = build_fast_governance_summary(extra_ctx={"verbosity": "operational"}, sensor_snapshot={})
    assert s.get("lines") and "Governance" in s["lines"][0]


def test_fastpath_validation_summary():
    s = build_fast_validation_summary(extra_ctx={"verbosity": "operational"}, sensor_snapshot={})
    assert s.get("lines") and "Validation" in s["lines"][0]


def test_fastpath_topology_summary():
    s = build_fast_topology_summary(extra_ctx={"verbosity": "operational"})
    assert s.get("lines") and "Topology" in s["lines"][0]


def test_fastpath_gpu_summary():
    s = build_fast_gpu_summary(extra_ctx={"verbosity": "operational"})
    assert s.get("lines") and "GPU" in s["lines"][0]


def test_fastpath_compactness():
    r = build_fastpath_response("estado runtime", extra_ctx={"enable_network": False}, sensor_snapshot={}, verbosity="operational")
    assert len(_lines(r)) <= 10


def test_fastpath_deterministic():
    os.environ["STRICT_VALIDATION_MODE"] = "true"
    try:
        r1 = build_fastpath_response("estado observabilidad", extra_ctx={"enable_network": False}, sensor_snapshot={}, verbosity="operational")
        r2 = build_fastpath_response("estado observabilidad", extra_ctx={"enable_network": False}, sensor_snapshot={}, verbosity="operational")
        assert r1.get("deterministic_signature") == r2.get("deterministic_signature")
    finally:
        os.environ.pop("STRICT_VALIDATION_MODE", None)


def test_fastpath_authority_backed():
    r = build_fastpath_response("qué exporters están down", extra_ctx={"enable_network": False}, sensor_snapshot={}, verbosity="operational")
    auth = r.get("authority", {}) or {}
    assert auth.get("contract_version")
    assert "prometheus_targets" in auth


def test_fastpath_no_hallucinations():
    r = build_fastpath_response("estado observabilidad", extra_ctx={"enable_network": False}, sensor_snapshot={}, verbosity="operational")
    auth = r.get("authority", {}) or {}
    prom = auth.get("prometheus_targets", {}) or {}
    assert isinstance(prom.get("active_total"), int)
    assert isinstance(prom.get("scrape_up"), int)


def test_fastpath_no_recursive_governance():
    r = build_fastpath_response("estado governance", extra_ctx={"enable_network": False}, sensor_snapshot={}, verbosity="operational")
    txt = "\n".join(_lines(r)).lower()
    assert txt.count("governance") <= 2


def test_fastpath_no_recursive_explainability():
    r = build_fastpath_response("estado runtime", extra_ctx={"enable_network": False}, sensor_snapshot={}, verbosity="operational")
    txt = "\n".join(_lines(r)).lower()
    assert "disclaimer" not in txt
    assert "no puedo" not in txt


def test_fastpath_cache_operational():
    c = get_fastpath_cache_state()
    assert c.get("contract_version") == "35D"


def test_fastpath_cache_deterministic():
    os.environ["STRICT_VALIDATION_MODE"] = "true"
    try:
        c1 = get_fastpath_cache_state()
        c2 = get_fastpath_cache_state()
        # Cache counters may change, but structure must be stable.
        assert c1.get("contract_version") == c2.get("contract_version")
        assert isinstance((c1.get("cache", {}) or {}).get("cache_entries"), int)
    finally:
        os.environ.pop("STRICT_VALIDATION_MODE", None)


def test_operational_queries_use_fastpath():
    os.environ["AI_LAB_ENABLE_LIVE_AUTHORITY_NETWORK"] = "false"
    server, port = _start_gateway_server()
    try:
        payload = {"model": "default", "messages": [{"role": "user", "content": "estado runtime"}]}
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        assert "Operational summary" in content
        assert content.count("\n") < 12
    finally:
        server.shutdown()
        os.environ.pop("AI_LAB_ENABLE_LIVE_AUTHORITY_NETWORK", None)


def test_deep_queries_use_deep_path():
    r = build_fastpath_response("haz un postmortem completo", extra_ctx={"enable_network": False}, sensor_snapshot={}, verbosity="operational")
    routing = r.get("routing", {}) or {}
    assert routing.get("deep_path") is True


def test_reporting_integration():
    from runtime.reporting.reporting_engine import build_fastpath_operational_summary

    rep = build_fastpath_operational_summary(extra_ctx={"enable_network": False}, sensor_snapshot={})
    assert rep.get("contract_version") == "35D"


def test_governance_integration():
    from runtime.governance.runtime_governance_registry import build_runtime_governance_registry

    reg = build_runtime_governance_registry(extra_ctx={"enable_network": False}, sensor_snapshot={})
    fp = reg.get("fastpath_health", {}) or {}
    assert fp.get("contract_version") == "35D"


def test_validation_integration():
    from runtime.validation.runtime_validation_framework import build_runtime_validation_report

    rep = build_runtime_validation_report(sensor_snapshot={}, extra_ctx={"enable_network": False})
    inv = rep.get("invariants", []) or []
    names = {i.get("name") for i in inv if isinstance(i, dict)}
    assert "INVARIANT-FASTPATH-COMPACTNESS" in names


def test_cognitive_compression_integration():
    from runtime.context.cognitive_compression import build_runtime_cognitive_summary

    rep = build_runtime_cognitive_summary(sensor_snapshot={"_": 1}, extra_ctx={"enable_network": False})
    sigs = rep.get("signals", []) or []
    assert any((s.get("domain") == "fastpath") for s in sigs if isinstance(s, dict))


def test_fastpath_apis_200():
    os.environ["AI_LAB_ENABLE_LIVE_AUTHORITY_NETWORK"] = "false"
    server, port = _start_gateway_server()
    try:
        for p in (
            "/runtime/fastpath",
            "/runtime/fastpath/operational",
            "/runtime/fastpath/observability",
            "/runtime/fastpath/governance",
            "/runtime/fastpath/validation",
            "/runtime/fastpath/topology",
            "/runtime/fastpath/infrastructure",
            "/runtime/fastpath/gpu",
            "/runtime/fastpath/score",
            "/runtime/fastpath/cache",
        ):
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{p}", timeout=5) as resp:
                assert resp.status == 200
    finally:
        server.shutdown()
        os.environ.pop("AI_LAB_ENABLE_LIVE_AUTHORITY_NETWORK", None)


def test_fastpath_json_safe():
    r = build_fastpath_response("estado runtime", extra_ctx={"enable_network": False}, sensor_snapshot={}, verbosity="operational")
    _assert_json_safe(r)


def test_operational_responses_short():
    r = build_fastpath_response("qué exporters están down", extra_ctx={"enable_network": False}, sensor_snapshot={}, verbosity="operational")
    txt = "\n".join(_lines(r))
    assert len(txt) <= 900
    assert len(_lines(r)) <= 10


def test_no_verbosity_storm():
    r = build_fastpath_response("estado governance", extra_ctx={"enable_network": False}, sensor_snapshot={}, verbosity="operational")
    txt = "\n".join(_lines(r)).lower()
    assert txt.count("unknown") < 6


def test_operational_runtime_feels_noc_like():
    r = build_fastpath_response("estado runtime", extra_ctx={"enable_network": False}, sensor_snapshot={}, verbosity="operational")
    lines = _lines(r)
    assert lines and len(lines[0]) < 40
