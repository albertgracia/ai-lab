from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from runtime.agentic.executor import SimulationExecutor, ExecutionResult, ActionResult
from runtime.agentic.planner import AgenticPlan
from runtime.agentic.workflow_state import WorkflowState, WorkflowTimeline
from runtime.agentic.execution_context import (
    ExecutionMode,
    DryRunReason,
    RuntimeExecutionContext,
    CURRENT_EXECUTION_MODE,
)
from runtime.agentic.safe_runner import run_safe, SafeRunnerResult
from runtime.agentic.readonly_policies import check_governance, assess_risk
from runtime.agentic.execution_audit import build_audit_entry, write_execution_audit


ENABLE_EXECUTOR = False
DRY_RUN = True


class RealReadonlyExecutor:
    @staticmethod
    def execute(
        plan: AgenticPlan,
        timeline: WorkflowTimeline,
        ctx: RuntimeExecutionContext | None = None,
    ) -> ExecutionResult:
        if ctx is None:
            ctx = RuntimeExecutionContext(
                execution_id=uuid.uuid4().hex[:8],
                mode=CURRENT_EXECUTION_MODE,
                dry_run=DRY_RUN,
            )

        if not ENABLE_EXECUTOR or DRY_RUN:
            reason = ctx.dry_run_reason or DryRunReason.FEATURE_FLAG.value
            if DRY_RUN:
                reason = DryRunReason.READONLY_PHASE.value
            ctx.dry_run_reason = reason
            sim_result = SimulationExecutor.execute_with_context(plan, timeline, ctx)
            return sim_result

        t_start = time.time()
        result = ExecutionResult(
            plan_id=plan.plan_id,
            simulation_only=False,
            timeline=timeline,
        )

        timeline.transition(WorkflowState.SIMULATING)
        timeline.add_event("execution_started", "readonly", {
            "action_count": len(plan.actions),
            "execution_mode": ctx.mode.value,
        })

        for action in plan.actions:
            action_start = time.time()
            gov = check_governance(action.intent, action.description, ctx.phase)

            if not gov.allowed:
                ar = ActionResult(
                    action_id=action.action_id,
                    step=action.step,
                    tool=action.tool,
                    intent=action.intent,
                    exit_code=-1,
                    stdout="",
                    stderr=gov.reason,
                    duration_ms=0,
                    simulated=False,
                    status="blocked_by_governance",
                )
                result.actions_results.append(ar)
                result.actions_failed += 1
                result.actions_executed += 1
                timeline.add_event("action_blocked", "readonly", {
                    "action_id": action.action_id,
                    "step": action.step,
                    "intent": action.intent,
                    "reason": gov.reason,
                })
                _write_audit(ctx, action, ar.to_dict())
                continue

            runner_result: SafeRunnerResult = run_safe(action.description)
            duration_ms = int((time.time() - action_start) * 1000)

            ar = ActionResult(
                action_id=action.action_id,
                step=action.step,
                tool=action.tool,
                intent=action.intent,
                exit_code=runner_result.exit_code,
                stdout=runner_result.stdout[:2000],
                stderr=runner_result.stderr[:1000],
                duration_ms=duration_ms,
                simulated=False,
                status="success" if runner_result.exit_code == 0 and not runner_result.blocked else "failed",
            )
            result.actions_results.append(ar)
            result.actions_executed += 1
            if ar.status == "failed":
                result.actions_failed += 1

            timeline.add_event("action_executed", "readonly", {
                "action_id": action.action_id,
                "step": action.step,
                "status": ar.status,
                "exit_code": runner_result.exit_code,
                "duration_ms": duration_ms,
                "stdout_hash": runner_result.stdout_hash,
                "stderr_hash": runner_result.stderr_hash,
            })

        result.total_duration_ms = int((time.time() - t_start) * 1000)
        result.status = "completed" if result.actions_failed == 0 else "completed_with_failures"

        timeline.transition(WorkflowState.DONE)
        timeline.add_event("execution_completed", "done", {
            "total_duration_ms": result.total_duration_ms,
            "actions_executed": result.actions_executed,
            "actions_failed": result.actions_failed,
            "execution_mode": ctx.mode.value,
        })

        return result


def _write_audit(ctx: RuntimeExecutionContext, action: Any, action_result: dict) -> None:
    entry = build_audit_entry(
        execution_id=ctx.execution_id,
        plan_id=action.plan_id if hasattr(action, "plan_id") else "",
        mode=ctx.mode.value,
        dry_run=ctx.dry_run,
        dry_run_reason=ctx.dry_run_reason,
        action={
            "step": action.step if hasattr(action, "step") else 0,
            "intent": action.intent if hasattr(action, "intent") else "",
            "tool": action.tool if hasattr(action, "tool") else "",
            "command": action.description if hasattr(action, "description") else "",
        },
        result=action_result,
    )
    write_execution_audit(entry)
