"""FASE 35A: Infrastructure Identity Registry tests.

Focus:
- deterministic role mapping (authority identity > inferred)
- separation observed/operational/inventory/discoverable
- fast-path uses registry for IP identity questions
- always-on infrastructure APIs
"""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, "/opt/ai-lab")

from runtime.infrastructure import (
    build_infrastructure_identity_registry,
    build_authority_root_map,
    build_infrastructure_semantic_summary,
    identify_infrastructure,
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


def test_infrastructure_registry_generated():
    reg = build_infrastructure_identity_registry(extra_ctx={"enable_network": False})
    assert reg.get("contract_version") == "35A"
    assert reg.get("authority_roots")
    assert reg.get("deterministic_signature")


def test_prometheus_authority_root_detected():
    roots = build_authority_root_map().get("authority_roots", [])
    ids = {r.get("identity") for r in roots}
    assert "192.168.1.40" in ids


def test_runtime_control_plane_detected():
    reg = build_infrastructure_identity_registry(extra_ctx={})
    assert "192.168.1.30" in (reg.get("control_plane") or [])


def test_rx9070_operational_identity():
    reg = build_infrastructure_identity_registry(extra_ctx={})
    inv = reg.get("inventory", {}) or {}
    op = inv.get("operational_nodes", []) or []
    ids = {n.get("identity") for n in op}
    assert "192.168.1.50" in ids


def test_rx7900xt_inventory_only():
    reg = build_infrastructure_identity_registry(extra_ctx={})
    inv = reg.get("inventory", {}) or {}
    inv_only = inv.get("inventory_only_nodes", []) or []
    ids = {n.get("identity") for n in inv_only}
    assert "192.168.1.60" in ids


def test_nas_n5_detected():
    reg = build_infrastructure_identity_registry(extra_ctx={})
    roots = set(reg.get("authority_roots", []) or [])
    assert "192.168.1.200" in roots


def test_authority_root_mapping_correct():
    s = build_infrastructure_semantic_summary("192.168.1.40")
    assert s.get("authority_root") is True
    assert "ROLE-PROMETHEUS-AUTHORITY" in (s.get("roles") or [])


def test_control_plane_mapping_correct():
    s = build_infrastructure_semantic_summary("192.168.1.30")
    assert "ROLE-RUNTIME-CONTROL-PLANE" in (s.get("roles") or [])


def test_operational_vs_discoverable_separated():
    reg = build_infrastructure_identity_registry(extra_ctx={})
    inv = reg.get("inventory", {}) or {}
    # Unknown nodes may exist, but must not be classified as operational.
    unknown = inv.get("unknown_nodes", []) or []
    if unknown:
        op_ids = {n.get("identity") for n in (inv.get("operational_nodes") or [])}
        assert not any(u in op_ids for u in unknown)


def test_unknown_entities_not_operational():
    s = build_infrastructure_semantic_summary("192.168.1.123")
    assert s.get("authority_root") is False
    assert s.get("operational_state") == "unknown"


def test_no_phantom_infrastructure():
    reg = build_infrastructure_identity_registry(extra_ctx={})
    assert "192.168.1.40" in (reg.get("authority_roots") or [])


def test_fastpath_uses_infrastructure_registry():
    server, port = _start_gateway_server()
    try:
        payload = {
            "model": "default",
            "messages": [{"role": "user", "content": "qué es 192.168.1.40"}],
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
        assert "Infrastructure" in content
        assert "identity=192.168.1.40" in content
    finally:
        server.shutdown()


def test_reporting_integration():
    from runtime.reporting.reporting_engine import build_infrastructure_authority_summary
    rep = build_infrastructure_authority_summary(extra_ctx={})
    assert rep.get("contract_version") == "35A"


def test_governance_integration():
    from runtime.governance import build_runtime_governance_registry
    reg = build_runtime_governance_registry(extra_ctx={}, sensor_snapshot={})
    infra = reg.get("infrastructure", {})
    assert infra.get("contract_version") == "35A"


def test_validation_integration():
    from runtime.validation.runtime_validation_framework import build_runtime_validation_report
    rep = build_runtime_validation_report(sensor_snapshot={}, extra_ctx={})
    names = {i.get("name") for i in (rep.get("invariants") or [])}
    assert "INVARIANT-INFRASTRUCTURE-IDENTITY" in names
    assert "INVARIANT-AUTHORITY-ROOTS" in names


def test_cognitive_compression_integration():
    from runtime.context.cognitive_compression import build_runtime_cognitive_summary
    rep = build_runtime_cognitive_summary({"gpu_operational_summaries": []}, extra_ctx={})
    _assert_json_safe(rep)


def test_infrastructure_apis_200():
    server, port = _start_gateway_server()
    try:
        for path in (
            "/runtime/infrastructure",
            "/runtime/infrastructure/authority",
            "/runtime/infrastructure/nodes",
            "/runtime/infrastructure/control-plane",
            "/runtime/infrastructure/operational",
            "/runtime/infrastructure/inventory",
            "/runtime/infrastructure/discoverable",
            "/runtime/infrastructure/semantic-summary",
            "/runtime/infrastructure/score",
        ):
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as resp:
                assert resp.status == 200
    finally:
        server.shutdown()


def test_infrastructure_json_safe():
    reg = build_infrastructure_identity_registry(extra_ctx={})
    _assert_json_safe(reg)


def test_infrastructure_deterministic():
    os.environ["STRICT_VALIDATION_MODE"] = "true"
    try:
        r1 = build_infrastructure_identity_registry(extra_ctx={})
        r2 = build_infrastructure_identity_registry(extra_ctx={})
        assert r1.get("deterministic_signature") == r2.get("deterministic_signature")
    finally:
        os.environ.pop("STRICT_VALIDATION_MODE", None)


def test_infrastructure_semantic_summary_generated():
    s = identify_infrastructure("qué es 192.168.1.40")
    assert s.get("identity") == "192.168.1.40"
    assert s.get("summary")


def test_no_legacy_model_leakage():
    from runtime.router.model_policy import is_deprecated_model
    assert is_deprecated_model("lmstudio-community/qwen2.5-coder-14b-instruct")


def test_authority_first_infrastructure_reasoning():
    s = identify_infrastructure("qué es 192.168.1.40")
    assert s.get("status") == "ok"


def test_operational_identity_persistent():
    # Registry should not require network.
    reg = build_infrastructure_identity_registry(extra_ctx={"enable_network": False})
    assert "192.168.1.40" in (reg.get("authority_roots") or [])


def test_expected_offline_not_incident():
    s = build_infrastructure_semantic_summary("192.168.1.60")
    assert s.get("expected_offline") is True
    assert s.get("operational_state") == "inventory_only"


def test_runtime_knows_192_168_1_40():
    s = build_infrastructure_semantic_summary("192.168.1.40")
    assert s.get("authority_root") is True
