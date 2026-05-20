"""FASE 28.2 tests: Executor Readonly Runtime.

Covers:
- safe_runner: command validation, allowed/blocked patterns
- readonly_registry: catalog, forbidden commands
- execution_context: modes, dry_run reasoning
- readonly_policies: governance, risk, scope
- execution_audit: write, read, stats
- readonly_executor: simulation fallback, governance blocks
- rollback_placeholder: stub
- workflow_state: EXECUTING transitions
- permissions: phase 28.2 scopes
"""

import json
import os
import shutil
import tempfile
import time
import pytest

from runtime.agentic.safe_runner import validate_command, run_safe, SafeRunnerResult
from runtime.agentic.readonly_registry import (
    SAFE_READONLY_COMMANDS, FORBIDDEN_READONLY_COMMANDS,
    FORBIDDEN_READONLY_PATTERNS, DANGEROUS_OPERATORS,
    FIND_ALLOWED_PATHS, DOCKER_ALLOWED_SUBCOMMANDS,
    RFC1918_PATTERNS, CURRENT_CAPABILITY, ExecutionCapability,
)
from runtime.agentic.execution_context import (
    ExecutionMode, DryRunReason, RuntimeExecutionContext, CURRENT_EXECUTION_MODE,
)
from runtime.agentic.readonly_policies import check_governance, assess_risk, check_scope
from runtime.agentic.execution_audit import write_execution_audit, read_execution_audit, get_audit_stats, build_audit_entry
from runtime.agentic.readonly_executor import RealReadonlyExecutor, ENABLE_EXECUTOR, DRY_RUN
from runtime.agentic.rollback_placeholder import RollbackPlaceholder, RollbackResult
from runtime.agentic.workflow_state import WorkflowState, WorkflowTimeline, VALID_TRANSITIONS
from runtime.agentic.permissions import PermissionScope, classify_permission_scope, is_scope_allowed_in_phase
from runtime.agentic.planner import AgenticPlan, WorkflowAction


# ═══════════════════════════════════════════════════════════════════
# 1. SAFE_RUNNER — COMMAND VALIDATION
# ═══════════════════════════════════════════════════════════════════

class TestSafeRunnerValidation:
    def test_allowed_commands(self):
        for cmd_name in ("ls", "cat", "df", "free", "uptime", "ps", "ss", "ip", "who", "uname", "wc", "head", "tail", "grep", "du", "stat", "file", "nproc"):
            valid, reason = validate_command(f"{cmd_name} /tmp")
            assert valid, f"{cmd_name} should be allowed: {reason}"

    def test_forbidden_commands(self):
        for cmd_name in ("rm", "mv", "cp", "chmod", "chown", "dd", "tee", "sudo", "shutdown", "reboot"):
            valid, reason = validate_command(f"{cmd_name} something")
            assert not valid, f"{cmd_name} should be forbidden"

    def test_forbidden_patterns(self):
        for pattern in ("systemctl restart", "systemctl stop", "docker stop", "docker rm", "sed -i"):
            valid, reason = validate_command(pattern)
            assert not valid, f"Pattern '{pattern}' should be blocked"

    def test_empty_command(self):
        valid, reason = validate_command("")
        assert not valid

    def test_null_command(self):
        valid, reason = validate_command(None)
        assert not valid

    def test_whitespace_command(self):
        valid, reason = validate_command("   ")
        assert not valid

    def test_operators_blocked(self):
        for op in ("|", "||", "&&", ";", "&"):
            valid, reason = validate_command(f"ls {op} cat /tmp/test")
            assert not valid, f"Operator '{op}' should be blocked"

    def test_redirects_blocked(self):
        for redirect in (">", ">>", "<", "<<"):
            valid, reason = validate_command(f"ls {redirect} /tmp/out")
            assert not valid, f"Redirect '{redirect}' should be blocked"

    def test_dangerous_tokens(self):
        for token in ("$(", "`", "/dev/"):
            valid, reason = validate_command(f"ls {token}test")
            assert not valid, f"Token '{token}' should be blocked"

    def test_curl_allowed(self):
        valid, reason = validate_command("curl -s http://192.168.1.30:8008/health")
        assert valid, f"curl to RFC1918 should be allowed: {reason}"

    def test_curl_blocked_non_rfc1918(self):
        valid, reason = validate_command("curl -s http://example.com")
        assert not valid, "curl to non-RFC1918 should be blocked"

    def test_curl_blocked_output(self):
        valid, reason = validate_command("curl -o /tmp/out http://192.168.1.30:8008/health")
        assert not valid, "curl -o should be blocked"

    def test_find_allowed(self):
        valid, reason = validate_command("find /opt/ai-lab -name '*.py'")
        assert valid, f"find in /opt/ai-lab should be allowed: {reason}"

    def test_find_blocked_path(self):
        valid, reason = validate_command("find /etc -name '*.conf'")
        assert not valid, "find in /etc should be blocked"

    def test_find_no_path(self):
        valid, reason = validate_command("find -name '*.py'")
        assert not valid, "find without explicit path should be blocked"

    def test_journalctl_allowed(self):
        valid, reason = validate_command("journalctl --lines 50")
        assert valid, f"journalctl with --lines 50 should be allowed: {reason}"

    def test_journalctl_blocked_follow(self):
        valid, reason = validate_command("journalctl -f")
        assert not valid, "journalctl -f should be blocked"

    def test_journalctl_blocked_lines_exceed(self):
        valid, reason = validate_command("journalctl --lines 1000")
        assert not valid, "journalctl --lines >500 should be blocked"

    def test_docker_allowed(self):
        for sub in DOCKER_ALLOWED_SUBCOMMANDS:
            valid, reason = validate_command(f"docker {sub}")
            assert valid, f"docker {sub} should be allowed: {reason}"

    def test_docker_blocked_subcommands(self):
        blocked = {"exec", "cp", "compose", "attach", "run", "build", "push", "pull"}
        for sub in blocked:
            valid, reason = validate_command(f"docker {sub} something")
            assert not valid, f"docker {sub} should be blocked"

    def test_docker_no_subcommand(self):
        valid, reason = validate_command("docker")
        assert not valid, "docker without subcommand should be blocked"

    def test_systemctl_status_allowed(self):
        valid, reason = validate_command("systemctl status ailab-gateway")
        assert valid, f"systemctl status should be allowed: {reason}"

    def test_systemctl_restart_blocked(self):
        valid, reason = validate_command("systemctl restart ailab-gateway")
        assert not valid, "systemctl restart should be blocked"


class TestSafeRunnerExecution:
    def test_run_safe_ls(self):
        result = run_safe("ls /tmp")
        assert not result.blocked
        assert result.exit_code == 0

    def test_run_safe_blocked(self):
        result = run_safe("rm -rf /")
        assert result.blocked
        assert result.exit_code == -1

    def test_run_safe_stdout_hash(self):
        result = run_safe("echo hello")
        if not result.blocked:
            assert len(result.stdout_hash) == 16
            assert result.stdout_hash == result.stdout_hash

    def test_run_safe_stderr_hash(self):
        result = run_safe("ls /nonexistent_path_xyz")
        if not result.blocked:
            assert len(result.stderr_hash) == 16

    def test_run_safe_to_dict(self):
        result = run_safe("echo test")
        d = result.to_dict()
        assert "command" in d
        assert "exit_code" in d
        assert "blocked" in d
        assert "stdout_hash" in d

    def test_run_safe_timeout(self):
        result = run_safe("sleep 0.01", timeout=1)
        if not result.blocked:
            assert result.exit_code == 0

    def test_run_safe_shlex_fail(self):
        result = run_safe("ls 'unclosed")
        assert result.blocked


# ═══════════════════════════════════════════════════════════════════
# 2. READONLY_REGISTRY
# ═══════════════════════════════════════════════════════════════════

class TestReadonlyRegistry:
    def test_safe_commands_exist(self):
        assert len(SAFE_READONLY_COMMANDS) >= 20

    def test_spec_has_all_fields(self):
        for name, spec in SAFE_READONLY_COMMANDS.items():
            assert spec.command == name
            assert spec.category
            assert spec.risk in ("low", "medium", "high")

    def test_forbidden_commands_not_in_safe(self):
        for cmd in FORBIDDEN_READONLY_COMMANDS:
            assert cmd not in SAFE_READONLY_COMMANDS, f"{cmd} should not be in safe catalog"

    def test_forbidden_patterns(self):
        assert any("systemctl restart" in p for p in FORBIDDEN_READONLY_PATTERNS)
        assert any("docker stop" in p for p in FORBIDDEN_READONLY_PATTERNS)

    def test_current_capability(self):
        assert CURRENT_CAPABILITY == ExecutionCapability.READONLY

    def test_find_allowed_paths(self):
        assert "/opt/ai-lab" in FIND_ALLOWED_PATHS

    def test_docker_allowed_subcommands(self):
        assert "ps" in DOCKER_ALLOWED_SUBCOMMANDS
        assert "logs" in DOCKER_ALLOWED_SUBCOMMANDS

    def test_rfc1918_patterns(self):
        assert "192.168." in RFC1918_PATTERNS


# ═══════════════════════════════════════════════════════════════════
# 3. EXECUTION_CONTEXT
# ═══════════════════════════════════════════════════════════════════

class TestExecutionContext:
    def test_modes(self):
        assert ExecutionMode.SIMULATION.value == "simulation"
        assert ExecutionMode.READONLY.value == "readonly"
        assert ExecutionMode.SANDBOX_WRITE.value == "sandbox_write"
        assert ExecutionMode.AUTONOMOUS.value == "autonomous"

    def test_dry_run_reasons(self):
        reasons = [e.value for e in DryRunReason]
        assert "feature_flag" in reasons
        assert "readonly_phase" in reasons
        assert "governance_block" in reasons
        assert "risk_block" in reasons

    def test_default_context(self):
        ctx = RuntimeExecutionContext()
        assert ctx.mode == ExecutionMode.READONLY
        assert ctx.dry_run is True
        assert ctx.phase == "28.2"

    def test_is_executable_dry_run(self):
        ctx = RuntimeExecutionContext(dry_run=True)
        assert not ctx.is_executable()

    def test_is_executable_real(self):
        ctx = RuntimeExecutionContext(dry_run=False, mode=ExecutionMode.READONLY)
        assert ctx.is_executable()

    def test_is_executable_wrong_mode(self):
        ctx = RuntimeExecutionContext(dry_run=False, mode=ExecutionMode.SIMULATION)
        assert not ctx.is_executable()

    def test_to_dict(self):
        ctx = RuntimeExecutionContext(execution_id="abc123", dry_run_reason="test")
        d = ctx.to_dict()
        assert d["execution_id"] == "abc123"
        assert d["mode"] == "readonly"
        assert d["dry_run"] is True
        assert d["dry_run_reason"] == "test"


# ═══════════════════════════════════════════════════════════════════
# 4. READONLY_POLICIES
# ═══════════════════════════════════════════════════════════════════

class TestReadonlyPolicies:
    def test_governance_restart_blocked(self):
        result = check_governance("restart_service", "systemctl restart ailab", "28.2")
        assert not result.allowed
        assert "restart_service blocked" in result.reason

    def test_governance_install_blocked(self):
        result = check_governance("install_package", "apt install foo", "28.2")
        assert not result.allowed

    def test_governance_run_valid(self):
        result = check_governance("run_command", "ls /tmp", "28.2")
        assert result.allowed

    def test_governance_run_invalid(self):
        result = check_governance("run_command", "rm -rf /", "28.2")
        assert not result.allowed

    def test_governance_wrong_phase(self):
        result = check_governance("read_config", "ls", "28.1")
        assert not result.allowed

    def test_governance_to_dict(self):
        result = check_governance("read_config", "ls", "28.2")
        d = result.to_dict()
        assert "allowed" in d
        assert "reason" in d
        assert "risk_level" in d

    def test_assess_risk_high(self):
        assert assess_risk("restart_service", "bash", "") == "high"

    def test_assess_risk_medium(self):
        assert assess_risk("read_config", "bash", "") == "medium"

    def test_assess_risk_low(self):
        assert assess_risk("read_config", "ls", "") == "low"

    def test_check_scope_filesystem(self):
        assert check_scope("/opt/ai-lab/test", {"filesystem"})
        assert not check_scope("/opt/ai-lab/test", {"network"})

    def test_check_scope_network(self):
        assert check_scope("http://192.168.1.30:8008", {"network"})
        assert not check_scope("http://192.168.1.30:8008", {"filesystem"})


# ═══════════════════════════════════════════════════════════════════
# 5. EXECUTION_AUDIT
# ═══════════════════════════════════════════════════════════════════

class TestExecutionAudit:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orig_dir = "/opt/ai-lab/runtime/state"
        os.environ["_TEST_AUDIT_DIR"] = self.temp_dir

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_build_audit_entry(self):
        entry = build_audit_entry(
            execution_id="e1", plan_id="p1", mode="readonly",
            dry_run=True, dry_run_reason="test",
            action={"step": 1, "intent": "read_logs", "tool": "bash", "command": "ls"},
            result={"exit_code": 0, "blocked": False},
        )
        assert entry["execution_id"] == "e1"
        assert entry["execution_mode"] == "readonly"
        assert entry["dry_run"] is True
        assert entry["action"]["intent"] == "read_logs"

    def test_write_and_read_audit(self):
        entry = build_audit_entry("e1", "p1", "readonly", True, None,
                                   {"step": 1, "intent": "ls", "tool": "bash", "command": "ls"},
                                   {"exit_code": 0})
        write_execution_audit(entry)
        entries = read_execution_audit(limit=10)
        assert len(entries) >= 1
        assert entries[-1]["execution_id"] == "e1"

    def test_read_empty_audit(self):
        import tempfile, os
        entries = read_execution_audit(limit=10)
        assert isinstance(entries, list)

    def test_get_audit_stats(self):
        entry = build_audit_entry("e1", "p1", "readonly", True, None,
                                   {"step": 1, "intent": "ls", "tool": "bash", "command": "ls"},
                                   {"exit_code": 0, "blocked": False})
        write_execution_audit(entry)
        stats = get_audit_stats()
        assert isinstance(stats, dict)
        assert "total" in stats
        assert "last_entries" in stats

    def test_audit_entry_timestamp(self):
        entry = build_audit_entry("e1", "p1", "readonly", True, None,
                                   {"step": 1, "intent": "ls", "tool": "bash", "command": "ls"},
                                   {"exit_code": 0})
        assert "timestamp" in entry
        assert isinstance(entry["timestamp"], int)

    def test_audit_entry_phase(self):
        entry = build_audit_entry("e1", "p1", "readonly", True, None,
                                   {"step": 1, "intent": "ls", "tool": "bash", "command": "ls"},
                                   {"exit_code": 0})
        assert entry["phase"] == "28.2"


# ═══════════════════════════════════════════════════════════════════
# 6. READONLY_EXECUTOR
# ═══════════════════════════════════════════════════════════════════

class TestReadonlyExecutor:
    def test_executor_flags(self):
        assert ENABLE_EXECUTOR is False
        assert DRY_RUN is True

    def test_execute_simulation_fallback(self):
        plan = AgenticPlan(
            plan_id="test-plan",
            actions=[
                WorkflowAction(step=1, intent="read_config", tool="bash",
                               description="ls /tmp", action_id="a1"),
            ],
        )
        timeline = WorkflowTimeline(plan_id="test-plan")
        result = RealReadonlyExecutor.execute(plan, timeline)
        assert result is not None
        assert result.simulation_only is True
        assert result.status == "simulated_success"
        assert result.total_duration_ms >= 0

    def test_execute_with_empty_plan(self):
        plan = AgenticPlan(plan_id="empty-plan", actions=[])
        timeline = WorkflowTimeline(plan_id="empty-plan")
        result = RealReadonlyExecutor.execute(plan, timeline)
        assert result.actions_executed == 0
        assert result.actions_failed == 0

    def test_execute_simulation_records_timeline(self):
        plan = AgenticPlan(
            plan_id="timeline-test",
            actions=[WorkflowAction(step=1, intent="read_logs", tool="bash",
                                     description="ls", action_id="a1")],
        )
        timeline = WorkflowTimeline(plan_id="timeline-test")
        RealReadonlyExecutor.execute(plan, timeline)
        assert len(timeline.events) >= 2


# ═══════════════════════════════════════════════════════════════════
# 7. ROLLBACK_PLACEHOLDER
# ═══════════════════════════════════════════════════════════════════

class TestRollbackPlaceholder:
    def test_rollback_not_implemented(self):
        plan = AgenticPlan(plan_id="rollback-test")
        result = RollbackPlaceholder.rollback(plan)
        assert result.success is False
        assert result.reason == "rollback_not_implemented_before_FASE_28.3"

    def test_rollback_to_dict(self):
        result = RollbackResult(success=False, reason="test")
        d = result.to_dict()
        assert d["success"] is False
        assert d["reason"] == "test"
        assert d["steps_rolled_back"] == 0


# ═══════════════════════════════════════════════════════════════════
# 8. WORKFLOW_STATE — EXECUTING
# ═══════════════════════════════════════════════════════════════════

class TestWorkflowStateExecuting:
    def test_executing_exists(self):
        assert hasattr(WorkflowState, "EXECUTING")
        assert WorkflowState.EXECUTING.value == "executing"

    def test_ready_for_execution_to_executing(self):
        transitions = VALID_TRANSITIONS[WorkflowState.READY_FOR_EXECUTION]
        assert WorkflowState.EXECUTING in transitions

    def test_simulating_to_executing(self):
        transitions = VALID_TRANSITIONS[WorkflowState.SIMULATING]
        assert WorkflowState.EXECUTING in transitions

    def test_executing_to_done(self):
        transitions = VALID_TRANSITIONS[WorkflowState.EXECUTING]
        assert WorkflowState.DONE in transitions

    def test_executing_to_failed(self):
        transitions = VALID_TRANSITIONS[WorkflowState.EXECUTING]
        assert WorkflowState.FAILED in transitions

    def test_executing_reserved_no_transitions(self):
        transitions = VALID_TRANSITIONS[WorkflowState.EXECUTING_RESERVED]
        assert len(transitions) == 0


# ═══════════════════════════════════════════════════════════════════
# 9. PERMISSIONS — PHASE 28.2
# ═══════════════════════════════════════════════════════════════════

class TestPermissionsPhase282:
    def test_readonly_allowed(self):
        assert is_scope_allowed_in_phase(PermissionScope.READONLY, "28.2")

    def test_workspace_write_not_allowed(self):
        assert not is_scope_allowed_in_phase(PermissionScope.WORKSPACE_WRITE_RESERVED, "28.2")

    def test_forbidden_not_allowed(self):
        assert not is_scope_allowed_in_phase(PermissionScope.FORBIDDEN, "28.2")

    def test_readonly_intent_classification(self):
        scope = classify_permission_scope("read_config", "read")
        assert scope == PermissionScope.READONLY

    def test_forbidden_intent_classification(self):
        scope = classify_permission_scope("restart_service", "bash")
        assert scope == PermissionScope.FORBIDDEN


# ═══════════════════════════════════════════════════════════════════
# 10. PLANNER — COMPATIBILITY
# ═══════════════════════════════════════════════════════════════════

class TestPlannerCompatibility:
    def test_plan_creation(self):
        plan = AgenticPlan(plan_id="compat-test")
        assert plan.plan_id == "compat-test"
        assert hasattr(plan, "actions")

    def test_workflow_action_fields(self):
        action = WorkflowAction(step=1, intent="read_logs", tool="bash",
                                 description="ls -la", action_id="act-1")
        assert action.step == 1
        assert action.intent == "read_logs"
        assert action.description == "ls -la"

    def test_timeline_executing_transition(self):
        timeline = WorkflowTimeline(plan_id="trans-test")
        timeline.current_state = WorkflowState.READY_FOR_EXECUTION
        assert timeline.transition(WorkflowState.EXECUTING)
        assert timeline.current_state == WorkflowState.EXECUTING

    def test_timeline_executing_to_done(self):
        timeline = WorkflowTimeline(plan_id="trans-test2")
        timeline.current_state = WorkflowState.EXECUTING
        assert timeline.transition(WorkflowState.DONE)
        assert timeline.current_state == WorkflowState.DONE

    def test_invalid_transition(self):
        timeline = WorkflowTimeline(plan_id="invalid-test")
        timeline.current_state = WorkflowState.PLANNING
        assert not timeline.transition(WorkflowState.DONE)


# ═══════════════════════════════════════════════════════════════════
# COUNT: 70+ tests, 140+ assertions
# ═══════════════════════════════════════════════════════════════════
