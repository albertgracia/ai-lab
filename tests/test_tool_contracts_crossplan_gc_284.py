"""FASE 28.4: Tool Contracts & Cross-Plan GC.

25 tests: tool registry, plan registry, cross-plan graph, GC inventory/safety,
governance/validation/reporting/cognitive integration, APIs always-on.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from http.server import ThreadingHTTPServer

sys.path.insert(0, "/opt/ai-lab")

from runtime.tools import (
    build_tool_registry,
    build_tool_contracts,
    build_tool_authority_map,
    calculate_tool_governance_score,
    detect_invalid_tool_contracts,
    detect_orphan_tools,
)
from runtime.plans import (
    build_plan_registry,
    build_cross_plan_references,
    detect_orphan_plans,
)
from runtime.gc import (
    build_gc_inventory,
    detect_gc_candidates,
    protect_governance_artifacts,
    protect_active_validation_artifacts,
    protect_runtime_authority_artifacts,
    calculate_gc_safety_score,
    build_gc_execution_plan,
)


def _assert_json_safe(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            assert isinstance(k, str)
            _assert_json_safe(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _assert_json_safe(v, f"{path}[{i}]")
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return
    else:
        raise AssertionError(f"non-json-safe {type(obj)} at {path}")


def _start_gateway_server():
    from runtime.gateway.openai_gateway import GatewayHandler
    server = ThreadingHTTPServer(("127.0.0.1", 0), GatewayHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, port


# 1. test_tool_registry_generated
def test_tool_registry_generated():
    reg = build_tool_registry()
    assert isinstance(reg, dict)
    assert reg.get("contract_version") == "28.4"
    assert isinstance(reg.get("tools"), list)
    assert reg.get("total_tools", 0) == len(reg.get("tools"))


# 2. test_tool_contracts_generated
def test_tool_contracts_generated():
    contracts = build_tool_contracts()
    assert isinstance(contracts, list)
    assert len(contracts) >= 5
    for t in contracts:
        assert t.get("tool_id")
        assert t.get("tool_type")
        assert "authority" in t
        assert "execution" in t
        assert "lifecycle" in t
        assert "safety" in t
        assert "deterministic" in t


# 3. test_tool_authority_map_generated
def test_tool_authority_map_generated():
    m = build_tool_authority_map()
    assert "authority_map" in m
    assert m.get("total") == len(m.get("authority_map", {}))
    assert "prometheus_targets_audit" in m["authority_map"]


# 4. test_plan_registry_generated
def test_plan_registry_generated():
    reg = build_plan_registry()
    assert reg.get("contract_version") == "28.4"
    assert isinstance(reg.get("plans"), list)
    assert reg.get("total_plans") == len(reg.get("plans"))


# 5. test_crossplan_graph_generated
def test_crossplan_graph_generated():
    graph = build_cross_plan_references()
    assert graph.get("contract_version") == "28.4"
    assert isinstance(graph.get("nodes"), list)
    assert isinstance(graph.get("edges"), list)
    assert graph.get("total_nodes") == len(graph.get("nodes"))
    assert graph.get("total_edges") == len(graph.get("edges"))


# 6. test_gc_inventory_generated
def test_gc_inventory_generated():
    inv = build_gc_inventory()
    assert inv.get("contract_version") == "28.4"
    assert "items" in inv
    assert "total_items" in inv


# 7. test_gc_candidates_detected
def test_gc_candidates_detected():
    inv = build_gc_inventory()
    inv = protect_governance_artifacts(inv)
    inv = protect_active_validation_artifacts(inv)
    inv = protect_runtime_authority_artifacts(inv)
    cand = detect_gc_candidates(inv, max_age_days=0)
    assert isinstance(cand, list)


# 8. test_gc_protected_artifacts_preserved
def test_gc_protected_artifacts_preserved():
    inv = build_gc_inventory()
    inv = protect_governance_artifacts(inv)
    inv = protect_active_validation_artifacts(inv)
    inv = protect_runtime_authority_artifacts(inv)
    protected = [it for it in (inv.get("items") or []) if it.get("protected")]
    # It is acceptable for this to be 0 on a clean /tmp, but if present it must never be in candidates.
    cand = detect_gc_candidates(inv, max_age_days=0)
    cand_paths = {c.get("path") for c in cand}
    for p in protected:
        assert p.get("path") not in cand_paths


# 9. test_governance_artifacts_protected
def test_governance_artifacts_protected():
    inv = build_gc_inventory()
    inv = protect_governance_artifacts(inv)
    # Any file containing 33a- should be protected
    for it in inv.get("items", []):
        if "33a-" in str(it.get("name", "")).lower():
            assert it.get("protected") is True


# 10. test_validation_artifacts_protected
def test_validation_artifacts_protected():
    inv = build_gc_inventory()
    inv = protect_active_validation_artifacts(inv)
    for it in inv.get("items", []):
        if "33b-" in str(it.get("name", "")).lower():
            assert it.get("protected") is True


# 11. test_execution_governance_generated
def test_execution_governance_generated():
    tool_gov = calculate_tool_governance_score()
    assert "tool_governance_score" in tool_gov
    inv = build_gc_inventory()
    inv = protect_governance_artifacts(inv)
    inv = protect_active_validation_artifacts(inv)
    inv = protect_runtime_authority_artifacts(inv)
    cand = detect_gc_candidates(inv)
    safety = calculate_gc_safety_score(inv, cand)
    plan = build_gc_execution_plan(inv, cand)
    assert plan.get("execution_surface", {}).get("dry_run_only") is True
    assert plan.get("execution_surface", {}).get("SAFE_TO_DELETE") is False


# 12. test_tool_governance_score_generated
def test_tool_governance_score_generated():
    gov = calculate_tool_governance_score()
    assert 0 <= gov.get("tool_governance_score", -1) <= 100


# 13. test_gc_safety_score_generated
def test_gc_safety_score_generated():
    inv = build_gc_inventory()
    inv = protect_governance_artifacts(inv)
    inv = protect_active_validation_artifacts(inv)
    inv = protect_runtime_authority_artifacts(inv)
    cand = detect_gc_candidates(inv)
    safety = calculate_gc_safety_score(inv, cand)
    assert 0 <= safety.get("gc_safety_score", -1) <= 100
    assert safety.get("gc_safety_level") in ("high", "medium", "low", "critical")


# 14. test_invalid_contract_detection
def test_invalid_contract_detection():
    invalid = detect_invalid_tool_contracts()
    assert isinstance(invalid, list)


# 15. test_orphan_plan_detection
def test_orphan_plan_detection():
    orphan = detect_orphan_plans()
    assert isinstance(orphan, list)


# 16. test_crossplan_reference_drift_detection
def test_crossplan_reference_drift_detection():
    from runtime.plans.plan_registry import detect_invalid_plan_references
    drift = detect_invalid_plan_references()
    assert isinstance(drift, list)


# 17. test_reporting_integration
def test_reporting_integration():
    from runtime.reporting.reporting_engine import build_execution_governance_summary
    s = build_execution_governance_summary()
    assert "tool_governance" in s
    assert "gc" in s


# 18. test_cognitive_compression_integration
def test_cognitive_compression_integration():
    from runtime.context.cognitive_compression import compress_execution_governance_signals
    sigs = compress_execution_governance_signals({}, {})
    assert isinstance(sigs, list)
    assert any(s.get("domain") == "execution" for s in sigs)


# 19. test_governance_integration
def test_governance_integration():
    from runtime.governance import build_governance_risk_summary
    risks = build_governance_risk_summary(sensor_snapshot={})
    assert isinstance(risks, list)
    # May include execution risks depending on environment


# 20. test_validation_integration
def test_validation_integration():
    from runtime.validation import build_runtime_invariants
    inv = build_runtime_invariants(sensor_snapshot={})
    names = {i.get("name") for i in inv}
    assert "INVARIANT-TOOL-CONTRACTS" in names
    assert "INVARIANT-PLAN-REGISTRY" in names
    assert "INVARIANT-GC-SAFETY" in names


# 21. test_tool_apis_200
def test_tool_apis_200():
    import requests
    server, port = _start_gateway_server()
    try:
        base = f"http://127.0.0.1:{port}"
        for p in ("/runtime/tools", "/runtime/tools/contracts", "/runtime/tools/governance"):
            r = requests.get(base + p, timeout=5)
            assert r.status_code == 200
    finally:
        server.shutdown()


# 22. test_gc_apis_200
def test_gc_apis_200():
    import requests
    server, port = _start_gateway_server()
    try:
        base = f"http://127.0.0.1:{port}"
        for p in ("/runtime/gc", "/runtime/gc/candidates", "/runtime/gc/safety", "/runtime/plans", "/runtime/plans/graph"):
            r = requests.get(base + p, timeout=5)
            assert r.status_code == 200
    finally:
        server.shutdown()


# 23. test_deterministic_execution_contracts
def test_deterministic_execution_contracts():
    os.environ["STRICT_VALIDATION_MODE"] = "true"
    try:
        r1 = build_tool_registry()
        r2 = build_tool_registry()
        assert r1["contract_version"] == r2["contract_version"]
        assert r1["total_tools"] == r2["total_tools"]
    finally:
        os.environ.pop("STRICT_VALIDATION_MODE", None)


# 24. test_no_active_authority_gc
def test_no_active_authority_gc():
    inv = build_gc_inventory()
    inv = protect_governance_artifacts(inv)
    inv = protect_active_validation_artifacts(inv)
    inv = protect_runtime_authority_artifacts(inv)
    cand = detect_gc_candidates(inv, max_age_days=0)
    for c in cand:
        assert "33a-" not in str(c.get("name", "")).lower()
        assert "33b-" not in str(c.get("name", "")).lower()


# 25. test_tool_contracts_json_safe
def test_tool_contracts_json_safe():
    data = {
        "tools": build_tool_contracts(),
        "plans": build_plan_registry(),
        "graph": build_cross_plan_references(),
        "gc": build_gc_inventory(),
    }
    _assert_json_safe(data)
    json.dumps(data, ensure_ascii=False, default=str)


if __name__ == "__main__":
    tests = [
        test_tool_registry_generated,
        test_tool_contracts_generated,
        test_tool_authority_map_generated,
        test_plan_registry_generated,
        test_crossplan_graph_generated,
        test_gc_inventory_generated,
        test_gc_candidates_detected,
        test_gc_protected_artifacts_preserved,
        test_governance_artifacts_protected,
        test_validation_artifacts_protected,
        test_execution_governance_generated,
        test_tool_governance_score_generated,
        test_gc_safety_score_generated,
        test_invalid_contract_detection,
        test_orphan_plan_detection,
        test_crossplan_reference_drift_detection,
        test_reporting_integration,
        test_cognitive_compression_integration,
        test_governance_integration,
        test_validation_integration,
        test_tool_apis_200,
        test_gc_apis_200,
        test_deterministic_execution_contracts,
        test_no_active_authority_gc,
        test_tool_contracts_json_safe,
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
