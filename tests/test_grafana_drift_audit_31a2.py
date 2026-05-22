"""FASE OBS-31A.2: Grafana Drift Audit Tests.

Validates Grafana inventory, dashboard validation, drift detection,
runtime alignment, and contract versioning for AI-LAB.
"""

from __future__ import annotations

import json as _json

from runtime.observability.grafana_inventory import (
    DashboardHealth,
    GRAFANA_INVENTORY_CONTRACT_VERSION,
    _AI_LAB_DASHBOARDS,
    _ALL_DASHBOARDS,
    _KNOWN_DATASOURCES,
    _LEGACY_DASHBOARDS,
    build_dashboard_inventory,
    build_inventory_summary,
    classify_dashboard_health,
    get_dashboard_by_uid,
    get_dashboards_by_domain,
    get_dashboards_by_owner,
)
from runtime.observability.dashboard_validator import (
    DASHBOARD_VALIDATOR_CONTRACT_VERSION,
    DashboardHealth as VDashboardHealth,
    DashboardValidationResult,
    DashboardValidator,
    QueryValidity,
)
from runtime.observability.drift_detector import (
    DRIFT_DETECTOR_CONTRACT_VERSION,
    DriftDetectionResult,
    DriftDetector,
    build_drift_summary,
    build_runtime_alignment_summary,
)
from runtime.observability.contracts import (
    GrafanaAlignmentContract,
    build_grafana_alignment_contract,
)


# ── Grafana Inventory ──

class TestGrafanaInventoryConstants:
    def test_contract_version(self):
        assert GRAFANA_INVENTORY_CONTRACT_VERSION == "OBS-31A.2"

    def test_ai_lab_dashboards_count(self):
        assert len(_AI_LAB_DASHBOARDS) == 5

    def test_legacy_dashboards_count(self):
        assert len(_LEGACY_DASHBOARDS) == 6

    def test_all_dashboards_count(self):
        assert len(_ALL_DASHBOARDS) == 11

    def test_known_datasources_count(self):
        assert len(_KNOWN_DATASOURCES) == 2

    def test_known_datasources_include_prometheus(self):
        uids = [ds["uid"] for ds in _KNOWN_DATASOURCES]
        assert "PBFA97CFB590B2093" in uids

    def test_known_datasources_include_loki(self):
        uids = [ds["uid"] for ds in _KNOWN_DATASOURCES]
        assert "fflfh9qp8mxogc" in uids

    def test_ai_lab_dashboard_has_required_fields(self):
        for d in _AI_LAB_DASHBOARDS:
            assert "uid" in d
            assert "title" in d
            assert "runtime_domain" in d
            assert "criticality" in d
            assert "datasource_uid" in d


class TestClassifyDashboardHealth:
    def test_healthy(self):
        d = {"deprecated": False, "experimental": False,
             "inventory_aligned": True, "runtime_aligned": True}
        assert classify_dashboard_health(d) == DashboardHealth.HEALTHY.value

    def test_deprecated(self):
        d = {"deprecated": True}
        assert classify_dashboard_health(d) == DashboardHealth.DEPRECATED.value

    def test_experimental(self):
        d = {"deprecated": False, "experimental": True}
        assert classify_dashboard_health(d) == DashboardHealth.EXPERIMENTAL.value

    def test_inventory_drift(self):
        d = {"deprecated": False, "experimental": False,
             "inventory_aligned": False}
        assert classify_dashboard_health(d) == DashboardHealth.INVENTORY_DRIFT.value

    def test_runtime_mismatch(self):
        d = {"deprecated": False, "experimental": False,
             "inventory_aligned": True, "runtime_aligned": False}
        assert classify_dashboard_health(d) == DashboardHealth.RUNTIME_MISMATCH.value


class TestBuildDashboardInventory:
    def test_returns_list(self):
        inv = build_dashboard_inventory()
        assert isinstance(inv, list)
        assert len(inv) == 11

    def test_each_entry_has_health(self):
        inv = build_dashboard_inventory()
        for entry in inv:
            assert "health" in entry
            assert entry["health"] in (
                "healthy", "deprecated", "experimental",
                "inventory_drift", "runtime_mismatch",
            )

    def test_ai_lab_dashboards_are_healthy(self):
        inv = build_dashboard_inventory()
        ai_lab = [d for d in inv if d["uid"].startswith("ai-lab")]
        for d in ai_lab:
            assert d["health"] == "healthy", f"{d['uid']} is {d['health']}"

    def test_legacy_dashboards_are_deprecated(self):
        inv = build_dashboard_inventory()
        legacy = [d for d in inv if d.get("deprecated")]
        assert len(legacy) == 6
        for d in legacy:
            assert d["health"] == "deprecated"

    def test_inventory_summary(self):
        summary = build_inventory_summary()
        assert summary["contract_version"] == "OBS-31A.2"
        assert summary["total_dashboards"] == 11
        assert summary["ai_lab_dashboards"] == 5
        assert summary["legacy_dashboards"] == 6
        assert "health_summary" in summary


class TestGetDashboardFunctions:
    def test_get_by_uid_found(self):
        d = get_dashboard_by_uid("ai-lab-overview")
        assert d is not None
        assert d["title"] == "AI-LAB Overview"

    def test_get_by_uid_not_found(self):
        d = get_dashboard_by_uid("nonexistent")
        assert d is None

    def test_get_by_uid_legacy(self):
        d = get_dashboard_by_uid("alpt7gt")
        assert d is not None
        assert d.get("deprecated") is True

    def test_get_by_domain(self):
        domains = get_dashboards_by_domain("legacy")
        assert len(domains) == 6

    def test_get_by_owner(self):
        owners = get_dashboards_by_owner("runtime")
        assert len(owners) >= 2


# ── Dashboard Validator ──

class TestDashboardValidatorDatasource:
    def test_valid_prometheus_uid(self):
        v = DashboardValidator()
        ok, msg = v.validate_datasource(uid="PBFA97CFB590B2093")
        assert ok is True
        assert msg == ""

    def test_valid_loki_uid(self):
        v = DashboardValidator()
        ok, msg = v.validate_datasource(uid="fflfh9qp8mxogc")
        assert ok is True

    def test_unknown_uid(self):
        v = DashboardValidator()
        ok, msg = v.validate_datasource(uid="unknown-ds-uid")
        assert ok is False
        assert msg == "unknown_datasource_uid"

    def test_forbidden_pattern(self):
        v = DashboardValidator()
        ok, msg = v.validate_datasource(uid="testdatasource")
        assert ok is False
        assert "forbidden" in msg


class TestDashboardValidatorPromQL:
    def test_valid_promql(self):
        v = DashboardValidator()
        ok, msg = v.validate_promql("ailab_requests_total")
        assert ok is True

    def test_empty_promql(self):
        v = DashboardValidator()
        ok, msg = v.validate_promql("")
        assert ok is False
        assert msg == "empty_query"

    def test_unmatched_brace(self):
        v = DashboardValidator()
        ok, msg = v.validate_promql('up{job="test"')
        assert ok is False
        assert msg == "unmatched_brace"

    def test_invalid_metric(self):
        v = DashboardValidator()
        ok, msg = v.validate_promql("test_metric_total")
        assert ok is False
        assert "invalid_metric" in msg

    def test_promql_expression_valid(self):
        v = DashboardValidator()
        validity, warnings = v.validate_promql_expression("ailab_requests_total")
        assert validity == QueryValidity.VALID.value
        assert warnings == []

    def test_promql_expression_stale(self):
        v = DashboardValidator()
        validity, warnings = v.validate_promql_expression("memory_contamination_risk")
        assert validity == QueryValidity.STALE.value
        assert any("stale_metric" in w for w in warnings)

    def test_promql_expression_stale_lowercase(self):
        v = DashboardValidator()
        validity, warnings = v.validate_promql_expression("hallucination_risk")
        assert validity == QueryValidity.STALE.value
        assert any("stale_metric" in w for w in warnings)

    def test_promql_expression_invalid_metric(self):
        v = DashboardValidator()
        validity, warnings = v.validate_promql_expression("fake_metric_total")
        assert validity == QueryValidity.INVALID.value

    def test_promql_expression_empty(self):
        v = DashboardValidator()
        validity, warnings = v.validate_promql_expression("")
        assert validity == QueryValidity.EMPTY.value


class TestDashboardValidatorLoki:
    def test_valid_loki_query(self):
        v = DashboardValidator()
        ok, msg = v.validate_loki_query('{job="docker_logs"} |= "error"')
        assert ok is True

    def test_empty_loki_query(self):
        v = DashboardValidator()
        ok, msg = v.validate_loki_query("")
        assert ok is False
        assert msg == "empty_query"

    def test_missing_stream_selector(self):
        v = DashboardValidator()
        ok, msg = v.validate_loki_query('job="test"')
        assert ok is False
        assert msg == "missing_stream_selector"


class TestDashboardValidatorGPU:
    def test_detect_forbidden_gpu_a100(self):
        v = DashboardValidator()
        found = v.detect_forbidden_gpu_references('{"gpu": "A100"}')
        assert len(found) >= 1
        assert "A100" in found or "a100" in found

    def test_detect_forbidden_gpu_h100(self):
        v = DashboardValidator()
        found = v.detect_forbidden_gpu_references('{"gpu": "H100"}')
        assert len(found) >= 1

    def test_expected_gpu_not_forbidden(self):
        v = DashboardValidator()
        found = v.detect_forbidden_gpu_references('{"gpu": "RX9070"}')
        assert len(found) == 0

    def test_no_gpu_match(self):
        v = DashboardValidator()
        found = v.detect_forbidden_gpu_references('{"gpu": "RX9070"}')
        assert len(found) == 0

    def test_detect_legacy_gpu_inventory_rtx3090(self):
        v = DashboardValidator()
        found = v.detect_legacy_gpu_inventory('{"gpu": "RTX 3090"}')
        assert len(found) >= 1

    def test_detect_legacy_gpu_inventory_gtx1080(self):
        v = DashboardValidator()
        found = v.detect_legacy_gpu_inventory('{"gpu": "GTX 1080"}')
        assert len(found) >= 1

    def test_no_legacy_gpu(self):
        v = DashboardValidator()
        found = v.detect_legacy_gpu_inventory('{"gpu": "RX9070"}')
        assert len(found) == 0


class TestDashboardValidatorNoData:
    def test_no_data_empty_ds(self):
        v = DashboardValidator()
        assert v.detect_no_data_panels({"datasource": {"uid": ""}}) is True

    def test_no_data_no_ds(self):
        v = DashboardValidator()
        assert v.detect_no_data_panels({"datasource": {"uid": "no-ds"}}) is True

    def test_has_datasource(self):
        v = DashboardValidator()
        assert v.detect_no_data_panels(
            {"datasource": {"uid": "PBFA97CFB590B2093"}}
        ) is False

    def test_datasource_as_string(self):
        v = DashboardValidator()
        assert v.detect_no_data_panels({"datasource": "no-ds"}) is True


class TestDashboardValidatorFakeTopology:
    def test_detect_fake_node(self):
        v = DashboardValidator()
        results = v.detect_fake_topology('{"node": "node-04"}')
        assert len(results) >= 1
        assert "fake_topology_nodes" in results[0]

    def test_no_fake_node(self):
        v = DashboardValidator()
        results = v.detect_fake_topology('{"node": "192.168.1.30"}')
        assert len(results) == 0


class TestDashboardValidatorStale:
    def test_stale_no_data_panels(self):
        v = DashboardValidator()
        dashboard = {
            "panels": [
                {"title": "P1", "datasource": {"uid": ""}},
                {"title": "P2", "targets": [{"expr": "up"}]},
            ]
        }
        warnings = v.detect_stale_dashboards(dashboard)
        assert any("no_data_panels" in w for w in warnings)

    def test_majority_no_data(self):
        v = DashboardValidator()
        dashboard = {
            "panels": [
                {"title": "P1", "datasource": {"uid": ""}},
                {"title": "P2", "datasource": {"uid": ""}},
                {"title": "P3", "targets": [{"expr": "up"}]},
            ]
        }
        warnings = v.detect_stale_dashboards(dashboard)
        assert any("majority_no_data" in w for w in warnings)


class TestDashboardValidatorInventoryDrift:
    def test_known_dashboard_no_drift(self):
        v = DashboardValidator()
        drifts = v.detect_inventory_drift("ai-lab-overview")
        assert len(drifts) == 0

    def test_unknown_dashboard_drift(self):
        v = DashboardValidator()
        drifts = v.detect_inventory_drift("unknown-uid-42")
        assert len(drifts) >= 1
        assert drifts[0]["type"] == "unknown_dashboard"

    def test_legacy_dashboard_no_drift(self):
        v = DashboardValidator()
        drifts = v.detect_inventory_drift("alpt7gt")
        assert len(drifts) == 0


class TestDashboardValidatorRuntimeMismatch:
    def test_no_forbidden_gpu_no_mismatch(self):
        v = DashboardValidator()
        drifts = v.detect_runtime_mismatch({"uid": "test"})
        assert len(drifts) == 0

    def test_forbidden_gpu_detected(self):
        v = DashboardValidator()
        drifts = v.detect_runtime_mismatch({"gpu": "A100", "uid": "test"})
        assert len(drifts) >= 1
        assert any(d["type"] == "forbidden_gpu" for d in drifts)

    def test_legacy_gpu_detected(self):
        v = DashboardValidator()
        drifts = v.detect_runtime_mismatch({"gpu": "RTX 3090", "uid": "test"})
        assert len(drifts) >= 1
        assert any(d["type"] == "legacy_gpu" for d in drifts)

    def test_fake_topology_detected(self):
        v = DashboardValidator()
        drifts = v.detect_runtime_mismatch({"node": "node-05", "uid": "test"})
        assert len(drifts) >= 1
        assert any(d["type"] == "fake_topology" for d in drifts)


class TestDashboardValidatorPanelQueries:
    def test_valid_panel_query(self):
        v = DashboardValidator()
        panel = {"title": "GPU Usage", "targets": [{"expr": "ailab_gpu_active_requests"}]}
        results = v.validate_panel_queries(panel)
        assert len(results) >= 1
        assert results[0]["validity"] == "valid"

    def test_stale_panel_query(self):
        v = DashboardValidator()
        panel = {"title": "Memory", "targets": [{"expr": "memory_contamination_risk{job='test'}"}]}
        results = v.validate_panel_queries(panel)
        assert len(results) >= 1
        stale = any(r["validity"] == "stale" for r in results)
        assert stale is True

    def test_no_targets(self):
        v = DashboardValidator()
        panel = {"title": "Empty Panel"}
        results = v.validate_panel_queries(panel)
        assert results == []


class TestDashboardValidatorValidateDashboard:
    def test_validate_known_ai_lab(self):
        v = DashboardValidator()
        for d in _AI_LAB_DASHBOARDS:
            result = v.validate_dashboard(d)
            assert result.uid == d["uid"]
            assert result.health in ("healthy",)  # all healthy

    def test_validate_known_legacy(self):
        v = DashboardValidator()
        d = _LEGACY_DASHBOARDS[0]
        result = v.validate_dashboard(d)
        assert result.uid == d["uid"]
        assert result.deprecated is True

    def test_validate_with_broken_panel(self):
        v = DashboardValidator()
        result = v.validate_dashboard({
            "uid": "test-broken", "title": "Broken",
            "panels": [{"targets": [{"expr": "up{broken"}]}],
        })
        assert result.health in ("broken",)

    def test_validate_with_no_data_panels(self):
        v = DashboardValidator()
        result = v.validate_dashboard({
            "uid": "test-nodata", "title": "No Data",
            "panels": [
                {"datasource": {"uid": ""}},
                {"datasource": {"uid": "no-ds"}},
            ],
        })
        assert result.panels_no_data >= 1

    def test_parse_error_returns_broken(self):
        v = DashboardValidator()
        result = v.validate_dashboard("not json at all")
        assert result.health == "broken"

    def test_validate_all_known_returns_11(self):
        v = DashboardValidator()
        results = v.validate_all_known()
        assert len(results) == 11

    def test_validate_all_known_ai_lab_healthy(self):
        v = DashboardValidator()
        results = v.validate_all_known()
        ai_lab = [r for r in results if r["uid"].startswith("ai-lab")]
        for r in ai_lab:
            assert r["health"] == "healthy"


class TestDashboardValidationResult:
    def test_to_dict(self):
        r = DashboardValidationResult(
            uid="test", title="Test",
            health="healthy", panels_total=5,
            datasource_valid=True,
        )
        d = r.to_dict()
        assert d["uid"] == "test"
        assert d["health"] == "healthy"
        assert d["panels_total"] == 5
        assert d["datasource_valid"] is True

    def test_defaults(self):
        r = DashboardValidationResult()
        d = r.to_dict()
        assert d["uid"] == ""
        assert d["health"] == "unknown"
        assert d["deprecated"] is False


class TestBuildDashboardAuditSummary:
    def test_summary_has_contract_version(self):
        v = DashboardValidator()
        summary = v.build_dashboard_audit_summary()
        assert summary["contract_version"] == DASHBOARD_VALIDATOR_CONTRACT_VERSION

    def test_summary_has_classification(self):
        v = DashboardValidator()
        summary = v.build_dashboard_audit_summary()
        assert "health_classification" in summary
        assert "total_dashboards" in summary

    def test_summary_classification_counts(self):
        v = DashboardValidator()
        summary = v.build_dashboard_audit_summary()
        hc = summary["health_classification"]
        assert sum(hc.values()) == summary["total_dashboards"]

    def test_critical_healthy_count(self):
        v = DashboardValidator()
        summary = v.build_dashboard_audit_summary()
        assert "critical_dashboards_healthy" in summary
        assert summary["critical_dashboards_healthy"] >= 3

    def test_critical_total_count(self):
        v = DashboardValidator()
        summary = v.build_dashboard_audit_summary()
        assert "critical_dashboards_total" in summary


class TestRunGrafanaDriftAudit:
    def test_drift_audit_has_all_keys(self):
        v = DashboardValidator()
        audit = v.run_grafana_drift_audit()
        assert "total_dashboards" in audit
        assert "health_classification" in audit
        assert "broken_dashboards" in audit
        assert "stale_dashboards" in audit
        assert "legacy_dashboards" in audit
        assert "total_drift_issues" in audit

    def test_drift_audit_legacy_count(self):
        v = DashboardValidator()
        audit = v.run_grafana_drift_audit()
        assert len(audit["legacy_dashboards"]) == 6

    def test_drift_audit_contract_version(self):
        v = DashboardValidator()
        audit = v.run_grafana_drift_audit()
        assert audit["contract_version"] == DASHBOARD_VALIDATOR_CONTRACT_VERSION

    def test_drift_audit_json_safe(self):
        v = DashboardValidator()
        audit = v.run_grafana_drift_audit()
        _json.dumps(audit)


# ── Drift Detector ──

class TestDriftDetectorConstants:
    def test_contract_version(self):
        assert DRIFT_DETECTOR_CONTRACT_VERSION == "OBS-31A.2"


class TestDriftDetectorGPU:
    def test_forbidden_gpu_detected(self):
        d = DriftDetector()
        drifts = d.detect_gpu_drift(
            dashboard_gpus=["A100", "RX9070"],
            runtime_gpus=["rx9070", "rx7900xt"],
        )
        assert len(drifts) >= 1
        assert drifts[0]["type"] == "forbidden_gpu_in_dashboard"

    def test_unknown_gpu_detected(self):
        d = DriftDetector()
        drifts = d.detect_gpu_drift(
            dashboard_gpus=["SOME_UNKNOWN_GPU"],
            runtime_gpus=["rx9070"],
        )
        assert len(drifts) >= 1
        assert drifts[0]["type"] == "unknown_gpu_in_dashboard"

    def test_no_drift_with_expected_gpus(self):
        d = DriftDetector()
        drifts = d.detect_gpu_drift(
            dashboard_gpus=["RX9070", "RX7900XT"],
            runtime_gpus=["rx9070", "rx7900xt"],
        )
        assert len(drifts) == 0

    def test_no_dashboard_gpus(self):
        d = DriftDetector()
        drifts = d.detect_gpu_drift(dashboard_gpus=None)
        assert len(drifts) == 0


class TestDriftDetectorTopology:
    def test_topology_mode_mismatch(self):
        d = DriftDetector(runtime_context={"runtime_topology": {"mode": "degraded_single_gpu"}})
        drifts = d.detect_topology_drift(
            dashboard_topology={"mode": "single_gpu", "node_count": 5},
        )
        assert len(drifts) >= 1
        assert drifts[0]["type"] == "topology_mode_mismatch"

    def test_node_count_mismatch(self):
        d = DriftDetector()
        drifts = d.detect_topology_drift(
            dashboard_topology={"mode": "single_gpu", "node_count": 20},
        )
        assert len(drifts) >= 1
        assert drifts[0]["type"] == "node_count_mismatch"

    def test_no_topology_drift(self):
        d = DriftDetector()
        drifts = d.detect_topology_drift(dashboard_topology={})
        assert len(drifts) == 0

    def test_no_dashboard_topology(self):
        d = DriftDetector()
        drifts = d.detect_topology_drift(dashboard_topology=None)
        assert len(drifts) == 0


class TestDriftDetectorService:
    def test_no_dashboard_services_returns_empty(self):
        d = DriftDetector()
        drifts = d.detect_service_drift(dashboard_services=None)
        assert len(drifts) == 0

    def test_empty_list_returns_empty(self):
        d = DriftDetector()
        drifts = d.detect_service_drift(dashboard_services=[])
        assert len(drifts) == 0


class TestDriftDetectorSemantic:
    def test_semantic_drift_detected(self):
        d = DriftDetector()
        drifts = d.detect_semantic_drift(
            dashboard_domains=["overview", "fake_domain"],
            runtime_domains=["overview", "runtime", "gpu"],
        )
        assert len(drifts) >= 1
        assert drifts[0]["type"] == "domain_mismatch"

    def test_no_semantic_drift(self):
        d = DriftDetector()
        drifts = d.detect_semantic_drift(
            dashboard_domains=["overview", "runtime"],
            runtime_domains=["overview", "runtime"],
        )
        assert len(drifts) == 0

    def test_none_domains_returns_empty(self):
        d = DriftDetector()
        drifts = d.detect_semantic_drift(None, None)
        assert len(drifts) == 0


class TestDriftDetectorInventory:
    def test_known_dashboard_no_drift(self):
        d = DriftDetector()
        drifts = d.detect_inventory_drift(
            dashboard_inventory=[{"uid": "ai-lab-overview", "title": "Overview"}],
        )
        assert len(drifts) == 0

    def test_unknown_dashboard_drift(self):
        d = DriftDetector()
        drifts = d.detect_inventory_drift(
            dashboard_inventory=[{"uid": "ghost-dash-99", "title": "Ghost"}],
        )
        assert len(drifts) >= 1
        assert drifts[0]["type"] == "unknown_dashboard"

    def test_none_inventory_returns_empty(self):
        d = DriftDetector()
        drifts = d.detect_inventory_drift(None)
        assert len(drifts) == 0


class TestDriftDetectorRuntimeMismatch:
    def test_invalid_runtime_domain(self):
        d = DriftDetector()
        drifts = d.detect_runtime_mismatch(
            dashboard_metadata={"runtime_domain": "fake_domain", "semantic_owner": "runtime"},
        )
        assert len(drifts) >= 1
        assert drifts[0]["type"] == "invalid_runtime_domain"

    def test_invalid_semantic_owner(self):
        d = DriftDetector()
        drifts = d.detect_runtime_mismatch(
            dashboard_metadata={"runtime_domain": "runtime", "semantic_owner": "fake_owner"},
        )
        assert len(drifts) >= 1
        assert drifts[0]["type"] == "invalid_semantic_owner"

    def test_valid_metadata_no_mismatch(self):
        d = DriftDetector()
        drifts = d.detect_runtime_mismatch(
            dashboard_metadata={"runtime_domain": "runtime", "semantic_owner": "runtime"},
        )
        assert len(drifts) == 0

    def test_none_metadata_returns_empty(self):
        d = DriftDetector()
        drifts = d.detect_runtime_mismatch(None)
        assert len(drifts) == 0


class TestDriftDetectorDetectAll:
    def test_detect_all_empty(self):
        d = DriftDetector()
        result = d.detect_all()
        assert result.total_drifts == 0
        assert len(result.gpu_drift) == 0

    def test_detect_all_with_gpu_drift(self):
        d = DriftDetector()
        result = d.detect_all(dashboard_gpus=["A100"])
        assert result.total_drifts > 0
        assert len(result.gpu_drift) > 0

    def test_detect_all_with_topology_drift(self):
        d = DriftDetector(runtime_context={"runtime_topology": {"mode": "degraded"}})
        result = d.detect_all(dashboard_topology={"mode": "healthy", "node_count": 10})
        assert result.total_drifts > 0

    def test_detect_all_with_semantic_and_inventory(self):
        d = DriftDetector()
        result = d.detect_all(
            dashboard_domains=["fake_domain"],
            runtime_domains=["runtime"],
            dashboard_inventory=[{"uid": "nope", "title": "Nope"}],
        )
        assert result.total_drifts >= 2

    def test_detect_all_returns_result(self):
        d = DriftDetector()
        result = d.detect_all()
        assert isinstance(result, DriftDetectionResult)

    def test_to_dict_has_all_fields(self):
        d = DriftDetector()
        result = d.detect_all()
        d3 = result.to_dict()
        assert "contract_version" in d3
        assert "gpu_drift" in d3
        assert "topology_drift" in d3
        assert "service_drift" in d3
        assert "model_drift" in d3
        assert "semantic_drift" in d3
        assert "inventory_drift" in d3
        assert "runtime_mismatch" in d3
        assert "total_drifts" in d3

    def test_to_dict_contract_version(self):
        d = DriftDetector()
        result = d.detect_all()
        d3 = result.to_dict()
        assert d3["contract_version"] == "OBS-31A.2"

    def test_to_dict_json_safe(self):
        d = DriftDetector()
        result = d.detect_all(dashboard_gpus=["A100"])
        _json.dumps(result.to_dict())


class TestBuildDriftSummary:
    def test_summary_from_none(self):
        summary = build_drift_summary(None)
        assert summary["total_drifts"] == 0
        assert summary["contract_version"] == DRIFT_DETECTOR_CONTRACT_VERSION

    def test_summary_from_result(self):
        d = DriftDetector()
        result = d.detect_all(dashboard_gpus=["A100"])
        summary = build_drift_summary(result)
        assert summary["total_drifts"] > 0

    def test_summary_json_safe(self):
        summary = build_drift_summary()
        _json.dumps(summary)


class TestBuildRuntimeAlignmentSummary:
    def test_alignment_summary_no_drifts(self):
        result = DriftDetectionResult()
        summary = build_runtime_alignment_summary(result)
        assert summary["alignment_score"] >= 90
        assert summary["alignment_level"] == "healthy"

    def test_alignment_summary_with_drifts(self):
        d = DriftDetector()
        result = d.detect_all(dashboard_gpus=["A100", "H100"])
        summary = build_runtime_alignment_summary(result)
        assert summary["alignment_score"] <= 90
        assert summary["alignment_level"] in ("healthy", "degraded")

    def test_alignment_summary_many_drifts(self):
        result = DriftDetectionResult()
        result.gpu_drift = [{"type": "forbidden_gpu_in_dashboard", "gpu": "a100", "severity": "critical"}] * 5
        summary = build_runtime_alignment_summary(result)
        assert summary["alignment_score"] == 75
        assert summary["alignment_level"] == "degraded"

    def test_alignment_summary_with_broken_dashboards(self):
        result = DriftDetectionResult()
        summary = build_runtime_alignment_summary(
            result,
            dashboard_results=[
                {"health": "healthy", "uid": "a"},
                {"health": "broken", "uid": "b"},
                {"health": "stale", "uid": "c"},
            ],
        )
        assert summary["alignment_score"] <= 80
        assert summary["components"]["broken_dashboards"] == 2

    def test_alignment_summary_contract_version(self):
        summary = build_runtime_alignment_summary()
        assert summary["contract_version"] == DRIFT_DETECTOR_CONTRACT_VERSION

    def test_alignment_summary_has_components(self):
        summary = build_runtime_alignment_summary()
        assert "components" in summary
        assert "drift_summary" in summary
        assert "alignment_score" in summary
        assert "alignment_level" in summary

    def test_alignment_summary_critical_level(self):
        result = DriftDetectionResult()
        result.gpu_drift = [{"type": "forbidden_gpu", "gpu": "a100", "severity": "critical"}] * 15
        summary = build_runtime_alignment_summary(
            result,
            dashboard_results=[{"health": "broken"}] * 5,
        )
        assert summary["alignment_level"] == "critical"

    def test_alignment_summary_json_safe(self):
        summary = build_runtime_alignment_summary()
        _json.dumps(summary)


# ── GrafanaAlignmentContract ──

class TestGrafanaAlignmentContract:
    def test_defaults(self):
        c = GrafanaAlignmentContract()
        d = c.to_dict()
        assert d["contract_version"] == "OBS-31A.2"
        assert d["total_dashboards"] == 0
        assert d["alignment_score"] == 0.0
        assert d["alignment_level"] == "unknown"

    def test_builder(self):
        contract = build_grafana_alignment_contract(
            total_dashboards=11,
            healthy_dashboards=5,
            broken_dashboards=0,
            legacy_dashboards=6,
            alignment_score=95.0,
            alignment_level="healthy",
        )
        assert contract["total_dashboards"] == 11
        assert contract["dashboards_healthy"] == 5
        assert contract["dashboards_legacy"] == 6
        assert contract["alignment_score"] == 95.0
        assert contract["alignment_level"] == "healthy"

    def test_builder_partial(self):
        contract = build_grafana_alignment_contract(total_dashboards=11)
        assert contract["total_dashboards"] == 11
        assert contract["dashboards_healthy"] == 0

    def test_contract_version_in_builder(self):
        contract = build_grafana_alignment_contract()
        assert contract["contract_version"] == "OBS-31A.2"

    def test_json_safe(self):
        contract = build_grafana_alignment_contract(
            total_dashboards=11, alignment_score=90.0,
        )
        _json.dumps(contract)

    def test_gpu_drifts_field(self):
        contract = build_grafana_alignment_contract(
            gpu_drifts=3, total_drifts=5,
        )
        assert contract["gpu_drifts"] == 3
        assert contract["total_drifts"] == 5

    def test_datasource_fields(self):
        contract = build_grafana_alignment_contract(
            datasource_valid=True,
            datasource_prometheus=True,
            datasource_loki=True,
        )
        assert contract["datasource_valid"] is True

    def test_panels_fields(self):
        contract = build_grafana_alignment_contract(
            broken_panels=2, no_data_panels=3,
        )
        assert contract["broken_panels"] == 2
        assert contract["no_data_panels"] == 3


# ── DriftDetectionResult ──

class TestDriftDetectionResult:
    def test_empty_default(self):
        r = DriftDetectionResult()
        assert r.total_drifts == 0
        assert len(r.gpu_drift) == 0

    def test_total_drifts_auto_calculated(self):
        r = DriftDetectionResult()
        r.gpu_drift = [{"type": "test"}]
        d = r.to_dict()
        assert d["total_drifts"] == 1

    def test_to_dict_all_empty(self):
        r = DriftDetectionResult()
        d = r.to_dict()
        assert d["total_drifts"] == 0
        assert d["gpu_drift"] == []
        assert d["topology_drift"] == []
        assert d["service_drift"] == []
        assert d["model_drift"] == []
        assert d["semantic_drift"] == []
        assert d["inventory_drift"] == []
        assert d["runtime_mismatch"] == []

    def test_to_dict_counts_all_categories(self):
        r = DriftDetectionResult()
        r.gpu_drift = [{"gpu": "a100"}]
        r.topology_drift = [{"type": "mismatch"}]
        r.semantic_drift = [{"type": "domain"}]
        d = r.to_dict()
        assert d["total_drifts"] == 3


# ── DashboardValidator Contract Version ──

class TestDashboardValidatorContract:
    def test_contract_version_set(self):
        assert DASHBOARD_VALIDATOR_CONTRACT_VERSION == "OBS-31A.2"

    def test_query_validity_enum(self):
        assert QueryValidity.VALID.value == "valid"
        assert QueryValidity.INVALID.value == "invalid"
        assert QueryValidity.STALE.value == "stale"
        assert QueryValidity.EMPTY.value == "empty"

    def test_dashboard_health_enum(self):
        assert VDashboardHealth.HEALTHY.value == "healthy"
        assert VDashboardHealth.BROKEN.value == "broken"
        assert VDashboardHealth.STALE.value == "stale"
        assert VDashboardHealth.DEPRECATED.value == "deprecated"
