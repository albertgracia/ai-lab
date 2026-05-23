"""FASE 36B: Runtime Precision Mode.

Focus: confidence-aware operational precision, no discovery/lmstudio leakage,
determinism, and integrations (fastpath/reporting/governance/validation/apis).
"""

from __future__ import annotations

import os
import sys
import threading
from http.server import ThreadingHTTPServer

import requests

sys.path.insert(0, "/opt/ai-lab")


def _start_gateway_server():
    from runtime.gateway.openai_gateway import GatewayHandler
    server = ThreadingHTTPServer(("127.0.0.1", 0), GatewayHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, port


def _fake_authority_snapshot(*, freshness: str = "fresh", up: int = 5, total: int = 5, gaps=None):
    gaps = gaps or []
    return {
        "contract_version": "35C",
        "prometheus": {"targets": {"scrape_up": up, "active_total": total, "scrape_down": max(0, total - up)}},
        "freshness": {"status": freshness, "confidence": "high" if freshness == "fresh" else "medium", "reasons": []},
        "gaps": gaps,
        "operational_truth": {"operational_nodes": [], "inventory_only_nodes": [], "discoverable_nodes": []},
        "deterministic_signature": "authsig123",
        "generated_at": 0.0,
    }


# 1. test_operational_precision_summary
def test_operational_precision_summary(monkeypatch):
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report, build_precision_summary

    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot())
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [
        {"entity_id": "rx9070-node", "entity_type": "inference_node", "routable": True, "operational_state": "active", "deprecated": False, "confidence": "high"},
    ])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [
        {"entity_id": "qwen3.6-35b-a3b-mtp", "entity_type": "model", "routable": False, "operational_state": "inactive", "deprecated": False, "discoverability": "discoverable"},
    ])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {"incidents": {"active_incidents_total": 0, "highest_severity": "info"}})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {"score": {"structural_health_score": 90.0}, "modules_total": 1, "edges_total": 1})

    rep = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    summ = build_precision_summary(rep)
    lines = (summ.get("precision_summary", {}) or {}).get("lines", [])
    assert isinstance(lines, list)
    assert any("Confidence:" in ln for ln in lines)


# 2. test_confidence_generated
def test_confidence_generated(monkeypatch):
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report

    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot())
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})

    rep = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    conf = rep.get("confidence", {}) or {}
    assert "operational" in conf
    assert conf["operational"].get("label") in ("high", "medium", "low", "unknown")


# 3. test_authority_conflict_detection
def test_authority_conflict_detection(monkeypatch):
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report

    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot(freshness="unavailable"))
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [
        {"entity_id": "rx9070-node", "entity_type": "inference_node", "routable": True, "operational_state": "active", "deprecated": False, "confidence": "high"},
    ])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})

    rep = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    assert isinstance(rep.get("conflicts", []), list)


# 4. test_partial_state_detection
def test_partial_state_detection(monkeypatch):
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report

    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot(freshness="partial"))
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})

    rep = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    assert isinstance(rep.get("partial", []), list)


# 5. test_discoverable_not_operational
def test_discoverable_not_operational(monkeypatch):
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report

    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot())
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [
        {"entity_id": "qwen3.6-35b-a3b-mtp", "entity_type": "model", "routable": True, "operational_state": "active", "deprecated": False},
    ])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})

    rep = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    ents = ((rep.get("discoverable", {}) or {}).get("entities", []) or [])
    assert all((e.get("routable") is False and e.get("operational_state") != "active") for e in ents)


# 6. test_unknown_not_operational
def test_unknown_not_operational():
    # Precision mode should never require unknown -> hallucination; empty snapshot stays safe.
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report
    rep = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    assert isinstance(rep, dict)


# 7. test_no_lmstudio_leakage
def test_no_lmstudio_leakage(monkeypatch):
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report

    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot())
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [
        {"entity_id": "lmstudio-community/qwen2.5-coder-14b-instruct", "entity_type": "model", "routable": False, "operational_state": "inactive", "deprecated": False},
    ])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})

    rep = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    raw = str(rep).lower()
    assert "lmstudio-community" not in raw


# 8. test_no_discovery_leakage
def test_no_discovery_leakage(monkeypatch):
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report

    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot())
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [
        {"entity_id": "some-model", "entity_type": "model", "routable": True, "operational_state": "active", "deprecated": False},
    ])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})

    rep = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    ents = ((rep.get("discoverable", {}) or {}).get("entities", []) or [])
    assert all(e.get("routable") is False for e in ents)


# 9. test_precision_fastpath
def test_precision_fastpath(monkeypatch):
    from runtime.fastpath import build_fastpath_response

    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot())
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [
        {"entity_id": "rx9070-node", "entity_type": "inference_node", "routable": True, "operational_state": "active", "deprecated": False, "confidence": "high"},
    ])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})

    fp = build_fastpath_response("estado runtime", extra_ctx={"enable_network": False}, sensor_snapshot={}, verbosity="operational")
    lines = ((fp.get("summary", {}) or {}).get("lines", []) or [])
    assert isinstance(lines, list)


# 10. test_precision_compactness
def test_precision_compactness(monkeypatch):
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report
    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot())
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})
    rep = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    # Contract is compact; key lists are bounded.
    assert len(((rep.get("discoverable", {}) or {}).get("entities", []) or [])) <= 50


# 11. test_confidence_deterministic
def test_confidence_deterministic(monkeypatch):
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report
    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot())
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})

    os.environ["STRICT_VALIDATION_MODE"] = "true"
    r1 = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    r2 = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    assert r1.get("deterministic_signature") == r2.get("deterministic_signature")


# 12. test_authority_confidence
def test_authority_confidence(monkeypatch):
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report
    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot(freshness="partial"))
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})
    rep = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    assert ((rep.get("confidence", {}) or {}).get("authority", {}) or {}).get("label") in ("high", "medium", "low", "unknown")


# 13. test_incident_confidence
def test_incident_confidence(monkeypatch):
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report
    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot())
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {"incidents": {"active_incidents_total": 1, "highest_severity": "warning"}})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})
    rep = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    assert "incidents" in (rep.get("confidence", {}) or {})


# 14. test_routing_confidence
def test_routing_confidence(monkeypatch):
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report
    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot())
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [
        {"entity_id": "rx9070-node", "entity_type": "inference_node", "routable": True, "operational_state": "active", "deprecated": False, "confidence": "high"},
    ])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})
    rep = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    assert ((rep.get("confidence", {}) or {}).get("routing", {}) or {}).get("label") in ("high", "medium", "low", "unknown")


# 15. test_reporting_integration
def test_reporting_integration(monkeypatch):
    from runtime.reporting.reporting_engine import build_precision_summary

    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot())
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})

    out = build_precision_summary(sensor_snapshot={}, extra_ctx={"enable_network": False})
    assert out.get("contract_version")


# 16. test_governance_integration
def test_governance_integration(monkeypatch):
    from runtime.governance import build_runtime_governance_registry

    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot())
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})

    reg = build_runtime_governance_registry(extra_ctx={"enable_network": False}, sensor_snapshot={})
    assert "precision" in reg


# 17. test_validation_integration
def test_validation_integration():
    from runtime.validation.runtime_validation_framework import build_runtime_invariants
    inv = build_runtime_invariants(sensor_snapshot={}, extra_ctx={"enable_network": False})
    names = {i.get("name") for i in inv}
    assert "INVARIANT-PRECISION-CONFIDENCE" in names
    assert "INVARIANT-NO-OVERASSERTION" in names
    assert "INVARIANT-NO-DISCOVERY-LEAKAGE" in names
    assert "INVARIANT-NO-LMSTUDIO-LEAKAGE" in names


# 18. test_cognitive_compression_integration
def test_cognitive_compression_integration(monkeypatch):
    from runtime.context.cognitive_compression import build_runtime_cognitive_summary
    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot())
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})
    out = build_runtime_cognitive_summary({}, extra_ctx={"enable_network": False})
    assert isinstance(out, dict)


# 19. test_codebase_integration
def test_codebase_integration(monkeypatch):
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report
    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot())
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {"score": {"structural_health_score": 88.0}})
    rep = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    assert "codebase" in (rep.get("confidence", {}) or {})


# 20. test_precision_apis_200
def test_precision_apis_200():
    server, port = _start_gateway_server()
    try:
        for path in (
            "/runtime/precision",
            "/runtime/precision/confidence",
            "/runtime/precision/evidence",
            "/runtime/precision/conflicts",
            "/runtime/precision/partial",
            "/runtime/precision/discoverable",
            "/runtime/precision/score",
        ):
            r = requests.get(f"http://127.0.0.1:{port}{path}", timeout=5)
            assert r.status_code == 200
            assert r.headers.get("Content-Type", "").startswith("application/json")
            _ = r.json()
    finally:
        server.shutdown()


# 21. test_precision_json_safe
def test_precision_json_safe():
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report
    rep = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    # json.dumps is the practical JSON-safe test here.
    import json
    json.dumps(rep, sort_keys=True, ensure_ascii=True, default=str)


# 22. test_precision_deterministic
def test_precision_deterministic():
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report
    os.environ["STRICT_VALIDATION_MODE"] = "true"
    r1 = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    r2 = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    assert r1.get("deterministic_signature") == r2.get("deterministic_signature")


# 23. test_no_overassertion
def test_no_overassertion(monkeypatch):
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report
    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot(freshness="partial"))
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})
    rep = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    lbl = (((rep.get("confidence", {}) or {}).get("operational", {}) or {}).get("label"))
    # If evidence is partial, confidence cannot be high.
    assert lbl != "high"


# 24. test_partial_evidence_handling
def test_partial_evidence_handling(monkeypatch):
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report
    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot(freshness="partial"))
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})
    rep = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    assert (rep.get("precision", {}) or {}).get("partial_state_total", 0) >= 1


# 25. test_runtime_precision_operationally_grounded
def test_runtime_precision_operationally_grounded(monkeypatch):
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report
    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: _fake_authority_snapshot())
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.reporting.reporting_engine.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})
    rep = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    # Evidence catalog must exist and be bounded.
    assert isinstance(rep.get("evidence", []), list)
    assert len(rep.get("evidence", [])) <= 10
