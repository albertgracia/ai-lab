"""FASE OBS-31A.5: Safe Quick Wins Execution Tests."""

from __future__ import annotations

import json
import time

from runtime.observability.remediation_executor import (
    EXECUTOR_CONTRACT_VERSION,
    AUTO_SAFE_PREFIXES,
    MANUAL_ONLY_PREFIXES,
    ExecutionResult,
    RemediationExecutor,
    build_manual_execution_guide,
)
from runtime.context.sensor_fusion import (
    SENSOR_CONTRACT_VERSION,
    COGNITIVE_CONTRACT_VERSION,
    GROUNDING_CONTRACT_VERSION,
)
from runtime.context.cognitive_compression import (
    COGNITIVE_CONTRACT_VERSION as COGNITIVE_CONTRACT_DIRECT,
)
from runtime.context.runtime_grounding import (
    GROUNDING_CONTRACT_VERSION as GROUNDING_CONTRACT_DIRECT,
)
from runtime.observability.drift_detector import DRIFT_DETECTOR_CONTRACT_VERSION
from runtime.observability.grafana_inventory import GRAFANA_INVENTORY_CONTRACT_VERSION


# ── Constants ──

class TestConstants:
    def test_executor_contract_version(self):
        assert EXECUTOR_CONTRACT_VERSION == "OBS-31A.5"

    def test_auto_safe_prefixes(self):
        assert "contract-" in AUTO_SAFE_PREFIXES
        assert len(AUTO_SAFE_PREFIXES) >= 1

    def test_manual_only_prefixes(self):
        for prefix in ("fake-gpu-", "stale-metric-", "orphan-ds-",
                       "unused-panels-", "broken-dash-"):
            assert prefix in MANUAL_ONLY_PREFIXES


# ── ExecutionResult ──

class TestExecutionResult:
    def test_defaults(self):
        r = ExecutionResult()
        assert r.uid == ""
        assert r.executed is False
        assert r.skipped is False
        assert r.reversible is True
        assert r.auto_fix_applied is False
        assert r.manual_steps == []
        assert r.verifications == []

    def test_to_dict(self):
        r = ExecutionResult(
            uid="test-001", title="Test item", domain="observability",
            executed=True, reason="Fixed",
            manual_steps=["step 1", "step 2"],
            verifications=["check 1"],
        )
        d = r.to_dict()
        assert d["uid"] == "test-001"
        assert d["domain"] == "observability"
        assert d["executed"] is True
        assert d["manual_steps"] == ["step 1", "step 2"]
        assert d["verifications"] == ["check 1"]

    def test_json_safe(self):
        r = ExecutionResult(uid="json-test", title="JSON", executed=True)
        json.dumps(r.to_dict())

    def test_timestamp_set(self):
        r = ExecutionResult()
        assert abs(r.timestamp - time.time()) < 2

    def test_skipped_flag(self):
        r = ExecutionResult(uid="skip-test", skipped=True, reason="Not applicable")
        assert r.skipped is True
        assert r.executed is False


# ── Contract Version Constants ──

class TestContractVersionsPresent:
    def test_sensor_contract_version(self):
        assert SENSOR_CONTRACT_VERSION == "30I-D"

    def test_cognitive_contract_version(self):
        assert COGNITIVE_CONTRACT_VERSION == "30I-F"
        assert COGNITIVE_CONTRACT_DIRECT == "30I-F"

    def test_grounding_contract_version(self):
        assert GROUNDING_CONTRACT_VERSION == "30I-G"
        assert GROUNDING_CONTRACT_DIRECT == "30I-G"

    def test_drift_detector_contract_version(self):
        assert DRIFT_DETECTOR_CONTRACT_VERSION == "OBS-31A.2"

    def test_grafana_inventory_contract_version(self):
        assert GRAFANA_INVENTORY_CONTRACT_VERSION == "OBS-31A.2"

    def test_all_contracts_match_expected_prefixes(self):
        assert SENSOR_CONTRACT_VERSION.startswith("30I-")
        assert COGNITIVE_CONTRACT_VERSION.startswith("30I-")
        assert GROUNDING_CONTRACT_VERSION.startswith("30I-")
        assert DRIFT_DETECTOR_CONTRACT_VERSION.startswith("OBS-31A.")
        assert GRAFANA_INVENTORY_CONTRACT_VERSION.startswith("OBS-31A.")


# ── Sensor Fusion Output ──

class TestSensorFusionContractVersions:
    def test_sensor_fusion_includes_cognitive(self):
        from runtime.context.sensor_fusion import RuntimeSensorFusionSnapshot
        snap = RuntimeSensorFusionSnapshot()
        d = snap.to_dict(max_chars=500)
        assert d.get("cognitive_contract_version") == "30I-F"

    def test_sensor_fusion_includes_grounding(self):
        from runtime.context.sensor_fusion import RuntimeSensorFusionSnapshot
        snap = RuntimeSensorFusionSnapshot()
        d = snap.to_dict(max_chars=500)
        assert d.get("grounding_contract_version") == "30I-G"

    def test_sensor_fusion_includes_sensor_contract(self):
        from runtime.context.sensor_fusion import RuntimeSensorFusionSnapshot
        snap = RuntimeSensorFusionSnapshot()
        d = snap.to_dict(max_chars=500)
        # The key is "sensor_contract_version", NOT "contract_version"
        assert d.get("sensor_contract_version") == "30I-D"
        # "contract_version" without prefix should NOT be in the output
        assert d.get("contract_version") is None


# ── RemediationExecutor Auto-Fix ──

class TestExecutorAutoFix:
    def test_contract_sensor_fix(self):
        executor = RemediationExecutor()
        items = [{
            "uid": "contract-sensor_version",
            "title": "Sensor contract version mismatch",
            "domain": "observability",
            "severity": "high",
            "safe_quick_win": True,
            "evidence": ["check=sensor_version", "actual=v1"],
            "recommended_action": "Fix sensor contract version",
        }]
        results = executor.execute_quick_wins(items)
        assert len(results) == 1
        r = results[0]
        assert r["executed"] is True
        assert r["skipped"] is False
        assert len(r["manual_steps"]) > 0
        assert any("sensor" in s.lower() for s in r["manual_steps"])

    def test_contract_cognitive_fix(self):
        executor = RemediationExecutor()
        items = [{
            "uid": "contract-cognitive_version",
            "title": "Cognitive contract mismatch",
            "domain": "observability",
            "safe_quick_win": True,
            "evidence": ["check=cognitive_version"],
        }]
        results = executor.execute_quick_wins(items)
        assert len(results) == 1
        r = results[0]
        assert r["executed"] is True
        assert any("cognitive" in s.lower() for s in r["manual_steps"])

    def test_contract_grounding_fix(self):
        executor = RemediationExecutor()
        items = [{
            "uid": "contract-grounding_version",
            "title": "Grounding contract mismatch",
            "domain": "observability",
            "safe_quick_win": True,
            "evidence": ["check=grounding_version"],
        }]
        results = executor.execute_quick_wins(items)
        assert len(results) == 1
        r = results[0]
        assert r["executed"] is True
        assert any("grounding" in s.lower() for s in r["manual_steps"])

    def test_contract_drift_detector_fix(self):
        executor = RemediationExecutor()
        items = [{
            "uid": "contract-drift_detector_version",
            "title": "Drift detector contract",
            "domain": "observability",
            "safe_quick_win": True,
            "evidence": ["check=drift_detector_version"],
        }]
        results = executor.execute_quick_wins(items)
        assert len(results) == 1
        r = results[0]
        assert r["executed"] is True
        assert any("drift" in s.lower() for s in r["manual_steps"])

    def test_contract_grafana_inventory_fix(self):
        executor = RemediationExecutor()
        items = [{
            "uid": "contract-grafana_inventory_version",
            "title": "Grafana inventory contract",
            "domain": "observability",
            "safe_quick_win": True,
            "evidence": ["check=grafana_inventory_version"],
        }]
        results = executor.execute_quick_wins(items)
        assert len(results) == 1
        r = results[0]
        assert r["executed"] is True
        assert any("grafana" in s.lower() for s in r["manual_steps"])

    def test_contract_unknown_fix(self):
        executor = RemediationExecutor()
        items = [{
            "uid": "contract-unknown_check",
            "title": "Unknown contract",
            "domain": "observability",
            "safe_quick_win": True,
            "evidence": ["check=unknown_check"],
            "recommended_action": "Investigate",
        }]
        results = executor.execute_quick_wins(items)
        assert len(results) == 1
        r = results[0]
        assert r["executed"] is True
        assert len(r["manual_steps"]) >= 1

    def test_auto_fix_with_verifications(self):
        executor = RemediationExecutor()
        items = [{
            "uid": "contract-sensor_version",
            "title": "Sensor version",
            "domain": "observability",
            "safe_quick_win": True,
            "evidence": ["check=sensor_version"],
        }]
        results = executor.execute_quick_wins(items)
        r = results[0]
        assert len(r["verifications"]) >= 1
        assert any("test" in v.lower() or "verify" in v.lower()
                    for v in r["verifications"])

    def test_auto_fix_not_applied_label(self):
        executor = RemediationExecutor()
        items = [{
            "uid": "contract-sensor_version",
            "title": "Sensor version",
            "domain": "observability",
            "safe_quick_win": True,
            "evidence": ["check=sensor_version"],
        }]
        results = executor.execute_quick_wins(items)
        r = results[0]
        assert r["auto_fix_applied"] is False
        assert r["executed"] is True


# ── RemediationExecutor Manual Steps ──

class TestExecutorManualSteps:
    def _make_item(self, uid: str, domain: str = "observability",
                   safe: bool = True) -> dict:
        return {
            "uid": uid,
            "title": f"Manual: {uid}",
            "domain": domain,
            "safe_quick_win": safe,
            "evidence": ["dashboard_uid=test-dash"],
            "recommended_action": "Fix it",
        }

    def test_fake_gpu_generates_grafana_steps(self):
        executor = RemediationExecutor()
        items = [self._make_item("fake-gpu-a100_utilization", "gpu")]
        results = executor.execute_quick_wins(items)
        r = results[0]
        assert r["executed"] is False
        assert r["auto_fix_applied"] is False
        steps_text = " ".join(r["manual_steps"]).lower()
        assert "grafana" in steps_text

    def test_stale_metric_generates_grafana_steps(self):
        executor = RemediationExecutor()
        items = [self._make_item("stale-metric-ai-lab-runtime", "observability")]
        results = executor.execute_quick_wins(items)
        r = results[0]
        assert r["executed"] is False
        assert "grafana" in " ".join(r["manual_steps"]).lower()

    def test_orphan_ds_generates_datasource_steps(self):
        executor = RemediationExecutor()
        items = [self._make_item("orphan-ds-unknown-99", "observability")]
        items[0]["evidence"] = ["datasource_uid=unknown-ds-99"]
        results = executor.execute_quick_wins(items)
        r = results[0]
        assert r["executed"] is False
        steps_text = " ".join(r["manual_steps"]).lower()
        assert "datasource" in steps_text or "data source" in steps_text

    def test_unused_panels_generates_panel_steps(self):
        executor = RemediationExecutor()
        items = [self._make_item("unused-panels-bulk", "observability")]
        results = executor.execute_quick_wins(items)
        r = results[0]
        assert r["executed"] is False
        steps_text = " ".join(r["manual_steps"]).lower()
        assert "panel" in steps_text

    def test_broken_dash_generates_manual_steps(self):
        executor = RemediationExecutor()
        items = [self._make_item("broken-dash-ai-lab-runtime", "observability")]
        results = executor.execute_quick_wins(items)
        r = results[0]
        assert r["executed"] is False
        assert r["reason"] == "Manual intervention required (Grafana/Infra)"

    def test_unknown_uid_falls_back(self):
        executor = RemediationExecutor()
        items = [self._make_item("something-else", "observability")]
        results = executor.execute_quick_wins(items)
        r = results[0]
        assert r["executed"] is False
        assert len(r["manual_steps"]) >= 1


# ── Execution Summary ──

class TestExecutionSummary:
    def test_empty_executor_summary(self):
        executor = RemediationExecutor()
        s = executor.get_execution_summary()
        assert s["contract_version"] == "OBS-31A.5"
        assert s["total_items"] == 0
        assert s["executed"] == 0
        assert s["skipped"] == 0

    def test_summary_after_execution(self):
        executor = RemediationExecutor()
        items = [
            {"uid": "contract-sensor", "title": "A", "domain": "obs",
             "safe_quick_win": True, "evidence": ["check=sensor"]},
            {"uid": "fake-gpu-x", "title": "B", "domain": "gpu",
             "safe_quick_win": True, "evidence": []},
        ]
        executor.execute_quick_wins(items)
        s = executor.get_execution_summary()
        assert s["total_items"] == 2
        assert s["executed"] == 1  # only contract- is auto
        assert s["auto_fix_applied"] == 0  # none are truly auto-applied
        assert s["manual_intervention_required"] == 1

    def test_summary_skips_non_safe_items(self):
        executor = RemediationExecutor()
        items = [
            {"uid": "contract-x", "title": "A", "domain": "obs",
             "safe_quick_win": False, "evidence": []},
        ]
        executor.execute_quick_wins(items)
        s = executor.get_execution_summary()
        assert s["total_items"] == 0  # filtered out

    def test_summary_json_safe(self):
        executor = RemediationExecutor()
        executor.execute_quick_wins([
            {"uid": "contract-x", "title": "T", "domain": "obs",
             "safe_quick_win": True, "evidence": ["check=x"]},
        ])
        json.dumps(executor.get_execution_summary())


# ── build_manual_execution_guide ──

class TestManualExecutionGuide:
    def test_guide_generates_markdown(self):
        items = [
            {"uid": "contract-sensor", "title": "Sensor fix",
             "domain": "obs", "safe_quick_win": True,
             "evidence": ["check=sensor"], "recommended_action": "Fix"},
        ]
        guide = build_manual_execution_guide(items)
        assert isinstance(guide, str)
        assert "OBS-31A.5" in guide
        assert "Sensor fix" in guide

    def test_guide_includes_status_labels(self):
        items = [
            {"uid": "contract-sensor", "title": "A", "domain": "obs",
             "safe_quick_win": True, "evidence": ["check=sensor"]},
            {"uid": "fake-gpu-x", "title": "B", "domain": "gpu",
             "safe_quick_win": True, "evidence": []},
        ]
        guide = build_manual_execution_guide(items)
        assert "[MANUAL]" in guide or "[AUTO]" in guide
        assert "Total quick wins" in guide


# ── Non-Safe Items ──

class TestNonSafeItems:
    def test_high_risk_items_are_skipped(self):
        executor = RemediationExecutor()
        items = [
            {"uid": "runtime-alignment-critical", "title": "Critical",
             "domain": "observability", "safe_quick_win": False,
             "high_risk_change": True, "evidence": []},
        ]
        results = executor.execute_quick_wins(items)
        assert len(results) == 0

    def test_mixed_safe_and_unsafe(self):
        executor = RemediationExecutor()
        items = [
            {"uid": "contract-x", "title": "Safe", "domain": "obs",
             "safe_quick_win": True, "evidence": ["check=x"]},
            {"uid": "broken-dash-y", "title": "Unsafe", "domain": "obs",
             "safe_quick_win": False, "evidence": []},
        ]
        results = executor.execute_quick_wins(items)
        assert len(results) == 1
        assert results[0]["uid"] == "contract-x"

    def test_mixed_safe_manual_and_auto(self):
        executor = RemediationExecutor()
        items = [
            {"uid": "contract-sensor", "title": "Auto", "domain": "obs",
             "safe_quick_win": True, "evidence": ["check=sensor"]},
            {"uid": "fake-gpu-x", "title": "Manual", "domain": "gpu",
             "safe_quick_win": True, "evidence": []},
            {"uid": "broken-dash-z", "title": "Skip", "domain": "obs",
             "safe_quick_win": False, "evidence": []},
        ]
        results = executor.execute_quick_wins(items)
        assert len(results) == 2  # only safe items
        # one auto, one manual
        auto_count = sum(1 for r in results if r["executed"])
        manual_count = sum(1 for r in results if not r["executed"])
        assert auto_count == 1
        assert manual_count == 1


# ── Cross-Validate Contracts Wiring ──

class TestCrossValidateContracts:
    """Verifica que gateway/prometheus_metrics wiring es correcto."""

    def test_prometheus_targets_contract_version(self):
        from runtime.observability.prometheus_audit import (
            run_prometheus_authority_audit,
            PROMETHEUS_AUDIT_CONTRACT_VERSION,
        )
        assert PROMETHEUS_AUDIT_CONTRACT_VERSION == "OBS-31A.1"
        audit = run_prometheus_authority_audit()
        assert audit.get("contract_version") == "OBS-31A.1"

    def test_runtime_alignment_contract_version(self):
        from runtime.observability.runtime_alignment import (
            RUNTIME_ALIGNMENT_CONTRACT_VERSION,
        )
        assert RUNTIME_ALIGNMENT_CONTRACT_VERSION == "OBS-31A.3"

    def test_observability_sensor_contract_wiring(self):
        # Verify gateway uses sensor_contract_version (not contract_version)
        from runtime.context.sensor_fusion import (
            RuntimeSensorFusionSnapshot,
            SENSOR_CONTRACT_VERSION,
        )
        snap = RuntimeSensorFusionSnapshot()
        d = snap.to_dict(max_chars=500)
        assert d.get("sensor_contract_version") == SENSOR_CONTRACT_VERSION
        # Old broken key should NOT be present
        assert d.get("contract_version") is None

    def test_all_five_runtime_contracts_have_versions(self):
        contracts = {
            "sensor": SENSOR_CONTRACT_VERSION,
            "cognitive": COGNITIVE_CONTRACT_DIRECT,
            "grounding": GROUNDING_CONTRACT_DIRECT,
            "drift_detector": DRIFT_DETECTOR_CONTRACT_VERSION,
            "grafana_inventory": GRAFANA_INVENTORY_CONTRACT_VERSION,
        }
        for name, version in contracts.items():
            assert version is not None, f"{name} contract version is None"
            assert len(version) > 0, f"{name} contract version is empty"


# ── Prometheus Metrics ──

class TestPrometheusMetrics:
    def test_execution_metrics_registered(self):
        import runtime.telemetry.prometheus_metrics  # noqa: F401
        from prometheus_client.registry import REGISTRY
        names = {m.name for m in REGISTRY.collect()}
        assert "ailab_observability_execution" in names
        assert "ailab_observability_execution_auto" in names
        assert "ailab_observability_execution_manual" in names
        assert "ailab_observability_execution_time_seconds" in names

    def test_record_execution(self):
        from runtime.telemetry.prometheus_metrics import (
            record_observability_execution,
        )
        record_observability_execution("test", "executed")
        record_observability_execution("test", "manual")

    def test_record_execution_auto(self):
        from runtime.telemetry.prometheus_metrics import (
            record_observability_execution_auto,
        )
        record_observability_execution_auto("test")

    def test_record_execution_manual(self):
        from runtime.telemetry.prometheus_metrics import (
            record_observability_execution_manual,
        )
        record_observability_execution_manual("test")


# ── Edge Cases ──

class TestEdgeCases:
    def test_empty_items_list(self):
        executor = RemediationExecutor()
        results = executor.execute_quick_wins([])
        assert results == []

    def test_items_with_missing_fields(self):
        executor = RemediationExecutor()
        items = [{"uid": "contract-x"}]  # missing safe_quick_win, title, etc
        results = executor.execute_quick_wins(items)
        assert len(results) == 0  # safe_quick_win defaults to False via .get()

    def test_multiple_identical_contracts(self):
        executor = RemediationExecutor()
        items = [
            {"uid": "contract-sensor", "title": "S1", "domain": "obs",
             "safe_quick_win": True, "evidence": ["check=sensor_version"]},
            {"uid": "contract-sensor", "title": "S2", "domain": "obs",
             "safe_quick_win": True, "evidence": ["check=sensor_version"]},
        ]
        results = executor.execute_quick_wins(items)
        assert len(results) == 2

    def test_manual_item_without_evidence(self):
        executor = RemediationExecutor()
        items = [{
            "uid": "fake-gpu-test",
            "title": "Test",
            "domain": "gpu",
            "safe_quick_win": True,
        }]
        results = executor.execute_quick_wins(items)
        assert len(results) == 1
        assert results[0]["executed"] is False
        assert len(results[0]["manual_steps"]) >= 1


# ── Integration: Full Plan Through Executor ──

class TestIntegration:
    def test_remediation_plan_to_executor(self):
        from runtime.observability.remediation_planner import build_remediation_plan

        plan = build_remediation_plan(
            grafana_dashboards=[{"uid": "gpu-dash", "title": "GPU Dash",
                                 "text": "A100_utilization"}],
        )
        items = plan.get("items", [])
        assert len(items) > 0

        executor = RemediationExecutor()
        results = executor.execute_quick_wins(items)
        assert isinstance(results, list)

    def test_executor_handles_all_plan_item_types(self):
        from runtime.observability.remediation_planner import RemediationPlanner
        from runtime.observability.dashboard_validator import DashboardValidator

        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            dashboard_audit={
                "dashboards": [
                    {"uid": "d1", "health": "broken", "panels_broken": 2,
                     "panels_no_data": 1, "datasource_valid": True,
                     "datasource_uid": "prom", "deprecated": False},
                ],
                "stale_metrics": ["memory_contamination"],
                "no_data_panels": 3,
            },
            grafana_dashboards=[{"uid": "gpu-dash", "text": "A100"}],
        )
        executor = RemediationExecutor()
        results = executor.execute_quick_wins(plan.items)
        # Should not crash; results may vary based on plan contents
        assert isinstance(results, list)
        for r in results:
            assert "uid" in r
            assert "executed" in r
            assert "manual_steps" in r
