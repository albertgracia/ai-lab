"""FASE OBS-31A.3: Runtime ↔ Observability Alignment Tests."""

from __future__ import annotations

import json

from runtime.observability.runtime_alignment import (
    RUNTIME_ALIGNMENT_CONTRACT_VERSION,
    AlignmentCheck,
    RuntimeAlignmentValidationResult,
    RuntimeAlignmentValidator,
    build_runtime_alignment_result,
    EXPECTED_ACTIVE_GPUS,
    EXPECTED_OFFLINE_GPUS,
    VALID_TOPOLOGY_MODES,
)


# ── Constants ──

class TestConstants:
    def test_contract_version(self):
        assert RUNTIME_ALIGNMENT_CONTRACT_VERSION == "OBS-31A.3"

    def test_expected_active_gpus(self):
        assert "rx9070" in EXPECTED_ACTIVE_GPUS

    def test_expected_offline_gpus(self):
        assert "rx7900xt" in EXPECTED_OFFLINE_GPUS

    def test_valid_topology_modes(self):
        assert "single_node" in VALID_TOPOLOGY_MODES
        assert "degraded_single_gpu" in VALID_TOPOLOGY_MODES
        assert "inventory_only" in VALID_TOPOLOGY_MODES


# ── AlignmentCheck ──

class TestAlignmentCheck:
    def test_defaults(self):
        c = AlignmentCheck()
        assert c.domain == ""
        assert c.passed is False
        assert c.severity == "info"

    def test_to_dict(self):
        c = AlignmentCheck(
            domain="gpu", check="rx9070_active",
            passed=True, severity="critical",
            detail="RX9070 detected", expected=True, actual=True,
        )
        d = c.to_dict()
        assert d["domain"] == "gpu"
        assert d["check"] == "rx9070_active"
        assert d["passed"] is True
        assert d["severity"] == "critical"
        assert d["expected"] is True
        assert d["actual"] is True

    def test_to_dict_json_safe(self):
        c = AlignmentCheck(domain="test", check="test", passed=True)
        json.dumps(c.to_dict())

    def test_all_fields(self):
        c = AlignmentCheck(
            domain="model", check="qwen_active",
            passed=False, severity="high",
            detail="Model not found",
            expected="active", actual="unknown",
        )
        assert c.domain == "model"
        assert c.check == "qwen_active"
        assert c.passed is False
        assert c.severity == "high"


# ── RuntimeAlignmentValidationResult ──

class TestRuntimeAlignmentValidationResult:
    def test_defaults(self):
        r = RuntimeAlignmentValidationResult()
        assert r.alignment_score == 0.0
        assert r.alignment_level == "unknown"
        assert r.gpu_checks == []
        assert r.gpu_passed == 0

    def test_to_dict_structure(self):
        r = RuntimeAlignmentValidationResult()
        d = r.to_dict()
        assert "contract_version" in d
        assert d["contract_version"] == "OBS-31A.3"
        assert "gpu_alignment" in d
        assert "topology_alignment" in d
        assert "model_alignment" in d
        assert "contract_alignment" in d
        assert "storage_alignment" in d
        assert "service_alignment" in d
        assert "alignment_score" in d
        assert "alignment_level" in d

    def test_to_dict_with_checks(self):
        r = RuntimeAlignmentValidationResult()
        r.gpu_checks = [AlignmentCheck(domain="gpu", check="test", passed=True)]
        r.gpu_passed = 1
        r.gpu_total = 1
        r.alignment_score = 100.0
        r.alignment_level = "healthy"
        d = r.to_dict()
        assert d["gpu_alignment"]["passed"] == 1
        assert d["gpu_alignment"]["total"] == 1
        assert d["alignment_score"] == 100.0
        assert d["alignment_level"] == "healthy"

    def test_to_dict_json_safe(self):
        r = RuntimeAlignmentValidationResult()
        json.dumps(r.to_dict())

    def test_each_domain_has_passed_total_checks(self):
        r = RuntimeAlignmentValidationResult()
        d = r.to_dict()
        for domain in ("gpu", "topology", "model", "contract", "storage", "service"):
            key = f"{domain}_alignment"
            assert key in d
            assert "passed" in d[key]
            assert "total" in d[key]
            assert "checks" in d[key]


# ── GPU State Alignment ──

class TestValidateGPUState:
    def make_validator(self) -> RuntimeAlignmentValidator:
        return RuntimeAlignmentValidator()

    def test_rx9070_detected_in_runtime(self):
        v = self.make_validator()
        sensor = {
            "gpu_operational_summaries": [
                {"gpu_id": "RX9070", "host": "192.168.1.50",
                 "operational_state": "active", "observed_state": "up"},
            ],
        }
        checks = v.validate_gpu_state(sensor_snapshot=sensor)
        rx9070 = [c for c in checks if c.check == "rx9070_active_in_runtime"]
        assert len(rx9070) == 1
        assert rx9070[0].passed is True

    def test_rx9070_not_detected(self):
        v = self.make_validator()
        sensor = {"gpu_operational_summaries": []}
        checks = v.validate_gpu_state(sensor_snapshot=sensor)
        rx9070 = [c for c in checks if c.check == "rx9070_active_in_runtime"]
        assert len(rx9070) == 1
        assert rx9070[0].passed is False

    def test_rx7900xt_in_inventory(self):
        v = self.make_validator()
        sensor = {
            "gpu_operational_summaries": [
                {"gpu_id": "RX9070", "host": "192.168.1.50"},
            ],
            "topology": {
                "inventory_gpus": [{"name": "RX7900XT", "host": "192.168.1.60"}],
            },
        }
        checks = v.validate_gpu_state(sensor_snapshot=sensor)
        rx7900xt = [c for c in checks if c.check == "rx7900xt_expected_offline_in_runtime"]
        assert len(rx7900xt) == 1
        assert rx7900xt[0].passed is True

    def test_rx7900xt_not_in_inventory(self):
        v = self.make_validator()
        sensor = {
            "gpu_operational_summaries": [],
            "topology": {"inventory_gpus": []},
        }
        checks = v.validate_gpu_state(sensor_snapshot=sensor)
        rx7900xt = [c for c in checks if c.check == "rx7900xt_expected_offline_in_runtime"]
        assert len(rx7900xt) == 1
        assert rx7900xt[0].passed is False

    def test_rx7900xt_expected_offline_in_prometheus(self):
        v = self.make_validator()
        targets = {
            "targets": [{"job": "ai-lab-gpu-rx7900xt", "status": "down"}],
            "expected_offline": ["ai-lab-gpu-rx7900xt"],
        }
        checks = v.validate_gpu_state(prometheus_targets=targets)
        expected = [c for c in checks if c.check == "rx7900xt_expected_offline_prometheus"]
        assert len(expected) >= 1
        assert expected[0].passed is True

    def test_rx7900xt_not_expected_offline(self):
        v = self.make_validator()
        targets = {
            "targets": [{"job": "ai-lab-gpu-rx7900xt", "status": "down"}],
            "expected_offline": [],
        }
        checks = v.validate_gpu_state(prometheus_targets=targets)
        expected = [c for c in checks if c.check == "rx7900xt_expected_offline_prometheus"]
        if expected:
            assert expected[0].passed is False

    def test_no_rx7900xt_in_prometheus_skips_check(self):
        v = self.make_validator()
        targets = {
            "targets": [{"job": "ai-lab-gateway", "status": "up"}],
            "expected_offline": [],
        }
        checks = v.validate_gpu_state(prometheus_targets=targets)
        expected = [c for c in checks if c.check == "rx7900xt_expected_offline_prometheus"]
        assert len(expected) == 0

    def test_forbidden_gpu_in_dashboard_detected(self):
        v = self.make_validator()
        dashboards = [{"uid": "dash-1", "title": "Test", "panels": [{"gpu": "A100"}]}]
        checks = v.validate_gpu_state(grafana_dashboards=dashboards)
        forbidden = [c for c in checks if c.check == "no_forbidden_gpu_in_dashboards"]
        assert len(forbidden) >= 1
        assert forbidden[0].passed is False

    def test_no_forbidden_gpu_in_dashboards(self):
        v = self.make_validator()
        dashboards = [{"uid": "dash-1", "title": "Test", "gpu": "RX9070"}]
        checks = v.validate_gpu_state(grafana_dashboards=dashboards)
        forbidden = [c for c in checks if c.check == "no_forbidden_gpu_in_dashboards"]
        assert len(forbidden) >= 1
        assert forbidden[0].passed is True

    def test_forbidden_gpu_in_runtime_detected(self):
        v = self.make_validator()
        sensor = {
            "gpu_operational_summaries": [
                {"gpu_id": "A100", "host": "fake", "operational_state": "active"},
            ],
        }
        checks = v.validate_gpu_state(sensor_snapshot=sensor)
        forbidden = [c for c in checks if c.check == "no_forbidden_gpu_in_runtime"]
        assert len(forbidden) >= 1
        assert forbidden[0].passed is False

    def test_no_data_defaults(self):
        v = self.make_validator()
        checks = v.validate_gpu_state()
        assert len(checks) >= 3  # rx9070, rx7900xt, no_forbidden checks
        rx9070 = [c for c in checks if c.check == "rx9070_active_in_runtime"]
        assert rx9070[0].passed is False  # no data = not detected
        forbidden = [c for c in checks if c.check == "no_forbidden_gpu_in_dashboards"]
        assert forbidden[0].passed is True  # no dashboards = no forbidden

    def test_gpu_state_records_passed_total(self):
        v = self.make_validator()
        sensor = {"gpu_operational_summaries": [{"gpu_id": "RX9070"}]}
        v.validate_gpu_state(sensor_snapshot=sensor)
        assert v._result.gpu_total > 0

    def test_multiple_forbidden_gpus_in_one_dashboard(self):
        v = self.make_validator()
        dashboards = [{"uid": "dash-1", "title": "Test",
                       "text": "Uses A100 and H100 GPUs"}]
        checks = v.validate_gpu_state(grafana_dashboards=dashboards)
        forbidden = [c for c in checks if c.check == "no_forbidden_gpu_in_dashboards"]
        assert len(forbidden) == 1
        assert forbidden[0].passed is False

    def test_all_checks_json_safe(self):
        v = self.make_validator()
        v.validate_gpu_state(
            sensor_snapshot={"gpu_operational_summaries": [{"gpu_id": "RX9070"}]},
            prometheus_targets={"targets": [{"job": "ai-lab-gpu-rx7900xt"}],
                                "expected_offline": ["ai-lab-gpu-rx7900xt"]},
            grafana_dashboards=[{"uid": "dash-1"}],
        )
        json.dumps([c.to_dict() for c in v._result.gpu_checks])


# ── Topology Alignment ──

class TestValidateTopology:
    def test_topology_modes_match(self):
        v = RuntimeAlignmentValidator()
        sensor = {"topology": {"mode": "degraded_single_gpu"}}
        summary = {"topology_mode": "degraded_single_gpu"}
        checks = v.validate_topology(runtime_summary=summary, sensor_snapshot=sensor)
        mode_check = [c for c in checks if c.check == "topology_mode_consistent"]
        assert len(mode_check) == 1
        assert mode_check[0].passed is True

    def test_topology_modes_mismatch(self):
        v = RuntimeAlignmentValidator()
        sensor = {"topology": {"mode": "single_gpu"}}
        summary = {"topology_mode": "multi_gpu"}
        checks = v.validate_topology(runtime_summary=summary, sensor_snapshot=sensor)
        mode_check = [c for c in checks if c.check == "topology_mode_consistent"]
        assert len(mode_check) == 1
        assert mode_check[0].passed is False

    def test_valid_topology_mode(self):
        v = RuntimeAlignmentValidator()
        for mode in VALID_TOPOLOGY_MODES:
            sensor = {"topology": {"mode": mode}}
            checks = v.validate_topology(sensor_snapshot=sensor)
            valid_check = [c for c in checks if c.check == "topology_mode_valid"]
            assert len(valid_check) == 1
            assert valid_check[0].passed is True, f"Mode {mode} should be valid"

    def test_invalid_topology_mode(self):
        v = RuntimeAlignmentValidator()
        sensor = {"topology": {"mode": "invalid_mode_xyz"}}
        checks = v.validate_topology(sensor_snapshot=sensor)
        valid_check = [c for c in checks if c.check == "topology_mode_valid"]
        assert len(valid_check) == 1
        assert valid_check[0].passed is False

    def test_fake_nodes_in_dashboards_detected(self):
        v = RuntimeAlignmentValidator()
        dashboards = [{"uid": "dash-1", "title": "Fake",
                       "panels": [{"node": "node-04"}]}]
        checks = v.validate_topology(grafana_dashboards=dashboards)
        fake_check = [c for c in checks if c.check == "no_fake_topology_in_dashboards"]
        assert len(fake_check) == 1
        assert fake_check[0].passed is False

    def test_no_fake_nodes(self):
        v = RuntimeAlignmentValidator()
        dashboards = [{"uid": "dash-1", "title": "Real", "node": "192.168.1.30"}]
        checks = v.validate_topology(grafana_dashboards=dashboards)
        fake_check = [c for c in checks if c.check == "no_fake_topology_in_dashboards"]
        assert len(fake_check) == 1
        assert fake_check[0].passed is True

    def test_no_data_defaults(self):
        v = RuntimeAlignmentValidator()
        checks = v.validate_topology()
        assert len(checks) >= 1
        fake_check = [c for c in checks if c.check == "no_fake_topology_in_dashboards"]
        assert fake_check[0].passed is True  # no dashboards = no fake nodes

    def test_topology_records_passed_total(self):
        v = RuntimeAlignmentValidator()
        v.validate_topology()
        assert v._result.topology_total > 0


# ── Model Inventory Alignment ──

class TestValidateModelInventory:
    def test_all_expected_models_active(self):
        v = RuntimeAlignmentValidator()
        rt_models = {
            "qwen2.5-coder-14b-instruct": {"status": "active"},
            "llama-3.1-8b-instruct": {"status": "active"},
            "nomic-embed-text-v1.5": {"status": "active"},
        }
        lmstudio = {
            "statuses": {
                "qwen2.5-coder-14b-instruct": {"id": "qwen2.5-coder-14b-instruct"},
                "llama-3.1-8b-instruct": {"id": "llama-3.1-8b-instruct"},
                "nomic-embed-text-v1.5": {"id": "nomic-embed-text-v1.5"},
            },
        }
        checks = v.validate_model_inventory(lmstudio_state=lmstudio, runtime_models=rt_models)
        assert all(c.passed for c in checks)

    def test_qwen_not_active(self):
        v = RuntimeAlignmentValidator()
        rt_models = {}
        lmstudio = {"statuses": {"llama-3.1-8b-instruct": {"id": "llama-3.1-8b-instruct"}}}
        checks = v.validate_model_inventory(lmstudio_state=lmstudio, runtime_models=rt_models)
        qwen_check = [c for c in checks if "qwen" in c.check]
        assert len(qwen_check) >= 1
        assert qwen_check[0].passed is False

    def test_no_data_defaults(self):
        v = RuntimeAlignmentValidator()
        checks = v.validate_model_inventory()
        assert len(checks) >= 3  # 3 expected models
        assert all(not c.passed for c in checks)  # all fail with no data

    def test_model_records_passed_total(self):
        v = RuntimeAlignmentValidator()
        v.validate_model_inventory()
        assert v._result.model_total == 3


# ── Contract Version Alignment ──

class TestValidateContractVersions:
    def test_all_contracts_match(self):
        v = RuntimeAlignmentValidator()
        contracts = {
            "sensor": "30I-D",
            "cognitive": "30I-F",
            "grounding": "30I-G",
            "observability": "OBS-31A",
            "prometheus_audit": "OBS-31A.1",
            "drift_detector": "OBS-31A.2",
            "grafana_inventory": "OBS-31A.2",
            "runtime_alignment": "OBS-31A.3",
        }
        checks = v.validate_contract_versions(contracts)
        assert all(c.passed for c in checks)

    def test_unknown_contract_fails(self):
        v = RuntimeAlignmentValidator()
        contracts = {
            "sensor": "30I-D",
            "observability": "UNKNOWN",
            "runtime_alignment": "OBS-31A.3",
        }
        checks = v.validate_contract_versions(contracts)
        obs_check = [c for c in checks if c.check == "observability_version"]
        assert len(obs_check) == 1
        assert obs_check[0].passed is False

    def test_none_contract_is_fail(self):
        v = RuntimeAlignmentValidator()
        contracts = {"sensor": None}
        checks = v.validate_contract_versions(contracts)
        sensor_check = [c for c in checks if c.check == "sensor_version"]
        assert len(sensor_check) == 1
        assert sensor_check[0].passed is False
        assert sensor_check[0].actual is None

    def test_missing_contract_all_none(self):
        v = RuntimeAlignmentValidator()
        checks = v.validate_contract_versions({})
        assert len(checks) == 8
        assert all(not c.passed for c in checks)

    def test_contract_records_passed_total(self):
        v = RuntimeAlignmentValidator()
        v.validate_contract_versions()
        assert v._result.contract_total == 8

    def test_prefix_matching_works(self):
        v = RuntimeAlignmentValidator()
        contracts = {
            "sensor": "30I-D-v2",
            "cognitive": "30I-F-modified",
        }
        checks = v.validate_contract_versions(contracts)
        sensor_check = [c for c in checks if c.check == "sensor_version"]
        assert sensor_check[0].passed is True  # starts with 30I-

    def test_observability_critical_severity(self):
        v = RuntimeAlignmentValidator()
        contracts = {"observability": None}
        checks = v.validate_contract_versions(contracts)
        obs_check = [c for c in checks if c.check == "observability_version"]
        assert obs_check[0].severity == "critical"


# ── Storage Alignment ──

class TestValidateStorage:
    def test_disk_available(self):
        v = RuntimeAlignmentValidator()
        sensor = {
            "observed_data": {
                "system_node": {
                    "disk": {"total_gb": 97, "used_gb": 50, "available_gb": 47},
                },
            },
        }
        checks = v.validate_storage(sensor_snapshot=sensor)
        disk_check = [c for c in checks if c.check == "disk_usage_available"]
        assert len(disk_check) == 1
        assert disk_check[0].passed is True

    def test_disk_not_available(self):
        v = RuntimeAlignmentValidator()
        checks = v.validate_storage(sensor_snapshot={})
        disk_check = [c for c in checks if c.check == "disk_usage_available"]
        assert len(disk_check) == 1
        assert disk_check[0].passed is False

    def test_archive_healthy(self):
        v = RuntimeAlignmentValidator()
        sensor = {
            "derived_state": {
                "storage": {"archive_healthy": True},
            },
        }
        checks = v.validate_storage(sensor_snapshot=sensor)
        archive_check = [c for c in checks if c.check == "archive_state_healthy"]
        assert len(archive_check) == 1
        assert archive_check[0].passed is True

    def test_archive_not_healthy(self):
        v = RuntimeAlignmentValidator()
        sensor = {
            "derived_state": {
                "storage": {"archive_healthy": False},
            },
        }
        checks = v.validate_storage(sensor_snapshot=sensor)
        archive_check = [c for c in checks if c.check == "archive_state_healthy"]
        assert len(archive_check) == 1
        assert archive_check[0].passed is False

    def test_storage_records_passed_total(self):
        v = RuntimeAlignmentValidator()
        v.validate_storage()
        assert v._result.storage_total > 0


# ── Service Alignment ──

class TestValidateServices:
    def test_all_services_up(self):
        v = RuntimeAlignmentValidator()
        targets = {
            "targets": [
                {"job": "ailab-gateway", "status": "healthy"},
                {"job": "ailab-router", "status": "healthy"},
                {"job": "ailab-live-api", "status": "healthy"},
                {"job": "prometheus", "status": "healthy"},
                {"job": "grafana", "status": "healthy"},
            ],
        }
        checks = v.validate_services(prometheus_targets=targets)
        assert all(c.passed for c in checks)

    def test_gateway_down(self):
        v = RuntimeAlignmentValidator()
        targets = {
            "targets": [
                {"job": "ailab-gateway", "status": "degraded"},
                {"job": "ailab-router", "status": "healthy"},
                {"job": "ailab-live-api", "status": "healthy"},
            ],
        }
        checks = v.validate_services(prometheus_targets=targets)
        gw_check = [c for c in checks if c.check == "service_ailab-gateway_up"]
        assert len(gw_check) == 1
        assert gw_check[0].passed is False
        assert gw_check[0].severity == "critical"

    def test_service_not_in_targets(self):
        v = RuntimeAlignmentValidator()
        checks = v.validate_services(prometheus_targets={})
        for c in checks:
            assert c.passed is False
            assert c.actual == "unknown"

    def test_service_results_fallback(self):
        v = RuntimeAlignmentValidator()
        targets = {
            "results": [
                {"job": "ailab-gateway", "status": "healthy"},
                {"job": "prometheus", "status": "healthy"},
            ],
        }
        checks = v.validate_services(prometheus_targets=targets)
        gw = [c for c in checks if c.check == "service_ailab-gateway_up"]
        assert gw[0].passed is True

    def test_service_records_passed_total(self):
        v = RuntimeAlignmentValidator()
        v.validate_services()
        assert v._result.service_total >= 5


# ── validate_all ──

class TestValidateAll:
    def test_validate_all_empty(self):
        v = RuntimeAlignmentValidator()
        result = v.validate_all()
        # Even with no data, some checks pass (no_forbidden_gpu, no_fake_topology)
        assert result.alignment_score < 50.0
        assert result.alignment_level in ("critical", "unhealthy")

    def test_validate_all_with_full_data(self):
        v = RuntimeAlignmentValidator()
        sensor = {
            "gpu_operational_summaries": [{"gpu_id": "RX9070"}],
            "topology": {
                "mode": "degraded_single_gpu",
                "inventory_gpus": [{"name": "RX7900XT", "host": "192.168.1.60"}],
            },
        }
        rt_models = {
            "qwen2.5-coder-14b-instruct": {"status": "active"},
            "llama-3.1-8b-instruct": {"status": "active"},
            "nomic-embed-text-v1.5": {"status": "active"},
        }
        lmstudio = {
            "statuses": {k: {"id": k} for k in rt_models},
        }
        targets = {
            "targets": [{"job": "ailab-gateway", "status": "healthy"}],
        }
        contracts = {
            "sensor": "30I-D",
            "cognitive": "30I-F",
            "grounding": "30I-G",
            "observability": "OBS-31A",
            "prometheus_audit": "OBS-31A.1",
            "drift_detector": "OBS-31A.2",
            "grafana_inventory": "OBS-31A.2",
            "runtime_alignment": "OBS-31A.3",
        }
        result = v.validate_all(
            sensor_snapshot=sensor,
            runtime_models=rt_models,
            lmstudio_state=lmstudio,
            prometheus_targets=targets,
            contracts=contracts,
        )
        assert result.alignment_score > 0
        assert result.alignment_level in ("healthy", "degraded", "unhealthy")

    def test_validate_all_returns_result(self):
        v = RuntimeAlignmentValidator()
        result = v.validate_all()
        assert isinstance(result, RuntimeAlignmentValidationResult)

    def test_validate_all_score_healthy(self):
        v = RuntimeAlignmentValidator()
        sensor = {
            "gpu_operational_summaries": [{"gpu_id": "RX9070"}],
            "topology": {
                "mode": "single_node",
                "inventory_gpus": [{"name": "RX7900XT"}],
            },
        }
        rt_models = {
            "qwen2.5-coder-14b-instruct": {"status": "active"},
            "llama-3.1-8b-instruct": {"status": "active"},
            "nomic-embed-text-v1.5": {"status": "active"},
        }
        lmstudio = {"statuses": {k: {"id": k} for k in rt_models}}
        targets = {
            "targets": [
                {"job": "ailab-gateway", "status": "healthy"},
                {"job": "ailab-router", "status": "healthy"},
                {"job": "ailab-live-api", "status": "healthy"},
                {"job": "prometheus", "status": "healthy"},
                {"job": "grafana", "status": "healthy"},
            ],
        }
        contracts = {k: v for k, v in [
            ("sensor", "30I-D"), ("cognitive", "30I-F"), ("grounding", "30I-G"),
            ("observability", "OBS-31A"), ("prometheus_audit", "OBS-31A.1"),
            ("drift_detector", "OBS-31A.2"), ("grafana_inventory", "OBS-31A.2"),
            ("runtime_alignment", "OBS-31A.3"),
        ]}
        result = v.validate_all(
            sensor_snapshot=sensor,
            runtime_summary=sensor,
            runtime_models=rt_models,
            lmstudio_state=lmstudio,
            prometheus_targets=targets,
            contracts=contracts,
            grafana_dashboards=[{"uid": "dash-1"}],
        )
        assert result.alignment_score >= 70
        assert result.alignment_level in ("healthy", "degraded")

    def test_validate_all_json_safe(self):
        v = RuntimeAlignmentValidator()
        result = v.validate_all()
        json.dumps(result.to_dict())

    def test_validate_all_score_components(self):
        v = RuntimeAlignmentValidator()
        result = v.validate_all()
        d = result.to_dict()
        for domain in ("gpu", "topology", "model", "contract", "storage", "service"):
            key = f"{domain}_alignment"
            assert key in d
            assert "passed" in d[key]
            assert "total" in d[key]


# ── Score Computation ──

class TestScoreComputation:
    def test_all_passes_100_score(self):
        v = RuntimeAlignmentValidator()
        v._result.gpu_passed = 5
        v._result.gpu_total = 5
        v._result.topology_passed = 3
        v._result.topology_total = 3
        v._result.model_passed = 3
        v._result.model_total = 3
        v._result.contract_passed = 8
        v._result.contract_total = 8
        v._result.storage_passed = 2
        v._result.storage_total = 2
        v._result.service_passed = 5
        v._result.service_total = 5
        v._compute_score()
        assert v._result.alignment_score == 100.0
        assert v._result.alignment_level == "healthy"

    def test_half_passes_50_score(self):
        v = RuntimeAlignmentValidator()
        v._result.gpu_passed = 2
        v._result.gpu_total = 4
        v._result.topology_passed = 1
        v._result.topology_total = 3
        v._result.model_passed = 1
        v._result.model_total = 3
        v._result.contract_passed = 4
        v._result.contract_total = 8
        v._result.storage_passed = 1
        v._result.storage_total = 2
        v._result.service_passed = 2
        v._result.service_total = 5
        v._compute_score()
        assert v._result.alignment_score == 44.0
        assert v._result.alignment_level == "critical"

    def test_zero_total_returns_unknown(self):
        v = RuntimeAlignmentValidator()
        v._compute_score()
        assert v._result.alignment_score == 0.0
        assert v._result.alignment_level == "unknown"

    def test_degraded_threshold(self):
        v = RuntimeAlignmentValidator()
        total = 20
        passed = 15  # 75%
        v._result.gpu_passed = passed
        v._result.gpu_total = total
        v._result.topology_total = 0
        v._result.model_total = 0
        v._result.contract_total = 0
        v._result.storage_total = 0
        v._result.service_total = 0
        v._compute_score()
        assert v._result.alignment_score == 75.0
        assert v._result.alignment_level == "degraded"


# ── build_runtime_alignment_result ──

class TestBuildRuntimeAlignmentResult:
    def test_no_validator_returns_empty(self):
        result = build_runtime_alignment_result(None)
        assert result["alignment_score"] == 0.0
        assert result["alignment_level"] == "unknown"

    def test_with_validator(self):
        v = RuntimeAlignmentValidator()
        v._result.gpu_passed = 5
        v._result.gpu_total = 5
        v._result.alignment_score = 100.0
        v._result.alignment_level = "healthy"
        result = build_runtime_alignment_result(v)
        assert result["alignment_score"] == 100.0
        assert result["alignment_level"] == "healthy"

    def test_json_safe(self):
        result = build_runtime_alignment_result()
        json.dumps(result)


# ── Integration: validate_all domain totals ──

class TestDomainTotals:
    def test_gpu_checks_counted(self):
        v = RuntimeAlignmentValidator()
        v.validate_gpu_state(sensor_snapshot={
            "gpu_operational_summaries": [{"gpu_id": "RX9070"}],
        })
        assert v._result.gpu_total >= 3
        assert v._result.gpu_passed >= 1

    def test_topology_checks_counted(self):
        v = RuntimeAlignmentValidator()
        v.validate_topology(sensor_snapshot={"topology": {"mode": "single_node"}},
                            runtime_summary={"topology_mode": "single_node"})
        assert v._result.topology_total >= 2

    def test_contract_checks_all_eight(self):
        v = RuntimeAlignmentValidator()
        v.validate_contract_versions({k: v for k, v in [
            ("sensor", "30I-D"), ("cognitive", "30I-F"), ("grounding", "30I-G"),
            ("observability", "OBS-31A"), ("prometheus_audit", "OBS-31A.1"),
            ("drift_detector", "OBS-31A.2"), ("grafana_inventory", "OBS-31A.2"),
            ("runtime_alignment", "OBS-31A.3"),
        ]})
        assert v._result.contract_total == 8
        assert v._result.contract_passed == 8

    def test_service_checks_all_five(self):
        v = RuntimeAlignmentValidator()
        v.validate_services(prometheus_targets={
            "targets": [{"job": "ailab-gateway", "status": "healthy"}],
        })
        assert v._result.service_total == 5

    def test_storage_checks_two(self):
        v = RuntimeAlignmentValidator()
        v.validate_storage()
        assert v._result.storage_total == 2


# ── Edge Cases ──

class TestEdgeCases:
    def test_forbidden_gpu_case_insensitive(self):
        v = RuntimeAlignmentValidator()
        dashboards = [{"uid": "d", "text": "uses a100 40gb"}]
        checks = v.validate_gpu_state(grafana_dashboards=dashboards)
        forbidden = [c for c in checks if c.check == "no_forbidden_gpu_in_dashboards"]
        assert len(forbidden) == 1
        assert forbidden[0].passed is False

    def test_none_sensor_snapshot(self):
        v = RuntimeAlignmentValidator()
        checks = v.validate_gpu_state(sensor_snapshot=None)
        assert len(checks) >= 3

    def test_empty_prometheus_targets(self):
        v = RuntimeAlignmentValidator()
        checks = v.validate_services(prometheus_targets={})
        assert all(not c.passed for c in checks)

    def test_unknown_contract_key_ignored(self):
        v = RuntimeAlignmentValidator()
        contracts = {"unknown_key_42": "v1"}
        checks = v.validate_contract_versions(contracts)
        # Only expected 8 keys are checked; unknown keys are ignored
        assert len(checks) == 8

    def test_grafana_panels_not_dict(self):
        v = RuntimeAlignmentValidator()
        dashboards = ["just a string, not a dict"]
        checks = v.validate_gpu_state(grafana_dashboards=dashboards)
        forbidden = [c for c in checks if c.check == "no_forbidden_gpu_in_dashboards"]
        assert len(forbidden) == 1

    def test_lmstudio_models_as_string_list(self):
        v = RuntimeAlignmentValidator()
        lmstudio_state = {"models": ["qwen2.5-coder-14b-instruct", "llama-3.1-8b-instruct"]}
        rt_models = {
            "qwen2.5-coder-14b-instruct": {"status": "active"},
            "llama-3.1-8b-instruct": {"status": "active"},
            "nomic-embed-text-v1.5": {"status": "active"},
        }
        checks = v.validate_model_inventory(lmstudio_state=lmstudio_state, runtime_models=rt_models)
        qwen = [c for c in checks if "qwen" in c.check]
        llama = [c for c in checks if "llama" in c.check]
        assert len(qwen) >= 1
        assert len(llama) >= 1
        # qwen present in both runtime (active) and lmstudio (list)
        assert qwen[0].passed is True
        # llama present in both
        assert llama[0].passed is True
