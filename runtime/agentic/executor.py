"""FASE 28.0.7 — Simulation Executor.

Executes agentic workflows in SIMULATION-ONLY mode.
When AGENTIC_EXECUTION_ENABLED=false, ALL actions are no-ops.
Records everything for replay.

CRITICAL: This executor NEVER runs real bash, writes, or restarts during simulation.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from runtime.agentic.planner import AgenticPlan, WorkflowAction
from runtime.agentic.workflow_state import WorkflowState, WorkflowTimeline
from runtime.agentic.execution_context import RuntimeExecutionContext


EXECUTION_MODE = "simulation_only"


@dataclass
class ActionResult:
    action_id: str = ""
    step: int = 0
    tool: str = ""
    intent: str = ""
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    simulated: bool = True
    status: str = "simulated_success"

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "step": self.step,
            "tool": self.tool,
            "intent": self.intent,
            "exit_code": self.exit_code,
            "stdout": self.stdout[:500] if self.stdout else "",
            "stderr": self.stderr[:500] if self.stderr else "",
            "duration_ms": self.duration_ms,
            "simulated": self.simulated,
            "status": self.status,
        }


@dataclass
class ExecutionResult:
    execution_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    plan_id: str = ""
    status: str = "simulated_success"
    actions_executed: int = 0
    actions_failed: int = 0
    actions_results: list[ActionResult] = field(default_factory=list)
    total_duration_ms: int = 0
    simulation_only: bool = True
    timeline: WorkflowTimeline | None = None

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "status": self.status,
            "actions_executed": self.actions_executed,
            "actions_failed": self.actions_failed,
            "actions_results": [r.to_dict() for r in self.actions_results],
            "total_duration_ms": self.total_duration_ms,
            "simulation_only": self.simulation_only,
        }


class SimulationExecutor:
    """Executes plans in simulation mode. NEVER runs real commands."""

    @staticmethod
    def execute(plan: AgenticPlan, timeline: WorkflowTimeline) -> ExecutionResult:
        t_start = time.time()

        result = ExecutionResult(
            plan_id=plan.plan_id,
            simulation_only=True,
            timeline=timeline,
        )

        timeline.transition(WorkflowState.SIMULATING)
        timeline.add_event("execution_started", "simulating", {
            "action_count": len(plan.actions),
        })

        for action in plan.actions:
            action_start = time.time()

            ar = ActionResult(
                action_id=action.action_id,
                step=action.step,
                tool=action.tool,
                intent=action.intent,
                exit_code=0,
                stdout=f"[SIMULATED] {action.description}",
                stderr="",
                duration_ms=10,
                simulated=True,
                status="simulated_success",
            )
            result.actions_results.append(ar)
            result.actions_executed += 1

            timeline.add_event("action_simulated", "simulating", {
                "action_id": action.action_id,
                "step": action.step,
                "tool": action.tool,
                "intent": action.intent,
                "duration_ms": int((time.time() - action_start) * 1000),
            })

        result.total_duration_ms = int((time.time() - t_start) * 1000)
        result.status = "simulated_success"

        timeline.transition(WorkflowState.DONE)
        timeline.add_event("execution_completed", "done", {
            "total_duration_ms": result.total_duration_ms,
            "actions_executed": result.actions_executed,
        })

        return result

    @staticmethod
    def execute_with_context(plan: AgenticPlan, timeline: WorkflowTimeline, ctx: RuntimeExecutionContext) -> ExecutionResult:
        result = SimulationExecutor.execute(plan, timeline)
        result.simulation_only = True
        timeline.add_event("dry_run_reason", "simulating", {
            "reason": ctx.dry_run_reason or "feature_flag",
            "execution_mode": ctx.mode.value,
            "phase": ctx.phase,
        })
        return result
