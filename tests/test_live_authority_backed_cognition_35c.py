"""FASE 35C: Live Authority-Backed Cognition tests."""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, "/opt/ai-lab")

from runtime.authority import (
    build_live_authority_snapshot,
    query_prometheus_authority,
    build_authority_backed_context,
    get_authority_cache_state,
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
    return {
        "status": "success",
        "data": {
            "activeTargets": [
                {"labels": {"job": "ai-lab-gateway", "instance": "192.168.1.30:8008"}, "health": "up", "lastError": ""},
                {"labels": {"job": "ai-lab-gpu-rx7900xt", "instance": "192.168.1.60:9182"}, "health": "down", "lastError": "dial tcp 192.168.1.60:9182: connect: no route to host"},
            ],
            "droppedTargets": [],
        },
    }


def test_live_authority_snapshot_generated():
    snap = build_live_authority_snapshot(extra_ctx={"enable_network": False}, live_prometheus_targets=_prom_targets_fixture())
    assert snap.get("contract_version") == "35C"
    assert snap.get("deterministic_signature")


def test_prometheus_authority_query():
    rep = query_prometheus_authority(extra_ctx={"enable_network": False}, live_targets=_prom_targets_fixture())
    assert rep.get("targets", {}).get("active_total") == 2


def test_authority_backed_targets():
    ctx = build_authority_backed_context(extra_ctx={"enable_network": False}, live_prometheus_targets=_prom_targets_fixture())
    targets = (ctx.get("prometheus", {}) or {}).get("targets", {}) or {}
    assert targets.get("scrape_up") == 1


def test_authority_backed_exporters():
    rep = query_prometheus_authority(extra_ctx={"enable_network": False}, live_targets=_prom_targets_fixture())
    down = rep.get("targets", {}).get("down_targets", [])
    assert down and down[0].get("job")


def test_grounded_operational_truth():
    ctx = build_authority_backed_context(extra_ctx={"enable_network": False}, live_prometheus_targets=_prom_targets_fixture())
    truth = ctx.get("operational_truth", {})
    assert truth.get("contract_version") == "35B"


def test_no_synthetic_operational_state():
    rep = query_prometheus_authority(extra_ctx={"enable_network": False}, live_targets=_prom_targets_fixture())
    assert rep.get("fetch", {}).get("targets", {}).get("status") == "fixture"


def test_authority_freshness_generated():
    snap = build_live_authority_snapshot(extra_ctx={"enable_network": False}, live_prometheus_targets=_prom_targets_fixture())
    assert snap.get("freshness", {}).get("status") in ("fresh", "partial", "unavailable")


def test_stale_authority_detected():
    snap = build_live_authority_snapshot(extra_ctx={"enable_network": False}, live_prometheus_targets={"status": "error"})
    assert snap.get("freshness", {}).get("status") in ("partial", "unavailable")


def test_authority_cache_operational():
    c = get_authority_cache_state()
    assert c.get("contract_version") == "35C"


def test_authority_cache_deterministic():
    os.environ["STRICT_VALIDATION_MODE"] = "true"
    try:
        s1 = build_live_authority_snapshot(extra_ctx={"enable_network": False}, live_prometheus_targets=_prom_targets_fixture())
        s2 = build_live_authority_snapshot(extra_ctx={"enable_network": False}, live_prometheus_targets=_prom_targets_fixture())
        assert s1.get("deterministic_signature") == s2.get("deterministic_signature")
    finally:
        os.environ.pop("STRICT_VALIDATION_MODE", None)


def test_grounded_cognition_summary_generated():
    server, port = _start_gateway_server()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/runtime/authority", timeout=5) as resp:
            obj = json.loads(resp.read().decode("utf-8"))
        assert obj.get("contract_version") == "35C"
        _assert_json_safe(obj)
    finally:
        server.shutdown()


def test_fastpath_uses_authority():
    server, port = _start_gateway_server()
    try:
        payload = {"model": "default", "messages": [{"role": "user", "content": "lista targets Prometheus"}]}
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        assert "Prometheus authority:" in content
    finally:
        server.shutdown()


def test_authority_apis_200():
    server, port = _start_gateway_server()
    try:
        for p in (
            "/runtime/authority",
            "/runtime/authority/live",
            "/runtime/authority/freshness",
            "/runtime/authority/prometheus",
            "/runtime/authority/operational",
            "/runtime/authority/grounded",
            "/runtime/authority/gaps",
            "/runtime/authority/score",
            "/runtime/authority/cache",
        ):
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{p}", timeout=5) as resp:
                assert resp.status == 200
    finally:
        server.shutdown()
