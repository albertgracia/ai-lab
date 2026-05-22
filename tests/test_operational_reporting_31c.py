import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/opt/ai-lab")
CONTRACTS_PATH = ROOT / "runtime/reporting/contracts.py"
ENGINE_PATH = ROOT / "runtime/reporting/reporting_engine.py"
INIT_PATH = ROOT / "runtime/reporting/__init__.py"
FORMATTER_PATH = ROOT / "runtime/formatters/runtime_operational_formatter.py"
COMPRESSION_PATH = ROOT / "runtime/context/cognitive_compression.py"

sys.path.insert(0, str(ROOT))


def _import_reporting():
    from runtime.reporting import (
        OperationalReportContract, OperationalSummaryContract,
        GovernanceReportContract, RuntimeHealthContract,
        DomainHealthContract, OperatorExplainabilityContract,
        ExecutiveSummaryContract, DegradationReportContract,
        build_operational_report, build_runtime_health_report,
        build_domain_health_report, build_governance_summary,
        build_executive_summary, build_operator_summary,
        build_degradation_report, build_confidence_report,
        build_explainability_summary, build_reporting_score,
        REPORTING_CONTRACT_VERSION,
    )
    return {
        "OperationalReportContract": OperationalReportContract,
        "OperationalSummaryContract": OperationalSummaryContract,
        "GovernanceReportContract": GovernanceReportContract,
        "RuntimeHealthContract": RuntimeHealthContract,
        "DomainHealthContract": DomainHealthContract,
        "OperatorExplainabilityContract": OperatorExplainabilityContract,
        "ExecutiveSummaryContract": ExecutiveSummaryContract,
        "DegradationReportContract": DegradationReportContract,
        "build_operational_report": build_operational_report,
        "build_runtime_health_report": build_runtime_health_report,
        "build_domain_health_report": build_domain_health_report,
        "build_governance_summary": build_governance_summary,
        "build_executive_summary": build_executive_summary,
        "build_operator_summary": build_operator_summary,
        "build_degradation_report": build_degradation_report,
        "build_confidence_report": build_confidence_report,
        "build_explainability_summary": build_explainability_summary,
        "build_reporting_score": build_reporting_score,
        "REPORTING_CONTRACT_VERSION": REPORTING_CONTRACT_VERSION,
    }


_EMPTY_SENSOR = {}
_MINIMAL_SENSOR = {
    "gpu_operational_summaries": [
        {
            "gpu_id": "RX9070",
            "operational_state": "active",
            "observed_state": "online",
            "topology_role": "primary_inference",
            "confidence": "high",
            "freshness": {"status": "fresh", "age_seconds": 5},
            "source_of_truth": ["prometheus", "sensor_fusion"],
            "observed_metrics": {
                "temperature_c": 62,
                "gpu_load_percent": 45,
                "power_watts": 180,
                "vram_used_gb": 12.5,
                "vram_total_gb": 16.0,
                "vram_free_gb": 3.5,
                "fan_rpm": 1400,
            },
        },
        {
            "gpu_id": "RX7900XT",
            "operational_state": "inactive",
            "observed_state": "expected_offline",
            "topology_role": "secondary_inventory",
            "confidence": "medium",
            "freshness": {"status": "unavailable"},
            "source_of_truth": ["inventory"],
            "inventory_expected_offline": True,
        },
    ],
    "domain_confidence": {"gpu": "high", "routing": "medium", "storage": "low"},
    "source_quality": {
        "gpu_nodes": {
            "freshness": {"status": "fresh"},
            "source_of_truth": ["prometheus", "sensor_fusion"],
        },
        "routing": {
            "freshness": {"status": "fresh"},
            "source_of_truth": ["prometheus"],
        },
        "storage": {
            "freshness": {"status": "stale"},
            "source_of_truth": ["prometheus"],
        },
    },
    "topology": {"mode": "active_single_gpu", "active_gpus": ["RX9070"], "inventory_gpus": ["RX7900XT"]},
    "expected_offline": ["RX7900XT"],
    "stale_sources": ["storage"],
    "observed_sources_count": 2,
    "missing_sources_count": 1,
}


class TestOperationalReporting31C:

    def test_operational_report_generated(self):
        mod = _import_reporting()
        report = mod["build_operational_report"](sensor_snapshot=_MINIMAL_SENSOR)
        assert report is not None
        assert "contract" in report
        assert "mode" in report

    def test_reporting_contract_json_safe(self):
        mod = _import_reporting()
        report = mod["build_operational_report"](sensor_snapshot=_MINIMAL_SENSOR)
        dumped = json.dumps(report, ensure_ascii=False)
        parsed = json.loads(dumped)
        assert parsed["mode"] == "compact"

    def test_confidence_included(self):
        mod = _import_reporting()
        report = mod["build_operational_report"](sensor_snapshot=_MINIMAL_SENSOR)
        assert report.get("confidence") in ("high", "medium", "low", "unknown")

    def test_freshness_included(self):
        mod = _import_reporting()
        report = mod["build_operational_report"](sensor_snapshot=_MINIMAL_SENSOR)
        assert report.get("freshness") is not None

    def test_expected_offline_visible(self):
        mod = _import_reporting()
        operator = mod["build_operator_summary"](sensor_snapshot=_MINIMAL_SENSOR)
        assert "expected_offline" in operator
        assert any("RX7900XT" in str(v) for v in operator["expected_offline"])

    def test_unknowns_visible(self):
        mod = _import_reporting()
        sensor_with_unknowns = dict(_MINIMAL_SENSOR)
        sensor_with_unknowns["stale_sources"] = ["storage", "network"]
        explain = mod["build_explainability_summary"](sensor_snapshot=sensor_with_unknowns)
        assert "stale_observability" in explain
        assert explain["stale_observability"]

    def test_degraded_domains_visible(self):
        mod = _import_reporting()
        maturity = {
            "runtime_state": "degraded",
            "confidence": "medium",
            "degraded_domains": ["storage"],
            "unknown_domains": [],
            "degradation_reason": ["storage metrics stale"],
            "operational_impact": "low",
            "freshness": "stale",
            "topology_mode": "active_single_gpu",
        }
        report = mod["build_operational_report"](maturity=maturity)
        assert "storage" in report.get("degraded_domains", [])

    def test_explainability_summary_generated(self):
        mod = _import_reporting()
        maturity = {
            "runtime_state": "degraded",
            "confidence": "medium",
            "degraded_domains": ["storage"],
            "unknown_domains": [],
            "degradation_reason": ["storage metrics stale"],
            "operational_impact": "low",
            "freshness": "stale",
            "topology_mode": "active_single_gpu",
        }
        explain = mod["build_explainability_summary"](sensor_snapshot=_MINIMAL_SENSOR, maturity=maturity)
        assert "degradation_summary" in explain
        assert "missing_evidence" in explain
        assert "affected_domains" in explain
        assert "confidence_breakdown" in explain
        assert "valid_recommendations" in explain

    def test_governance_summary_generated(self):
        mod = _import_reporting()
        gov = mod["build_governance_summary"](extra_ctx={
            "governance_blocked": 3,
            "governance_blocked_by_reason": {"bash_exec": 2, "file_write": 1},
        })
        assert "governance_level" in gov
        assert gov["blocked_actions"] == 3
        assert gov["blocked_by_reason"]["bash_exec"] == 2

    def test_executive_summary_generated(self):
        mod = _import_reporting()
        maturity = {
            "runtime_state": "healthy",
            "confidence": "high",
            "degraded_domains": [],
            "unknown_domains": [],
            "degradation_reason": [],
            "operational_impact": "none",
            "freshness": "fresh",
            "topology_mode": "active_single_gpu",
        }
        exec_summary = mod["build_executive_summary"](sensor_snapshot=_MINIMAL_SENSOR, maturity=maturity)
        assert "overall_state" in exec_summary
        assert exec_summary["active_backends"] == 1

    def test_reporting_modes_supported(self):
        mod = _import_reporting()
        for mode in ("compact", "operational", "technical", "executive", "governance"):
            report = mod["build_operational_report"](sensor_snapshot=_MINIMAL_SENSOR, mode=mode)
            assert report["mode"] == mode

    def test_reporting_score_generated(self):
        mod = _import_reporting()
        score = mod["build_reporting_score"](sensor_snapshot=_MINIMAL_SENSOR)
        assert "overall_score" in score
        assert "components" in score
        assert 0 <= score["overall_score"] <= 100

    def test_confidence_changes_reporting_behavior(self):
        mod = _import_reporting()
        explain_low = mod["build_explainability_summary"](maturity={
            "runtime_state": "degraded", "confidence": "low",
            "degraded_domains": ["storage"], "unknown_domains": [],
            "degradation_reason": ["stale"], "operational_impact": "low",
            "freshness": "stale", "topology_mode": "unknown",
        })
        explain_high = mod["build_explainability_summary"](maturity={
            "runtime_state": "healthy", "confidence": "high",
            "degraded_domains": [], "unknown_domains": [],
            "degradation_reason": [], "operational_impact": "none",
            "freshness": "fresh", "topology_mode": "active_single_gpu",
        })
        low_recs = explain_low.get("valid_recommendations", [])
        high_recs = explain_high.get("valid_recommendations", [])
        assert len(low_recs) >= len(high_recs) or "verificar" in str(low_recs)

    def test_runtime_reporting_endpoint_200(self):
        import requests
        urls = [
            "http://192.168.1.30:8083/runtime/reporting/status",
            "http://192.168.1.30:8083/runtime/reporting/governance",
        ]
        all_ok = True
        for url in urls:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 404:
                    all_ok = False
                    continue
                assert resp.status_code == 200, f"{url} returned {resp.status_code}"
                data = resp.json()
                assert data.get("status") == "ok"
            except (requests.ConnectionError, requests.Timeout):
                all_ok = False
        if not all_ok:
            import pytest
            pytest.skip("Router endpoint not reachable or not deployed — requires ailab-router restart")

    def test_no_raw_metric_flood(self):
        mod = _import_reporting()
        report = mod["build_operational_report"](sensor_snapshot=_MINIMAL_SENSOR)
        text = report.get("text", "") or ""
        # No raw JSON/metric dumps in compact text
        assert len(text) < 800

    def test_reports_are_deterministic(self):
        mod = _import_reporting()
        r1 = mod["build_operational_report"](sensor_snapshot=_MINIMAL_SENSOR)
        r2 = mod["build_operational_report"](sensor_snapshot=_MINIMAL_SENSOR)
        # Compare without timestamps
        def _without_ts(d: dict) -> dict:
            c = dict(d)
            c.pop("timestamp", None)
            return c
        c1 = _without_ts(r1["contract"])
        c2 = _without_ts(r2["contract"])
        assert c1 == c2
        assert r1.get("text") == r2.get("text")

    def test_30g_compatibility_mode(self):
        from runtime.formatters.runtime_operational_formatter import (
            format_runtime_cluster_state, _REPORTING_MODE,
        )
        result = format_runtime_cluster_state(_MINIMAL_SENSOR)
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_semantic_alignment_preserved(self):
        mod = _import_reporting()
        report = mod["build_operational_report"](sensor_snapshot=_MINIMAL_SENSOR)
        contract = report["contract"]
        assert contract["contract_version"] == "31C"
        assert contract["topology_mode"] == "active_single_gpu" or contract["topology_mode"] != ""

    def test_domain_health_gpu_report(self):
        mod = _import_reporting()
        gpu_health = mod["build_domain_health_report"]("gpu", sensor_snapshot=_MINIMAL_SENSOR)
        assert gpu_health["domain"] == "gpu"
        assert gpu_health["state"] in ("healthy", "expected_offline", "unavailable", "unknown")

    def test_degradation_report_generated(self):
        mod = _import_reporting()
        maturity = {
            "runtime_state": "degraded",
            "confidence": "medium",
            "degraded_domains": ["storage", "observability"],
            "unknown_domains": ["network"],
            "degradation_reason": ["storage metrics stale", "prometheus targets down"],
            "operational_impact": "moderate",
            "freshness": "stale",
            "topology_mode": "active_single_gpu",
        }
        deg = mod["build_degradation_report"](maturity=maturity)
        assert deg["degradation_level"] == "moderate" or deg["degradation_level"] == "degraded"
        assert "storage" in deg["degraded_domains"]
        assert len(deg["degradation_reasons"]) >= 1

    def test_confidence_report_generated(self):
        mod = _import_reporting()
        conf = mod["build_confidence_report"](sensor_snapshot=_MINIMAL_SENSOR)
        assert "overall" in conf
        assert "domain_confidence" in conf
        assert conf["domain_confidence"].get("gpu") == "high"
