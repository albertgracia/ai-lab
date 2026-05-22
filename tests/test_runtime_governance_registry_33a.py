"""
FASE 33A: Runtime Governance Registry — 20 tests, 70+ assertions.
"""

from __future__ import annotations

import json
import sys
import time

sys.path.insert(0, "/opt/ai-lab")

from runtime.governance.runtime_governance_registry import (
    build_runtime_governance_registry,
    build_governance_domains,
    build_governance_authority_map,
    build_governance_confidence_map,
    build_governance_contract_registry,
    build_governance_health_summary,
    build_governance_risk_summary,
    build_governance_remediation_summary,
    calculate_governance_score,
    detect_governance_drift,
    build_governance_executive_summary,
    build_governance_degradation_summary,
    build_governance_risk_executive,
    GOVERNANCE_DOMAINS,
    DOMAIN_AUTHORITY,
    REGISTERED_PHASES,
    ACTIVE_CONTRACTS,
    DEPRECATED_CONTRACTS,
)
from runtime.governance.contracts import (
    GovernanceRegistryContract,
    GovernanceDomainContract,
    GovernanceAuthorityContract,
    GovernanceConfidenceContract,
    GovernanceRiskContract,
    GovernanceRemediationContract,
    GovernanceHealthContract,
    GovernanceContractRegistry,
    GOVERNANCE_CONTRACT_VERSION,
)


def _assert_json_safe(obj, path=""):
    """Recursively verify JSON-safe types."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            assert isinstance(k, str), f"non-string key at {path}"
            _assert_json_safe(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _assert_json_safe(v, f"{path}[{i}]")
    elif isinstance(obj, (str, int, float, bool)):
        pass
    elif obj is None:
        pass
    else:
        assert False, f"non-JSON-safe type {type(obj)} at {path}"


def _count_by_severity(risks, severity):
    return sum(1 for r in risks if r.get("severity") == severity)


# ── 1. test_governance_registry_generated ──

def test_governance_registry_generated():
    registry = build_runtime_governance_registry()
    assert isinstance(registry, dict)
    assert "governance_score" in registry
    assert "governance_level" in registry
    assert "domains" in registry
    assert "risks" in registry
    assert "authority_map" in registry
    assert "confidence_map" in registry
    assert "contract_registry" in registry
    assert "remediation" in registry
    assert "health_summary" in registry
    assert "governance_score_info" in registry
    assert "drift" in registry
    assert registry.get("contract_version") == GOVERNANCE_CONTRACT_VERSION
    assert registry.get("freshness") == "fresh"


# ── 2. test_governance_domains_generated ──

def test_governance_domains_generated():
    domains = build_governance_domains()
    assert isinstance(domains, list)
    assert len(domains) >= 15
    domain_names = {d["domain"] for d in domains}
    for expected in GOVERNANCE_DOMAINS:
        assert expected in domain_names, f"domain {expected} missing"
    for d in domains:
        assert "operational_state" in d
        assert "confidence" in d
        assert "authority" in d
        assert "source_of_truth" in d
        assert "freshness" in d
        assert "explainable" in d
        assert isinstance(d["degraded"], bool)
        assert isinstance(d["explainable"], bool)
    # Prometheus should have operational authority
    prom = [d for d in domains if d["domain"] == "prometheus"]
    assert len(prom) == 1
    assert prom[0]["authority"] == "operational"


# ── 3. test_governance_authority_map_generated ──

def test_governance_authority_map_generated():
    auth = build_governance_authority_map()
    assert isinstance(auth, dict)
    assert "authorities" in auth
    assert "operational_authority" in auth
    assert "visualization_authority" in auth
    assert "dependency_authority" in auth
    assert "validation_authority" in auth
    assert "fallback_authority" in auth
    assert auth["operational_authority"] == "prometheus"
    assert auth["visualization_authority"] == "grafana"
    assert auth["dependency_authority"] == "topology"
    assert auth["fallback_authority"] == "inventory"
    for domain, info in auth["authorities"].items():
        assert isinstance(info, dict)
        assert "authority_type" in info
        assert "source_of_truth" in info
        assert "confidence" in info
        assert "freshness" in info


# ── 4. test_governance_confidence_map_generated ──

def test_governance_confidence_map_generated():
    conf_map = build_governance_confidence_map()
    assert isinstance(conf_map, dict)
    assert "domains" in conf_map
    assert "topology_confidence" in conf_map
    for domain, info in conf_map["domains"].items():
        assert isinstance(info, dict)
        assert "confidence" in info
        assert "freshness" in info
        assert "propagated_from" in info
        assert "degraded" in info
        assert isinstance(info["degraded"], bool)
        assert "score" in info
    # governance should exist
    assert "governance" in conf_map["domains"]


# ── 5. test_governance_score_generated ──

def test_governance_score_generated():
    score = calculate_governance_score()
    assert isinstance(score, dict)
    assert "governance_score" in score
    assert "governance_level" in score
    assert "components" in score
    assert "contract_version" in score
    assert "generated_at" in score
    assert 0 <= score["governance_score"] <= 100
    assert score["governance_level"] in ("high", "medium", "low", "critical", "degraded")
    assert "topology_confidence_weighted" in score["components"]
    assert "domain_confidence_avg" in score["components"]
    assert "freshness_score" in score["components"]
    assert "explainability_ratio" in score["components"]


# ── 6. test_governance_risk_detection ──

def test_governance_risk_detection():
    risks = build_governance_risk_summary()
    assert isinstance(risks, list)
    assert len(risks) >= 1
    for r in risks:
        assert "risk_type" in r
        assert "severity" in r
        assert "domain" in r
        assert "description" in r
        assert "confidence" in r
        assert r.get("explainable", True) is True
    # risk with stale authority
    risks_with_stale = build_governance_risk_summary(
        extra_ctx={}, sensor_snapshot={"stale_sources": ["prometheus"]}
    )
    stale_risks = [r for r in risks_with_stale if r["risk_type"] == "stale_authority"]
    assert len(stale_risks) >= 1


# ── 7. test_governance_contract_registry_generated ──

def test_governance_contract_registry_generated():
    contracts = build_governance_contract_registry()
    assert isinstance(contracts, dict)
    assert "registered_phases" in contracts
    assert "active_contracts" in contracts
    assert "deprecated_contracts" in contracts
    assert "incompatible_contracts" in contracts
    assert "stale_contracts" in contracts
    assert contracts["total_contracts"] == len(REGISTERED_PHASES)
    # 33A should be active
    assert "33A" in contracts["active_contracts"]
    # 31B-32B should be active
    assert "32B" in contracts["active_contracts"]
    assert "31D" in contracts["active_contracts"]

    for phase in contracts["registered_phases"]:
        assert "phase" in phase
        assert "label" in phase
        assert "domain" in phase


# ── 8. test_prometheus_operational_authority ──

def test_prometheus_operational_authority():
    auth = build_governance_authority_map()
    assert auth["operational_authority"] == "prometheus"
    prom = auth["authorities"].get("prometheus", {})
    assert prom.get("authority_type") == "operational"
    assert prom.get("source_of_truth") == "prometheus"
    assert prom.get("confidence") == "high"

    # With prometheus targets missing, authority should be stale
    auth_missing = build_governance_authority_map(extra_ctx={"prometheus_targets": False})
    prom_missing = auth_missing["authorities"].get("prometheus", {})
    assert prom_missing.get("freshness") == "stale"


# ── 9. test_grafana_visualization_authority ──

def test_grafana_visualization_authority():
    auth = build_governance_authority_map()
    assert auth["visualization_authority"] == "grafana"
    grafana = auth["authorities"].get("grafana", {})
    assert grafana.get("authority_type") == "visualization"
    assert grafana.get("source_of_truth") == "grafana"


# ── 10. test_inventory_not_runtime_authority ──

def test_inventory_not_runtime_authority():
    auth = build_governance_authority_map()
    assert auth["fallback_authority"] == "inventory"
    assert auth["operational_authority"] != "inventory"
    assert auth["dependency_authority"] != "inventory"
    # Inventory should not be in authority map at all, or should be marked fallback
    if "inventory" in auth.get("authorities", {}):
        inv = auth["authorities"]["inventory"]
        assert inv.get("authority_type") in ("fallback", "inventory")


# ── 11. test_governance_confidence_propagation ──

def test_governance_confidence_propagation():
    # Test that propagated_from works for observability
    conf_map = build_governance_confidence_map(
        sensor_snapshot={"domain_confidence": {"observability": "unknown"}}
    )
    obs = conf_map["domains"].get("observability", {})
    assert "propagated_from" in obs
    # When observability confidence is unknown, it should propagate from prometheus
    if obs.get("confidence") == "unknown":
        assert "prometheus" in obs.get("propagated_from", [])


# ── 12. test_governance_degradation_propagation ──

def test_governance_degradation_propagation():
    # Create sensor snapshot with low confidence domains
    sensor = {
        "domain_confidence": {
            "prometheus": "low",
            "observability": "low",
            "gpu": "low",
        }
    }
    domains = build_governance_domains(sensor_snapshot=sensor)
    degraded = [d for d in domains if d.get("degraded")]
    assert len(degraded) >= 3
    degraded_names = {d["domain"] for d in degraded}
    assert "prometheus" in degraded_names
    assert "observability" in degraded_names

    health = build_governance_health_summary(sensor_snapshot=sensor, domains=domains)
    assert health.get("operational_state") == "degraded"
    assert len(health.get("degraded_domains", [])) >= 3


# ── 13. test_governance_remediation_integration ──

def test_governance_remediation_integration():
    remediation = build_governance_remediation_summary()
    assert isinstance(remediation, dict)
    assert "registered_phases_total" in remediation
    assert "phases" in remediation
    assert remediation["registered_phases_total"] == len(REGISTERED_PHASES)

    phases = remediation["phases"]
    for phase in phases:
        assert "phase" in phase
        assert "domain" in phase
        assert "status" in phase
        assert "severity" in phase
        assert "description" in phase

    # 33A should be present
    f33a = [p for p in phases if p["phase"] == "33A"]
    assert len(f33a) == 1
    assert f33a[0]["domain"] == "governance"

    # Deprecated phases should be marked
    deprecated_phases = [p for p in phases if p["status"] == "deprecated"]
    assert len(deprecated_phases) >= 1


# ── 14. test_governance_reporting_integration ──

def test_governance_reporting_integration():
    from runtime.reporting.reporting_engine import build_governance_summary
    summary = build_governance_summary()
    assert isinstance(summary, dict)
    assert "governance_level" in summary
    assert "blocked_actions" in summary
    assert "evidence_guard_active" in summary
    # FASE 33A fields should be present
    if summary.get("governance_score") is not None:
        assert 0 <= summary["governance_score"] <= 100
    if summary.get("governance_registry"):
        assert "governance_score" in summary["governance_registry"]
        assert "governance_level" in summary["governance_registry"]
        assert "contract_version" in summary["governance_registry"]


# ── 15. test_governance_cognitive_summary ──

def test_governance_cognitive_summary():
    from runtime.context.cognitive_compression import compress_governance_signals
    signals = compress_governance_signals(
        sensor_snapshot={},
        extra_ctx={},
    )
    if signals:
        governance_signals = [s for s in signals if s.get("domain") == "governance"]
        if governance_signals:
            # There should be a governance registry signal (score, degradation, or unavailable)
            has_registry = any(
                "governance score" in s.get("message", "").lower()
                for s in governance_signals
            )
            has_unavailable = any(
                "no disponible" in s.get("message", "").lower()
                or "no integrada" in s.get("message", "").lower()
                for s in governance_signals
            )
            # One of these should be true
            assert has_registry or has_unavailable, "no governance registry signal found"


# ── 16. test_governance_contract_validation ──

def test_governance_contract_validation():
    contracts = build_governance_contract_registry()
    # All active contracts should be in registered_phases
    registered_phases_set = {p["phase"] for p in contracts["registered_phases"]}
    for active in contracts["active_contracts"]:
        assert active in registered_phases_set, f"active contract {active} not in registered phases"

    # All deprecated contracts should be in registered_phases
    for dep in contracts["deprecated_contracts"]:
        assert dep in registered_phases_set, f"deprecated contract {dep} not in registered phases"

    # 30I-F0 should be in incompatible contracts
    assert "30I-F0" in contracts["incompatible_contracts"]


# ── 17. test_governance_unknown_state_handled ──

def test_governance_unknown_state_handled():
    # Governance registry should handle empty/missing data gracefully
    registry = build_runtime_governance_registry(extra_ctx={}, sensor_snapshot={})
    assert isinstance(registry, dict)
    assert registry.get("contract_version") == GOVERNANCE_CONTRACT_VERSION
    assert registry.get("freshness") == "fresh"
    # Even with empty data, domains should be generated
    assert len(registry.get("domains", [])) >= 15
    # Risks should exist even with empty data (at minimum "no_risks")
    assert len(registry.get("risks", [])) >= 1

    # Empty sensor should not crash
    domains = build_governance_domains(extra_ctx={}, sensor_snapshot={})
    assert len(domains) >= 15
    # confidence defaults should fill in
    for d in domains:
        assert d.get("confidence", "unknown") != ""


# ── 18. test_governance_deterministic ──

def test_governance_deterministic():
    # Same inputs should produce same outputs (fields present, same domains)
    extra = {}
    sensor = {}
    d1 = build_governance_domains(extra, sensor)
    d2 = build_governance_domains(extra, sensor)
    assert len(d1) == len(d2)
    domain_names_1 = [(d["domain"], d.get("confidence")) for d in d1]
    domain_names_2 = [(d["domain"], d.get("confidence")) for d in d2]
    assert domain_names_1 == domain_names_2

    # Registry should be deterministic in structure
    r1 = build_runtime_governance_registry(extra, sensor)
    r2 = build_runtime_governance_registry(extra, sensor)
    assert r1["contract_version"] == r2["contract_version"]
    assert len(r1["domains"]) == len(r2["domains"])


# ── 19. test_governance_apis_200 ──

def test_governance_json_safe():
    registry = build_runtime_governance_registry()
    _assert_json_safe(registry)
    # Test that it serializes to JSON fine
    dumped = json.dumps(registry, ensure_ascii=False)
    assert len(dumped) > 0
    reloaded = json.loads(dumped)
    assert reloaded["contract_version"] == GOVERNANCE_CONTRACT_VERSION
    assert isinstance(reloaded["governance_score"], (int, float))
    assert "governance_level" in reloaded


# ── 20. test_governance_summary_functions ──

def test_governance_summary_functions():
    exec_summary = build_governance_executive_summary()
    assert isinstance(exec_summary, str)
    assert "GOVERNANCE EXECUTIVE SUMMARY" in exec_summary
    assert "Governance score:" in exec_summary
    assert "Degraded domains:" in exec_summary
    assert "Operational state:" in exec_summary

    deg_summary = build_governance_degradation_summary()
    assert isinstance(deg_summary, dict)
    assert "degraded_domains" in deg_summary
    assert "operational_state" in deg_summary
    assert "total_degraded" in deg_summary
    assert deg_summary["contract_version"] == GOVERNANCE_CONTRACT_VERSION

    risk_exec = build_governance_risk_executive()
    assert isinstance(risk_exec, str)
    assert "GOVERNANCE RISK REPORT" in risk_exec or "No governance risks detected." in risk_exec


if __name__ == "__main__":
    test_funcs = [
        test_governance_registry_generated,
        test_governance_domains_generated,
        test_governance_authority_map_generated,
        test_governance_confidence_map_generated,
        test_governance_score_generated,
        test_governance_risk_detection,
        test_governance_contract_registry_generated,
        test_prometheus_operational_authority,
        test_grafana_visualization_authority,
        test_inventory_not_runtime_authority,
        test_governance_confidence_propagation,
        test_governance_degradation_propagation,
        test_governance_remediation_integration,
        test_governance_reporting_integration,
        test_governance_cognitive_summary,
        test_governance_contract_validation,
        test_governance_unknown_state_handled,
        test_governance_deterministic,
        test_governance_json_safe,
        test_governance_summary_functions,
    ]
    passed = 0
    failed = 0
    for test_fn in test_funcs:
        try:
            test_fn()
            passed += 1
            print(f"  PASS  {test_fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL  {test_fn.__name__}: {e}")
    total = passed + failed
    print(f"\n{'='*50}")
    print(f"Total: {total} | PASS: {passed} | FAIL: {failed}")
    sys.exit(0 if failed == 0 else 1)
