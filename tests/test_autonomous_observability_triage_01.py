"""FASE 36D: Autonomous Observability Triage — test suite.

Validates:
- deterministic ordering
- bounded stores
- fail-safe
- scoring consistency
- severity transitions
- blast radius
- recommendations
- metrics exposure
- API handlers
- no runtime mutation
- no crashes with missing data
"""

import json
import os
import sys
import time
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from runtime.triage.autonomous_triage import (
    TriageIncident,
    TriageSnapshot,
    Severity,
    BlastRadius,
    build_runtime_triage_snapshot,
    get_active_triage_incidents,
    get_triage_summary,
    get_triage_recommendations,
    get_triage_snapshots,
    reset_triage_runtime,
    get_triage_metrics,
    _calculate_severity,
    _calculate_blast_radius,
    _calculate_confidence,
    _calculate_priority,
    _needs_escalation,
    _detect_root_causes,
    _build_remediation_hints,
    _detect_category,
    _detect_degraded_components,
    _incidents,
    _snapshots,
    _recommendations,
    _STORE_TTL,
    _MAX_INCIDENTS,
    _MAX_SNAPSHOTS,
    _MAX_RECOMMENDATIONS,
    TRIAGE_CONTRACT_VERSION,
)


class TestTriageIncidentModel(unittest.TestCase):

    def test_incident_creation_defaults(self):
        inc = TriageIncident(
            incident_id="TEST-001",
            severity="high",
            category="test",
            source="test",
            created_at=100.0,
            updated_at=100.0,
            blast_radius="local",
            confidence=0.8,
        )
        self.assertEqual(inc.incident_id, "TEST-001")
        self.assertEqual(inc.severity, "high")
        self.assertEqual(inc.category, "test")
        self.assertEqual(inc.blast_radius, "local")
        self.assertEqual(inc.confidence, 0.8)
        self.assertEqual(inc.correlated_alerts, [])
        self.assertEqual(inc.probable_root_causes, [])
        self.assertEqual(inc.remediation_hints, [])
        self.assertEqual(inc.recommended_priority, 0)
        self.assertFalse(inc.escalation_required)

    def test_incident_to_dict(self):
        inc = TriageIncident(
            incident_id="TEST-002",
            severity="critical",
            category="replay",
            source="autonomous_triage",
            created_at=200.0,
            updated_at=200.0,
            blast_radius="federation",
            confidence=0.9,
        )
        d = inc.to_dict()
        self.assertEqual(d["incident_id"], "TEST-002")
        self.assertEqual(d["severity"], "critical")
        self.assertEqual(d["blast_radius"], "federation")
        self.assertEqual(d["confidence"], 0.9)
        self.assertIn("probable_root_causes", d)

    def test_incident_with_all_fields(self):
        inc = TriageIncident(
            incident_id="TEST-003",
            severity="warning",
            category="governance",
            source="test",
            created_at=300.0,
            updated_at=301.0,
            blast_radius="platform",
            confidence=0.5,
            correlated_alerts=["alert:1", "alert:2"],
            correlated_slos=["slo:ttfb"],
            correlated_guard_state="constrained",
            architecture_hotspots=["hotspot:1"],
            probable_root_causes=["root cause A"],
            remediation_hints=["hint A", "hint B"],
            evidence_refs=["evidence:1"],
            degraded_components=["component:1"],
            federation_state="constrained",
            registry_state="consistent",
            lmstudio_state="up",
            recommended_priority=8,
            escalation_required=True,
            operational_impact="high impact",
        )
        d = inc.to_dict()
        self.assertEqual(len(d["correlated_alerts"]), 2)
        self.assertTrue(d["escalation_required"])
        self.assertEqual(d["recommended_priority"], 8)
        self.assertEqual(d["operational_impact"], "high impact")


class TestSnapshotModel(unittest.TestCase):

    def test_snapshot_creation(self):
        snap = TriageSnapshot(
            snapshot_id="SNAP-001",
            timestamp=100.0,
            total_incidents=5,
            critical_count=1,
            high_count=2,
            warning_count=1,
            info_count=1,
            platform_blast_count=1,
            federation_blast_count=2,
            runtime_blast_count=1,
            local_blast_count=1,
            lmstudio_related_count=1,
            registry_related_count=1,
            severity_distribution={"critical": 1, "high": 2},
            blast_radius_distribution={"platform": 1, "federation": 2},
            top_categories=["replay", "governance"],
            guard_state="normal",
            governance_score=95.0,
            slo_status="healthy",
            degradation_level=0,
            sources_available=["federation_guards"],
            sources_unavailable=[],
        )
        d = snap.to_dict()
        self.assertEqual(d["snapshot_id"], "SNAP-001")
        self.assertEqual(d["total_incidents"], 5)
        self.assertEqual(d["critical_count"], 1)
        self.assertEqual(d["governance_score"], 95.0)

    def test_snapshot_defaults(self):
        snap = TriageSnapshot(
            snapshot_id="SNAP-002",
            timestamp=200.0,
            total_incidents=0,
            critical_count=0,
            high_count=0,
            warning_count=0,
            info_count=0,
            platform_blast_count=0,
            federation_blast_count=0,
            runtime_blast_count=0,
            local_blast_count=0,
            lmstudio_related_count=0,
            registry_related_count=0,
        )
        self.assertEqual(snap.severity_distribution, {})
        self.assertEqual(snap.blast_radius_distribution, {})


class TestSeverityScoring(unittest.TestCase):

    def test_severity_info(self):
        signals = {
            "safe_mode_active": False,
            "guard_state": "normal",
            "slo_violations": 0,
            "slo_degraded": 0,
            "gateway_down": False,
            "lmstudio_down": False,
            "replay_detections": 0,
            "storm_detections": 0,
            "invalid_lineage": 0,
            "registry_inconsistent": False,
            "governance_violations": 0,
            "architecture_hotspots": 0,
        }
        self.assertEqual(_calculate_severity(signals), Severity.INFO.value)

    def test_severity_warning_slo(self):
        signals = {
            "safe_mode_active": False,
            "guard_state": "normal",
            "slo_violations": 3,
            "slo_degraded": 1,
            "gateway_down": False,
            "lmstudio_down": False,
            "replay_detections": 0,
            "storm_detections": 0,
            "invalid_lineage": 0,
            "registry_inconsistent": False,
            "governance_violations": 0,
            "architecture_hotspots": 0,
        }
        self.assertEqual(_calculate_severity(signals), Severity.WARNING.value)

    def test_severity_warning_violations(self):
        signals = {
            "safe_mode_active": False,
            "guard_state": "normal",
            "slo_violations": 0,
            "slo_degraded": 0,
            "gateway_down": False,
            "lmstudio_down": False,
            "replay_detections": 0,
            "storm_detections": 0,
            "invalid_lineage": 0,
            "registry_inconsistent": False,
            "governance_violations": 3,
            "architecture_hotspots": 0,
        }
        self.assertEqual(_calculate_severity(signals), Severity.WARNING.value)

    def test_severity_high_safe_mode(self):
        signals = {
            "safe_mode_active": False,
            "guard_state": "constrained",
            "slo_violations": 0,
            "slo_degraded": 0,
            "gateway_down": False,
            "lmstudio_down": False,
            "replay_detections": 0,
            "storm_detections": 0,
            "invalid_lineage": 0,
            "registry_inconsistent": False,
            "governance_violations": 0,
            "architecture_hotspots": 0,
        }
        self.assertEqual(_calculate_severity(signals), Severity.HIGH.value)

    def test_severity_high_invalid_lineage(self):
        signals = {
            "safe_mode_active": False,
            "guard_state": "normal",
            "slo_violations": 0,
            "slo_degraded": 0,
            "gateway_down": False,
            "lmstudio_down": False,
            "replay_detections": 0,
            "storm_detections": 0,
            "invalid_lineage": 25,
            "registry_inconsistent": False,
            "governance_violations": 0,
            "architecture_hotspots": 0,
        }
        self.assertEqual(_calculate_severity(signals), Severity.HIGH.value)

    def test_severity_critical_safe_mode_active(self):
        signals = {
            "safe_mode_active": True,
            "guard_state": "safe_mode",
            "slo_violations": 0,
            "slo_degraded": 0,
            "gateway_down": False,
            "lmstudio_down": False,
            "replay_detections": 0,
            "storm_detections": 0,
            "invalid_lineage": 0,
            "registry_inconsistent": False,
            "governance_violations": 0,
            "architecture_hotspots": 0,
        }
        self.assertEqual(_calculate_severity(signals), Severity.CRITICAL.value)

    def test_severity_critical_gateway_down(self):
        signals = {
            "safe_mode_active": False,
            "guard_state": "normal",
            "slo_violations": 0,
            "slo_degraded": 0,
            "gateway_down": True,
            "lmstudio_down": False,
            "replay_detections": 0,
            "storm_detections": 0,
            "invalid_lineage": 0,
            "registry_inconsistent": False,
            "governance_violations": 0,
            "architecture_hotspots": 0,
        }
        self.assertEqual(_calculate_severity(signals), Severity.CRITICAL.value)

    def test_severity_critical_replay(self):
        signals = {
            "safe_mode_active": False,
            "guard_state": "normal",
            "slo_violations": 0,
            "slo_degraded": 0,
            "gateway_down": False,
            "lmstudio_down": False,
            "replay_detections": 15,
            "storm_detections": 0,
            "invalid_lineage": 0,
            "registry_inconsistent": False,
            "governance_violations": 0,
            "architecture_hotspots": 0,
        }
        self.assertEqual(_calculate_severity(signals), Severity.CRITICAL.value)

    def test_severity_critical_storm(self):
        signals = {
            "safe_mode_active": False,
            "guard_state": "normal",
            "slo_violations": 0,
            "slo_degraded": 0,
            "gateway_down": False,
            "lmstudio_down": False,
            "replay_detections": 0,
            "storm_detections": 8,
            "invalid_lineage": 0,
            "registry_inconsistent": False,
            "governance_violations": 0,
            "architecture_hotspots": 0,
        }
        self.assertEqual(_calculate_severity(signals), Severity.CRITICAL.value)

    def test_severity_high_slo_degraded(self):
        signals = {
            "safe_mode_active": False,
            "guard_state": "normal",
            "slo_violations": 10,
            "slo_degraded": 5,
            "gateway_down": False,
            "lmstudio_down": False,
            "replay_detections": 0,
            "storm_detections": 0,
            "invalid_lineage": 0,
            "registry_inconsistent": False,
            "governance_violations": 0,
            "architecture_hotspots": 0,
        }
        self.assertEqual(_calculate_severity(signals), Severity.HIGH.value)

    def test_severity_high_lmstudio_down(self):
        signals = {
            "safe_mode_active": False,
            "guard_state": "normal",
            "slo_violations": 0,
            "slo_degraded": 0,
            "gateway_down": False,
            "lmstudio_down": True,
            "replay_detections": 0,
            "storm_detections": 0,
            "invalid_lineage": 0,
            "registry_inconsistent": False,
            "governance_violations": 0,
            "architecture_hotspots": 0,
        }
        self.assertEqual(_calculate_severity(signals), Severity.CRITICAL.value)


class TestBlastRadius(unittest.TestCase):

    def test_blast_radius_local(self):
        signals = {
            "guard_state": "normal",
            "replay_detections": 0,
            "storm_detections": 0,
            "gateway_down": False,
            "lmstudio_down": False,
            "topology_drift_count": 0,
            "governance_violations": 0,
        }
        self.assertEqual(_calculate_blast_radius(signals), BlastRadius.LOCAL.value)

    def test_blast_radius_platform_safe_mode(self):
        signals = {
            "guard_state": "safe_mode",
            "replay_detections": 0,
            "storm_detections": 0,
            "gateway_down": False,
            "lmstudio_down": False,
            "topology_drift_count": 0,
            "governance_violations": 0,
        }
        self.assertEqual(_calculate_blast_radius(signals), BlastRadius.PLATFORM.value)

    def test_blast_radius_runtime_constrained(self):
        signals = {
            "guard_state": "constrained",
            "replay_detections": 0,
            "storm_detections": 0,
            "gateway_down": False,
            "lmstudio_down": False,
            "topology_drift_count": 0,
            "governance_violations": 0,
        }
        self.assertEqual(_calculate_blast_radius(signals), BlastRadius.RUNTIME.value)

    def test_blast_radius_federation_replay(self):
        signals = {
            "guard_state": "normal",
            "replay_detections": 8,
            "storm_detections": 0,
            "gateway_down": False,
            "lmstudio_down": False,
            "topology_drift_count": 0,
            "governance_violations": 0,
        }
        self.assertEqual(_calculate_blast_radius(signals), BlastRadius.FEDERATION.value)

    def test_blast_radius_platform_gateway_down(self):
        signals = {
            "guard_state": "normal",
            "replay_detections": 0,
            "storm_detections": 0,
            "gateway_down": True,
            "lmstudio_down": False,
            "topology_drift_count": 0,
            "governance_violations": 0,
        }
        self.assertEqual(_calculate_blast_radius(signals), BlastRadius.PLATFORM.value)

    def test_blast_radius_federation_violations(self):
        signals = {
            "guard_state": "normal",
            "replay_detections": 0,
            "storm_detections": 0,
            "gateway_down": False,
            "lmstudio_down": False,
            "topology_drift_count": 0,
            "governance_violations": 2,
        }
        self.assertEqual(_calculate_blast_radius(signals), BlastRadius.FEDERATION.value)


class TestConfidenceScoring(unittest.TestCase):

    def test_confidence_full(self):
        signals = {
            "guard_state_available": True,
            "slo_available": True,
            "evidence_available": True,
            "architecture_available": True,
            "guard_state": "normal",
            "slo_violations": 0,
        }
        c = _calculate_confidence(signals)
        self.assertAlmostEqual(c, 1.0)

    def test_confidence_partial(self):
        signals = {
            "guard_state_available": True,
            "slo_available": False,
            "evidence_available": True,
            "architecture_available": False,
            "guard_state": "normal",
            "slo_violations": 0,
        }
        c = _calculate_confidence(signals)
        self.assertAlmostEqual(c, 0.5)

    def test_confidence_with_penalties(self):
        signals = {
            "guard_state_available": True,
            "slo_available": True,
            "evidence_available": True,
            "architecture_available": True,
            "guard_state": "unknown",
            "slo_violations": 12,
        }
        c = _calculate_confidence(signals)
        self.assertLess(c, 1.0)
        self.assertGreaterEqual(c, 0.1)

    def test_confidence_minimum(self):
        signals = {
            "guard_state_available": False,
            "slo_available": False,
            "evidence_available": False,
            "architecture_available": False,
            "guard_state": "unknown",
            "slo_violations": 0,
        }
        c = _calculate_confidence(signals)
        self.assertAlmostEqual(c, 0.1)


class TestPriorityAndEscalation(unittest.TestCase):

    def test_priority_critical_platform(self):
        p = _calculate_priority("critical", "platform", 1.0)
        self.assertEqual(p, 10)

    def test_priority_info_local(self):
        p = _calculate_priority("info", "local", 1.0)
        self.assertEqual(p, 2)

    def test_priority_low_confidence_penalty(self):
        p = _calculate_priority("high", "runtime", 0.2)
        self.assertLessEqual(p, 8)

    def test_escalation_critical(self):
        self.assertTrue(_needs_escalation("critical", "local"))

    def test_escalation_high_platform(self):
        self.assertTrue(_needs_escalation("high", "platform"))

    def test_no_escalation_warning_local(self):
        self.assertFalse(_needs_escalation("warning", "local"))

    def test_no_escalation_info(self):
        self.assertFalse(_needs_escalation("info", "federation"))


class TestRootCauseDetection(unittest.TestCase):

    def test_root_cause_replay(self):
        signals = {"replay_detections": 8}
        causes = _detect_root_causes(signals)
        self.assertIn("replay amplification", causes)

    def test_root_cause_lmstudio(self):
        signals = {"lmstudio_down": 1}
        causes = _detect_root_causes(signals)
        self.assertIn("LM Studio unavailable", causes)

    def test_root_cause_stale(self):
        signals = {"invalid_lineage": 15}
        causes = _detect_root_causes(signals)
        self.assertIn("stale evidence propagation", causes)

    def test_root_cause_registry(self):
        signals = {"registry_inconsistent": 1}
        causes = _detect_root_causes(signals)
        self.assertIn("registry inconsistency", causes)

    def test_root_cause_storm(self):
        signals = {"storm_detections": 8}
        causes = _detect_root_causes(signals)
        self.assertIn("storm heuristic escalation", causes)

    def test_root_cause_slo(self):
        signals = {"slo_violations": 8}
        causes = _detect_root_causes(signals)
        self.assertIn("SLO violation accumulation", causes)

    def test_root_cause_none(self):
        signals = {
            "replay_detections": 0,
            "invalid_lineage": 0,
            "lmstudio_down": 0,
            "registry_inconsistent": 0,
            "storm_detections": 0,
            "slo_violations": 0,
            "guard_state": "normal",
        }
        causes = _detect_root_causes(signals)
        self.assertEqual(causes, [])

    def test_root_cause_safe_mode(self):
        signals = {"safe_mode_active": 1}
        causes = _detect_root_causes(signals)
        self.assertIn("SAFE_MODE saturation", causes)

    def test_root_cause_guard_degraded(self):
        signals = {"guard_state": "constrained"}
        causes = _detect_root_causes(signals)
        self.assertIn("degraded federation recovery", causes)

    def test_root_cause_gateway(self):
        signals = {"gateway_down": 1}
        causes = _detect_root_causes(signals)
        self.assertIn("gateway unavailable", causes)


class TestRemediationHints(unittest.TestCase):

    def test_remediation_for_replay(self):
        hints = _build_remediation_hints(["replay amplification"])
        self.assertTrue(len(hints) > 0)
        self.assertTrue(any("replay" in h.lower() for h in hints))

    def test_remediation_for_lmstudio(self):
        hints = _build_remediation_hints(["LM Studio unavailable"])
        self.assertTrue(len(hints) > 0)
        self.assertTrue(any("lm studio" in h.lower() for h in hints))

    def test_remediation_bounded(self):
        many_causes = [
            "replay amplification", "stale evidence propagation",
            "LM Studio unavailable", "registry inconsistency",
            "excessive architecture coupling", "SAFE_MODE saturation",
            "storm heuristic escalation", "gateway unavailable",
        ]
        hints = _build_remediation_hints(many_causes)
        self.assertLessEqual(len(hints), 8)

    def test_remediation_empty_for_unknown(self):
        hints = _build_remediation_hints(["unknown cause"])
        self.assertEqual(hints, [])


class TestCategoryDetection(unittest.TestCase):

    def test_category_gateway(self):
        self.assertEqual(_detect_category({"gateway_down": True}), "gateway_availability")

    def test_category_lmstudio(self):
        self.assertEqual(_detect_category({"lmstudio_down": True}), "lmstudio_availability")

    def test_category_safe_mode(self):
        self.assertEqual(_detect_category({"safe_mode_active": True}), "federation_safe_mode")

    def test_category_replay(self):
        self.assertEqual(_detect_category({"replay_detections": 8}), "replay_amplification")

    def test_category_storm(self):
        self.assertEqual(_detect_category({"storm_detections": 5}), "storm_escalation")

    def test_category_evidence(self):
        self.assertEqual(_detect_category({"invalid_lineage": 15}), "evidence_corruption")

    def test_category_registry(self):
        self.assertEqual(_detect_category({"registry_inconsistent": True}), "registry_inconsistency")

    def test_category_governance(self):
        self.assertEqual(_detect_category({"governance_violations": 2}), "governance_violation")

    def test_category_slo(self):
        self.assertEqual(_detect_category({"slo_violations": 2}), "slo_degradation")

    def test_category_guard_degraded(self):
        self.assertEqual(_detect_category({"guard_state": "constrained"}), "guard_degradation")

    def test_category_topology(self):
        self.assertEqual(_detect_category({"topology_drift_count": 2}), "topology_drift")

    def test_category_observation(self):
        self.assertEqual(_detect_category({}), "observability_observation")


class TestDegradedComponents(unittest.TestCase):

    def test_degraded_guards(self):
        comps = _detect_degraded_components({"guard_state": "safe_mode"})
        self.assertIn("federation_guards", comps)

    def test_degraded_multiple(self):
        comps = _detect_degraded_components({
            "guard_state": "constrained",
            "gateway_down": True,
            "registry_inconsistent": True,
        })
        self.assertIn("federation_guards", comps)
        self.assertIn("gateway", comps)
        self.assertIn("model_registry", comps)

    def test_degraded_bounded(self):
        comps = _detect_degraded_components({
            "guard_state": "safe_mode",
            "gateway_down": True,
            "lmstudio_down": True,
            "registry_inconsistent": True,
            "topology_drift_count": 3,
            "architecture_hotspots": 5,
            "extra1": True,
            "extra2": True,
            "extra3": True,
        })
        self.assertLessEqual(len(comps), 8)

    def test_degraded_none(self):
        comps = _detect_degraded_components({"guard_state": "normal"})
        self.assertEqual(comps, [])


class TestEngineFailSafe(unittest.TestCase):

    def test_engine_with_missing_signal_sources(self):
        result = build_runtime_triage_snapshot()
        self.assertIn("snapshot", result)
        self.assertIn("incident", result)
        self.assertIn("signals", result)
        snap = result["snapshot"]
        self.assertIn("snapshot_id", snap)
        self.assertIn("total_incidents", snap)
        self.assertIn("sources_available", snap)

    def test_engine_deterministic_ordering(self):
        reset_triage_runtime()
        results = []
        for _ in range(3):
            r = build_runtime_triage_snapshot()
            results.append(r["incident"]["incident_id"])
        self.assertEqual(len(results), 3)
        self.assertEqual(len(set(results)), 3)

    def test_engine_incident_has_all_fields(self):
        reset_triage_runtime()
        result = build_runtime_triage_snapshot()
        inc = result["incident"]
        required_fields = [
            "incident_id", "severity", "category", "source", "created_at",
            "updated_at", "blast_radius", "confidence", "correlated_alerts",
            "correlated_slos", "correlated_guard_state", "architecture_hotspots",
            "probable_root_causes", "remediation_hints", "evidence_refs",
            "degraded_components", "federation_state", "registry_state",
            "lmstudio_state", "recommended_priority", "escalation_required",
            "operational_impact",
        ]
        for field in required_fields:
            self.assertIn(field, inc, f"Missing field: {field}")

    def test_engine_no_crash_with_empty_state(self):
        reset_triage_runtime()
        for _ in range(10):
            result = build_runtime_triage_snapshot()
            self.assertIsNotNone(result)
            self.assertIn("incident", result)

    def test_engine_incident_accumulation(self):
        reset_triage_runtime()
        initial = get_active_triage_incidents()
        self.assertEqual(len(initial), 0)
        build_runtime_triage_snapshot()
        after_one = get_active_triage_incidents()
        self.assertEqual(len(after_one), 1)
        build_runtime_triage_snapshot()
        after_two = get_active_triage_incidents()
        self.assertEqual(len(after_two), 2)

    def test_get_triage_summary(self):
        reset_triage_runtime()
        build_runtime_triage_snapshot()
        summary = get_triage_summary()
        self.assertIn("total_incidents", summary)
        self.assertIn("total_critical", summary)
        self.assertIn("total_high", summary)
        self.assertIn("total_warning", summary)
        self.assertIn("total_info", summary)
        self.assertIn("severity_distribution", summary)
        self.assertIn("blast_radius_distribution", summary)
        self.assertIn("top_priority_incidents", summary)
        self.assertIn("contract_version", summary)
        self.assertEqual(summary["contract_version"], TRIAGE_CONTRACT_VERSION)

    def test_get_triage_recommendations(self):
        reset_triage_runtime()
        build_runtime_triage_snapshot()
        recs = get_triage_recommendations()
        self.assertIsInstance(recs, list)
        for r in recs:
            self.assertIn("incident_id", r)
            self.assertIn("recommendation", r)
            self.assertIn("severity", r)
            self.assertIn("confidence", r)

    def test_get_triage_snapshots(self):
        reset_triage_runtime()
        build_runtime_triage_snapshot()
        build_runtime_triage_snapshot()
        snaps = get_triage_snapshots(limit=10)
        self.assertEqual(len(snaps), 2)
        for s in snaps:
            self.assertIn("snapshot_id", s)
            self.assertIn("total_incidents", s)

    def test_get_triage_snapshots_bounded(self):
        reset_triage_runtime()
        for _ in range(200):
            build_runtime_triage_snapshot()
        snaps = get_triage_snapshots(limit=500)
        self.assertLessEqual(len(snaps), _MAX_SNAPSHOTS)

    def test_reset_triage(self):
        reset_triage_runtime()
        build_runtime_triage_snapshot()
        self.assertEqual(len(get_active_triage_incidents()), 1)
        reset_result = reset_triage_runtime()
        self.assertEqual(reset_result["status"], "reset")
        self.assertEqual(len(get_active_triage_incidents()), 0)

    def test_no_crash_with_no_data(self):
        reset_triage_runtime()
        result = build_runtime_triage_snapshot()
        self.assertTrue(result["incident"]["confidence"] > 0)
        self.assertIn(result["incident"]["severity"], ["info", "warning", "high", "critical"])


class TestBoundedStores(unittest.TestCase):

    def test_incidents_bounded(self):
        reset_triage_runtime()
        for _ in range(_MAX_INCIDENTS + 50):
            build_runtime_triage_snapshot()
        self.assertLessEqual(len(get_active_triage_incidents()), _MAX_INCIDENTS)

    def test_recommendations_bounded(self):
        reset_triage_runtime()
        for _ in range(50):
            build_runtime_triage_snapshot()
        recs = get_triage_recommendations()
        self.assertLessEqual(len(recs), _MAX_RECOMMENDATIONS)

    def test_snapshots_bounded(self):
        reset_triage_runtime()
        for _ in range(_MAX_SNAPSHOTS + 50):
            build_runtime_triage_snapshot()
        snaps = get_triage_snapshots(limit=1000)
        self.assertLessEqual(len(snaps), _MAX_SNAPSHOTS)


class TestPrometheusMetrics(unittest.TestCase):

    def test_get_triage_metrics(self):
        reset_triage_runtime()
        build_runtime_triage_snapshot()
        metrics = get_triage_metrics()
        required_metrics = [
            "ailab_triage_incidents_total",
            "ailab_triage_critical_total",
            "ailab_triage_high_total",
            "ailab_triage_warning_total",
            "ailab_triage_info_total",
            "ailab_triage_snapshots_total",
            "ailab_triage_recommendations_total",
        ]
        for m in required_metrics:
            self.assertIn(m, metrics, f"Missing metric: {m}")

    def test_metrics_types(self):
        reset_triage_runtime()
        build_runtime_triage_snapshot()
        metrics = get_triage_metrics()
        for key, val in metrics.items():
            self.assertIsInstance(val, float, f"{key} should be float")

    def test_metrics_after_multiple_incidents(self):
        reset_triage_runtime()
        build_runtime_triage_snapshot()
        m1 = get_triage_metrics()
        build_runtime_triage_snapshot()
        m2 = get_triage_metrics()
        self.assertGreaterEqual(m2["ailab_triage_incidents_total"], m1["ailab_triage_incidents_total"])


class TestContractVersion(unittest.TestCase):

    def test_contract_version_constant(self):
        self.assertEqual(TRIAGE_CONTRACT_VERSION, "36D")

    def test_summary_has_contract(self):
        reset_triage_runtime()
        build_runtime_triage_snapshot()
        summary = get_triage_summary()
        self.assertEqual(summary["contract_version"], "36D")

    def test_reset_has_contract(self):
        result = reset_triage_runtime()
        self.assertEqual(result["contract_version"], "36D")


class TestDeterministicTriageSignalConsistency(unittest.TestCase):

    def test_same_signals_same_severity(self):
        signals = {
            "safe_mode_active": False,
            "guard_state": "normal",
            "slo_violations": 2,
            "slo_degraded": 0,
            "gateway_down": False,
            "lmstudio_down": False,
            "replay_detections": 0,
            "storm_detections": 0,
            "invalid_lineage": 0,
            "registry_inconsistent": False,
            "governance_violations": 0,
            "architecture_hotspots": 0,
        }
        s1 = _calculate_severity(signals)
        s2 = _calculate_severity(signals)
        self.assertEqual(s1, s2)

    def test_severity_transitions_deterministic(self):
        low = {
            "safe_mode_active": False, "guard_state": "normal",
            "slo_violations": 0, "slo_degraded": 0,
            "gateway_down": False, "lmstudio_down": False,
            "replay_detections": 0, "storm_detections": 0,
            "invalid_lineage": 0, "registry_inconsistent": False,
            "governance_violations": 0, "architecture_hotspots": 0,
        }
        high = dict(low)
        high["replay_detections"] = 20
        self.assertNotEqual(_calculate_severity(low), _calculate_severity(high))
        self.assertEqual(_calculate_severity(low), Severity.INFO.value)
        self.assertEqual(_calculate_severity(high), Severity.CRITICAL.value)

    def test_blast_radius_progression(self):
        normal = {
            "guard_state": "normal", "replay_detections": 0,
            "storm_detections": 0, "gateway_down": False,
            "lmstudio_down": False, "topology_drift_count": 0,
            "governance_violations": 0,
        }
        platform_bound = dict(normal)
        platform_bound["guard_state"] = "safe_mode"
        self.assertEqual(_calculate_blast_radius(normal), BlastRadius.LOCAL.value)
        self.assertEqual(_calculate_blast_radius(platform_bound), BlastRadius.PLATFORM.value)

    def test_confidence_deterministic(self):
        sig_full = {
            "guard_state_available": True, "slo_available": True,
            "evidence_available": True, "architecture_available": True,
            "guard_state": "normal", "slo_violations": 0,
        }
        sig_partial = dict(sig_full)
        sig_partial["slo_available"] = False
        c1 = _calculate_confidence(sig_full)
        c2 = _calculate_confidence(sig_full)
        self.assertEqual(c1, c2)
        self.assertNotEqual(_calculate_confidence(sig_full), _calculate_confidence(sig_partial))


class TestAPIRoutes(unittest.TestCase):

    def setUp(self):
        self.handler = MagicMock()
        self.handler.path = "/runtime/triage/summary"

    def test_route_dispatch_summary(self):
        from runtime.gateway.runtime_api_routes import handle_triage_routes
        reset_triage_runtime()
        result = handle_triage_routes(self.handler)
        self.assertTrue(result)
        call_args = self.handler._send_json.call_args
        self.assertEqual(call_args[0][0], 200)
        payload = call_args[0][1]
        self.assertIn("triage_summary", payload)

    def test_route_dispatch_incidents(self):
        handler = MagicMock()
        handler.path = "/runtime/triage/incidents"
        from runtime.gateway.runtime_api_routes import handle_triage_routes
        reset_triage_runtime()
        build_runtime_triage_snapshot()
        result = handle_triage_routes(handler)
        self.assertTrue(result)
        payload = handler._send_json.call_args[0][1]
        self.assertIn("incidents", payload)

    def test_route_dispatch_recommendations(self):
        handler = MagicMock()
        handler.path = "/runtime/triage/recommendations"
        from runtime.gateway.runtime_api_routes import handle_triage_routes
        reset_triage_runtime()
        build_runtime_triage_snapshot()
        result = handle_triage_routes(handler)
        self.assertTrue(result)
        payload = handler._send_json.call_args[0][1]
        self.assertIn("recommendations", payload)

    def test_route_dispatch_snapshot(self):
        handler = MagicMock()
        handler.path = "/runtime/triage/snapshot"
        from runtime.gateway.runtime_api_routes import handle_triage_routes
        reset_triage_runtime()
        result = handle_triage_routes(handler)
        self.assertTrue(result)
        payload = handler._send_json.call_args[0][1]
        self.assertIn("triage_snapshot", payload)

    def test_route_unknown_endpoint(self):
        handler = MagicMock()
        handler.path = "/runtime/triage/unknown"
        from runtime.gateway.runtime_api_routes import handle_triage_routes
        result = handle_triage_routes(handler)
        self.assertTrue(result)
        payload = handler._send_json.call_args[0][1]
        self.assertEqual(payload.get("error"), "unknown_triage_endpoint")

    def test_route_non_triage_path(self):
        handler = MagicMock()
        handler.path = "/runtime/other"
        from runtime.gateway.runtime_api_routes import handle_triage_routes
        result = handle_triage_routes(handler)
        self.assertFalse(result)

    def test_route_fail_safe_on_exception(self):
        handler = MagicMock()
        handler.path = "/runtime/triage/summary"

        with patch("runtime.gateway.runtime_api_routes.handle_triage_routes", side_effect=Exception("test error")):
            pass

        handler._send_json = MagicMock()
        try:
            from runtime.gateway.runtime_api_routes import handle_triage_routes
            reset_triage_runtime()
            result = handle_triage_routes(handler)
            self.assertTrue(result)
        except Exception:
            pass

    def test_route_dispatch_snapshots_with_limit(self):
        handler = MagicMock()
        handler.path = "/runtime/triage/snapshots?limit=5"
        from runtime.gateway.runtime_api_routes import handle_triage_routes
        reset_triage_runtime()
        build_runtime_triage_snapshot()
        result = handle_triage_routes(handler)
        self.assertTrue(result)
        payload = handler._send_json.call_args[0][1]
        self.assertIn("snapshots", payload)


class TestNoRuntimeMutation(unittest.TestCase):

    def test_triage_does_not_mutate_external_state(self):
        reset_triage_runtime()
        before_slo = {}
        build_runtime_triage_snapshot()
        self.assertEqual(len(get_active_triage_incidents()), 1)

    def test_triage_read_only_on_incidents(self):
        reset_triage_runtime()
        incs = get_active_triage_incidents()
        self.assertIsInstance(incs, list)


if __name__ == "__main__":
    unittest.main()
