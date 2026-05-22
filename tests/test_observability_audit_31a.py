"""FASE OBS-31A: Observability Source-of-Truth Audit Tests."""

import json
import time
from unittest.mock import patch

from runtime.observability import (
    OBSERVABILITY_CONTRACT_VERSION,
    build_observability_source_contract,
    build_dashboard_contract,
    build_metric_contract,
    build_datasource_contract,
)
from runtime.observability.prometheus_audit import (
    PrometheusTargetStatus,
    audit_prometheus_targets,
    classify_scrape_target,
    build_prometheus_audit_summary,
)
from runtime.observability.metric_inventory import (
    MetricCriticality,
    build_metric_inventory,
    build_observability_health_score,
)
from runtime.observability.dashboard_validator import (
    DashboardHealth,
    DashboardValidationResult,
    DashboardValidator,
)
from runtime.observability.drift_detector import (
    DriftDetectionResult,
    DriftDetector,
)
from runtime.observability.loki_audit import (
    LokiStreamStatus,
    audit_loki,
    build_loki_audit_summary,
)


class TestPrometheusTargetsClassified:
    def test_prometheus_targets_classified(self):
        up_map = {
            "ai-lab-gateway": True,
            "ai-lab-router": True,
            "ai-lab-live-api": True,
            "ai-lab-cadvisor": True,
            "ai-lab-node": True,
            "ai-lab-gpu-rx9070": True,
            "ai-lab-gpu-metrics": True,
        }
        results = audit_prometheus_targets(up_map=up_map)
        assert len(results) >= 13  # 16 known
        healthy = sum(1 for r in results if r["status"] == "healthy")
        expected_offline = sum(1 for r in results if r["status"] == "expected_offline")
        assert healthy >= 7  # gateway, router, live-api, cadvisor, node, gpu-rx9070, gpu-metrics
        assert expected_offline == 1  # RX7900XT only

    def test_classify_scrape_target_healthy(self):
        target = {"job": "test", "endpoint": "host:9100", "expected_offline": False, "critical": True}
        entry = classify_scrape_target(target, is_up=True, scrape_duration_ms=200)
        assert entry.status == "healthy"

    def test_classify_scrape_target_expected_offline(self):
        target = {"job": "test", "endpoint": "host:9100", "expected_offline": True, "critical": False}
        entry = classify_scrape_target(target, is_up=False)
        assert entry.status == "expected_offline"

    def test_classify_scrape_target_degraded(self):
        target = {"job": "test", "endpoint": "host:9100", "expected_offline": False, "critical": True}
        entry = classify_scrape_target(target, is_up=False)
        assert entry.status == "degraded"


class TestDashboardValidation:
    def test_dashboard_validation_detects_broken_panel(self):
        validator = DashboardValidator()
        result = validator.validate_dashboard({
            "uid": "test-broken",
            "title": "Test Broken",
            "panels": [
                {
                    "title": "GPU Usage",
                    "targets": [{"expr": "ailab_gpu_active_requests{test_unclosed"}],
                },
            ],
        })
        assert result.health in ("broken", "stale")

    def test_dashboard_validation_detects_no_data(self):
        validator = DashboardValidator()
        result = validator.validate_dashboard({
            "uid": "test-nodata",
            "title": "Test No Data",
            "panels": [
                {"title": "Panel 1", "datasource": {"uid": "no-ds"}},
                {"title": "Panel 2", "datasource": {"uid": ""}},
            ],
        })
        assert result.panels_no_data >= 1

    def test_dashboard_validation_all_known(self):
        validator = DashboardValidator()
        results = validator.validate_all_known()
        assert len(results) >= 11  # 5 AI-LAB + 6 legacy
        ai_lab = [r for r in results if r.get("runtime_domain") != "legacy"]
        for d in ai_lab:
            assert d.get("health") == "healthy"

    def test_dashboard_validation_detects_forbidden_gpu(self):
        validator = DashboardValidator()
        panels = json.dumps({"panels": [{"targets": [{"expr": "NVIDIA A100 usage"}]}]})
        matches = validator.detect_forbidden_gpu_references(panels)
        assert len(matches) > 0


class TestDatasourceValidation:
    def test_datasource_validation_valid(self):
        validator = DashboardValidator()
        valid, _ = validator.validate_datasource(uid="PBFA97CFB590B2093")
        assert valid

    def test_datasource_validation_invalid(self):
        validator = DashboardValidator()
        valid, msg = validator.validate_datasource(uid="some-unknown-uid")
        assert not valid
        assert "unknown_datasource_uid" in msg

    def test_datasource_contract_build(self):
        contract = build_datasource_contract(
            name="Prometheus", uid="PBFA97CFB590B2093",
            type="prometheus", url="http://192.168.1.40:9090",
        )
        assert contract["name"] == "Prometheus"
        assert contract["accessible"] is True


class TestPromQLValidation:
    def test_promql_valid(self):
        validator = DashboardValidator()
        valid, _ = validator.validate_promql("rate(ailab_requests_total[5m])")
        assert valid

    def test_promql_invalid_unmatched_brace(self):
        validator = DashboardValidator()
        valid, msg = validator.validate_promql("rate(ailab_requests_total{test[5m])")
        assert not valid
        assert "unmatched_brace" in msg

    def test_promql_empty(self):
        validator = DashboardValidator()
        valid, msg = validator.validate_promql("")
        assert not valid
        assert "empty_query" in msg


class TestLokiQueryValidation:
    def test_loki_query_valid(self):
        validator = DashboardValidator()
        valid, _ = validator.validate_loki_query('{compose_project="ailab"} |= "error"')
        assert valid

    def test_loki_query_invalid_missing_braces(self):
        validator = DashboardValidator()
        valid, msg = validator.validate_loki_query('compose_project="ailab"')
        assert not valid
        assert "missing_stream_selector" in msg

    def test_loki_audit(self):
        results = audit_loki()
        assert len(results) >= 4
        docker = next((r for r in results if r["name"] == "docker_logs"), None)
        assert docker is not None
        assert docker["status"] in ("healthy", "broken")


class TestRuntimeDriftDetection:
    def test_runtime_drift_detected(self):
        detector = DriftDetector()
        result = detector.detect_all(
            dashboard_gpus=["RX9070", "A100"],
            runtime_gpus=["RX9070", "RX7900XT"],
        )
        assert len(result.gpu_drift) > 0

    def test_gpu_inventory_alignment(self):
        detector = DriftDetector()
        result = detector.detect_all(
            dashboard_gpus=["RX9070", "RX7900XT"],
            runtime_gpus=["RX9070", "RX7900XT"],
        )
        assert len(result.gpu_drift) == 0

    def test_topology_drift(self):
        detector = DriftDetector(runtime_context={"runtime_topology": {"mode": "degraded_single_gpu"}})
        result = detector.detect_all(
            dashboard_topology={"mode": "single_gpu"},
        )
        assert len(result.topology_drift) > 0

    def test_drift_summary_has_contract(self):
        result = DriftDetector().detect_all()
        summary = result.to_dict()
        assert summary["contract_version"] == "OBS-31A.2"
        assert "total_drifts" in summary


class TestMetricInventory:
    def test_metric_inventory_contains_runtime_metrics(self):
        inventory = build_metric_inventory()
        assert len(inventory) >= 30
        names = [m["metric_name"] for m in inventory]
        assert "ailab_first_token_latency_ms" in names
        assert "ailab_route_family_total" in names
        assert "ailab_quality_score" in names

    def test_metric_inventory_critical_present(self):
        inventory = build_metric_inventory()
        critical = [m for m in inventory if m["criticality"] == "critical"]
        assert len(critical) >= 10

    def test_metric_inventory_fields(self):
        inventory = build_metric_inventory()
        for m in inventory:
            assert "metric_name" in m
            assert "domain" in m
            assert "criticality" in m
            assert "source" in m
            assert "freshness_status" in m


class TestObservabilityScore:
    def test_observability_score_generated(self):
        score = build_observability_health_score(
            targets_healthy=8, targets_total=10,
            dashboards_healthy=4, dashboards_total=5,
            no_data_panels=1, stale_metrics=2, query_failures=0,
            runtime_alignment_score=0.9,
        )
        assert "score" in score
        assert "level" in score
        assert 0 <= score["score"] <= 100

    def test_observability_score_healthy_at_high_values(self):
        score = build_observability_health_score(
            targets_healthy=10, targets_total=10,
            dashboards_healthy=5, dashboards_total=5,
            runtime_alignment_score=1.0,
        )
        assert score["level"] == "healthy"

    def test_observability_score_critical_at_low_values(self):
        score = build_observability_health_score(
            targets_healthy=0, targets_total=10,
            dashboards_healthy=0, dashboards_total=5,
            no_data_panels=10, stale_metrics=20, query_failures=5,
            runtime_alignment_score=0.1,
        )
        assert score["level"] in ("unhealthy", "critical")


class TestContracts:
    def test_observability_contract_json_safe(self):
        contract = build_observability_source_contract(
            prometheus_up=True, grafana_up=True, targets_total=10,
        )
        dumped = json.dumps(contract, ensure_ascii=False)
        assert len(dumped) > 10
        assert contract["contract_version"] == "OBS-31A"
        assert contract["targets"]["total"] == 10

    def test_dashboard_contract_metadata(self):
        contract = build_dashboard_contract(
            uid="ai-lab-gpus",
            title="AI-LAB GPUs",
            runtime_domain="gpu",
            criticality="critical",
            semantic_owner="gpu",
            health="healthy",
        )
        assert contract["uid"] == "ai-lab-gpus"
        assert contract["criticality"] == "critical"
        assert contract["semantic_owner"] == "gpu"

    def test_metric_contract(self):
        contract = build_metric_contract(
            metric_name="ailab_first_token_latency_ms",
            domain="latency",
            criticality="critical",
            used_by_runtime=True,
        )
        assert contract["metric_name"] == "ailab_first_token_latency_ms"
        assert contract["query_valid"] is True

    def test_dashboard_owner_metadata(self):
        contract = build_dashboard_contract(
            uid="ai-lab-overview",
            title="AI-LAB Overview",
            runtime_domain="overview",
            criticality="critical",
            semantic_owner="runtime",
            deprecated=False,
        )
        assert contract["semantic_owner"] == "runtime"
        assert contract["deprecated"] is False


class TestExpectedOffline:
    def test_expected_offline_not_broken(self):
        target = {"job": "test-offline", "endpoint": "host:9182", "expected_offline": True, "critical": False}
        entry = classify_scrape_target(target, is_up=False)
        assert entry.status == "expected_offline"
        assert not entry.critical

    def test_stale_metric_classification(self):
        target = {"job": "test-stale", "endpoint": "host:9100", "expected_offline": False, "critical": True}
        entry = classify_scrape_target(target, is_up=None, error="connection_timeout")
        assert entry.status == "stale"


class TestRuntimeObservabilityEndpoint:
    def test_observability_audit_summary(self):
        summary = build_prometheus_audit_summary()
        assert summary["contract_version"] == "OBS-31A"
        assert "classification" in summary
        assert "critical_targets" in summary
        assert "targets" in summary

    def test_loki_audit_summary(self):
        summary = build_loki_audit_summary()
        assert summary["contract_version"] == "OBS-31A"
        assert "datasource" in summary
        assert "classification" in summary

    def test_dashboard_audit_summary(self):
        validator = DashboardValidator()
        summary = validator.build_dashboard_audit_summary()
        assert summary["contract_version"] == "OBS-31A.2"
        assert "health_classification" in summary
        assert "dashboards" in summary


class TestGeneral:
    def test_contract_version_constant(self):
        assert OBSERVABILITY_CONTRACT_VERSION == "OBS-31A"
