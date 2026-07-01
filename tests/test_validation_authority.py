"""Tests for AI-LAB Validation Authority (read-only layer).

Validates:
- ALLOW decisions for read-only actions
- REQUIRE_MORE_EVIDENCE for risky actions without evidence
- REQUIRE_APPROVAL for restart/deploy/push
- BLOCK for destructive actions
- Integration with operator intent and observability triage
- safe_to_auto_execute always false
"""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from runtime.governance.validation_authority import (
    build_validation_decision,
    validate_action_request,
    SAFE_TO_AUTO_EXECUTE,
    VALIDATION_AUTHORITY_CONTRACT_VERSION,
    _action_type,
    _classify_risk,
    _classify_severity,
    assess_evidence,
    assess_rollback,
    assess_approval_requirement,
)


class TestActionClassification(unittest.TestCase):

    def test_action_type_gateway_health(self):
        t = _action_type("show gateway health")
        self.assertEqual(t, "gateway-health")

    def test_action_type_explain_route(self):
        t = _action_type("explain last route")
        self.assertEqual(t, "explain-route")

    def test_action_type_restart_gateway(self):
        t = _action_type("restart gateway")
        self.assertEqual(t, "restart-gateway")

    def test_action_type_push_code(self):
        t = _action_type("push to origin main")
        self.assertEqual(t, "push-code")

    def test_action_type_deploy(self):
        t = _action_type("deploy this change")
        self.assertEqual(t, "deploy-change")

    def test_action_type_delete_logs(self):
        t = _action_type("delete logs")
        self.assertEqual(t, "delete-logs")

    def test_action_type_disable_prometheus(self):
        t = _action_type("disable Prometheus")
        self.assertEqual(t, "disable-prometheus")

    def test_action_type_disable_slo(self):
        t = _action_type("disable SLO enforcement")
        self.assertEqual(t, "disable-slo")

    def test_action_type_reset_hard(self):
        t = _action_type("reset --hard")
        self.assertEqual(t, "reset-hard")

    def test_action_type_prepare_deploy(self):
        t = _action_type("prepare deployment plan")
        self.assertEqual(t, "prepare-deploy")

    def test_action_type_rollback(self):
        t = _action_type("generate rollback plan")
        self.assertEqual(t, "rollback-plan")

    def test_action_type_default(self):
        t = _action_type("what is the weather")
        self.assertEqual(t, "default")


class TestRiskClassification(unittest.TestCase):

    def test_low_risk_read_only(self):
        self.assertEqual(_classify_risk("gateway-health"), "low")
        self.assertEqual(_classify_risk("explain-route"), "low")

    def test_high_risk_restart_deploy(self):
        self.assertEqual(_classify_risk("restart-gateway"), "high")
        self.assertEqual(_classify_risk("deploy-change"), "high")
        self.assertEqual(_classify_risk("push-code"), "high")

    def test_critical_risk_destructive(self):
        self.assertEqual(_classify_risk("reset-hard"), "critical")
        self.assertEqual(_classify_risk("delete-logs"), "critical")
        self.assertEqual(_classify_risk("disable-prometheus"), "critical")
        self.assertEqual(_classify_risk("disable-slo"), "critical")


class TestEvidenceAssessment(unittest.TestCase):

    def test_gateway_health_no_context(self):
        found, missing = assess_evidence("gateway-health", None, None, None)
        self.assertIn("gateway_health_endpoint", found)
        self.assertEqual(missing, [])

    def test_gateway_health_with_context(self):
        found, missing = assess_evidence(
            "gateway-health",
            {"category": "FAST_STATUS"},
            {"triage_id": "TRIAGE-001"},
            None,
        )
        self.assertIn("gateway_health_endpoint", found)

    def test_restart_gateway_missing_reason(self):
        found, missing = assess_evidence("restart-gateway", None, None, None)
        self.assertIn("gateway_health_endpoint", found)
        self.assertIn("triage_status", missing)
        self.assertIn("reason_provided", missing)

    def test_push_code_missing_git_status(self):
        found, missing = assess_evidence("push-code", None, None, None)
        self.assertIn("git_status_clean", missing)
        self.assertIn("test_results", missing)

    def test_push_code_with_full_context(self):
        found, missing = assess_evidence(
            "push-code",
            {"category": "IMPLEMENTATION_REQUEST"},
            {"triage_id": "TRIAGE-001"},
            {"git_status": "clean", "tests_passing": True},
        )
        self.assertIn("git_status_clean", found)
        self.assertIn("test_results", found)
        self.assertNotIn("git_status_clean", missing)


class TestRollbackAssessment(unittest.TestCase):

    def test_read_only_no_rollback_needed(self):
        has_rb, steps = assess_rollback("gateway-health", None)
        self.assertTrue(has_rb)
        self.assertIn("no rollback needed", steps[0])

    def test_restart_gateway_auto_rollback(self):
        has_rb, steps = assess_rollback("restart-gateway", None)
        self.assertTrue(has_rb)
        self.assertTrue(len(steps) > 0)

    def test_destructive_no_rollback(self):
        has_rb, steps = assess_rollback("delete-logs", None)
        self.assertFalse(has_rb)

    def test_destructive_with_rollback(self):
        has_rb, steps = assess_rollback(
            "delete-logs",
            {"rollback_plan": ["restore from backup"]},
        )
        self.assertTrue(has_rb)
        self.assertIn("restore from backup", steps)


class TestApprovalRequirement(unittest.TestCase):

    def test_read_only_no_approval(self):
        req, level = assess_approval_requirement("gateway-health", "low", None)
        self.assertFalse(req)
        self.assertEqual(level, "none")

    def test_restart_gateway_admin_approval(self):
        req, level = assess_approval_requirement("restart-gateway", "high", None)
        self.assertTrue(req)
        self.assertEqual(level, "admin")

    def test_destructive_emergency_approval(self):
        req, level = assess_approval_requirement("reset-hard", "critical", None)
        self.assertTrue(req)
        self.assertEqual(level, "emergency")

    def test_operator_intent_approval_propagated(self):
        oi = {"requires_approval": True, "risk": "high"}
        req, level = assess_approval_requirement("deploy-change", "high", oi)
        self.assertTrue(req)

    def test_prepare_deploy_operator_approval(self):
        req, level = assess_approval_requirement("prepare-deploy", "medium", None)
        self.assertTrue(req)
        self.assertEqual(level, "operator")


class TestValidationDecision(unittest.TestCase):

    def test_gateway_health_allow(self):
        d = build_validation_decision("show gateway health")
        self.assertEqual(d["decision"], "allow")
        self.assertEqual(d["risk"], "low")
        self.assertFalse(d["requires_approval"])
        self.assertFalse(d["safe_to_auto_execute"])
        self.assertTrue(d["safe_to_execute"])

    def test_explain_route_allow(self):
        d = build_validation_decision("explain last route")
        self.assertEqual(d["decision"], "allow")

    def test_restart_gateway_missing_evidence(self):
        d = build_validation_decision("restart gateway")
        self.assertEqual(d["decision"], "require_more_evidence")
        self.assertEqual(d["risk"], "high")
        self.assertTrue(d["requires_approval"])
        self.assertEqual(d["approval_level"], "admin")
        self.assertFalse(d["safe_to_execute"])
        self.assertIn("triage_status", d["missing_evidence"])
        self.assertIn("reason_provided", d["missing_evidence"])

    def test_restart_gateway_with_full_context(self):
        d = build_validation_decision(
            "restart gateway",
            operator_intent={"category": "FAST_INFRASTRUCTURE", "risk": "high"},
            triage={"triage_id": "TRIAGE-001", "severity": "medium"},
        )
        self.assertEqual(d["decision"], "require_approval")

    def test_deploy_change_requires_approval(self):
        d = build_validation_decision("deploy this change")
        self.assertEqual(d["decision"], "require_more_evidence")
        self.assertIn("missing_evidence", d)
        self.assertTrue(len(d["missing_evidence"]) > 0)

    def test_deploy_change_with_full_context(self):
        d = build_validation_decision(
            "deploy this change",
            operator_intent={"category": "IMPLEMENTATION_REQUEST", "risk": "high"},
            triage={"triage_id": "TRIAGE-001", "severity": "info"},
            context={"git_status": "clean", "tests_passing": True, "rollback_plan": ["git revert"]},
        )
        self.assertEqual(d["decision"], "require_approval")
        self.assertEqual(d["approval_level"], "admin")
        self.assertTrue(d["has_rollback"])

    def test_push_code_requires_approval(self):
        d = build_validation_decision("push to origin main")
        self.assertEqual(d["decision"], "require_more_evidence")

    def test_push_code_with_full_context(self):
        d = build_validation_decision(
            "push to origin main",
            operator_intent={"category": "IMPLEMENTATION_REQUEST", "risk": "high"},
            triage={"triage_id": "TRIAGE-001", "severity": "info"},
            context={"git_status": "clean", "tests_passing": True, "rollback_plan": ["git revert"]},
        )
        self.assertEqual(d["decision"], "require_approval")

    def test_delete_logs_block(self):
        d = build_validation_decision("delete logs")
        self.assertEqual(d["decision"], "block")
        self.assertEqual(d["risk"], "critical")
        self.assertEqual(d["approval_level"], "emergency")
        self.assertFalse(d["safe_to_execute"])

    def test_delete_logs_with_backup(self):
        d = build_validation_decision(
            "delete logs",
            context={"backup_available": True, "log_path_confirmed": True},
        )
        self.assertEqual(d["decision"], "require_approval")

    def test_disable_prometheus_block(self):
        d = build_validation_decision("disable Prometheus")
        self.assertEqual(d["decision"], "block")
        self.assertEqual(d["risk"], "critical")

    def test_disable_slo_enforcement_block(self):
        d = build_validation_decision("disable SLO enforcement")
        self.assertEqual(d["decision"], "block")
        self.assertEqual(d["risk"], "critical")

    def test_reset_hard_block(self):
        d = build_validation_decision("reset --hard")
        self.assertEqual(d["decision"], "block")
        self.assertEqual(d["risk"], "critical")

    def test_safe_to_auto_execute_always_false(self):
        actions = [
            "show gateway health",
            "restart gateway",
            "delete logs",
            "push to origin main",
        ]
        for action in actions:
            d = build_validation_decision(action)
            self.assertFalse(
                d["safe_to_auto_execute"],
                f"safe_to_auto_execute should be false for: {action}",
            )

    def test_prepare_deploy_missing_evidence(self):
        d = build_validation_decision("prepare deployment plan")
        self.assertEqual(d["decision"], "require_more_evidence")

    def test_generate_rollback_plan(self):
        d = build_validation_decision("generate rollback plan")
        self.assertEqual(d["decision"], "require_approval")
        self.assertEqual(d["approval_level"], "operator")

    def test_default_action_low_risk(self):
        d = build_validation_decision("what is the weather")
        self.assertEqual(d["decision"], "allow")

    def test_default_action_missing_evidence(self):
        d = build_validation_decision("some random unknown action")
        self.assertEqual(d["decision"], "allow")

    def test_triage_critical_blocks_high_risk(self):
        d = build_validation_decision(
            "restart gateway",
            triage={"triage_id": "TRIAGE-001", "severity": "critical"},
        )
        self.assertEqual(d["decision"], "block")

    def test_triage_high_escalates_allow_to_approval(self):
        d = build_validation_decision(
            "show gateway health",
            triage={"triage_id": "TRIAGE-001", "severity": "high"},
        )
        self.assertEqual(d["decision"], "require_approval")

    def test_schema_has_required_fields(self):
        d = build_validation_decision("show gateway health")
        required = [
            "validation_id", "timestamp", "requested_action", "action_type",
            "operator_intent", "risk", "severity", "evidence", "missing_evidence",
            "preconditions", "validation_plan", "rollback_plan", "has_rollback",
            "expected_impact", "affected_components", "requires_approval",
            "approval_level", "safe_to_execute", "safe_to_auto_execute",
            "decision", "reason", "confidence", "next_steps", "contract_version",
        ]
        for field in required:
            self.assertIn(field, d, f"Missing field: {field}")

    def test_contract_version(self):
        self.assertEqual(
            VALIDATION_AUTHORITY_CONTRACT_VERSION,
            "VALIDATION-AUTHORITY-01",
        )

    def test_safe_to_auto_execute_constant(self):
        self.assertFalse(SAFE_TO_AUTO_EXECUTE)

    def test_validate_action_request_wrapper(self):
        d = validate_action_request("show gateway health")
        self.assertEqual(d["decision"], "allow")
        self.assertEqual(d["requested_action"], "show gateway health")

    def test_decision_has_reason(self):
        d = build_validation_decision("delete logs")
        self.assertTrue(len(d["reason"]) > 0)

    def test_decision_has_next_steps(self):
        d = build_validation_decision("delete logs")
        self.assertTrue(len(d["next_steps"]) > 0)

    def test_operator_intent_unsafe_markers_escalates(self):
        d = build_validation_decision(
            "show gateway health",
            operator_intent={
                "category": "FAST_STATUS",
                "risk": "low",
                "safety": {"unsafe_action_markers": ["rm -rf"]},
            },
        )
        self.assertEqual(d["decision"], "require_approval")

    def test_high_risk_action_with_rollback(self):
        d = build_validation_decision(
            "restart gateway",
            operator_intent={"category": "FAST_INFRASTRUCTURE", "risk": "high"},
            triage={"triage_id": "TRIAGE-001", "severity": "medium"},
            context={"rollback_plan": ["systemctl restart ailab-gateway"]},
        )
        self.assertEqual(d["decision"], "require_approval")
        self.assertTrue(d["has_rollback"])
        self.assertNotIn("triage_status", d["missing_evidence"])
        self.assertNotIn("reason_provided", d["missing_evidence"])


if __name__ == "__main__":
    unittest.main()
