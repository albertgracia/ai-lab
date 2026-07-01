"""Tests for AI-LAB Autonomous Observability Triage (read-only layer).

Validates:
- collect_prometheus_snapshot() fail-safe
- build_observability_triage_report() schema
- severity classification
- evidence collection
- operator intent linking
- safe_to_auto_execute always false
- requires_approval logic
- next_validation_commands
"""

import json
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from runtime.observability.observability_triage import (
    collect_prometheus_snapshot,
    build_observability_triage_report,
    SAFE_TO_AUTO_EXECUTE,
    OBSERVABILITY_TRIAGE_CONTRACT_VERSION,
    _classify_triage_severity,
    _build_symptom,
    _build_evidence,
    _build_likely_causes,
    _build_impact,
    _build_recommended_actions,
    _calculate_triage_confidence,
)


class TestCollectPrometheusSnapshot(unittest.TestCase):

    @patch("runtime.observability.prometheus_audit.fetch_prometheus_targets")
    def test_all_targets_up(self, mock_fetch):
        mock_fetch.return_value = {
            "status": "ok",
            "fetch_time_ms": 42.0,
            "active": [
                {
                    "labels": {"job": "ai-lab-gateway", "instance": "192.168.1.30:8008"},
                    "health": "up",
                    "lastScrape": "2026-06-30T12:00:00Z",
                    "lastScrapeDuration": 0.015,
                    "scrapeUrl": "http://192.168.1.30:8008/metrics",
                },
                {
                    "labels": {"job": "ai-lab-router", "instance": "192.168.1.30:8083"},
                    "health": "up",
                    "lastScrape": "2026-06-30T12:00:00Z",
                    "lastScrapeDuration": 0.012,
                    "scrapeUrl": "http://192.168.1.30:8083/metrics",
                },
            ],
            "dropped": [],
        }
        result = collect_prometheus_snapshot()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["active_total"], 2)
        self.assertEqual(result["down_total"], 0)
        self.assertEqual(len(result["targets"]), 2)
        self.assertEqual(result["targets"][0]["health"], "up")

    @patch("runtime.observability.prometheus_audit.fetch_prometheus_targets")
    def test_one_target_down(self, mock_fetch):
        mock_fetch.return_value = {
            "status": "ok",
            "fetch_time_ms": 35.0,
            "active": [
                {
                    "labels": {"job": "ai-lab-gpu-rx7900xt", "instance": "192.168.1.60:9182"},
                    "health": "down",
                    "lastScrape": "",
                    "lastScrapeDuration": 0,
                    "scrapeUrl": "http://192.168.1.60:9182/metrics",
                },
                {
                    "labels": {"job": "ai-lab-gateway", "instance": "192.168.1.30:8008"},
                    "health": "up",
                    "lastScrape": "2026-06-30T12:00:00Z",
                    "lastScrapeDuration": 0.015,
                    "scrapeUrl": "http://192.168.1.30:8008/metrics",
                },
            ],
            "dropped": [],
        }
        result = collect_prometheus_snapshot()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["active_total"], 2)
        self.assertEqual(result["down_total"], 1)
        down_targets = [t for t in result["targets"] if t["health"] == "down"]
        self.assertEqual(len(down_targets), 1)
        self.assertEqual(down_targets[0]["job"], "ai-lab-gpu-rx7900xt")

    @patch("runtime.observability.prometheus_audit.fetch_prometheus_targets")
    def test_fetch_error(self, mock_fetch):
        mock_fetch.side_effect = Exception("connection refused")
        result = collect_prometheus_snapshot()
        self.assertEqual(result["status"], "error")
        self.assertIn("connection refused", result["error"])
        self.assertEqual(result["active_total"], 0)

    @patch("runtime.observability.prometheus_audit.fetch_prometheus_targets")
    def test_api_error(self, mock_fetch):
        mock_fetch.return_value = {
            "status": "error",
            "error": "api_status:error",
            "fetch_time_ms": 10.0,
            "active": [],
            "dropped": [],
        }
        result = collect_prometheus_snapshot()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["active_total"], 0)


class TestTriageReportSchema(unittest.TestCase):

    @patch("runtime.observability.prometheus_audit.fetch_prometheus_targets")
    @patch("runtime.triage.autonomous_triage.get_active_triage_incidents")
    @patch("runtime.triage.autonomous_triage.get_triage_summary")
    def test_schema_all_healthy(self, mock_summary, mock_incidents, mock_fetch):
        mock_fetch.return_value = {
            "status": "ok", "fetch_time_ms": 30.0,
            "active": [
                {"labels": {"job": "ai-lab-gateway", "instance": "1.30:8008"},
                 "health": "up", "lastScrape": "", "lastScrapeDuration": 0,
                 "scrapeUrl": "http://1.30:8008/metrics"},
            ],
            "dropped": [],
        }
        mock_incidents.return_value = []
        mock_summary.return_value = {
            "total_incidents": 0, "total_critical": 0, "total_high": 0,
            "total_warning": 0, "total_info": 0,
        }

        report = build_observability_triage_report()

        self.assertIn("triage_id", report)
        self.assertIn("timestamp", report)
        self.assertEqual(report["source"], "observability_triage")
        self.assertEqual(report["severity"], "info")
        self.assertEqual(report["status"], "healthy")
        self.assertFalse(report["safe_to_auto_execute"])
        self.assertFalse(report["requires_approval"])
        self.assertEqual(report["contract_version"], OBSERVABILITY_TRIAGE_CONTRACT_VERSION)
        self.assertIn("evidence", report)
        self.assertIn("likely_causes", report)
        self.assertIn("recommended_actions", report)
        self.assertIn("next_validation_commands", report)
        self.assertIsNone(report["operator_intent_link"])
        self.assertIn("prometheus_snapshot", report)
        self.assertIn("triage_summary", report)

    @patch("runtime.observability.prometheus_audit.fetch_prometheus_targets")
    @patch("runtime.triage.autonomous_triage.get_active_triage_incidents")
    @patch("runtime.triage.autonomous_triage.get_triage_summary")
    def test_severity_medium_with_one_down(self, mock_summary, mock_incidents, mock_fetch):
        mock_fetch.return_value = {
            "status": "ok", "fetch_time_ms": 30.0,
            "active": [
                {"labels": {"job": "ai-lab-gateway", "instance": "1.30:8008"},
                 "health": "down", "lastScrape": "", "lastScrapeDuration": 0,
                 "scrapeUrl": "http://1.30:8008/metrics"},
            ],
            "dropped": [],
        }
        mock_incidents.return_value = []
        mock_summary.return_value = {
            "total_incidents": 0, "total_critical": 0, "total_high": 0,
            "total_warning": 0, "total_info": 0,
        }

        report = build_observability_triage_report()
        self.assertEqual(report["severity"], "medium")  # 1 down, not high/critical
        self.assertFalse(report["requires_approval"])

    @patch("runtime.observability.prometheus_audit.fetch_prometheus_targets")
    @patch("runtime.triage.autonomous_triage.get_active_triage_incidents")
    @patch("runtime.triage.autonomous_triage.get_triage_summary")
    def test_severity_critical_many_targets_down(self, mock_summary, mock_incidents, mock_fetch):
        mock_fetch.return_value = {
            "status": "ok", "fetch_time_ms": 30.0,
            "active": [
                {"labels": {"job": f"svc-{i}", "instance": f"1.30:{8000+i}"},
                 "health": "down", "lastScrape": "", "lastScrapeDuration": 0,
                 "scrapeUrl": f"http://1.30:{8000+i}/metrics"}
                for i in range(5)
            ],
            "dropped": [],
        }
        mock_incidents.return_value = []
        mock_summary.return_value = {
            "total_incidents": 0, "total_critical": 0, "total_high": 0,
            "total_warning": 0, "total_info": 0,
        }

        report = build_observability_triage_report()
        self.assertEqual(report["severity"], "critical")
        self.assertTrue(report["requires_approval"])

    @patch("runtime.observability.prometheus_audit.fetch_prometheus_targets")
    @patch("runtime.triage.autonomous_triage.get_active_triage_incidents")
    @patch("runtime.triage.autonomous_triage.get_triage_summary")
    def test_operator_intent_linking(self, mock_summary, mock_incidents, mock_fetch):
        mock_fetch.return_value = {
            "status": "ok", "fetch_time_ms": 30.0,
            "active": [
                {"labels": {"job": "ai-lab-gateway", "instance": "1.30:8008"},
                 "health": "up", "lastScrape": "", "lastScrapeDuration": 0,
                 "scrapeUrl": "http://1.30:8008/metrics"},
            ],
            "dropped": [],
        }
        mock_incidents.return_value = []
        mock_summary.return_value = {
            "total_incidents": 0, "total_critical": 0, "total_high": 0,
            "total_warning": 0, "total_info": 0,
        }

        with patch(
            "runtime.operator_intent.operator_intent_reasoning.analyze_operator_intent"
        ) as mock_operator:
            mock_operator.return_value = {
                "intent": "observability_query",
                "risk": "low",
                "requires_approval": False,
                "target": "gateway",
                "recommended_action": None,
            }
            report = build_observability_triage_report(
                operator_intent_text="why is gateway slow"
            )

        self.assertIsNotNone(report["operator_intent_link"])
        self.assertEqual(
            report["operator_intent_link"]["input"], "why is gateway slow"
        )
        self.assertEqual(
            report["operator_intent_link"]["classification"], "observability_query"
        )

    @patch("runtime.observability.prometheus_audit.fetch_prometheus_targets")
    @patch("runtime.triage.autonomous_triage.get_active_triage_incidents")
    @patch("runtime.triage.autonomous_triage.get_triage_summary")
    def test_safe_to_auto_execute_always_false(self, mock_summary, mock_incidents, mock_fetch):
        mock_fetch.return_value = {
            "status": "ok", "fetch_time_ms": 30.0,
            "active": [
                {"labels": {"job": "ai-lab-gateway", "instance": "1.30:8008"},
                 "health": "up", "lastScrape": "", "lastScrapeDuration": 0,
                 "scrapeUrl": "http://1.30:8008/metrics"},
            ],
            "dropped": [],
        }
        mock_incidents.return_value = []
        mock_summary.return_value = {
            "total_incidents": 0, "total_critical": 0, "total_high": 0,
            "total_warning": 0, "total_info": 0,
        }

        report = build_observability_triage_report()
        self.assertFalse(report["safe_to_auto_execute"])
        for action in report["recommended_actions"]:
            self.assertFalse(action["safe_to_auto_execute"])

    @patch("runtime.observability.prometheus_audit.fetch_prometheus_targets")
    @patch("runtime.triage.autonomous_triage.get_active_triage_incidents")
    @patch("runtime.triage.autonomous_triage.get_triage_summary")
    def test_requires_approval_in_severity_high(self, mock_summary, mock_incidents, mock_fetch):
        mock_fetch.return_value = {
            "status": "ok", "fetch_time_ms": 30.0,
            "active": [
                {"labels": {"job": "ai-lab-gpu-rx7900xt", "instance": "1.60:9182"},
                 "health": "down", "lastScrape": "", "lastScrapeDuration": 0,
                 "scrapeUrl": "http://1.60:9182/metrics"},
                {"labels": {"job": "ai-lab-gpu-rx7900xt-metrics", "instance": "1.60:9183"},
                 "health": "down", "lastScrape": "", "lastScrapeDuration": 0,
                 "scrapeUrl": "http://1.60:9183/metrics"},
            ],
            "dropped": [],
        }
        mock_incidents.return_value = []
        mock_summary.return_value = {
            "total_incidents": 0, "total_critical": 0, "total_high": 0,
            "total_warning": 0, "total_info": 0,
        }

        report = build_observability_triage_report()
        self.assertIn(report["severity"], ("high", "medium"))
        self.assertTrue(report["requires_approval"])
        for action in report["recommended_actions"]:
            if action["action"].startswith("investigate_down_target"):
                self.assertTrue(action["requires_approval"])

    @patch("runtime.observability.prometheus_audit.fetch_prometheus_targets")
    @patch("runtime.triage.autonomous_triage.get_active_triage_incidents")
    @patch("runtime.triage.autonomous_triage.get_triage_summary")
    def test_next_validation_commands_critical(self, mock_summary, mock_incidents, mock_fetch):
        mock_fetch.return_value = {
            "status": "ok", "fetch_time_ms": 30.0,
            "active": [
                {"labels": {"job": f"svc-{i}", "instance": f"1.30:{8000+i}"},
                 "health": "down", "lastScrape": "", "lastScrapeDuration": 0,
                 "scrapeUrl": f"http://1.30:{8000+i}/metrics"}
                for i in range(5)
            ],
            "dropped": [],
        }
        mock_incidents.return_value = []
        mock_summary.return_value = {
            "total_incidents": 0, "total_critical": 0, "total_high": 0,
            "total_warning": 0, "total_info": 0,
        }

        report = build_observability_triage_report()
        self.assertEqual(report["severity"], "critical")
        cmds = report["next_validation_commands"]
        self.assertTrue(any("/runtime/triage/summary" in c for c in cmds))
        self.assertTrue(any("/slo/health" in c for c in cmds))
        self.assertTrue(any("/api/v1/alerts" in c for c in cmds))

    @patch("runtime.observability.prometheus_audit.fetch_prometheus_targets")
    @patch("runtime.triage.autonomous_triage.get_active_triage_incidents")
    @patch("runtime.triage.autonomous_triage.get_triage_summary")
    def test_evidence_includes_down_targets(self, mock_summary, mock_incidents, mock_fetch):
        mock_fetch.return_value = {
            "status": "ok", "fetch_time_ms": 30.0,
            "active": [
                {"labels": {"job": "ai-lab-gpu-rx7900xt", "instance": "1.60:9182"},
                 "health": "down", "lastScrape": "", "lastScrapeDuration": 0,
                 "scrapeUrl": "http://1.60:9182/metrics"},
                {"labels": {"job": "ai-lab-gateway", "instance": "1.30:8008"},
                 "health": "up", "lastScrape": "", "lastScrapeDuration": 0,
                 "scrapeUrl": "http://1.30:8008/metrics"},
            ],
            "dropped": [],
        }
        mock_incidents.return_value = []
        mock_summary.return_value = {
            "total_incidents": 0, "total_critical": 0, "total_high": 0,
            "total_warning": 0, "total_info": 0,
        }

        report = build_observability_triage_report()
        evidence_str = " ".join(report["evidence"])
        self.assertIn("target_down:ai-lab-gpu-rx7900xt", evidence_str)
        self.assertNotIn("target_down:ai-lab-gateway", evidence_str)

    @patch("runtime.observability.prometheus_audit.fetch_prometheus_targets")
    @patch("runtime.triage.autonomous_triage.get_active_triage_incidents")
    @patch("runtime.triage.autonomous_triage.get_triage_summary")
    def test_fail_safe_when_triage_engine_unavailable(self, mock_summary, mock_incidents, mock_fetch):
        mock_fetch.return_value = {
            "status": "ok", "fetch_time_ms": 30.0,
            "active": [
                {"labels": {"job": "ai-lab-gateway", "instance": "1.30:8008"},
                 "health": "up", "lastScrape": "", "lastScrapeDuration": 0,
                 "scrapeUrl": "http://1.30:8008/metrics"},
            ],
            "dropped": [],
        }
        mock_incidents.side_effect = ImportError("triage not available")
        mock_summary.side_effect = ImportError("triage not available")

        report = build_observability_triage_report()
        self.assertEqual(report["severity"], "info")
        self.assertIn("evidence", report)

    @patch("runtime.observability.prometheus_audit.fetch_prometheus_targets")
    @patch("runtime.triage.autonomous_triage.get_active_triage_incidents")
    @patch("runtime.triage.autonomous_triage.get_triage_summary")
    def test_triage_confidence_calculation(self, mock_summary, mock_incidents, mock_fetch):
        mock_fetch.return_value = {
            "status": "ok", "fetch_time_ms": 30.0,
            "active": [
                {"labels": {"job": "ai-lab-gateway", "instance": "1.30:8008"},
                 "health": "up", "lastScrape": "", "lastScrapeDuration": 0,
                 "scrapeUrl": "http://1.30:8008/metrics"},
            ],
            "dropped": [],
        }
        mock_incidents.return_value = []
        mock_summary.return_value = {
            "total_incidents": 0, "total_critical": 0, "total_high": 0,
            "total_warning": 0, "total_info": 0,
        }

        with patch(
            "runtime.operator_intent.operator_intent_reasoning.analyze_operator_intent"
        ) as mock_op:
            mock_op.return_value = {"intent": "observability_query"}
            report = build_observability_triage_report(
                operator_intent_text="check health"
            )

        self.assertGreaterEqual(report["confidence"], 0.5)
        self.assertLessEqual(report["confidence"], 1.0)


class TestTriageHelpers(unittest.TestCase):

    def test_classify_severity_all_up(self):
        snap = {"status": "ok", "active_total": 10, "down_total": 0}
        sev = _classify_triage_severity(snap, [])
        self.assertEqual(sev, "info")

    def test_classify_severity_one_down(self):
        snap = {"status": "ok", "active_total": 10, "down_total": 1}
        sev = _classify_triage_severity(snap, [])
        self.assertEqual(sev, "medium")

    def test_classify_severity_two_down(self):
        snap = {"status": "ok", "active_total": 10, "down_total": 2}
        sev = _classify_triage_severity(snap, [])
        self.assertEqual(sev, "high")

    def test_classify_severity_four_down(self):
        snap = {"status": "ok", "active_total": 10, "down_total": 4}
        sev = _classify_triage_severity(snap, [])
        self.assertEqual(sev, "critical")

    def test_classify_severity_fetch_error(self):
        snap = {"status": "error", "error": "connection_failed", "active_total": 0, "down_total": 0}
        sev = _classify_triage_severity(snap, [])
        self.assertEqual(sev, "high")

    def test_classify_severity_critical_incident(self):
        snap = {"status": "ok", "active_total": 10, "down_total": 0}
        incidents = [{"severity": "critical", "incident_id": "INC-001"}]
        sev = _classify_triage_severity(snap, incidents)
        self.assertEqual(sev, "critical")

    def test_classify_severity_high_incident(self):
        snap = {"status": "ok", "active_total": 10, "down_total": 0}
        incidents = [{"severity": "high", "incident_id": "INC-001"}]
        sev = _classify_triage_severity(snap, incidents)
        self.assertEqual(sev, "high")

    def test_symptom_healthy(self):
        snap = {"status": "ok", "active_total": 10, "down_total": 0}
        s = _build_symptom(snap, [], "info")
        self.assertIn("healthy", s)

    def test_symptom_down(self):
        snap = {"status": "ok", "active_total": 10, "down_total": 2}
        s = _build_symptom(snap, [], "high")
        self.assertIn("down", s)

    def test_impact_healthy(self):
        snap = {"status": "ok", "active_total": 10, "down_total": 0}
        imp = _build_impact(snap, [], "info")
        self.assertIn("routine health", imp)

    def test_impact_down(self):
        snap = {"status": "ok", "active_total": 10, "down_total": 2}
        imp = _build_impact(snap, [], "high")
        self.assertIn("Prometheus targets down", imp)

    def test_causes_include_down_target(self):
        snap = {
            "status": "ok", "active_total": 10, "down_total": 1,
            "targets": [{"job": "ai-lab-gpu-rx7900xt", "instance": "1.60:9182", "health": "down"}],
        }
        causes = _build_likely_causes([], snap)
        self.assertTrue(any("rx7900xt" in c for c in causes))

    def test_causes_include_incident_root_causes(self):
        snap = {"status": "ok", "active_total": 10, "down_total": 0, "targets": []}
        incidents = [{"probable_root_causes": ["LM Studio unavailable", "gateway unavailable"]}]
        causes = _build_likely_causes(incidents, snap)
        self.assertIn("LM Studio unavailable", causes)
        self.assertIn("gateway unavailable", causes)

    def test_confidence_base(self):
        c = _calculate_triage_confidence(
            {"status": "ok"}, [], None
        )
        self.assertGreaterEqual(c, 0.5)

    def test_confidence_with_operator(self):
        c = _calculate_triage_confidence(
            {"status": "ok"}, [], {"intent": "health_check"}
        )
        self.assertGreaterEqual(c, 0.5)

    def test_recommended_actions_empty_when_healthy(self):
        snap = {"status": "ok", "active_total": 10, "down_total": 0, "targets": [], "error": ""}
        actions = _build_recommended_actions(snap, [], "info")
        self.assertTrue(len(actions) >= 1)
        self.assertEqual(actions[0]["action"], "continue_monitoring")

    def test_recommended_actions_for_down_target(self):
        snap = {
            "status": "ok", "active_total": 10, "down_total": 1,
            "targets": [{"job": "ai-lab-gpu-rx7900xt", "instance": "1.60:9182", "health": "down"}],
            "error": "",
        }
        actions = _build_recommended_actions(snap, [], "medium")
        self.assertTrue(any("investigate_down_target" in a["action"] for a in actions))

    def test_safe_to_auto_execute_constant(self):
        self.assertFalse(SAFE_TO_AUTO_EXECUTE)

    def test_evidence_limits_at_20(self):
        snap = {
            "status": "ok", "active_total": 30, "down_total": 15,
            "targets": [{"job": f"svc-{i}", "instance": f"1.30:{i}", "health": "down"} for i in range(15)],
            "error": "",
        }
        evidence = _build_evidence(snap, [])
        self.assertLessEqual(len(evidence), 20)

    def test_report_contract_version(self):
        self.assertEqual(OBSERVABILITY_TRIAGE_CONTRACT_VERSION, "OBSERVABILITY-TRIAGE-01")


if __name__ == "__main__":
    unittest.main()
