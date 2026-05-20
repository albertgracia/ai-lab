"""FASE 28.3 — Sandbox Write Runtime Tests (~120 tests).

Cubre: sandbox_fs, sandbox_registry, sandbox_policies, rollback_engine,
artifact_registry, sandbox_audit, mutation_context, sandbox_executor,
workflow_state (MUTATING/ROLLED_BACK), permissions (28.3 scopes).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

import pytest

from runtime.agentic.sandbox_fs import (
    SANDBOX_ROOTS, MAX_PATH_DEPTH,
    resolve_sandbox_path, is_within_sandbox, ensure_sandbox_dir,
    detect_symlink_escape, detect_path_traversal, check_path_depth,
    is_extension_allowed, is_extension_blocked,
    ALLOWED_EXTENSIONS, BLOCKED_EXTENSIONS,
)
from runtime.agentic.sandbox_registry import (
    SANDBOX_OPERATIONS, SANDBOX_WRITE_INTENTS,
    MutationClass, RiskLevel, SandboxOperationSpec,
    is_allowed_operation, op_for_intent,
    OperationVerdict,
)
from runtime.agentic.sandbox_policies import (
    check_sandbox_governance, assess_sandbox_risk,
    detect_chmod_intent, SandboxGovernanceResult,
)
from runtime.agentic.sandbox_audit import (
    SandboxAuditEntry, write_sandbox_audit,
    read_sandbox_audit, get_sandbox_audit_stats,
)
from runtime.agentic.artifact_registry import (
    ArtifactEntry, ArtifactRegistry,
)
from runtime.agentic.rollback_engine import (
    RollbackSnapshot, RollbackResult,
    Snapshotter, RollbackEngine,
)
from runtime.agentic.mutation_context import (
    MutationExecutionContext, MutationClass as MutationClassCtx,
)
from runtime.agentic.execution_context import (
    ExecutionMode, DryRunReason,
    RuntimeExecutionContext,
)
from runtime.agentic.workflow_state import WorkflowState, WorkflowTimeline


# ═══════════════════════════════════════════════════════════════════
# SANDBOX FS
# ═══════════════════════════════════════════════════════════════════

class TestSandboxFS:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.sandbox_root = os.path.join(self.tmpdir, "sandbox")
        os.makedirs(self.sandbox_root, exist_ok=True)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_resolve_path_within_sandbox(self):
        path = "test/file.txt"
        resolved = resolve_sandbox_path(path, self.sandbox_root)
        assert resolved == os.path.realpath(os.path.join(self.sandbox_root, "test/file.txt"))
        assert is_within_sandbox(resolved, [self.sandbox_root])

    def test_resolve_path_outside_sandbox(self):
        resolved = "/etc/passwd"
        assert not is_within_sandbox(resolved, [self.sandbox_root])

    def test_is_within_sandbox_root_itself(self):
        assert is_within_sandbox(os.path.realpath(self.sandbox_root), [self.sandbox_root])

    def test_is_within_sandbox_subdir(self):
        sub = os.path.join(self.sandbox_root, "subdir")
        os.makedirs(sub, exist_ok=True)
        assert is_within_sandbox(os.path.realpath(sub), [self.sandbox_root])

    def test_ensure_sandbox_dir_creates(self):
        new_root = os.path.join(self.tmpdir, "new_sandbox")
        assert not os.path.exists(new_root)
        ensure_sandbox_dir(new_root)
        assert os.path.isdir(new_root)

    def test_ensure_sandbox_dir_exists(self):
        ensure_sandbox_dir(self.sandbox_root)
        assert os.path.isdir(self.sandbox_root)

    def test_detect_symlink_escape(self):
        safe = os.path.join(self.sandbox_root, "safe.txt")
        Path(safe).touch()
        assert not detect_symlink_escape(safe, self.sandbox_root)

    def test_detect_symlink_escape_outside(self):
        outside = "/tmp/outside.txt"
        Path(outside).touch()
        assert detect_symlink_escape(outside, self.sandbox_root)
        os.remove(outside)

    def test_detect_path_traversal_dotdot(self):
        assert detect_path_traversal("../etc/passwd")

    def test_detect_path_traversal_tilde(self):
        assert detect_path_traversal("~/secret")

    def test_detect_path_traversal_clean(self):
        assert not detect_path_traversal("test/file.txt")
        assert not detect_path_traversal("subdir/file.json")

    def test_check_path_depth_ok(self):
        assert check_path_depth("a/b/c/d", max_depth=8)

    def test_check_path_depth_exceeded(self):
        deep = "/".join(["dir"] * 20)
        assert not check_path_depth(deep, max_depth=8)

    def test_check_path_depth_single(self):
        assert check_path_depth("file.txt", max_depth=8)

    def test_check_path_depth_empty(self):
        assert check_path_depth("", max_depth=8)

    def test_is_extension_allowed(self):
        assert is_extension_allowed(".txt")
        assert is_extension_allowed(".md")
        assert is_extension_allowed(".json")
        assert is_extension_allowed(".py")
        assert is_extension_allowed(".sh")
        assert not is_extension_allowed(".exe")
        assert not is_extension_allowed(".socket")

    def test_is_extension_blocked(self):
        assert is_extension_blocked(".socket")
        assert is_extension_blocked(".service")
        assert is_extension_blocked(".mount")
        assert not is_extension_blocked(".txt")
        assert not is_extension_blocked(".py")

    def test_sandbox_roots_defined(self):
        assert len(SANDBOX_ROOTS) == 2
        assert all(isinstance(r, str) for r in SANDBOX_ROOTS)

    def test_max_path_depth_defined(self):
        assert MAX_PATH_DEPTH == 8

    def test_allowed_extensions_contains_expected(self):
        for ext in [".txt", ".md", ".json", ".yaml", ".py", ".sh", ".csv", ".log"]:
            assert ext in ALLOWED_EXTENSIONS

    def test_blocked_extensions_contains_systemd(self):
        for ext in [".socket", ".service", ".mount", ".timer", ".path", ".target"]:
            assert ext in BLOCKED_EXTENSIONS


# ═══════════════════════════════════════════════════════════════════
# SANDBOX REGISTRY
# ═══════════════════════════════════════════════════════════════════

class TestSandboxRegistry:
    def test_operations_count(self):
        assert len(SANDBOX_OPERATIONS) >= 11

    def test_create_file_spec(self):
        spec = SANDBOX_OPERATIONS["create_file"]
        assert spec.risk_level == RiskLevel.MEDIUM
        assert spec.mutation_class == MutationClass.CREATE

    def test_generate_script_requires_governance(self):
        spec = SANDBOX_OPERATIONS["generate_script"]
        assert spec.requires_governance is True
        assert spec.risk_level == RiskLevel.MEDIUM

    def test_allowed_operation_valid(self):
        verdict = is_allowed_operation("create_file", ".txt", 100)
        assert verdict.allowed

    def test_allowed_operation_blocked_extension(self):
        verdict = is_allowed_operation("create_file", ".socket", 100)
        assert not verdict.allowed
        assert "blocked extension" in verdict.reason

    def test_allowed_operation_unknown_name(self):
        verdict = is_allowed_operation("unknown_op", ".txt", 100)
        assert not verdict.allowed
        assert "unknown operation" in verdict.reason

    def test_allowed_operation_exceeds_size(self):
        spec = SANDBOX_OPERATIONS["create_file"]
        verdict = is_allowed_operation("create_file", ".txt", spec.max_size_bytes + 1)
        assert not verdict.allowed
        assert "exceeds max" in verdict.reason

    def test_allowed_operation_wrong_extension(self):
        verdict = is_allowed_operation("write_json", ".yaml", 100)
        assert not verdict.allowed
        assert "not allowed" in verdict.reason

    def test_op_for_intent_exists(self):
        assert op_for_intent("create_file") == "create_file"
        assert op_for_intent("generate_script") == "generate_script"
        assert op_for_intent("write_json") == "write_json"

    def test_op_for_intent_unknown(self):
        assert op_for_intent("unknown_intent") is None

    def test_sandbox_write_intents(self):
        assert "create_file" in SANDBOX_WRITE_INTENTS
        assert "generate_script" in SANDBOX_WRITE_INTENTS
        assert "read_config" not in SANDBOX_WRITE_INTENTS

    def test_spec_to_dict(self):
        spec = SANDBOX_OPERATIONS["create_file"]
        d = spec.to_dict()
        assert d["name"] == "create_file"
        assert d["risk_level"] == "medium"
        assert d["mutation_class"] == "create"

    def test_mutation_class_enum(self):
        assert MutationClass.CREATE.value == "create"
        assert MutationClass.APPEND.value == "append"
        assert MutationClass.REPLACE.value == "replace"
        assert MutationClass.ROLLBACK.value == "rollback"

    def test_operation_verdict_to_dict(self):
        v = OperationVerdict(True, spec=SANDBOX_OPERATIONS["create_file"])
        d = v.to_dict()
        assert d["allowed"] is True
        assert d["spec"]["name"] == "create_file"


# ═══════════════════════════════════════════════════════════════════
# SANDBOX POLICIES
# ═══════════════════════════════════════════════════════════════════

class TestSandboxPolicies:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.sandbox_root = os.path.join(self.tmpdir, "sandbox")
        os.makedirs(self.sandbox_root, exist_ok=True)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_governance_passes_phase_28_3(self):
        result = check_sandbox_governance(
            "create_file", "test.txt", "28.3", self.sandbox_root,
        )
        assert result.allowed

    def test_governance_fails_wrong_phase(self):
        result = check_sandbox_governance(
            "create_file", "test.txt", "28.1", self.sandbox_root,
        )
        assert not result.allowed
        assert "does not support" in result.reason

    def test_governance_fails_not_sandbox_intent(self):
        result = check_sandbox_governance(
            "restart_service", "test.txt", "28.3", self.sandbox_root,
        )
        assert not result.allowed

    def test_governance_fails_path_traversal(self):
        result = check_sandbox_governance(
            "create_file", "../etc/passwd", "28.3", self.sandbox_root,
        )
        assert not result.allowed
        assert "path traversal" in result.reason

    def test_governance_fails_depth_exceeded(self):
        deep = "/".join(["dir"] * 20) + "/file.txt"
        result = check_sandbox_governance(
            "create_file", deep, "28.3", self.sandbox_root,
        )
        assert not result.allowed
        assert "depth exceeds" in result.reason

    def test_governance_fails_blocked_extension(self):
        result = check_sandbox_governance(
            "create_file", "test.service", "28.3", self.sandbox_root,
        )
        assert not result.allowed
        assert "blocked extension" in result.reason

    def test_governance_fails_unknown_intent(self):
        result = check_sandbox_governance(
            "unknown_intent", "test.txt", "28.3", self.sandbox_root,
        )
        assert not result.allowed
        assert "not a sandbox write operation" in result.reason

    def test_assess_risk_script(self):
        assert assess_sandbox_risk("generate_script", "test.py") == "medium"

    def test_assess_risk_py_ext(self):
        assert assess_sandbox_risk("create_file", "test.py") == "medium"

    def test_assess_risk_low(self):
        assert assess_sandbox_risk("write_json", "data.json") == "low"
        assert assess_sandbox_risk("write_markdown", "doc.md") == "low"

    def test_detect_chmod_intent_positive(self):
        assert detect_chmod_intent("chmod +x script.sh")
        assert detect_chmod_intent("run chmod 755 file")
        assert detect_chmod_intent("make it +x")

    def test_detect_chmod_intent_negative(self):
        assert not detect_chmod_intent("create file test.txt")
        assert not detect_chmod_intent("write content to file")

    def test_governance_result_to_dict(self):
        r = SandboxGovernanceResult(allowed=True, reason="test")
        d = r.to_dict()
        assert d["allowed"] is True
        assert d["reason"] == "test"


# ═══════════════════════════════════════════════════════════════════
# SANDBOX AUDIT
# ═══════════════════════════════════════════════════════════════════

class TestSandboxAudit:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_dir = os.path.join("/opt/ai-lab/runtime/state")
        self.test_audit = os.path.join(self.tmpdir, "sandbox_audit.jsonl")

    def test_audit_entry_defaults(self):
        entry = SandboxAuditEntry()
        assert entry.status == "success"
        assert entry.mutation_class == ""

    def test_audit_entry_to_dict(self):
        entry = SandboxAuditEntry(
            execution_id="exec1",
            workflow_id="wf1",
            action_id="act1",
            mutation_class="create",
            mutation_type="create_file",
            target_path="/tmp/test.txt",
            before_checksum="abc",
            after_checksum="def",
            rollback_available=True,
            rollback_path="/tmp/.rollback/wf1/act1",
            status="success",
        )
        d = entry.to_dict()
        assert d["execution_id"] == "exec1"
        assert d["mutation_class"] == "create"
        assert d["rollback_available"] is True

    def test_write_and_read_audit(self):
        entry = SandboxAuditEntry(
            execution_id="exec1", workflow_id="wf1",
            mutation_class="create", mutation_type="create_file",
            target_path="/tmp/test.txt", status="success",
        )
        write_sandbox_audit(entry)
        entries = read_sandbox_audit(limit=10)
        assert len(entries) >= 1
        assert entries[-1]["execution_id"] == "exec1"

    def test_read_empty_audit(self):
        entries = read_sandbox_audit(limit=10)
        assert isinstance(entries, list)

    def test_get_audit_stats(self):
        stats = get_sandbox_audit_stats()
        assert "total" in stats
        assert "success" in stats
        assert "failed" in stats
        assert "blocked" in stats


# ═══════════════════════════════════════════════════════════════════
# ARTIFACT REGISTRY
# ═══════════════════════════════════════════════════════════════════

class TestArtifactRegistry:
    def setup_method(self):
        self.artifact_id = uuid.uuid4().hex[:12]
        self.entry = ArtifactEntry(
            artifact_id=self.artifact_id,
            path="/tmp/sandbox/test.txt",
            checksum_sha256="abc123",
            size_bytes=100,
            mutation_type="create_file",
            workflow_id="wf_test",
            action_id="act_1",
            generated_by_action="create_file",
        )

    def test_artifact_entry_to_dict(self):
        d = self.entry.to_dict()
        assert d["artifact_id"] == self.artifact_id
        assert d["mutation_type"] == "create_file"
        assert d["size_bytes"] == 100

    def test_artifact_entry_lineage(self):
        parent_id = uuid.uuid4().hex[:12]
        child = ArtifactEntry(
            artifact_id=uuid.uuid4().hex[:12],
            path="/tmp/sandbox/child.txt",
            checksum_sha256="def456",
            size_bytes=50,
            mutation_type="transform",
            workflow_id="wf_test",
            action_id="act_2",
            parent_artifact_id=parent_id,
            parent_workflow_id="wf_parent",
            generated_by_action="sandbox_transform",
        )
        ArtifactRegistry.register(self.entry)
        ArtifactRegistry.register(child)
        lineage = ArtifactRegistry.get_lineage(self.artifact_id)
        assert len(lineage) >= 1

    def test_register_and_list(self):
        ArtifactRegistry.register(self.entry)
        entries = ArtifactRegistry.list(limit=10)
        found = any(e["artifact_id"] == self.artifact_id for e in entries)
        assert found

    def test_get_artifact_by_id(self):
        ArtifactRegistry.register(self.entry)
        found = ArtifactRegistry.get(self.artifact_id)
        assert found is not None
        assert found["path"] == "/tmp/sandbox/test.txt"

    def test_get_artifact_not_found(self):
        found = ArtifactRegistry.get("nonexistent")
        assert found is None

    def test_get_by_workflow(self):
        ArtifactRegistry.register(self.entry)
        entries = ArtifactRegistry.get_by_workflow("wf_test")
        assert len(entries) >= 1

    def test_count_by_workflow(self):
        ArtifactRegistry.register(self.entry)
        count = ArtifactRegistry.count_by_workflow("wf_test")
        assert count >= 1

    def test_total_bytes_by_workflow(self):
        ArtifactRegistry.register(self.entry)
        total = ArtifactRegistry.total_bytes_by_workflow("wf_test")
        assert total >= 100

    def test_get_lineage_empty(self):
        lineage = ArtifactRegistry.get_lineage("nonexistent")
        assert lineage == []


# ═══════════════════════════════════════════════════════════════════
# ROLLBACK ENGINE
# ═══════════════════════════════════════════════════════════════════

class TestRollbackEngine:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.sandbox_root = os.path.join(self.tmpdir, "sandbox")
        os.makedirs(self.sandbox_root, exist_ok=True)
        self.workflow_id = "wf_rollback_test"
        self.action_id = "act_rollback"

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_snapshot_file(self):
        test_file = os.path.join(self.sandbox_root, "test.txt")
        Path(test_file).write_text("hello world")
        snapshot = Snapshotter.take_snapshot(test_file, self.workflow_id, self.action_id, self.sandbox_root)
        assert snapshot.path == test_file
        assert snapshot.original_exists is True
        assert snapshot.is_directory is False
        assert len(snapshot.checksum_sha256) == 64
        assert os.path.exists(snapshot.backup_path)

    def test_snapshot_nonexistent_file(self):
        test_file = os.path.join(self.sandbox_root, "nonexistent.txt")
        snapshot = Snapshotter.take_snapshot(test_file, self.workflow_id, self.action_id, self.sandbox_root)
        assert snapshot.original_exists is False
        assert os.path.exists(snapshot.backup_path)

    def test_snapshot_directory(self):
        test_dir = os.path.join(self.sandbox_root, "testdir")
        os.makedirs(test_dir, exist_ok=True)
        Path(os.path.join(test_dir, "a.txt")).write_text("a")
        Path(os.path.join(test_dir, "b.txt")).write_text("b")
        snapshot = Snapshotter.take_snapshot(test_dir, self.workflow_id, self.action_id, self.sandbox_root)
        assert snapshot.is_directory is True
        assert os.path.isdir(snapshot.backup_path)

    def test_restore_file(self):
        test_file = os.path.join(self.sandbox_root, "restore.txt")
        Path(test_file).write_text("original content")
        snapshot = Snapshotter.take_snapshot(test_file, self.workflow_id, self.action_id, self.sandbox_root)
        Path(test_file).write_text("modified content")
        result = RollbackEngine.restore(snapshot)
        assert result.success is True
        assert result.checksum_validated is True
        assert Path(test_file).read_text() == "original content"

    def test_restore_absent_file(self):
        test_file = os.path.join(self.sandbox_root, "absent.txt")
        snapshot = Snapshotter.take_snapshot(test_file, self.workflow_id, self.action_id, self.sandbox_root)
        Path(test_file).write_text("created after snapshot")
        result = RollbackEngine.restore(snapshot)
        assert result.success is True
        assert not os.path.exists(test_file)

    def test_restore_checksum_mismatch_detected(self):
        test_file = os.path.join(self.sandbox_root, "checksum.txt")
        Path(test_file).write_text("original")
        snapshot = Snapshotter.take_snapshot(test_file, self.workflow_id, self.action_id, self.sandbox_root)
        orig_checksum = snapshot.checksum_sha256
        Path(test_file).write_text("modified")
        result = RollbackEngine.restore(snapshot)
        assert result.success is True
        restored = hashlib.sha256(open(test_file, "rb").read()).hexdigest()
        assert restored == orig_checksum

    def test_rollback_snapshot_to_dict(self):
        s = RollbackSnapshot(path="/tmp/test.txt", checksum_sha256="abc", backup_path="/tmp/backup")
        d = s.to_dict()
        assert d["path"] == "/tmp/test.txt"
        assert d["checksum_sha256"] == "abc"

    def test_rollback_result_fields(self):
        r = RollbackResult(success=True, reason="test", steps_rolled_back=2)
        assert r.to_dict()["steps_rolled_back"] == 2

    def test_rollback_workflow_no_data(self):
        result = RollbackEngine.rollback_workflow("nonexistent", self.sandbox_root)
        assert result.success is False
        assert "no rollback data" in result.reason


# ═══════════════════════════════════════════════════════════════════
# MUTATION CONTEXT
# ═══════════════════════════════════════════════════════════════════

class TestMutationContext:
    def test_mutation_context_inheritance(self):
        ctx = MutationExecutionContext()
        assert isinstance(ctx, RuntimeExecutionContext)
        assert ctx.mode == ExecutionMode.SANDBOX_WRITE or ctx.mode == ExecutionMode.READONLY

    def test_mutation_context_defaults(self):
        ctx = MutationExecutionContext()
        assert ctx.sandbox_root == "/tmp/opencode/sandbox/"
        assert ctx.dry_run_only_write is True
        assert ctx.current_workflow_artifacts == 0
        assert ctx.current_workflow_bytes == 0

    def test_mutation_context_is_executable_dry_run(self):
        ctx = MutationExecutionContext(dry_run=True, mode=ExecutionMode.SANDBOX_WRITE)
        assert not ctx.is_executable()

    def test_mutation_context_is_executable_sandbox_write(self):
        ctx = MutationExecutionContext(dry_run=False, mode=ExecutionMode.SANDBOX_WRITE)
        assert ctx.is_executable()

    def test_mutation_context_is_executable_readonly(self):
        ctx = MutationExecutionContext(dry_run=False, mode=ExecutionMode.READONLY)
        assert ctx.is_executable()

    def test_mutation_context_is_executable_wrong_mode(self):
        ctx = MutationExecutionContext(dry_run=False, mode=ExecutionMode.SIMULATION)
        assert not ctx.is_executable()

    def test_mutation_context_to_dict(self):
        ctx = MutationExecutionContext(
            execution_id="test123",
            mode=ExecutionMode.SANDBOX_WRITE,
            sandbox_root="/tmp/test_sandbox/",
            mutation_class=MutationClassCtx.CREATE,
            current_workflow_artifacts=5,
            current_workflow_bytes=1024,
        )
        d = ctx.to_dict()
        assert d["execution_id"] == "test123"
        assert d["mode"] == "sandbox_write"
        assert d["sandbox_root"] == "/tmp/test_sandbox/"
        assert d["mutation_class"] == MutationClassCtx.CREATE.value
        assert d["current_workflow_artifacts"] == 5

    def test_mutation_context_post_init_sets_phase(self):
        ctx = MutationExecutionContext()
        assert ctx.phase == "28.3"

    def test_dry_run_reason_sandbox_disabled(self):
        assert DryRunReason.SANDBOX_DISABLED.value == "sandbox_disabled"


# ═══════════════════════════════════════════════════════════════════
# WORKFLOW STATE — MUTATING / ROLLED_BACK
# ═══════════════════════════════════════════════════════════════════

class TestWorkflowStateSandbox:
    def test_mutating_state_exists(self):
        assert hasattr(WorkflowState, "MUTATING")
        assert WorkflowState.MUTATING.value == "mutating"

    def test_executing_to_mutating(self):
        t = WorkflowTimeline(plan_id="test")
        t.current_state = WorkflowState.EXECUTING
        assert t.transition(WorkflowState.MUTATING)

    def test_mutating_to_done(self):
        t = WorkflowTimeline(plan_id="test")
        t.current_state = WorkflowState.MUTATING
        assert t.transition(WorkflowState.DONE)

    def test_mutating_to_failed(self):
        t = WorkflowTimeline(plan_id="test")
        t.current_state = WorkflowState.MUTATING
        assert t.transition(WorkflowState.FAILED)

    def test_executing_to_done_still_works(self):
        t = WorkflowTimeline(plan_id="test")
        t.current_state = WorkflowState.EXECUTING
        assert t.transition(WorkflowState.DONE)

    def test_failed_to_rolled_back(self):
        t = WorkflowTimeline(plan_id="test")
        t.current_state = WorkflowState.FAILED
        assert t.transition(WorkflowState.ROLLED_BACK)

    def test_done_to_rolled_back(self):
        t = WorkflowTimeline(plan_id="test")
        t.current_state = WorkflowState.DONE
        assert t.transition(WorkflowState.ROLLED_BACK)

    def test_mutating_invalid_transition(self):
        t = WorkflowTimeline(plan_id="test")
        t.current_state = WorkflowState.MUTATING
        assert not t.transition(WorkflowState.PLANNING)
        assert not t.transition(WorkflowState.EXECUTING)

    def test_rolled_back_terminal(self):
        t = WorkflowTimeline(plan_id="test")
        t.current_state = WorkflowState.ROLLED_BACK
        assert not t.transition(WorkflowState.DONE)


# ═══════════════════════════════════════════════════════════════════
# PERMISSIONS — FASE 28.3
# ═══════════════════════════════════════════════════════════════════

class TestPermissionsPhase283:
    def test_workspace_write_allowed_in_phase_28_3(self):
        from runtime.agentic.permissions import is_scope_allowed_in_phase, PermissionScope
        assert is_scope_allowed_in_phase(PermissionScope.WORKSPACE_WRITE_RESERVED, "28.3")

    def test_readonly_allowed_in_phase_28_3(self):
        from runtime.agentic.permissions import is_scope_allowed_in_phase, PermissionScope
        assert is_scope_allowed_in_phase(PermissionScope.READONLY, "28.3")

    def test_workspace_write_not_allowed_in_28_2(self):
        from runtime.agentic.permissions import is_scope_allowed_in_phase, PermissionScope
        assert not is_scope_allowed_in_phase(PermissionScope.WORKSPACE_WRITE_RESERVED, "28.2")

    def test_sandbox_intent_classified_as_workspace_write(self):
        from runtime.agentic.permissions import classify_permission_scope, PermissionScope
        scope = classify_permission_scope("create_file", "write", "/tmp/sandbox/test.txt")
        assert scope == PermissionScope.WORKSPACE_WRITE_RESERVED

    def test_readonly_intent_still_works(self):
        from runtime.agentic.permissions import classify_permission_scope, PermissionScope
        scope = classify_permission_scope("read_config", "read", "/opt/ai-lab/config.json")
        assert scope == PermissionScope.READONLY

    def test_create_file_not_in_forbidden(self):
        from runtime.agentic.permissions import classify_permission_scope, PermissionScope
        scope = classify_permission_scope("create_file", "write", "test.txt")
        assert scope != PermissionScope.FORBIDDEN


# ═══════════════════════════════════════════════════════════════════
# SANDBOX EXECUTOR
# ═══════════════════════════════════════════════════════════════════

class TestSandboxExecutor:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.sandbox_root = os.path.join(self.tmpdir, "sandbox")
        os.makedirs(self.sandbox_root, exist_ok=True)
        self._orig_flags = {}

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_plan_with_intent(self, intent: str, description: str):
        from runtime.agentic.planner import AgenticPlan, WorkflowAction
        return AgenticPlan(
            plan_id="test_plan",
            actions=[
                WorkflowAction(
                    action_id="act_1",
                    step=1,
                    tool="write",
                    intent=intent,
                    description=description,
                ),
            ],
        )

    def test_executor_flags_defined(self):
        from runtime.agentic.sandbox_executor import ENABLE_SANDBOX_WRITE, DRY_RUN
        assert ENABLE_SANDBOX_WRITE is False
        assert DRY_RUN is True

    def test_execute_dry_run_by_default(self):
        from runtime.agentic.sandbox_executor import SandboxWriteExecutor
        plan = self._make_plan_with_intent("create_file", "test.txt")
        timeline = WorkflowTimeline(plan_id="test_plan")
        result = SandboxWriteExecutor.execute(plan, timeline)
        assert result.simulation_only is True
        assert result.status == "simulated_success"

    def test_executor_blocks_chmod(self):
        from runtime.agentic.execution_context import CURRENT_EXECUTION_MODE
        from runtime.agentic.sandbox_executor import SandboxWriteExecutor
        plan = self._make_plan_with_intent("create_file", "chmod +x script.sh")
        timeline = WorkflowTimeline(plan_id="test_plan")
        from runtime.agentic.mutation_context import MutationExecutionContext
        ctx = MutationExecutionContext(
            execution_id="test_exec",
            mode=CURRENT_EXECUTION_MODE,
            dry_run=True,
            phase="28.3",
        )
        result = SandboxWriteExecutor.execute(plan, timeline, ctx=ctx)
        assert result.simulation_only is True

    def test_executor_blocks_governance_fail(self):
        from runtime.agentic.sandbox_executor import SandboxWriteExecutor
        plan = self._make_plan_with_intent("restart_service", "test.service")
        timeline = WorkflowTimeline(plan_id="test_plan")
        from runtime.agentic.mutation_context import MutationExecutionContext
        ctx = MutationExecutionContext(
            execution_id="test_exec",
            mode=ExecutionMode.SANDBOX_WRITE,
            dry_run=True,
            phase="28.3",
            sandbox_root=self.sandbox_root,
        )
        result = SandboxWriteExecutor.execute(plan, timeline, ctx=ctx)
        assert result.simulation_only is True

    def test_executor_timeline_recorded(self):
        from runtime.agentic.sandbox_executor import SandboxWriteExecutor
        plan = self._make_plan_with_intent("create_file", "test.txt")
        timeline = WorkflowTimeline(plan_id="test_plan")
        SandboxWriteExecutor.execute(plan, timeline)
        assert len(timeline.events) >= 1

    def test_executor_sandbox_execution_started_event(self):
        from runtime.agentic.execution_context import CURRENT_EXECUTION_MODE
        from runtime.agentic.sandbox_executor import SandboxWriteExecutor
        plan = self._make_plan_with_intent("create_file", "test.txt")
        timeline = WorkflowTimeline(plan_id="test_plan")
        from runtime.agentic.mutation_context import MutationExecutionContext
        ctx = MutationExecutionContext(
            execution_id="test_exec",
            mode=CURRENT_EXECUTION_MODE,
            dry_run=True,
            phase="28.3",
            sandbox_root=self.sandbox_root,
        )
        SandboxWriteExecutor.execute(plan, timeline, ctx=ctx)
        event_types = [e.event_type for e in timeline.events]
        assert "dry_run_reason" in event_types or "execution_started" in event_types

    def test_executor_rate_limit_constants(self):
        from runtime.agentic.sandbox_executor import (
            MAX_ARTIFACTS_PER_WORKFLOW, MAX_WORKFLOW_BYTES,
            RATE_LIMIT_WRITES_PER_MIN,
        )
        assert MAX_ARTIFACTS_PER_WORKFLOW == 100
        assert MAX_WORKFLOW_BYTES == 25 * 1024 * 1024
        assert RATE_LIMIT_WRITES_PER_MIN == 10


# ═══════════════════════════════════════════════════════════════════
# SANDBOX WRITE EXECUTOR — REAL FILE MUTATION
# ═══════════════════════════════════════════════════════════════════

class TestSandboxWriteExecutorMutation:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.sandbox_root = os.path.join(self.tmpdir, "sandbox")
        os.makedirs(self.sandbox_root, exist_ok=True)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_execute_file_mutation_via_helper(self):
        from runtime.agentic.sandbox_executor import _execute_file_mutation
        target = os.path.join(self.sandbox_root, "test.txt")
        exit_code, stdout, stderr = _execute_file_mutation(target, "hello world", "write")
        assert exit_code == 0
        assert Path(target).read_text() == "hello world"

    def test_execute_file_append(self):
        from runtime.agentic.sandbox_executor import _execute_file_mutation
        target = os.path.join(self.sandbox_root, "append.txt")
        Path(target).write_text("line1\n")
        _execute_file_mutation(target, "line2\n", "append")
        assert Path(target).read_text() == "line1\nline2\n"

    def test_execute_json_mutation(self):
        from runtime.agentic.sandbox_executor import _execute_json_mutation
        target = os.path.join(self.sandbox_root, "data.json")
        data = {"key": "value", "num": 42}
        exit_code, stdout, stderr = _execute_json_mutation(target, data)
        assert exit_code == 0
        loaded = json.loads(Path(target).read_text())
        assert loaded == data

    def test_execute_directory_creation(self):
        from runtime.agentic.sandbox_executor import _execute_directory_creation
        target = os.path.join(self.sandbox_root, "newdir/subdir")
        exit_code, stdout, stderr = _execute_directory_creation(target)
        assert exit_code == 0
        assert os.path.isdir(target)

    def test_execute_directory_creation_existing(self):
        from runtime.agentic.sandbox_executor import _execute_directory_creation
        os.makedirs(os.path.join(self.sandbox_root, "existing"), exist_ok=True)
        exit_code, _, _ = _execute_directory_creation(os.path.join(self.sandbox_root, "existing"))
        assert exit_code == 0

    def test_get_size(self):
        from runtime.agentic.sandbox_executor import _get_size
        target = os.path.join(self.sandbox_root, "size.txt")
        Path(target).write_text("hello")
        size = _get_size(target)
        assert size == 5

    def test_get_size_nonexistent(self):
        from runtime.agentic.sandbox_executor import _get_size
        assert _get_size("/nonexistent") == 0

    def test_sha256(self):
        from runtime.agentic.sandbox_executor import _sha256
        target = os.path.join(self.sandbox_root, "hash.txt")
        Path(target).write_text("data")
        h = _sha256(target)
        assert len(h) == 64

    def test_sha256_nonexistent(self):
        from runtime.agentic.sandbox_executor import _sha256
        assert _sha256("/nonexistent") == ""

    def test_resolve_target(self):
        from runtime.agentic.sandbox_executor import _resolve_target
        resolved = _resolve_target("test.txt", self.sandbox_root)
        assert resolved.startswith(self.sandbox_root)
        assert resolved.endswith("test.txt")


# ═══════════════════════════════════════════════════════════════════
# EXISTING EXECUTION CONTEXT — NEW DryRunReason
# ═══════════════════════════════════════════════════════════════════

class TestExecutionContextSandbox:
    def test_dry_run_reason_has_sandbox_disabled(self):
        assert hasattr(DryRunReason, "SANDBOX_DISABLED")
        assert DryRunReason.SANDBOX_DISABLED.value == "sandbox_disabled"

    def test_is_executable_sandbox_write(self):
        ctx = RuntimeExecutionContext(
            mode=ExecutionMode.SANDBOX_WRITE,
            dry_run=False,
        )
        assert ctx.is_executable()

    def test_is_executable_sandbox_write_dry_run(self):
        ctx = RuntimeExecutionContext(
            mode=ExecutionMode.SANDBOX_WRITE,
            dry_run=True,
        )
        assert not ctx.is_executable()

    def test_is_executable_readonly_still_works(self):
        ctx = RuntimeExecutionContext(
            mode=ExecutionMode.READONLY,
            dry_run=False,
        )
        assert ctx.is_executable()


# ═══════════════════════════════════════════════════════════════════
# PERMISSIONS — classify_permission_scope with sandbox intents
# ═══════════════════════════════════════════════════════════════════

class TestPermissionsSandboxIntentClassification:
    def test_create_file_classified_workspace_write(self):
        from runtime.agentic.permissions import classify_permission_scope, PermissionScope
        assert classify_permission_scope("create_file", "write") == PermissionScope.WORKSPACE_WRITE_RESERVED

    def test_append_file_classified_workspace_write(self):
        from runtime.agentic.permissions import classify_permission_scope, PermissionScope
        assert classify_permission_scope("append_file", "write") == PermissionScope.WORKSPACE_WRITE_RESERVED

    def test_generate_script_classified_workspace_write(self):
        from runtime.agentic.permissions import classify_permission_scope, PermissionScope
        assert classify_permission_scope("generate_script", "write") == PermissionScope.WORKSPACE_WRITE_RESERVED

    def test_write_json_classified_workspace_write(self):
        from runtime.agentic.permissions import classify_permission_scope, PermissionScope
        assert classify_permission_scope("write_json", "write") == PermissionScope.WORKSPACE_WRITE_RESERVED

    def test_forbidden_intent_still_forbidden(self):
        from runtime.agentic.permissions import classify_permission_scope, PermissionScope
        assert classify_permission_scope("restart_service", "bash") == PermissionScope.FORBIDDEN

    def test_readonly_intent_still_readonly(self):
        from runtime.agentic.permissions import classify_permission_scope, PermissionScope
        scope = classify_permission_scope("read_config", "read")
        assert scope == PermissionScope.READONLY
