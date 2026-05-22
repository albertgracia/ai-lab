"""FASE 31B: Runtime Semantic Maturity & Degraded Mode Governance Tests."""

from __future__ import annotations

import json
import time

from runtime.semantics.contracts import (
    SEMANTICS_CONTRACT_VERSION,
    RUNTIME_STATES,
    CONFIDENCE_LEVELS,
    UNCERTAINTY_TYPES,
    DEGRADED_DOMAINS,
    RuntimeMaturityContract,
    DegradationContract,
    ConfidenceContract,
    UncertaintyContract,
    OperationalImpactContract,
    build_maturity_contract,
    build_degradation_contract,
    build_confidence_contract,
    build_uncertainty_contract,
    build_operational_impact_contract,
)
from runtime.semantics.runtime_maturity import (
    RUNTIME_MATURITY_CONTRACT_VERSION,
    RuntimeMaturityEngine,
    calculate_runtime_maturity,
    classify_runtime_state,
    classify_operational_impact,
    calculate_operational_confidence,
    calculate_observability_confidence,
    calculate_uncertainty_level,
    propagate_degradation,
    build_degradation_summary,
    calculate_maturity_score,
)


_BASE_HEALTHY_SNAPSHOT = {
    "domain_confidence": {
        "gpu_nodes": "high", "gateway": "high", "observability": "high",
        "storage": "high", "telemetry": "high",
    },
    "freshness": {"gpu_nodes": "fresh", "gateway": "fresh", "observability": "fresh"},
    "observed_sources": ["gpu_nodes", "gateway", "observability", "storage", "telemetry"],
    "missing_sources": [],
    "stale_sources": [],
    "expected_offline": [],
    "unexpected_down": [],
    "topology": {"mode": "single_gpu", "active_gpus": [{"id": "rx9070"}], "inventory_gpus": []},
    "observability_audit": {
        "prometheus_targets": {"healthy": 15, "total": 15, "degraded": 0, "expected_offline": 2},
        "critical_targets_alignment_pct": 100.0,
    },
}


# ── Constants & Contracts ──

class TestConstants:
    def test_semantics_contract_version(self):
        assert SEMANTICS_CONTRACT_VERSION == "31B"

    def test_runtime_maturity_contract_version(self):
        assert RUNTIME_MATURITY_CONTRACT_VERSION == "31B"

    def test_runtime_states(self):
        for s in ("healthy", "healthy_degraded", "degraded", "critical",
                  "unknown", "partially_observed", "inventory_only", "stale",
                  "expected_offline"):
            assert s in RUNTIME_STATES

    def test_confidence_levels(self):
        for c in ("high", "medium", "low", "unknown"):
            assert c in CONFIDENCE_LEVELS

    def test_uncertainty_types(self):
        for u in ("low_confidence", "mixed_confidence", "unknown_state",
                  "stale_evidence", "partially_observed", "degraded_observability"):
            assert u in UNCERTAINTY_TYPES

    def test_degraded_domains(self):
        for d in ("gpu", "routing", "observability", "storage", "governance",
                  "telemetry", "services", "grounding"):
            assert d in DEGRADED_DOMAINS


class TestRuntimeMaturityContract:
    def test_defaults(self):
        c = RuntimeMaturityContract()
        assert c.runtime_state == "unknown"
        assert c.maturity_score == 0.0
        assert c.degraded_domains == []
        assert c.contract_version == "31B"

    def test_to_dict(self):
        c = RuntimeMaturityContract(
            runtime_state="healthy", maturity_score=85.0, confidence="high",
            degraded_domains=["storage"], unknown_domains=[],
        )
        d = c.to_dict()
        assert d["runtime_state"] == "healthy"
        assert d["maturity_score"] == 85.0
        assert d["degraded_domains"] == ["storage"]

    def test_json_safe(self):
        json.dumps(RuntimeMaturityContract().to_dict())

    def test_build_maturity_contract(self):
        d = build_maturity_contract(runtime_state="degraded")
        assert d["runtime_state"] == "degraded"
        assert d["contract_version"] == "31B"


class TestDegradationContract:
    def test_defaults(self):
        c = DegradationContract()
        assert c.reversible is True
        assert c.domain == ""

    def test_to_dict(self):
        c = DegradationContract(
            domain="gpu", previous_state="healthy", current_state="degraded",
            reason=["stale metrics"], confidence_after="low",
        )
        d = c.to_dict()
        assert d["domain"] == "gpu"
        assert d["confidence_after"] == "low"
        assert d["reversible"] is True

    def test_build_degradation_contract(self):
        d = build_degradation_contract(domain="observability", current_state="stale")
        assert d["domain"] == "observability"
        assert d["current_state"] == "stale"


class TestConfidenceContract:
    def test_defaults(self):
        c = ConfidenceContract()
        assert c.base_confidence == "high"
        assert c.effective_confidence == "high"
        assert c.degradation_applied is False

    def test_degradation(self):
        c = ConfidenceContract(
            domain="gpu", base_confidence="high", effective_confidence="low",
            degradation_applied=True, reason=["source missing"],
        )
        d = c.to_dict()
        assert d["degradation_applied"] is True
        assert d["reason"] == ["source missing"]

    def test_build_confidence_contract(self):
        d = build_confidence_contract(domain="storage", effective_confidence="medium")
        assert d["domain"] == "storage"
        assert d["effective_confidence"] == "medium"


class TestUncertaintyContract:
    def test_defaults(self):
        c = UncertaintyContract()
        assert c.uncertainty_type == ""

    def test_build_uncertainty_contract(self):
        d = build_uncertainty_contract(
            uncertainty_type="stale_evidence", domain="observability",
            severity="warning", description="Prometheus sources stale",
        )
        assert d["uncertainty_type"] == "stale_evidence"
        assert d["severity"] == "warning"


class TestOperationalImpactContract:
    def test_defaults(self):
        c = OperationalImpactContract()
        assert c.impact_level == "none"
        assert c.requires_attention is False

    def test_build_operational_impact_contract(self):
        d = build_operational_impact_contract(impact_level="high", requires_attention=True)
        assert d["impact_level"] == "high"
        assert d["requires_attention"] is True


# ── classify_runtime_state ──

class TestClassifyRuntimeState:
    def test_healthy(self):
        assert classify_runtime_state(_BASE_HEALTHY_SNAPSHOT) == "healthy"

    def test_healthy_degraded_topology(self):
        snap = dict(_BASE_HEALTHY_SNAPSHOT)
        snap["topology"] = {"mode": "degraded_single_gpu"}
        assert classify_runtime_state(snap) == "healthy_degraded"

    def test_critical(self):
        snap = dict(_BASE_HEALTHY_SNAPSHOT)
        snap["domain_confidence"] = {"gpu_nodes": "low", "gateway": "low"}
        snap["missing_sources"] = ["gpu_nodes", "gateway", "prometheus"]
        assert classify_runtime_state(snap) == "critical"

    def test_degraded(self):
        snap = dict(_BASE_HEALTHY_SNAPSHOT)
        snap["domain_confidence"] = {"gpu_nodes": "low", "gateway": "high"}
        snap["unexpected_down"] = [{"job": "some-exporter"}]
        assert classify_runtime_state(snap) == "degraded"

    def test_stale(self):
        snap = dict(_BASE_HEALTHY_SNAPSHOT)
        snap["freshness"] = {"gpu_nodes": {"status": "expired"}}
        assert classify_runtime_state(snap) == "stale"

    def test_partially_observed(self):
        snap = dict(_BASE_HEALTHY_SNAPSHOT)
        snap["observed_sources"] = ["gpu_nodes"]
        snap["missing_sources"] = ["gateway", "observability", "storage", "telemetry"]
        assert classify_runtime_state(snap) == "partially_observed"

    def test_unknown_empty(self):
        assert classify_runtime_state({}) == "unknown"

    def test_expected_offline_not_degraded(self):
        snap = dict(_BASE_HEALTHY_SNAPSHOT)
        snap["expected_offline"] = [{"job": "ai-lab-gpu-rx7900xt"}]
        assert classify_runtime_state(snap) == "healthy"

    def test_healthy_degraded_with_low_conf(self):
        snap = dict(_BASE_HEALTHY_SNAPSHOT)
        snap["domain_confidence"] = {"gpu_nodes": "low", "gateway": "high"}
        snap["topology"] = {"mode": "degraded_single_gpu"}
        expected = classify_runtime_state(snap)
        assert expected in ("healthy_degraded", "degraded")


# ── classify_operational_impact ──

class TestClassifyOperationalImpact:
    def test_critical_state(self):
        assert classify_operational_impact("critical", "low", []) == "critical"

    def test_unknown_state(self):
        assert classify_operational_impact("unknown", "unknown", []) == "high"

    def test_stale_state(self):
        assert classify_operational_impact("stale", "low", []) == "medium"

    def test_degraded_low_conf(self):
        assert classify_operational_impact("degraded", "low", []) == "high"

    def test_degraded_high_conf(self):
        assert classify_operational_impact("degraded", "high", []) == "medium"

    def test_two_degraded_domains(self):
        assert classify_operational_impact("healthy", "high", ["gpu", "storage"]) == "medium"

    def test_one_degraded_domain(self):
        assert classify_operational_impact("healthy", "high", ["gpu"]) == "low"

    def test_healthy_degraded(self):
        assert classify_operational_impact("healthy_degraded", "high", []) == "low"

    def test_healthy_none(self):
        assert classify_operational_impact("healthy", "high", []) == "none"


# ── calculate_operational_confidence ──

class TestOperationalConfidence:
    def test_all_high(self):
        snap = {"domain_confidence": {"gpu": "high", "gw": "high"},
                "freshness": {"gpu": "fresh"}}
        assert calculate_operational_confidence(snap) == "high"

    def test_low_conf(self):
        snap = {"domain_confidence": {"gpu": "low", "gw": "high"},
                "freshness": {"gpu": "fresh"}}
        assert calculate_operational_confidence(snap) == "low"

    def test_stale_freshness_degrades(self):
        snap = {"domain_confidence": {"gpu": "high"},
                "freshness": {"gpu": {"status": "expired"}}}
        assert calculate_operational_confidence(snap) == "low"

    def test_medium_conf(self):
        snap = {"domain_confidence": {"gpu": "medium", "gw": "high"},
                "freshness": {"gpu": "fresh"}}
        assert calculate_operational_confidence(snap) == "medium"


# ── calculate_observability_confidence ──

class TestObservabilityConfidence:
    def test_all_healthy(self):
        snap = {"observability_audit": {
            "prometheus_targets": {"healthy": 15, "total": 15},
            "critical_targets_alignment_pct": 100.0,
        }}
        assert calculate_observability_confidence(snap) == "high"

    def test_no_audit(self):
        assert calculate_observability_confidence({}) == "unknown"

    def test_partial_alignment(self):
        snap = {"observability_audit": {
            "prometheus_targets": {"healthy": 8, "total": 15},
            "critical_targets_alignment_pct": 50.0,
        }}
        assert calculate_observability_confidence(snap) == "medium"

    def test_low_alignment(self):
        snap = {"observability_audit": {
            "prometheus_targets": {"healthy": 2, "total": 15},
            "critical_targets_alignment_pct": 10.0,
        }}
        assert calculate_observability_confidence(snap) == "low"

    def test_empty_targets(self):
        snap = {"observability_audit": {"prometheus_targets": {}}}
        assert calculate_observability_confidence(snap) == "unknown"


# ── calculate_uncertainty_level ──

class TestUncertaintyLevel:
    def test_low_with_expired(self):
        snap = {"domain_confidence": {"gpu": "low"},
                "freshness": {"gpu": {"status": "expired"}},
                "stale_sources": [], "missing_sources": []}
        assert calculate_uncertainty_level(snap) == "degraded_observability"

    def test_low_confidence(self):
        snap = {"domain_confidence": {"gpu": "low"},
                "freshness": {"gpu": "fresh"},
                "stale_sources": [], "missing_sources": []}
        assert calculate_uncertainty_level(snap) == "low_confidence"

    def test_stale_evidence(self):
        snap = {"domain_confidence": {"gpu": "high"},
                "freshness": {"gpu": {"status": "expired"}},
                "stale_sources": [], "missing_sources": []}
        assert calculate_uncertainty_level(snap) == "stale_evidence"

    def test_stale_sources(self):
        snap = {"domain_confidence": {"gpu": "high"},
                "freshness": {"gpu": {"status": "stale"}},
                "stale_sources": ["gpu_nodes"],
                "missing_sources": []}
        assert calculate_uncertainty_level(snap) == "stale_evidence"

    def test_mixed_confidence(self):
        snap = {"domain_confidence": {"gpu": "high", "gw": "medium"},
                "freshness": {"gpu": "fresh"},
                "stale_sources": [], "missing_sources": []}
        assert calculate_uncertainty_level(snap) == "mixed_confidence"

    def test_partially_observed(self):
        snap = {"domain_confidence": {"gpu": "high"},
                "freshness": {"gpu": "fresh"},
                "stale_sources": [], "missing_sources": ["observability"]}
        assert calculate_uncertainty_level(snap) == "partially_observed"


# ── propagate_degradation ──

class TestPropagateDegradation:
    def test_no_degradation(self):
        snap = {"domain_confidence": {"gpu": "high"},
                "freshness": {"gpu": "fresh"},
                "stale_sources": [], "missing_sources": []}
        contracts = propagate_degradation(snap)
        for c in contracts:
            assert c.get("degradation_applied") is False
            assert c.get("effective_confidence") == c.get("base_confidence")

    def test_missing_source_degrades(self):
        snap = {"domain_confidence": {"gpu": "high"},
                "freshness": {"gpu": "fresh"},
                "stale_sources": [], "missing_sources": ["gpu"]}
        contracts = propagate_degradation(snap)
        gpu = [c for c in contracts if c.get("domain") == "gpu"][0]
        assert gpu.get("degradation_applied") is True
        assert "missing source" in " ".join(gpu.get("reason", []))

    def test_stale_source_degrades(self):
        snap = {"domain_confidence": {"observability": "high"},
                "freshness": {"observability": "fresh"},
                "stale_sources": ["observability"], "missing_sources": []}
        contracts = propagate_degradation(snap)
        obs = [c for c in contracts if c.get("domain") == "observability"][0]
        assert obs.get("degradation_applied") is True


# ── build_degradation_summary ──

class TestDegradationSummary:
    def test_healthy(self):
        summary = build_degradation_summary(_BASE_HEALTHY_SNAPSHOT)
        assert summary["runtime_state"] == "healthy"
        assert summary["degraded_domains"] == []
        assert summary["operational_impact"] == "none"

    def test_degraded_domains_listed(self):
        snap = dict(_BASE_HEALTHY_SNAPSHOT)
        snap["domain_confidence"] = {"gpu": "low", "gateway": "high"}
        snap["unexpected_down"] = [{"job": "some-exporter"}]
        summary = build_degradation_summary(snap)
        assert summary["runtime_state"] in ("degraded",)
        assert isinstance(summary["degraded_domains"], list)

    def test_recommended_actions(self):
        snap = dict(_BASE_HEALTHY_SNAPSHOT)
        snap["domain_confidence"] = {"gpu": "low", "gateway": "low"}
        snap["missing_sources"] = ["gpu_nodes", "gateway", "prometheus"]
        summary = build_degradation_summary(snap)
        assert len(summary["recommended_actions"]) > 0

    def test_expected_offline_not_degraded(self):
        snap = dict(_BASE_HEALTHY_SNAPSHOT)
        snap["expected_offline"] = [{"job": "ai-lab-gpu-rx7900xt"}]
        summary = build_degradation_summary(snap)
        assert summary["runtime_state"] == "healthy"


# ── calculate_maturity_score ──

class TestMaturityScore:
    def test_healthy_score(self):
        score = calculate_maturity_score(_BASE_HEALTHY_SNAPSHOT)
        assert score >= 80.0

    def test_critical_low_score(self):
        snap = dict(_BASE_HEALTHY_SNAPSHOT)
        snap["domain_confidence"] = {"gpu": "low"}
        snap["missing_sources"] = ["gpu_nodes", "gateway", "prometheus"]
        snap["stale_sources"] = ["observability"]
        snap["freshness"] = {"gpu": {"status": "expired"}}
        score = calculate_maturity_score(snap)
        assert score < 50.0

    def test_stale_penalty(self):
        healthy_score = calculate_maturity_score(_BASE_HEALTHY_SNAPSHOT)
        snap = dict(_BASE_HEALTHY_SNAPSHOT)
        snap["stale_sources"] = ["gpu_nodes", "observability"]
        stale_score = calculate_maturity_score(snap)
        assert stale_score < healthy_score

    def test_range_clamped(self):
        snap = dict(_BASE_HEALTHY_SNAPSHOT)
        snap["missing_sources"] = ["gpu_nodes", "gateway", "obs", "prom", "storage"]
        snap["domain_confidence"] = {"gpu": "low"}
        score = calculate_maturity_score(snap)
        assert 0.0 <= score <= 100.0


# ── calculate_runtime_maturity (full integration) ──

class TestRuntimeMaturity:
    def test_healthy_snapshot(self):
        result = calculate_runtime_maturity(_BASE_HEALTHY_SNAPSHOT)
        assert result["runtime_state"] == "healthy"
        assert result["maturity_score"] >= 80.0
        assert result["contract_version"] == "31B"

    def test_empty_snapshot(self):
        result = calculate_runtime_maturity({})
        assert result["runtime_state"] == "unknown"
        assert result["maturity_score"] == 0.0

    def test_confidence_high(self):
        result = calculate_runtime_maturity(_BASE_HEALTHY_SNAPSHOT)
        assert result["confidence"] == "high"

    def test_json_safe(self):
        result = calculate_runtime_maturity(_BASE_HEALTHY_SNAPSHOT)
        json.dumps(result)


# ── RuntimeMaturityEngine ──

class TestRuntimeMaturityEngine:
    def test_evaluate(self):
        engine = RuntimeMaturityEngine()
        result = engine.evaluate(_BASE_HEALTHY_SNAPSHOT)
        assert result["runtime_state"] == "healthy"

    def test_needs_attention_healthy(self):
        engine = RuntimeMaturityEngine()
        engine.evaluate(_BASE_HEALTHY_SNAPSHOT)
        assert engine.needs_attention() is False

    def test_needs_attention_critical(self):
        engine = RuntimeMaturityEngine()
        snap = dict(_BASE_HEALTHY_SNAPSHOT)
        snap["domain_confidence"] = {"gpu": "low", "gateway": "low"}
        snap["missing_sources"] = ["gpu_nodes", "gateway", "prometheus"]
        engine.evaluate(snap)
        assert engine.needs_attention() is True

    def test_get_degraded_domains(self):
        engine = RuntimeMaturityEngine()
        engine.evaluate(_BASE_HEALTHY_SNAPSHOT)
        assert engine.get_degraded_domains() == []

    def test_get_recommended_actions(self):
        engine = RuntimeMaturityEngine()
        engine.evaluate(_BASE_HEALTHY_SNAPSHOT)
        actions = engine.get_recommended_actions()
        assert len(actions) > 0


# ── Cognitive Summary Degradation Awareness (FASE 31B injection) ──

class TestCognitiveDegradation:
    def test_cognitive_summary_includes_maturity(self):
        from runtime.context.cognitive_compression import build_runtime_cognitive_summary
        result = build_runtime_cognitive_summary(_BASE_HEALTHY_SNAPSHOT)
        assert "runtime_maturity" in result
        mat = result["runtime_maturity"]
        assert mat["runtime_state"] == "healthy"
        assert mat["confidence"] == "high"

    def test_cognitive_degraded_risk_injected(self):
        from runtime.context.cognitive_compression import build_runtime_cognitive_summary
        snap = dict(_BASE_HEALTHY_SNAPSHOT)
        snap["domain_confidence"] = {"gpu": "low", "gateway": "low"}
        snap["missing_sources"] = ["gpu_nodes", "gateway", "prometheus"]
        result = build_runtime_cognitive_summary(snap)
        risks = result.get("risks", [])
        has_maturity_risk = any("[maturity]" in r for r in risks)
        assert has_maturity_risk is True

    def test_cognitive_low_conf_recommendations(self):
        from runtime.context.cognitive_compression import build_runtime_cognitive_summary
        snap = dict(_BASE_HEALTHY_SNAPSHOT)
        snap["domain_confidence"] = {"gpu": "low", "gateway": "low"}
        snap["missing_sources"] = ["gpu_nodes", "gateway", "prometheus"]
        snap["freshness"] = {"gpu": {"status": "expired"}}
        result = build_runtime_cognitive_summary(snap)
        texts = " ".join(result.get("recommended_actions", []))
        assert "confianza baja" in texts or "verificar" in texts


# ── Operational Summary Degradation Awareness ──

class TestOperationalFormatterDegradation:
    def test_operational_format_includes_state(self):
        from runtime.formatters.runtime_operational_formatter import (
            format_runtime_cluster_state,
        )
        text = format_runtime_cluster_state(_BASE_HEALTHY_SNAPSHOT)
        assert "runtime_state=" in text
        assert "confidence=" in text
        assert "operational_impact=" in text

    def test_operational_format_includes_uncertainty(self):
        from runtime.formatters.runtime_operational_formatter import (
            format_runtime_cluster_state,
        )
        text = format_runtime_cluster_state(_BASE_HEALTHY_SNAPSHOT)
        assert "uncertainty=" in text


# ── Prometheus Metrics ──

class TestPrometheusMetrics31B:
    def test_maturity_metrics_registered(self):
        import runtime.telemetry.prometheus_metrics  # noqa: F401
        from prometheus_client.registry import REGISTRY
        names = {m.name for m in REGISTRY.collect()}
        assert "ailab_runtime_maturity_score" in names
        assert "ailab_runtime_confidence_score" in names
        assert "ailab_runtime_degraded_domains_total" in names
        assert "ailab_runtime_semantic_state" in names

    def test_record_runtime_maturity(self):
        from runtime.telemetry.prometheus_metrics import record_runtime_maturity
        maturity = {
            "maturity_score": 85.0, "confidence": "high",
            "degraded_domains": [], "unknown_domains": [],
            "uncertainty_level": "unknown_state",
            "operational_impact": "none", "runtime_state": "healthy",
        }
        record_runtime_maturity(maturity)


# ── Report Runtime Context ──

class TestReportContextMaturity:
    def test_report_context_includes_maturity(self):
        from runtime.context.report_runtime_context import build_report_runtime_context
        ctx = build_report_runtime_context(target_ip="192.168.1.30")
        assert "runtime_maturity" in ctx
        mat = ctx["runtime_maturity"]
        assert mat.get("runtime_state") is not None

    def test_report_maturity_has_required_fields(self):
        from runtime.context.report_runtime_context import build_report_runtime_context
        ctx = build_report_runtime_context()
        mat = ctx.get("runtime_maturity", {})
        for field in ("runtime_state", "maturity_score", "confidence",
                      "degraded_domains", "uncertainty_level", "operational_impact"):
            assert field in mat, f"Missing: {field}"


# ── Runtime Maturity Endpoint Integration ──

class TestEndpointIntegration:
    def test_maturity_from_engine_matches_contract(self):
        engine = RuntimeMaturityEngine()
        mat = engine.evaluate(_BASE_HEALTHY_SNAPSHOT)
        assert mat["runtime_state"] == "healthy"
        assert mat["maturity_score"] >= 80.0

    def test_maturity_json_serializable(self):
        engine = RuntimeMaturityEngine()
        mat = engine.evaluate(_BASE_HEALTHY_SNAPSHOT)
        json.dumps(mat)


# ── Edge Cases ──

class TestEdgeCases:
    def test_empty_domain_confidence(self):
        snap = dict(_BASE_HEALTHY_SNAPSHOT)
        snap["domain_confidence"] = {}
        result = calculate_runtime_maturity(snap)
        assert result["runtime_state"] != ""

    def test_all_sources_missing(self):
        snap = {
            "domain_confidence": {},
            "freshness": {},
            "observed_sources": [],
            "missing_sources": ["gpu", "gateway", "prometheus"],
            "stale_sources": [],
            "expected_offline": [],
            "unexpected_down": [],
            "topology": {"mode": "unknown"},
        }
        result = calculate_runtime_maturity(snap)
        assert result["runtime_state"] in ("unknown", "critical", "degraded")

    def test_freshness_dict_vs_string(self):
        snap = dict(_BASE_HEALTHY_SNAPSHOT)
        snap["freshness"] = {"gpu": "fresh", "gateway": "stale"}
        conf = calculate_operational_confidence(snap)
        assert conf in ("low", "medium")
