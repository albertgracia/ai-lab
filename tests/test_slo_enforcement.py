"""Tests for AI-LAB SLO Enforcement (read-only layer).

Validates:
- SLO evaluation for healthy environment
- SLO evaluation with gateway/component down
- Budget and burn rate calculation
- Report schema
- No auto-remediation
"""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from runtime.governance.slo_enforcement import (
    SLO_DEFINITIONS,
    SLO_ENFORCEMENT_CONTRACT_VERSION,
    SAFE_TO_AUTO_EXECUTE,
    _evaluate_single_slo,
    _calculate_burn_rate,
    build_slo_report,
    evaluate_slos,
    collect_slo_snapshot,
)


def _healthy_snapshot():
    """Simulated healthy environment."""
    return {
        "timestamp": time.time(),
        "gateway": {
            "health": {"ok": True, "status": 200},
            "slo": {"enabled": True, "state": "active", "degradation_level": 0},
            "status": {"service": "ai-lab-openai-gateway", "status": "healthy", "uptime": 3600},
            "latency_p50_ms": 500,
            "latency_p95_ms": 3000,
            "error_rate": 2,
        },
        "router": {
            "health": {"ok": True, "status": 200},
        },
        "cognitive_health_score": 85.0,
        "cognitive_health": {"health_score": 85.0},
        "prometheus": {
            "total_targets": 10,
            "up_targets": 10,
        },
        "gpu": {"rx9070_online": True},
        "governance": {
            "operator_intent": True,
            "observability_triage": True,
            "validation_authority": True,
        },
        "live_api_ok": True,
    }


def _degraded_snapshot():
    """Simulated degraded environment."""
    return {
        "timestamp": time.time(),
        "gateway": {
            "health": {"ok": False, "status": 0, "error": "connection refused"},
            "slo": {"enabled": False, "state": "disabled", "degradation_level": 3},
            "status": None,
            "latency_p50_ms": None,
            "latency_p95_ms": None,
            "error_rate": None,
        },
        "router": {
            "health": {"ok": False, "status": 0, "error": "connection refused"},
        },
        "cognitive_health_score": 25.0,
        "cognitive_health": {"health_score": 25.0},
        "prometheus": {
            "total_targets": 10,
            "up_targets": 0,
        },
        "gpu": {"rx9070_online": False},
        "governance": {
            "operator_intent": False,
            "observability_triage": False,
            "validation_authority": False,
        },
        "live_api_ok": False,
    }


class TestSloDefinitions(unittest.TestCase):

    def test_all_slos_have_required_fields(self):
        required = {"slo_id", "component", "description", "target",
                     "warning_threshold", "critical_threshold",
                     "higher_is_better", "unit"}
        for slo in SLO_DEFINITIONS:
            with self.subTest(slo_id=slo["slo_id"]):
                for field in required:
                    self.assertIn(field, slo, f"Missing {field} in {slo['slo_id']}")

    def test_slo_ids_are_unique(self):
        ids = [s["slo_id"] for s in SLO_DEFINITIONS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_established_slos(self):
        expected = {
            "gateway_availability", "router_availability",
            "slo_endpoint_operational", "cognitive_health_score",
            "gateway_latency_p50", "gateway_latency_p95",
            "degradation_normal", "prometheus_targets_up",
            "gpu_rx9070_online", "operator_intent_operational",
            "observability_triage_operational",
            "validation_authority_operational",
            "live_api_operational",
        }
        ids = set(s["slo_id"] for s in SLO_DEFINITIONS)
        self.assertEqual(ids, expected)

    def test_contract_version(self):
        self.assertEqual(SLO_ENFORCEMENT_CONTRACT_VERSION, "SLO-ENFORCEMENT-01")

    def test_safe_to_auto_execute(self):
        self.assertFalse(SAFE_TO_AUTO_EXECUTE)


class TestSloEvaluation(unittest.TestCase):

    def test_healthy_all_pass(self):
        snap = _healthy_snapshot()
        for slo in SLO_DEFINITIONS:
            with self.subTest(slo_id=slo["slo_id"]):
                result = _evaluate_single_slo(slo, snap)
                self.assertEqual(result["status"], "pass",
                                 f"{slo['slo_id']}: expected pass, got {result['status']} (value={result['current_value']})")
                self.assertFalse(result["requires_approval"])
                self.assertFalse(result["safe_to_auto_execute"])

    def test_healthy_has_budget(self):
        snap = _healthy_snapshot()
        for slo in SLO_DEFINITIONS:
            with self.subTest(slo_id=slo["slo_id"]):
                result = _evaluate_single_slo(slo, snap)
                self.assertGreaterEqual(result["budget_remaining"], 0.0)
                self.assertLessEqual(result["budget_remaining"], 1.0)

    def test_degraded_all_critical_or_insufficient(self):
        snap = _degraded_snapshot()
        for slo in SLO_DEFINITIONS:
            with self.subTest(slo_id=slo["slo_id"]):
                result = _evaluate_single_slo(slo, snap)
                self.assertIn(
                    result["status"],
                    ("critical", "insufficient_data"),
                    f"{slo['slo_id']}: expected critical or insufficient_data, got {result['status']}",
                )

    def test_degraded_requires_approval(self):
        snap = _degraded_snapshot()
        for slo in SLO_DEFINITIONS:
            with self.subTest(slo_id=slo["slo_id"]):
                result = _evaluate_single_slo(slo, snap)
                if result["status"] == "critical":
                    self.assertTrue(result["requires_approval"],
                                    f"{slo['slo_id']}: critical should require approval")
                if result["status"] == "insufficient_data":
                    self.assertFalse(result["requires_approval"])

    def test_each_slo_has_evidence(self):
        snap = _healthy_snapshot()
        for slo in SLO_DEFINITIONS:
            with self.subTest(slo_id=slo["slo_id"]):
                result = _evaluate_single_slo(slo, snap)
                self.assertTrue(len(result["evidence"]) > 0,
                                f"{slo['slo_id']}: should have evidence")

    def test_each_slo_has_recommendation(self):
        snap = _healthy_snapshot()
        for slo in SLO_DEFINITIONS:
            with self.subTest(slo_id=slo["slo_id"]):
                result = _evaluate_single_slo(slo, snap)
                self.assertTrue(len(result["recommendation"]) > 0)

    def test_partial_gateway_down_other_up(self):
        snap = _healthy_snapshot()
        snap["gateway"]["health"]["ok"] = False
        snap["gateway"]["health"]["error"] = "timeout"
        snap["cognitive_health_score"] = None
        snap["gateway"]["latency_p50_ms"] = None
        snap["gateway"]["latency_p95_ms"] = None

        results = {s["slo_id"]: _evaluate_single_slo(s, snap) for s in SLO_DEFINITIONS}
        self.assertEqual(results["gateway_availability"]["status"], "critical")
        self.assertEqual(results["gateway_latency_p50"]["status"], "insufficient_data")
        self.assertEqual(results["router_availability"]["status"], "pass")
        self.assertEqual(results["gpu_rx9070_online"]["status"], "pass")
        self.assertEqual(results["operator_intent_operational"]["status"], "pass")

    def test_prometheus_all_down(self):
        snap = _healthy_snapshot()
        snap["prometheus"]["up_targets"] = 0
        result = _evaluate_single_slo(
            [s for s in SLO_DEFINITIONS if s["slo_id"] == "prometheus_targets_up"][0],
            snap,
        )
        self.assertEqual(result["status"], "critical")
        self.assertEqual(result["current_value"], 0.0)

    def test_gpu_offline(self):
        snap = _healthy_snapshot()
        snap["gpu"]["rx9070_online"] = False
        result = _evaluate_single_slo(
            [s for s in SLO_DEFINITIONS if s["slo_id"] == "gpu_rx9070_online"][0],
            snap,
        )
        self.assertEqual(result["status"], "critical")
        self.assertEqual(result["current_value"], 0.0)


class TestBurnRate(unittest.TestCase):

    def test_all_pass_zero_burn(self):
        evals = [
            {"status": "pass", "slo_id": "a"},
            {"status": "pass", "slo_id": "b"},
        ]
        b = _calculate_burn_rate(evals)
        self.assertEqual(b["burn_rate"], 0.0)
        self.assertEqual(b["critical"], 0)
        self.assertEqual(b["warning"], 0)

    def test_mixed_burn_rate(self):
        evals = [
            {"status": "pass", "slo_id": "a"},
            {"status": "critical", "slo_id": "b"},
            {"status": "warning", "slo_id": "c"},
            {"status": "insufficient_data", "slo_id": "d"},
        ]
        b = _calculate_burn_rate(evals)
        self.assertEqual(b["total_slos"], 4)
        self.assertEqual(b["pass"], 1)
        self.assertEqual(b["warning"], 1)
        self.assertEqual(b["critical"], 1)
        self.assertEqual(b["insufficient_data"], 1)

    def test_healthy_ratio(self):
        evals = [{"status": "pass", "slo_id": f"s{i}"} for i in range(8)]
        evals.append({"status": "critical", "slo_id": "bad"})
        b = _calculate_burn_rate(evals)
        self.assertEqual(b["total_slos"], 9)
        self.assertAlmostEqual(b["healthy_ratio"], 8 / 9, places=4)

    def test_has_required_fields(self):
        evals = [{"status": "pass", "slo_id": "a"}]
        b = _calculate_burn_rate(evals)
        required = {"total_slos", "pass", "warning", "critical",
                     "insufficient_data", "healthy_ratio", "critical_ratio",
                     "burn_rate", "budget_remaining", "timestamp"}
        for field in required:
            self.assertIn(field, b, f"Missing field: {field}")


class TestSloReport(unittest.TestCase):

    def test_report_schema_with_healthy_snapshot(self):
        from runtime.governance.slo_enforcement import build_slo_report
        original = build_slo_report.__globals__.get("_collect_slo_snapshot", collect_slo_snapshot)

        try:
            import runtime.governance.slo_enforcement as se
            se.collect_slo_snapshot = _healthy_snapshot

            report = build_slo_report()
            self.assertEqual(report["overall_status"], "pass")
            self.assertEqual(report["overall_severity"], "info")
            self.assertFalse(report["requires_approval"])
            self.assertFalse(report["safe_to_auto_execute"])
            self.assertEqual(report["contract_version"], "SLO-ENFORCEMENT-01")
            self.assertEqual(len(report["critical_slos"]), 0)
            self.assertEqual(len(report["warning_slos"]), 0)
            self.assertTrue(len(report["slos"]) > 0)
            self.assertEqual(report["budget"]["critical"], 0)
        finally:
            se.collect_slo_snapshot = original

    def test_report_schema_with_degraded_snapshot(self):
        import runtime.governance.slo_enforcement as se
        original = se.collect_slo_snapshot

        try:
            se.collect_slo_snapshot = _degraded_snapshot

            report = build_slo_report()
            self.assertEqual(report["overall_status"], "critical")
            self.assertEqual(report["overall_severity"], "critical")
            self.assertTrue(report["requires_approval"])
            self.assertTrue(len(report["critical_slos"]) > 0)
            self.assertTrue(len(report["recommendations"]) > 0)
        finally:
            se.collect_slo_snapshot = original

    def test_report_has_required_fields(self):
        import runtime.governance.slo_enforcement as se
        original = se.collect_slo_snapshot

        try:
            se.collect_slo_snapshot = _healthy_snapshot
            report = build_slo_report()
            required = {
                "report_id", "timestamp", "overall_status", "overall_severity",
                "contract_version", "evaluation_window_seconds",
                "snapshot", "slos", "budget",
                "critical_slos", "warning_slos", "recommendations",
                "requires_approval", "safe_to_auto_execute",
            }
            for field in required:
                self.assertIn(field, report, f"Missing field: {field}")
        finally:
            se.collect_slo_snapshot = original

    def test_no_auto_remediation_in_report(self):
        import runtime.governance.slo_enforcement as se
        original = se.collect_slo_snapshot

        try:
            se.collect_slo_snapshot = _healthy_snapshot
            report = build_slo_report()
            self.assertFalse(report["safe_to_auto_execute"])
        finally:
            se.collect_slo_snapshot = original


class TestEvaluateSlos(unittest.TestCase):

    def test_evaluate_slos_returns_list(self):
        snap = _healthy_snapshot()
        results = evaluate_slos(snapshot=snap)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), len(SLO_DEFINITIONS))

    def test_evaluate_slos_no_snapshot_calls_collect(self):
        import runtime.governance.slo_enforcement as se
        original = se.collect_slo_snapshot

        try:
            se.collect_slo_snapshot = _healthy_snapshot
            results = evaluate_slos()
            self.assertEqual(len(results), len(SLO_DEFINITIONS))
        finally:
            se.collect_slo_snapshot = original


class TestSchema(unittest.TestCase):

    def test_single_slo_schema(self):
        snap = _healthy_snapshot()
        for slo in SLO_DEFINITIONS:
            with self.subTest(slo_id=slo["slo_id"]):
                result = _evaluate_single_slo(slo, snap)
                required = {
                    "slo_id", "component", "objective", "current_value",
                    "target", "status", "severity", "unit",
                    "budget_remaining", "burn_rate", "confidence",
                    "evidence", "recommendation",
                    "requires_approval", "safe_to_auto_execute",
                }
                for field in required:
                    self.assertIn(field, result, f"{slo['slo_id']}: missing {field}")

    def test_confidence_range(self):
        snap = _healthy_snapshot()
        for slo in SLO_DEFINITIONS:
            with self.subTest(slo_id=slo["slo_id"]):
                result = _evaluate_single_slo(slo, snap)
                self.assertGreaterEqual(result["confidence"], 0.0)
                self.assertLessEqual(result["confidence"], 1.0)


if __name__ == "__main__":
    unittest.main()
