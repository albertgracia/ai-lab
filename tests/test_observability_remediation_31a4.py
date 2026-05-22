"""FASE OBS-31A.4: Observability Remediation Plan Tests."""

from __future__ import annotations

import json
import time

from runtime.observability.remediation_contracts import (
    REMEDIATION_CONTRACT_VERSION,
    RemediationSeverity,
    ProblemClass,
    RemediationPhase,
    RemediationRisk,
    RemediationItem,
    RemediationPlan,
    RemediationSummary,
    build_remediation_item,
)
from runtime.observability.remediation_planner import (
    REMEDIATION_PLANNER_CONTRACT_VERSION,
    RemediationPlanner,
    build_remediation_plan,
    classify_remediation_priority,
)


# ── Constants ──

class TestConstants:
    def test_contract_version(self):
        assert REMEDIATION_CONTRACT_VERSION == "OBS-31A.4"

    def test_planner_contract_version(self):
        assert REMEDIATION_PLANNER_CONTRACT_VERSION == "OBS-31A.4"


class TestEnums:
    def test_severity_values(self):
        assert RemediationSeverity.CRITICAL.value == "critical"
        assert RemediationSeverity.INFORMATIONAL.value == "informational"

    def test_problem_class_values(self):
        assert ProblemClass.RUNTIME_BLOCKING.value == "runtime_blocking"
        assert ProblemClass.EXPECTED_OFFLINE.value == "expected_offline"

    def test_phase_values(self):
        assert RemediationPhase.PHASE_1.value == "phase_1_safe_quick_wins"
        assert RemediationPhase.PHASE_5.value == "phase_5_governance_hardening"


# ── RemediationRisk ──

class TestRemediationRisk:
    def test_defaults(self):
        r = RemediationRisk()
        d = r.to_dict()
        assert d["severity"] == "low"
        assert d["reversible"] is True

    def test_all_fields(self):
        r = RemediationRisk(
            severity="critical", runtime_impact="high",
            operational_risk="high", change_risk="high",
            reversible=False, requires_restart=True,
        )
        d = r.to_dict()
        assert d["severity"] == "critical"
        assert d["requires_restart"] is True
        assert d["reversible"] is False

    def test_json_safe(self):
        json.dumps(RemediationRisk().to_dict())


# ── RemediationItem ──

class TestRemediationItem:
    def test_defaults(self):
        i = RemediationItem()
        assert i.uid == ""
        assert i.problem_class == "technical_debt"
        assert i.safe_quick_win is False

    def test_to_dict(self):
        i = build_remediation_item(
            uid="test-001", title="Test item",
            description="A test remediation item",
            domain="gpu", severity="high",
            problem_class="cosmetic",
            source="test", evidence=["evidence1"],
            safe_quick_win=True,
            phase="phase_1_safe_quick_wins",
            recommended_action="Fix it",
        )
        d = i.to_dict()
        assert d["uid"] == "test-001"
        assert d["domain"] == "gpu"
        assert d["severity"] == "high"
        assert d["safe_quick_win"] is True
        assert d["phase"] == "phase_1_safe_quick_wins"

    def test_to_dict_json_safe(self):
        i = build_remediation_item(uid="t1", title="t")
        json.dumps(i.to_dict())

    def test_risk_in_to_dict(self):
        i = build_remediation_item(uid="t1", title="t")
        d = i.to_dict()
        assert "risk" in d

    def test_build_remediation_item_sets_fields(self):
        i = build_remediation_item(
            uid="u1", title="Test", description="Desc",
            domain="domain", problem_class="legacy",
            severity="critical", source="src",
            evidence=["e1"], safe_quick_win=False,
            high_risk_change=True, phase="phase_5",
            owner="me", recommended_action="do it",
            runtime_dependency="dep",
        )
        assert i.uid == "u1"
        assert i.owner == "me"
        assert i.high_risk_change is True
        assert i.runtime_dependency == "dep"


# ── RemediationPlan ──

class TestRemediationPlan:
    def test_defaults(self):
        p = RemediationPlan()
        assert p.total_items == 0

    def test_to_dict(self):
        p = RemediationPlan()
        p.total_items = 10
        p.critical_count = 2
        p.quick_wins = [build_remediation_item(uid="qw1", title="Quick win")]
        p.high_risk_changes = [build_remediation_item(uid="hr1", title="High risk")]
        p.items = [build_remediation_item(uid="i1", title="Item")]
        p.phases = {"phase_1": p.quick_wins}
        d = p.to_dict()
        assert d["total_items"] == 10
        assert d["classification"]["critical"] == 2
        assert d["quick_wins"] == 1
        assert d["high_risk_changes"] == 1
        assert d["phase_summary"]["phase_1"] == 1

    def test_to_dict_json_safe(self):
        p = RemediationPlan()
        p.items = [build_remediation_item(uid="x", title="x")]
        json.dumps(p.to_dict())

    def test_contract_version(self):
        p = RemediationPlan()
        d = p.to_dict()
        assert d["contract_version"] == "OBS-31A.4"


# ── RemediationSummary ──

class TestRemediationSummary:
    def test_defaults(self):
        s = RemediationSummary()
        d = s.to_dict()
        assert d["total_findings"] == 0
        assert d["remediation_score"] == 0.0

    def test_all_fields(self):
        s = RemediationSummary(
            total_findings=25, critical_findings=3,
            legacy_dashboards=6, stale_panels=5,
            orphan_datasources=1, runtime_drift_count=7,
            estimated_complexity="high", quick_win_count=10,
            high_risk_count=2, remediation_score=65.0,
            phases_summary={"phase_1": 10, "phase_2": 5},
        )
        d = s.to_dict()
        assert d["total_findings"] == 25
        assert d["critical_findings"] == 3
        assert d["legacy_dashboards"] == 6
        assert d["remediation_score"] == 65.0
        assert d["estimated_complexity"] == "high"

    def test_json_safe(self):
        json.dumps(RemediationSummary().to_dict())


# ── classify_remediation_priority ──

class TestClassifyPriority:
    def test_critical_is_p0(self):
        i = build_remediation_item(uid="t", title="t", severity="critical")
        assert classify_remediation_priority(i) == "P0"

    def test_high_risk_change_is_p1(self):
        i = build_remediation_item(uid="t", title="t", severity="high", high_risk_change=True)
        assert classify_remediation_priority(i) == "P1"

    def test_high_no_risk_is_p2(self):
        i = build_remediation_item(uid="t", title="t", severity="high", high_risk_change=False)
        assert classify_remediation_priority(i) == "P2"

    def test_medium_is_p3(self):
        i = build_remediation_item(uid="t", title="t", severity="medium")
        assert classify_remediation_priority(i) == "P3"

    def test_low_is_p4(self):
        i = build_remediation_item(uid="t", title="t", severity="low")
        assert classify_remediation_priority(i) == "P4"

    def test_other_is_p5(self):
        i = build_remediation_item(uid="t", title="t", severity="informational")
        assert classify_remediation_priority(i) == "P5"


# ── RemediationPlanner ──

class TestRemediationPlanner:
    def test_plan_generated_empty_input(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan()
        assert plan.total_items >= 0
        assert isinstance(plan, RemediationPlan)

    def test_quick_wins_detected(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            grafana_dashboards=[{"uid": "d1", "title": "D1", "text": "Uses A100"}],
        )
        assert len(plan.quick_wins) >= 1
        assert any("fake-gpu" in i.uid for i in plan.quick_wins)

    def test_high_risk_changes_detected(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            dashboard_audit={"broken_dashboards": ["ai-lab-runtime"]},
        )
        assert len(plan.high_risk_changes) >= 1
        assert any("broken-dash" in i.uid for i in plan.high_risk_changes)

    def test_legacy_topology_detected(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            grafana_dashboards=[{"uid": "d1", "node": "node-04"}],
        )
        topo_items = [i for i in plan.items if "fake-topo" in i.uid]
        assert len(topo_items) >= 1

    def test_stale_metrics_detected(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            dashboard_audit={
                "dashboards": [{"uid": "d1", "warnings": ["memory_contamination"]}],
            },
        )
        stale_items = [i for i in plan.items if "stale-metric" in i.uid]
        assert len(stale_items) >= 1

    def test_expected_offline_not_critical(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            prometheus_targets={"expected_offline": ["ai-lab-gpu-rx7900xt"]},
        )
        offline_items = [i for i in plan.items if "expected-offline" in i.uid]
        assert len(offline_items) >= 1
        assert all(i.severity == "informational" for i in offline_items)

    def test_broken_dashboard_detected(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            dashboard_audit={"broken_dashboards": ["some-dash"]},
        )
        broken = [i for i in plan.items if "broken-dash" in i.uid]
        assert len(broken) >= 1

    def test_orphan_datasource_detected(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            dashboard_inventory=[{"uid": "d1", "datasource_uid": "unknown-ds-123"}],
        )
        orphan = [i for i in plan.items if "orphan-ds" in i.uid]
        assert len(orphan) >= 1

    def test_runtime_alignment_critical_detected(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            runtime_alignment={
                "alignment_score": 25.0,
                "alignment_level": "critical",
            },
        )
        critical = [i for i in plan.items if "runtime-alignment-critical" in i.uid]
        assert len(critical) == 1
        assert critical[0].severity == "critical"

    def test_unexpected_down_detected(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            prometheus_targets={
                "unexpected_down": [{"job": "ailab-gateway", "status": "down"}],
            },
        )
        down = [i for i in plan.items if "unexpected-down" in i.uid]
        assert len(down) >= 1

    def test_duplicate_dashboard_detected(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            dashboard_inventory=[
                {"uid": "d1", "title": "Same Title"},
                {"uid": "d2", "title": "Same Title"},
            ],
        )
        dup = [i for i in plan.items if "dup-dash" in i.uid]
        assert len(dup) >= 1

    def test_unused_panels_detected(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            dashboard_audit={"total_no_data_panels": 5},
        )
        unused = [i for i in plan.items if "unused-panels" in i.uid]
        assert len(unused) >= 1

    def test_remediation_phases_grouped(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            grafana_dashboards=[{"uid": "d1", "text": "A100"}],
        )
        phases = p.group_remediation_by_phase()
        assert "phase_1_safe_quick_wins" in phases
        assert "phase_2_runtime_alignment" in phases
        assert "phase_3_dashboard_modernization" in phases
        assert "phase_4_legacy_cleanup" in phases
        assert "phase_5_governance_hardening" in phases

    def test_remediation_risk_calculation_critical(self):
        p = RemediationPlanner()
        item = build_remediation_item(uid="t", title="t", severity="critical")
        risk = p.calculate_remediation_risk(item)
        assert risk.severity == "critical"
        assert risk.requires_restart is True
        assert risk.reversible is False

    def test_remediation_risk_calculation_low(self):
        p = RemediationPlanner()
        item = build_remediation_item(uid="t", title="t", severity="low")
        risk = p.calculate_remediation_risk(item)
        assert risk.severity == "low"
        assert risk.reversible is True

    def test_technical_debt_report(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            grafana_dashboards=[{"uid": "d1", "text": "A100"}],
        )
        debt = p.get_technical_debt_report(plan)
        assert "summary" in debt
        assert "technical_debt_items" in debt
        assert "by_domain" in debt
        assert "estimated_effort" in debt
        assert debt["contract_version"] == "OBS-31A.4"

    def test_remediation_summary(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            grafana_dashboards=[{"uid": "d1", "text": "A100"}],
        )
        summary = p.generate_remediation_summary(plan)
        assert isinstance(summary, RemediationSummary)
        assert summary.total_findings > 0
        assert "phase_1_safe_quick_wins" in summary.phases_summary

    def test_remediation_score_100_when_clean(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan()
        summary = p.generate_remediation_summary(plan)
        assert summary.remediation_score >= 90

    def test_remediation_score_lower_with_critical(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            runtime_alignment={
                "alignment_score": 20.0,
                "alignment_level": "critical",
            },
        )
        summary = p.generate_remediation_summary(plan)
        assert summary.remediation_score < 90

    def test_inconsistent_contracts_detected(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            runtime_alignment={
                "contract_alignment": {
                    "checks": [
                        {"check": "observability_version", "passed": False,
                         "severity": "critical", "actual": "OBS-30", "detail": "mismatch"},
                    ],
                },
            },
        )
        contract_items = [i for i in plan.items if "contract-" in i.uid]
        assert len(contract_items) >= 1

    def test_planner_json_safe(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            grafana_dashboards=[{"uid": "d1", "text": "A100"}],
        )
        json.dumps(plan.to_dict())

    def test_fake_gpu_remediation_generated(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            grafana_dashboards=[{"uid": "gpu-dash", "title": "GPU Dash",
                                 "panels": [{"expr": "a100_utilization"}]}],
        )
        gpu_items = [i for i in plan.items if "fake-gpu" in i.uid]
        assert len(gpu_items) >= 1

    def test_observability_remediation_score(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            dashboard_audit={"broken_dashboards": ["d1", "d2"]},
            runtime_alignment={"alignment_score": 30.0, "alignment_level": "critical"},
        )
        summary = p.generate_remediation_summary(plan)
        assert 0 <= summary.remediation_score <= 100

    def test_build_remediation_plan_function(self):
        result = build_remediation_plan(
            grafana_dashboards=[{"uid": "d1", "text": "RTX 5070"}],
        )
        assert "contract_version" in result
        assert "total_items" in result
        assert "items" in result
        assert result["contract_version"] == "OBS-31A.4"

    def test_fake_gpu_multiple_dashboards(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            grafana_dashboards=[
                {"uid": "d1", "text": "A100"},
                {"uid": "d2", "text": "H100"},
            ],
        )
        gpu_items = [i for i in plan.items if "fake-gpu" in i.uid]
        assert len(gpu_items) >= 2

    def test_no_fake_gpu_in_clean_dashboards(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            grafana_dashboards=[{"uid": "d1", "text": "RX9070 utilization"}],
        )
        gpu_items = [i for i in plan.items if "fake-gpu" in i.uid]
        assert len(gpu_items) == 0

    def test_prometheus_unexpected_down_empty(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(prometheus_targets={})
        down = [i for i in plan.items if "unexpected-down" in i.uid]
        assert len(down) == 0

    def test_duplicate_dashboard_multiple_titles(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            dashboard_inventory=[
                {"uid": "d1", "title": "A"},
                {"uid": "d2", "title": "A"},
                {"uid": "d3", "title": "B"},
                {"uid": "d4", "title": "B"},
            ],
        )
        dup = [i for i in plan.items if "dup-dash" in i.uid]
        assert len(dup) >= 2

    def test_runtime_impact_scoring(self):
        p = RemediationPlanner()
        item_critical = build_remediation_item(uid="c1", title="Critical", severity="critical")
        risk_critical = p.calculate_remediation_risk(item_critical)
        assert risk_critical.runtime_impact == "high"

        item_low = build_remediation_item(uid="l1", title="Low", severity="low")
        risk_low = p.calculate_remediation_risk(item_low)
        assert risk_low.runtime_impact == "none"

    def test_mixed_severities_classified(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            grafana_dashboards=[{"uid": "d1", "text": "A100 utilization"}],
            prometheus_targets={"expected_offline": ["rx7900xt"]},
            dashboard_audit={"broken_dashboards": ["ai-lab-overview"]},
        )
        assert plan.critical_count >= 0
        assert len(plan.quick_wins) >= 1

    def test_duplicate_uuid_not_created(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan(
            grafana_dashboards=[{"uid": "d1", "text": "A100"}],
        )
        uids = [i.uid for i in plan.items]
        assert len(uids) == len(set(uids))

    def test_summary_json_safe(self):
        p = RemediationPlanner()
        plan = p.build_remediation_plan()
        summary = p.generate_remediation_summary(plan)
        json.dumps(summary.to_dict())
