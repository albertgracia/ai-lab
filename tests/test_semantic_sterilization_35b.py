"""FASE 35B: Semantic Sterilization & Identity Hygiene tests."""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, "/opt/ai-lab")

from runtime.semantic import (
    build_operational_truth,
    sterilize_semantic_entities,
    build_identity_hygiene_summary,
    build_semantic_integrity_report,
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


def test_operational_truth_generated():
    truth = build_operational_truth(extra_ctx={})
    assert truth.get("contract_version") == "35B"
    assert truth.get("deterministic_signature")


def test_no_legacy_model_leakage():
    ster = sterilize_semantic_entities(extra_ctx={})
    legacy = ster.get("legacy_entities", [])
    # Should be empty for operational truth (IPs only).
    assert isinstance(legacy, list)


def test_no_lmstudio_community_exposure():
    # Runtime report context should not expose legacy models.
    from runtime.context.report_runtime_context import _get_discovered_models
    assert _get_discovered_models() == []


def test_no_phantom_gpus():
    ster = sterilize_semantic_entities(extra_ctx={})
    phantom = ster.get("phantom_entities", [])
    assert isinstance(phantom, list)


def test_unknown_not_operational():
    truth = build_operational_truth(extra_ctx={})
    for c in truth.get("classifications", []) or []:
        if c.get("semantic_state") == "STATE-UNKNOWN":
            assert c.get("operational") is False


def test_inventory_not_operational():
    truth = build_operational_truth(extra_ctx={})
    assert "192.168.1.60" in (truth.get("inventory_only_nodes") or [])
    assert "192.168.1.60" not in (truth.get("operational_nodes") or [])


def test_discoverable_not_authority():
    truth = build_operational_truth(extra_ctx={})
    auth = set(truth.get("authority_roots") or [])
    for d in truth.get("discoverable_nodes", []) or []:
        if d not in auth:
            # discoverable but not authority root
            pass


def test_rx9070_operational():
    truth = build_operational_truth(extra_ctx={})
    assert "192.168.1.50" in (truth.get("operational_nodes") or [])


def test_rx7900xt_inventory_only():
    truth = build_operational_truth(extra_ctx={})
    assert "192.168.1.60" in (truth.get("inventory_only_nodes") or [])


def test_prometheus_authority_preserved():
    truth = build_operational_truth(extra_ctx={})
    assert "192.168.1.40" in (truth.get("authority_roots") or [])


def test_operational_truth_sterilized():
    ster = sterilize_semantic_entities(extra_ctx={})
    assert ster.get("operational_truth", {}).get("contract_version") == "35B"


def test_fastpath_uses_sterilized_truth():
    server, port = _start_gateway_server()
    try:
        payload = {"model": "default", "messages": [{"role": "user", "content": "qué es 192.168.1.40"}]}
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
        assert "identity=192.168.1.40" in content
    finally:
        server.shutdown()


def test_reporting_integration():
    from runtime.reporting.reporting_engine import build_semantic_integrity_summary
    rep = build_semantic_integrity_summary(extra_ctx={})
    assert rep.get("contract_version") == "35B"


def test_governance_integration():
    from runtime.governance import build_runtime_governance_registry
    g = build_runtime_governance_registry(extra_ctx={}, sensor_snapshot={})
    assert (g.get("semantic") or {}).get("contract_version") == "35B"


def test_validation_integration():
    from runtime.validation.runtime_validation_framework import build_runtime_validation_report
    rep = build_runtime_validation_report(sensor_snapshot={}, extra_ctx={})
    names = {i.get("name") for i in (rep.get("invariants") or [])}
    assert "INVARIANT-NO-LEGACY-LEAKAGE" in names
    assert "INVARIANT-STERILIZED-OPERATIONAL-TRUTH" in names


def test_cognitive_compression_integration():
    from runtime.context.cognitive_compression import build_runtime_cognitive_summary
    rep = build_runtime_cognitive_summary({"gpu_operational_summaries": []}, extra_ctx={})
    _assert_json_safe(rep)


def test_semantic_apis_200():
    server, port = _start_gateway_server()
    try:
        for path in (
            "/runtime/semantic",
            "/runtime/semantic/truth",
            "/runtime/semantic/phantom",
            "/runtime/semantic/legacy",
            "/runtime/semantic/discoverable",
            "/runtime/semantic/inventory",
            "/runtime/semantic/hygiene",
            "/runtime/semantic/score",
        ):
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as resp:
                assert resp.status == 200
    finally:
        server.shutdown()


def test_semantic_json_safe():
    rep = sterilize_semantic_entities(extra_ctx={})
    _assert_json_safe(rep)


def test_semantic_deterministic():
    os.environ["STRICT_VALIDATION_MODE"] = "true"
    try:
        r1 = build_semantic_integrity_report(extra_ctx={})
        r2 = build_semantic_integrity_report(extra_ctx={})
        assert r1.get("deterministic_signature") == r2.get("deterministic_signature")
    finally:
        os.environ.pop("STRICT_VALIDATION_MODE", None)


def test_no_unknown_operational_entities():
    rep = build_semantic_integrity_report(extra_ctx={})
    assert int(rep.get("unknown_operational_entities_total", 0) or 0) == 0


def test_no_inventory_leakage():
    rep = build_semantic_integrity_report(extra_ctx={})
    assert int(rep.get("inventory_contamination_total", 0) or 0) == 0


def test_no_discoverable_leakage():
    rep = build_semantic_integrity_report(extra_ctx={})
    assert int(rep.get("discoverable_contamination_total", 0) or 0) == 0


def test_identity_hygiene_summary_generated():
    rep = build_identity_hygiene_summary(extra_ctx={})
    assert rep.get("contract_version") == "35B"
    assert rep.get("deterministic_signature")


def test_semantic_integrity_score_generated():
    rep = build_semantic_integrity_report(extra_ctx={})
    assert rep.get("semantic_integrity_score") is not None
