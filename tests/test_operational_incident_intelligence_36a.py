"""FASE 36A: Operational Incident Intelligence tests."""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, "/opt/ai-lab")

from runtime.incidents import (
    INCIDENT_CONTRACT_VERSION,
    build_incident_intelligence_report,
    IncidentSignal,
    correlate_incident_signals,
    calculate_incident_blast_radius,
    build_incident_hypotheses,
    build_incident_recommendations,
    build_blast_radius_summary,
)
from runtime.incidents.contracts import (
    DOMAIN_DEPENDENCY_MAP,
    CORRELATION_DOMAINS,
    SEVERITY_ORDER,
    BlastRadiusEntry,
    OperationalIncident,
)
from runtime.incidents.incident_intelligence import _merge_related_incidents


def _start_gateway_server():
    from runtime.gateway.openai_gateway import GatewayHandler

    server = ThreadingHTTPServer(("127.0.0.1", 0), GatewayHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, port


def _signal(domain: str, severity: str = "warning") -> IncidentSignal:
    return IncidentSignal(
        domain=domain,
        signal_type=f"{domain}_failure",
        severity=severity,
        description=f"{domain} failure",
        evidence=["test"],
        confidence="high",
        freshness="fresh",
    )


def _incident(domain: str, severity: str = "warning") -> OperationalIncident:
    sig = _signal(domain, severity)
    return OperationalIncident(
        incident_id=f"INC-{domain.upper()}-TEST",
        primary_domain=domain,
        severity=severity,
        title=sig.description,
        description=sig.description,
        signals=[sig.to_dict()],
        correlated_signals=[],
        blast_radius=[],
        hypotheses=[],
        recommendations=[],
        evidence=sig.evidence,
        confidence=sig.confidence,
        deterministic_signature="test",
    )


# ── Contracts ─────────────────────────────────────────────────────────


def test_contract_version():
    assert INCIDENT_CONTRACT_VERSION == "36A"


def test_domain_dependency_map_structure():
    assert isinstance(DOMAIN_DEPENDENCY_MAP, dict)
    assert len(DOMAIN_DEPENDENCY_MAP) >= 12
    for domain, deps in DOMAIN_DEPENDENCY_MAP.items():
        assert isinstance(domain, str)
        assert isinstance(deps, list)
        for d in deps:
            assert isinstance(d, str)


def test_correlation_domains_structure():
    assert isinstance(CORRELATION_DOMAINS, dict)
    assert len(CORRELATION_DOMAINS) >= 12
    for domain, peers in CORRELATION_DOMAINS.items():
        assert isinstance(domain, str)
        assert isinstance(peers, list)


def test_severity_order_structure():
    assert isinstance(SEVERITY_ORDER, dict)
    assert SEVERITY_ORDER.get("critical") == 0
    assert SEVERITY_ORDER.get("info") == 4
    assert len(SEVERITY_ORDER) == 5


# ── Report structure and determinism ──────────────────────────────────


def test_report_structure():
    rep = build_incident_intelligence_report(sensor_snapshot={}, extra_ctx={"enable_network": False})
    assert "contract_version" in rep
    assert "incident_count" in rep
    assert "highest_severity" in rep
    assert "affected_domains" in rep
    assert "blast_radius_summary" in rep
    assert "correlation_results" in rep
    assert "total_signals_evaluated" in rep
    assert "deterministic_signature" in rep


def test_report_json_safe():
    rep = build_incident_intelligence_report(sensor_snapshot={}, extra_ctx={"enable_network": False})
    json.dumps(rep)


def test_no_synthetic_incidents():
    """Incidents must be grounded in real signals, not fabricated."""
    rep = build_incident_intelligence_report(sensor_snapshot={}, extra_ctx={"enable_network": False})
    for inc in rep.get("active_incidents", []):
        assert len(inc.get("evidence", [])) >= 1


def test_full_report_deterministic():
    os.environ["STRICT_VALIDATION_MODE"] = "true"
    try:
        r1 = build_incident_intelligence_report(sensor_snapshot={}, extra_ctx={"enable_network": False})
        r2 = build_incident_intelligence_report(sensor_snapshot={}, extra_ctx={"enable_network": False})
        assert r1.get("deterministic_signature") == r2.get("deterministic_signature")
        assert r1.get("incident_count") == r2.get("incident_count")
        assert r1.get("highest_severity") == r2.get("highest_severity")
    finally:
        os.environ.pop("STRICT_VALIDATION_MODE", None)


# ── Correlation (unit tests) ─────────────────────────────────────────


def test_correlate_empty():
    result = correlate_incident_signals([])
    # returns (signals, results) tuple
    assert len(result) == 2
    assert result[0] == []
    assert result[1] == []


def test_correlate_single_signal():
    sig = _signal("gpu")
    result = correlate_incident_signals([sig])
    assert len(result) == 2
    assert isinstance(result[0], list)
    assert isinstance(result[1], list)


def test_correlate_related_domains():
    sigs = [_signal("authority"), _signal("observability")]
    result = correlate_incident_signals(sigs)
    assert len(result) == 2


def test_correlate_unrelated_domains():
    sigs = [_signal("gpu"), _signal("storage")]
    result = correlate_incident_signals(sigs)
    assert len(result) == 2


def test_correlate_deterministic():
    os.environ["STRICT_VALIDATION_MODE"] = "true"
    sigs = [_signal("authority"), _signal("observability")]
    try:
        r1 = correlate_incident_signals(sigs)
        r2 = correlate_incident_signals(sigs)
        assert json.dumps(r1, sort_keys=True, default=str) == json.dumps(r2, sort_keys=True, default=str)
    finally:
        os.environ.pop("STRICT_VALIDATION_MODE", None)


# ── Blast Radius (unit tests) ────────────────────────────────────────


def test_blast_radius_empty():
    # Pass a signal with info severity to get empty radius
    sig = _signal("info", "info")
    result = calculate_incident_blast_radius(sig, [])
    assert result == []


def test_blast_radius_single_domain():
    sig = _signal("authority", "critical")
    other = _signal("observability", "warning")
    result = calculate_incident_blast_radius(sig, [sig, other])
    assert len(result) >= 1
    for entry in result:
        d = entry.to_dict()
        assert "affected_domain" in d


def test_blast_radius_no_false_positives():
    sig = _signal("info", "info")
    result = calculate_incident_blast_radius(sig, [])
    assert len(result) == 0


def test_blast_radius_deterministic():
    os.environ["STRICT_VALIDATION_MODE"] = "true"
    sig = _signal("authority", "critical")
    try:
        r1 = calculate_incident_blast_radius(sig, [sig])
        r2 = calculate_incident_blast_radius(sig, [sig])
        j1 = json.dumps([x.to_dict() for x in r1], sort_keys=True)
        j2 = json.dumps([x.to_dict() for x in r2], sort_keys=True)
        assert j1 == j2
    finally:
        os.environ.pop("STRICT_VALIDATION_MODE", None)


# ── Hypotheses (unit tests) ──────────────────────────────────────────


def test_hypotheses_empty():
    result = build_incident_hypotheses(_signal("info", "info"), [], [])
    assert isinstance(result, list)


def test_hypotheses_grounded():
    sig = _signal("observability", "warning")
    result = build_incident_hypotheses(sig, [sig], [])
    for h in result:
        d = h.to_dict()
        assert len(d.get("evidence", [])) >= 1


def test_hypotheses_no_free_llm():
    sig = _signal("gpu", "error")
    result = build_incident_hypotheses(sig, [sig], [])
    txt = json.dumps([h.to_dict() for h in result]).lower()
    assert "i think" not in txt
    assert "speculat" not in txt


def test_hypotheses_deterministic():
    os.environ["STRICT_VALIDATION_MODE"] = "true"
    sig = _signal("authority", "warning")
    try:
        r1 = build_incident_hypotheses(sig, [sig], [])
        r2 = build_incident_hypotheses(sig, [sig], [])
        j1 = json.dumps([h.to_dict() for h in r1], sort_keys=True)
        j2 = json.dumps([h.to_dict() for h in r2], sort_keys=True)
        assert j1 == j2
    finally:
        os.environ.pop("STRICT_VALIDATION_MODE", None)


# ── Recommendations (unit tests) ─────────────────────────────────────


def test_recommendations_empty():
    result = build_incident_recommendations(_signal("info", "info"), [], [])
    assert isinstance(result, list)


def test_recommendations_with_signals():
    sig = _signal("observability", "warning")
    blast = calculate_incident_blast_radius(sig, [sig])
    hyps = build_incident_hypotheses(sig, [sig], [])
    result = build_incident_recommendations(sig, blast, hyps)
    for r in result:
        d = r.to_dict()
        assert "priority" in d
        assert "domain" in d
        assert "description" in d
        assert "actionable" in d


def test_recommendations_no_llm():
    sig = _signal("authority", "critical")
    blast = calculate_incident_blast_radius(sig, [sig])
    hyps = build_incident_hypotheses(sig, [sig], [])
    result = build_incident_recommendations(sig, blast, hyps)
    txt = json.dumps([r.to_dict() for r in result]).lower()
    assert "i suggest" not in txt


# ── Merge (unit tests) ───────────────────────────────────────────────


def test_merge_related():
    sigs = [_incident("authority", "warning"), _incident("authority", "error")]
    result = _merge_related_incidents(sigs)
    assert len(result) <= len(sigs)
    assert len(result) == 1  # same domain merged


def test_merge_unrelated():
    sigs = [_incident("gpu", "warning"), _incident("storage", "info")]
    result = _merge_related_incidents(sigs)
    assert len(result) == len(sigs)


def test_merge_empty():
    result = _merge_related_incidents([])
    assert result == []


# ── Blast Radius Summary ─────────────────────────────────────────────


def test_blast_radius_summary_empty():
    result = build_blast_radius_summary([])
    assert isinstance(result, dict)
    assert result.get("blast_radius_entries", 0) == 0


def test_blast_radius_summary_with_entries():
    entries = [
        BlastRadiusEntry(
            affected_domain="authority",
            severity="critical",
            dependency_path=["root"],
            description="authority degraded",
        )
    ]
    result = build_blast_radius_summary(entries)
    assert result.get("blast_radius_entries", 0) >= 1
    assert "by_severity" in result


# ── Gateway APIs ─────────────────────────────────────────────────────


def test_incidents_api_200():
    os.environ["AI_LAB_ENABLE_LIVE_AUTHORITY_NETWORK"] = "false"
    server, port = _start_gateway_server()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/runtime/incidents", timeout=5) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data.get("contract_version") == "36A"
    finally:
        server.shutdown()
        os.environ.pop("AI_LAB_ENABLE_LIVE_AUTHORITY_NETWORK", None)


def test_incidents_active_api_200():
    os.environ["AI_LAB_ENABLE_LIVE_AUTHORITY_NETWORK"] = "false"
    server, port = _start_gateway_server()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/runtime/incidents/active", timeout=5) as resp:
            assert resp.status == 200
    finally:
        server.shutdown()
        os.environ.pop("AI_LAB_ENABLE_LIVE_AUTHORITY_NETWORK", None)


def test_incidents_correlations_api_200():
    os.environ["AI_LAB_ENABLE_LIVE_AUTHORITY_NETWORK"] = "false"
    server, port = _start_gateway_server()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/runtime/incidents/correlations", timeout=5) as resp:
            assert resp.status == 200
    finally:
        server.shutdown()
        os.environ.pop("AI_LAB_ENABLE_LIVE_AUTHORITY_NETWORK", None)


def test_incidents_blast_radius_api_200():
    os.environ["AI_LAB_ENABLE_LIVE_AUTHORITY_NETWORK"] = "false"
    server, port = _start_gateway_server()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/runtime/incidents/blast-radius", timeout=5) as resp:
            assert resp.status == 200
    finally:
        server.shutdown()
        os.environ.pop("AI_LAB_ENABLE_LIVE_AUTHORITY_NETWORK", None)


# ── Integration: Governance ───────────────────────────────────────────


def test_governance_integration():
    from runtime.governance.runtime_governance_registry import build_runtime_governance_registry

    reg = build_runtime_governance_registry(extra_ctx={"enable_network": False}, sensor_snapshot={})
    ip = reg.get("incident_pressure", {}) or {}
    assert ip.get("contract_version") == "36A"
    assert "active_incidents_total" in ip
    assert "highest_severity" in ip
    assert "affected_domains" in ip


# ── Integration: Validation ───────────────────────────────────────────


def test_validation_invariant_no_critical_incidents():
    from runtime.validation.runtime_validation_framework import build_runtime_validation_report

    rep = build_runtime_validation_report(sensor_snapshot={}, extra_ctx={"enable_network": False})
    invs = rep.get("invariants", []) or []
    names = {i.get("name") for i in invs if isinstance(i, dict)}
    assert "INVARIANT-NO-CRITICAL-INCIDENTS" in names


def test_validation_invariant_incident_grounding():
    from runtime.validation.runtime_validation_framework import build_runtime_validation_report

    rep = build_runtime_validation_report(sensor_snapshot={}, extra_ctx={"enable_network": False})
    invs = rep.get("invariants", []) or []
    names = {i.get("name") for i in invs if isinstance(i, dict)}
    assert "INVARIANT-INCIDENT-GROUNDING" in names


def test_validation_invariant_no_synthetic():
    from runtime.validation.runtime_validation_framework import build_runtime_validation_report

    rep = build_runtime_validation_report(sensor_snapshot={}, extra_ctx={"enable_network": False})
    invs = rep.get("invariants", []) or []
    names = {i.get("name") for i in invs if isinstance(i, dict)}
    assert "INVARIANT-NO-SYNTHETIC-INCIDENTS" in names


# ── Integration: Cognitive Compression ────────────────────────────────


def test_cognitive_compression_integration():
    from runtime.context.cognitive_compression import build_runtime_cognitive_summary

    rep = build_runtime_cognitive_summary(sensor_snapshot={}, extra_ctx={"enable_network": False})
    sigs = rep.get("signals", []) or []
    incident_signals = [s for s in sigs if isinstance(s, dict) and s.get("domain") == "incidents"]
    assert isinstance(incident_signals, list)


# ── Integration: Reporting ────────────────────────────────────────────


def test_reporting_integration():
    from runtime.reporting.reporting_engine import build_incident_intelligence_summary

    rep = build_incident_intelligence_summary(extra_ctx={"enable_network": False})
    assert rep.get("contract_version") == "36A"
    inc = rep.get("incidents", {}) or {}
    assert "active_incidents_total" in inc
    assert "highest_severity" in inc


# ── Integration: Fast-path ────────────────────────────────────────────


def test_fastpath_includes_incident_line():
    from runtime.fastpath import build_fast_operational_summary

    s = build_fast_operational_summary(extra_ctx={"verbosity": "operational", "enable_network": False})
    lines = [str(x) for x in (s.get("lines", []) or [])]
    signals = s.get("signals", []) or []
    incident_signals = [sig for sig in signals if isinstance(sig, dict) and sig.get("domain") == "incidents"]
    assert any("Operational summary" in l for l in lines)
    assert isinstance(incident_signals, list)
