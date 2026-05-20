"""FASE 28.3 — Sandbox Write Executor.

Orquestador de mutaciones sandbox con governance, snapshot pre-mutacion,
budget por workflow, rate limiting, rollback automatico en error.
Usa SOLO Python I/O (open, pathlib, shutil) — NUNCA subprocess.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

from runtime.agentic.executor import SimulationExecutor, ExecutionResult, ActionResult
from runtime.agentic.planner import AgenticPlan, WorkflowAction
from runtime.agentic.workflow_state import WorkflowState, WorkflowTimeline
from runtime.agentic.execution_context import (
    ExecutionMode,
    DryRunReason,
    RuntimeExecutionContext,
    CURRENT_EXECUTION_MODE,
)
from runtime.agentic.mutation_context import MutationExecutionContext
from runtime.agentic.sandbox_fs import (
    SANDBOX_ROOTS,
    resolve_sandbox_path,
    ensure_sandbox_dir,
    is_within_sandbox,
    detect_symlink_escape,
    detect_path_traversal,
    check_path_depth,
    MAX_PATH_DEPTH,
)
from runtime.agentic.sandbox_registry import (
    SANDBOX_OPERATIONS,
    op_for_intent,
    is_allowed_operation,
    MutationClass,
)
from runtime.agentic.sandbox_policies import (
    check_sandbox_governance,
    assess_sandbox_risk,
    detect_chmod_intent,
)
from runtime.agentic.sandbox_audit import (
    SandboxAuditEntry,
    write_sandbox_audit,
)
from runtime.agentic.artifact_registry import (
    ArtifactEntry,
    ArtifactRegistry,
)
from runtime.agentic.rollback_engine import (
    Snapshotter,
    RollbackEngine,
    write_original_path_marker,
)


ENABLE_SANDBOX_WRITE = False
DRY_RUN = True

MAX_ARTIFACTS_PER_WORKFLOW = 100
MAX_WORKFLOW_BYTES = 25 * 1024 * 1024

RATE_LIMIT_WRITES_PER_MIN = 10
RATE_LIMIT_WINDOW_SEC = 60


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except FileNotFoundError:
        return ""
    except Exception:
        return ""


def _resolve_target(target_path: str, sandbox_root: str) -> str:
    return resolve_sandbox_path(target_path, sandbox_root)


def _execute_file_mutation(
    target: str,
    content: str,
    mutation_type: str,
) -> tuple[int, str, str]:
    parent = os.path.dirname(target)
    os.makedirs(parent, exist_ok=True)
    try:
        if mutation_type == "append":
            with open(target, "a", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
        return 0, "", ""
    except Exception as e:
        return 1, "", str(e)


def _execute_json_mutation(target: str, data: Any) -> tuple[int, str, str]:
    parent = os.path.dirname(target)
    os.makedirs(parent, exist_ok=True)
    try:
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return 0, "", ""
    except Exception as e:
        return 1, "", str(e)


def _execute_directory_creation(target: str) -> tuple[int, str, str]:
    try:
        os.makedirs(target, exist_ok=True)
        return 0, "", ""
    except Exception as e:
        return 1, "", str(e)


class SandboxWriteExecutor:
    _rate_tracker: dict[str, list[float]] = {}

    @staticmethod
    def _check_rate_limit(workflow_id: str) -> bool:
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW_SEC
        timestamps = SandboxWriteExecutor._rate_tracker.get(workflow_id, [])
        timestamps = [t for t in timestamps if t > window_start]
        SandboxWriteExecutor._rate_tracker[workflow_id] = timestamps
        return len(timestamps) < RATE_LIMIT_WRITES_PER_MIN

    @staticmethod
    def _record_write(workflow_id: str) -> None:
        if workflow_id not in SandboxWriteExecutor._rate_tracker:
            SandboxWriteExecutor._rate_tracker[workflow_id] = []
        SandboxWriteExecutor._rate_tracker[workflow_id].append(time.time())

    @staticmethod
    def execute(
        plan: AgenticPlan,
        timeline: WorkflowTimeline,
        ctx: RuntimeExecutionContext | None = None,
    ) -> ExecutionResult:
        if ctx is None:
            ctx = MutationExecutionContext(
                execution_id=uuid.uuid4().hex[:8],
                mode=ExecutionMode.SANDBOX_WRITE,
                dry_run=DRY_RUN,
                phase="28.3",
            )

        sandbox_root = getattr(ctx, "sandbox_root", SANDBOX_ROOTS[0])
        ensure_sandbox_dir(sandbox_root)

        if not ENABLE_SANDBOX_WRITE or DRY_RUN:
            reason = ctx.dry_run_reason or DryRunReason.FEATURE_FLAG.value
            if DRY_RUN:
                reason = DryRunReason.SANDBOX_DISABLED.value
            ctx.dry_run_reason = reason
            sim_result = SimulationExecutor.execute_with_context(plan, timeline, ctx)
            return sim_result

        t_start = time.time()
        result = ExecutionResult(
            plan_id=plan.plan_id,
            simulation_only=False,
            timeline=timeline,
        )

        timeline.transition(WorkflowState.EXECUTING)
        timeline.add_event("sandbox_execution_started", "sandbox_write", {
            "action_count": len(plan.actions),
            "sandbox_root": sandbox_root,
            "execution_mode": ctx.mode.value,
        })

        for action in plan.actions:
            action_start = time.time()
            target = action.description
            intent = action.intent

            if detect_chmod_intent(target):
                ar = _blocked_result(action, "chmod_not_allowed_in_sandbox")
                result.actions_results.append(ar)
                result.actions_failed += 1
                result.actions_executed += 1
                timeline.add_event("action_chmod_blocked", "sandbox_write", {
                    "action_id": action.action_id, "step": action.step,
                })
                _write_sandbox_audit_entry(ctx, action, ar.to_dict(), "blocked")
                continue

            gov = check_sandbox_governance(intent, target, ctx.phase, sandbox_root)
            if not gov.allowed:
                ar = _blocked_result(action, gov.reason)
                result.actions_results.append(ar)
                result.actions_failed += 1
                result.actions_executed += 1
                timeline.add_event("action_blocked_by_governance", "sandbox_write", {
                    "action_id": action.action_id, "step": action.step,
                    "reason": gov.reason,
                })
                _write_sandbox_audit_entry(ctx, action, ar.to_dict(), "blocked")
                continue

            workflow_id = plan.plan_id
            artifact_count = ArtifactRegistry.count_by_workflow(workflow_id)
            if artifact_count >= MAX_ARTIFACTS_PER_WORKFLOW:
                ar = _blocked_result(action, f"max artifacts per workflow ({MAX_ARTIFACTS_PER_WORKFLOW}) exceeded")
                result.actions_results.append(ar)
                result.actions_failed += 1
                result.actions_executed += 1
                timeline.add_event("budget_exceeded", "sandbox_write", {
                    "action_id": action.action_id, "artifact_count": artifact_count,
                })
                _write_sandbox_audit_entry(ctx, action, ar.to_dict(), "blocked")
                continue

            total_bytes = ArtifactRegistry.total_bytes_by_workflow(workflow_id)
            if total_bytes >= MAX_WORKFLOW_BYTES:
                ar = _blocked_result(action, f"max workflow bytes ({MAX_WORKFLOW_BYTES}) exceeded")
                result.actions_results.append(ar)
                result.actions_failed += 1
                result.actions_executed += 1
                timeline.add_event("budget_bytes_exceeded", "sandbox_write", {
                    "action_id": action.action_id, "total_bytes": total_bytes,
                })
                _write_sandbox_audit_entry(ctx, action, ar.to_dict(), "blocked")
                continue

            if not SandboxWriteExecutor._check_rate_limit(workflow_id):
                ar = _blocked_result(action, f"rate limit exceeded ({RATE_LIMIT_WRITES_PER_MIN}/min)")
                result.actions_results.append(ar)
                result.actions_failed += 1
                result.actions_executed += 1
                timeline.add_event("rate_limit_exceeded", "sandbox_write", {
                    "action_id": action.action_id,
                })
                _write_sandbox_audit_entry(ctx, action, ar.to_dict(), "blocked")
                continue

            resolved_target = _resolve_target(target, sandbox_root)
            action_id = action.action_id or uuid.uuid4().hex[:8]

            snapshot = Snapshotter.take_snapshot(resolved_target, workflow_id, action_id, sandbox_root)
            write_original_path_marker(resolved_target, os.path.dirname(snapshot.backup_path))

            op_name = op_for_intent(intent) or "unknown"
            exit_code, stdout, stderr = _perform_mutation(op_name, resolved_target, action)

            duration_ms = int((time.time() - action_start) * 1000)

            after_checksum = _sha256(resolved_target) if exit_code == 0 else ""

            op_spec = SANDBOX_OPERATIONS.get(op_name)
            mutation_class = op_spec.mutation_class.value if op_spec else MutationClass.CREATE.value

            ar = ActionResult(
                action_id=action_id,
                step=action.step,
                tool=action.tool,
                intent=intent,
                exit_code=exit_code,
                stdout=stdout[:2000],
                stderr=stderr[:1000],
                duration_ms=duration_ms,
                simulated=False,
                status="success" if exit_code == 0 else "failed",
            )
            result.actions_results.append(ar)
            result.actions_executed += 1

            if exit_code == 0:
                SandboxWriteExecutor._record_write(workflow_id)
                artifact_entry = ArtifactEntry(
                    path=resolved_target,
                    checksum_sha256=after_checksum,
                    size_bytes=_get_size(resolved_target),
                    mutation_type=op_name,
                    workflow_id=workflow_id,
                    action_id=action_id,
                    generated_by_action=intent,
                    metadata={"sandbox_root": sandbox_root},
                )
                ArtifactRegistry.register(artifact_entry)

                audit_entry = SandboxAuditEntry(
                    execution_id=ctx.execution_id,
                    workflow_id=workflow_id,
                    action_id=action_id,
                    mutation_class=mutation_class,
                    mutation_type=op_name,
                    target_path=resolved_target,
                    before_checksum=snapshot.checksum_sha256,
                    after_checksum=after_checksum,
                    rollback_available=True,
                    rollback_path=snapshot.backup_path,
                    status="success",
                )
                write_sandbox_audit(audit_entry)

                timeline.add_event("mutation_success", "sandbox_write", {
                    "action_id": action_id, "step": action.step,
                    "op": op_name, "target": resolved_target,
                })
            else:
                result.actions_failed += 1
                rollback_result = RollbackEngine.restore(snapshot)
                audit_entry = SandboxAuditEntry(
                    execution_id=ctx.execution_id,
                    workflow_id=workflow_id,
                    action_id=action_id,
                    mutation_class=mutation_class,
                    mutation_type=op_name,
                    target_path=resolved_target,
                    before_checksum=snapshot.checksum_sha256,
                    after_checksum=after_checksum,
                    rollback_available=False,
                    status="rollback",
                    error=f"mutation_failed_rollback: {rollback_result.reason}",
                )
                write_sandbox_audit(audit_entry)

                timeline.add_event("mutation_failed_rollback", "sandbox_write", {
                    "action_id": action_id, "step": action.step,
                    "error": stderr[:500],
                    "rollback_result": rollback_result.reason,
                })

        result.total_duration_ms = int((time.time() - t_start) * 1000)
        result.status = "completed" if result.actions_failed == 0 else "completed_with_failures"

        timeline.transition(WorkflowState.DONE)
        timeline.add_event("sandbox_execution_completed", "done", {
            "total_duration_ms": result.total_duration_ms,
            "actions_executed": result.actions_executed,
            "actions_failed": result.actions_failed,
            "execution_mode": ctx.mode.value,
        })

        return result


def _perform_mutation(op_name: str, target: str, action: WorkflowAction) -> tuple[int, str, str]:
    if op_name == "create_directory":
        return _execute_directory_creation(target)
    if op_name in ("write_json", "generate_config"):
        try:
            data = json.loads(action.description)
            return _execute_json_mutation(target, data)
        except (json.JSONDecodeError, TypeError):
            return _execute_file_mutation(target, action.description, "write")
    if op_name in ("write_yaml",):
        try:
            import yaml
            data = yaml.safe_load(action.description)
            parent = os.path.dirname(target)
            os.makedirs(parent, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            return 0, "", ""
        except Exception as e:
            return 1, "", str(e)
    return _execute_file_mutation(target, action.description, op_name)


def _blocked_result(action: WorkflowAction, reason: str) -> ActionResult:
    return ActionResult(
        action_id=action.action_id,
        step=action.step,
        tool=action.tool,
        intent=action.intent,
        exit_code=-1,
        stdout="",
        stderr=reason,
        duration_ms=0,
        simulated=False,
        status="blocked_by_governance",
    )


def _write_sandbox_audit_entry(ctx: RuntimeExecutionContext, action: WorkflowAction, ar_dict: dict, status: str) -> None:
    entry = SandboxAuditEntry(
        execution_id=ctx.execution_id,
        workflow_id=getattr(ctx, "execution_id", ""),
        action_id=action.action_id,
        mutation_class="",
        mutation_type="",
        target_path=action.description,
        status=status,
        error=ar_dict.get("stderr", ""),
    )
    write_sandbox_audit(entry)


def _get_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except Exception:
        return 0
