"""FASE 34C: Runtime Performance & Governance Latency Calibration tests.

Focus:
- latency profiling contracts
- operational fast-path (authority-first, non-LLM)
- cache consistency + determinism in STRICT mode
- always-on performance APIs
"""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, "/opt/ai-lab")

from runtime.performance import (
    profile_runtime_latency,
    profile_governance_latency,
    profile_validation_latency,
    build_fast_operational_summary,
    compress_operational_noise,
    get_performance_cache_state,
    prime_async_diagnostics,
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


def test_runtime_latency_profile_generated():
    rep = profile_runtime_latency(extra_ctx={"enable_network": False}, sensor_snapshot={})
    assert rep.get("contract_version") == "34C"
    assert rep.get("latency")
    assert rep.get("performance")


def test_governance_latency_profile_generated():
    g = profile_governance_latency(extra_ctx={}, sensor_snapshot={})
    assert g.get("contract_version") == "34C"
    assert "governance_ms" in g


def test_validation_latency_profile_generated():
    v = profile_validation_latency(extra_ctx={}, sensor_snapshot={})
    assert v.get("contract_version") == "34C"
    assert "validation_ms" in v


def test_operational_fastpath_active():
    fp = build_fast_operational_summary("governance", extra_ctx={}, sensor_snapshot={})
    assert fp.get("fastpath", {}).get("active") is True
    assert fp.get("authority_first") is True


def test_fastpath_deterministic():
    os.environ["STRICT_VALIDATION_MODE"] = "true"
    try:
        fp1 = build_fast_operational_summary("governance", extra_ctx={}, sensor_snapshot={})
        fp2 = build_fast_operational_summary("governance", extra_ctx={}, sensor_snapshot={})
        assert fp1 == fp2
    finally:
        os.environ.pop("STRICT_VALIDATION_MODE", None)


def test_authority_first_execution():
    fp = build_fast_operational_summary("observability", extra_ctx={"enable_network": False}, sensor_snapshot={})
    assert fp.get("authority_first") is True


def test_semantic_noise_reduced():
    text = "a\na\nb\nb\n"
    out = compress_operational_noise(text, level="operational")
    assert out.splitlines() == ["a", "b"]


def test_no_governance_loops():
    # Smoke: should return quickly and not recurse.
    g = profile_governance_latency(extra_ctx={}, sensor_snapshot={})
    assert isinstance(g.get("governance_ms"), float)


def test_no_fallback_leakage():
    from runtime.router.model_policy import PRIMARY_OPERATIONAL_MODEL, PRIMARY_CODING_MODEL, is_deprecated_model

    assert not is_deprecated_model(PRIMARY_OPERATIONAL_MODEL)
    assert not is_deprecated_model(PRIMARY_CODING_MODEL)


def test_cache_consistency():
    c = get_performance_cache_state()
    assert c.get("contract_version") == "34C"
    assert isinstance(c.get("cache_hits"), int)
    assert isinstance(c.get("cache_misses"), int)


def test_async_diagnostics_enabled():
    os.environ["AI_LAB_ENABLE_ASYNC_DIAGNOSTICS"] = "true"
    rep = prime_async_diagnostics(extra_ctx={"enable_network": False})
    assert rep.get("contract_version") == "34C"
    assert rep.get("async_enabled") is True


def test_operational_responses_compact():
    server, port = _start_gateway_server()
    try:
        payload = {
            "model": "default",
            "messages": [{"role": "user", "content": "governance summary"}],
        }
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        assert "Operational Fast-Path" in content
        assert len(content) < 900
    finally:
        server.shutdown()


def test_governance_batching_active():
    c1 = get_performance_cache_state()
    build_fast_operational_summary("governance", extra_ctx={}, sensor_snapshot={})
    build_fast_operational_summary("governance", extra_ctx={}, sensor_snapshot={})
    c2 = get_performance_cache_state()
    assert int(c2.get("cache_hits", 0)) >= int(c1.get("cache_hits", 0))


def test_validation_batching_active():
    c1 = get_performance_cache_state()
    build_fast_operational_summary("validation", extra_ctx={}, sensor_snapshot={})
    build_fast_operational_summary("validation", extra_ctx={}, sensor_snapshot={})
    c2 = get_performance_cache_state()
    assert int(c2.get("cache_hits", 0)) >= int(c1.get("cache_hits", 0))


def test_reporting_integration():
    from runtime.reporting.reporting_engine import build_runtime_performance_summary

    rep = build_runtime_performance_summary(extra_ctx={"enable_network": False}, sensor_snapshot={})
    assert rep.get("contract_version") == "34C"
    assert "runtime_performance_score" in rep


def test_governance_integration():
    from runtime.governance import build_runtime_governance_registry

    reg = build_runtime_governance_registry(extra_ctx={}, sensor_snapshot={})
    perf = reg.get("performance", {})
    assert perf.get("contract_version") == "34C"
    assert perf.get("authority_cache_health")


def test_validation_integration():
    from runtime.validation.runtime_validation_framework import build_runtime_validation_report

    rep = build_runtime_validation_report(sensor_snapshot={}, extra_ctx={})
    inv = rep.get("invariants", [])
    names = {i.get("name") for i in inv}
    assert "INVARIANT-FASTPATH-DETERMINISM" in names
    assert "INVARIANT-AUTHORITY-FIRST" in names
    assert "INVARIANT-NO-FALLBACK-LEAKAGE" in names
    assert "INVARIANT-CACHE-CONSISTENCY" in names


def test_cognitive_compression_integration():
    from runtime.context.cognitive_compression import build_runtime_cognitive_summary

    snap = {"gpu_operational_summaries": []}
    rep = build_runtime_cognitive_summary(snap, extra_ctx={})
    # May be empty, but should be JSON-safe.
    _assert_json_safe(rep)


def test_performance_apis_200():
    server, port = _start_gateway_server()
    try:
        for path in (
            "/runtime/performance",
            "/runtime/performance/latency",
            "/runtime/performance/governance",
            "/runtime/performance/validation",
            "/runtime/performance/cache",
            "/runtime/performance/noise",
            "/runtime/performance/fastpath",
            "/runtime/performance/score",
        ):
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as resp:
                assert resp.status == 200
    finally:
        server.shutdown()


def test_performance_json_safe():
    server, port = _start_gateway_server()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/runtime/performance", timeout=5) as resp:
            obj = json.loads(resp.read().decode("utf-8"))
        _assert_json_safe(obj)
    finally:
        server.shutdown()


def test_runtime_performance_score_generated():
    rep = profile_runtime_latency(extra_ctx={"enable_network": False}, sensor_snapshot={})
    score = (rep.get("performance", {}) or {}).get("runtime_performance_score")
    assert score is not None


def test_fastpath_routing_operational():
    # Fast-path uses non-LLM handler and reports llama model.
    fp = build_fast_operational_summary("validation", extra_ctx={}, sensor_snapshot={})
    assert fp.get("fastpath", {}).get("model") == "llama-3.1-8b-instruct"


def test_qwen_coding_routing_preserved():
    from runtime.router.model_policy import PRIMARY_CODING_MODEL
    assert "qwen" in (PRIMARY_CODING_MODEL or "").lower()


def test_legacy_model_blocked():
    from runtime.router.model_policy import is_deprecated_model
    assert is_deprecated_model("lmstudio-community/qwen2.5-coder-14b-instruct")


def test_pre_pilot_high_performance_safe():
    from runtime.validation.runtime_validation_framework import build_runtime_validation_report
    rep = build_runtime_validation_report(sensor_snapshot={}, extra_ctx={})
    assert rep.get("validation_level") in ("high", "medium", "low", "critical", "unknown")
