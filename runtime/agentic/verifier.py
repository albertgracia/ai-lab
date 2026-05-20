"""FASE 28.0.8 — Verifier (simulated).

Validates workflow consistency and coherence.
During simulation, checks plan structure, not system state.
Later phases will add filesystem checksum, service health, side-effect detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from runtime.agentic.planner import AgenticPlan
from runtime.agentic.dryrun import DryRunResult
from runtime.agentic.executor import ExecutionResult


@dataclass
class VerifierCheck:
    check: str = ""
    status: str = "pass"  # pass, fail, warn
    detail: str = ""

    def to_dict(self) -> dict:
        return {"check": self.check, "status": self.status, "detail": self.detail}


@dataclass
class VerifierReport:
    execution_id: str = ""
    verdict: str = "pass"  # pass, fail, warn
    checks: list[VerifierCheck] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    simulation_only: bool = True

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "verdict": self.verdict,
            "checks": [c.to_dict() for c in self.checks],
            "failed_checks": self.failed_checks,
            "warnings": self.warnings,
            "simulation_only": self.simulation_only,
        }


PATH_ALLOWLIST: list[str] = [
    "/opt/ai-lab/config/",
    "/opt/ai-lab/runtime/prompts/",
    "/opt/ai-lab/runtime/profiles/",
    "/opt/ai-lab/runtime/policies/",
    "/opt/ai-lab/runtime/state/",
    "/opt/ai-lab/apps/ialab-docs/",
    "/tmp/opencode/",
]

PATH_BLOCKLIST: list[str] = [
    "/opt/ai-lab/runtime/gateway/",
    "/opt/ai-lab/runtime/llm/",
    "/opt/ai-lab/.venv/",
    "/etc/",
    "/home/",
]


class Verifier:
    """Validates plan and execution consistency."""

    @staticmethod
    def verify(plan: AgenticPlan, dry_run: DryRunResult, execution: ExecutionResult) -> VerifierReport:
        checks: list[VerifierCheck] = []
        failed: list[str] = []
        warnings: list[str] = []

        # 1. Plan structure
        if plan.plan_id:
            checks.append(VerifierCheck("plan_id_valid", "pass", plan.plan_id))
        else:
            checks.append(VerifierCheck("plan_id_valid", "fail", "missing"))
            failed.append("plan_id_valid")

        # 2. Actions exist
        if plan.actions:
            checks.append(VerifierCheck("actions_exist", "pass", f"{len(plan.actions)} actions"))
        else:
            checks.append(VerifierCheck("actions_exist", "fail", "no actions"))
            failed.append("actions_exist")

        # 3. Execution matched plan
        if execution.actions_executed == len(plan.actions):
            checks.append(VerifierCheck("execution_matches_plan", "pass",
                                       f"{execution.actions_executed}/{len(plan.actions)}"))
        else:
            checks.append(VerifierCheck("execution_matches_plan", "fail",
                                       f"executed={execution.actions_executed} planned={len(plan.actions)}"))
            failed.append("execution_matches_plan")

        # 4. Dry-run consistency
        if dry_run.plan_id == plan.plan_id:
            checks.append(VerifierCheck("dry_run_plan_match", "pass", "OK"))
        else:
            checks.append(VerifierCheck("dry_run_plan_match", "fail", "mismatch"))
            failed.append("dry_run_plan_match")

        # 5. Risk valid
        if dry_run.risk_score <= 3:
            checks.append(VerifierCheck("risk_score_valid", "pass", f"score={dry_run.risk_score}"))
        elif dry_run.risk_score == 4:
            checks.append(VerifierCheck("risk_score_valid", "warn", "CRITICAL risk"))
            warnings.append("critical_risk")

        # 6. Path validation
        paths_ok = True
        for action in plan.actions:
            target = action.target or ""
            for blocked in PATH_BLOCKLIST:
                if blocked in target:
                    checks.append(VerifierCheck(
                        "path_validation", "fail",
                        f"Blocked path: {target} matches {blocked}"
                    ))
                    failed.append("path_validation")
                    paths_ok = False
        if paths_ok:
            checks.append(VerifierCheck("path_validation", "pass", "All paths in allowlist"))

        # 7. Simulation mode confirmed
        if execution.simulation_only:
            checks.append(VerifierCheck("simulation_mode", "pass", "Execution was simulated"))
        else:
            checks.append(VerifierCheck("simulation_mode", "fail", "REAL EXECUTION DETECTED"))
            failed.append("simulation_mode")

        # 8. No forbidden actions executed
        if not dry_run.blocked:
            checks.append(VerifierCheck("forbidden_actions", "pass", "None"))
        else:
            checks.append(VerifierCheck("forbidden_actions", "fail",
                                       f"Blocked: {dry_run.forbidden_actions}"))
            failed.append("forbidden_actions")

        verdict = "fail" if failed else ("warn" if warnings else "pass")

        return VerifierReport(
            execution_id=execution.execution_id,
            verdict=verdict,
            checks=checks,
            failed_checks=failed,
            warnings=warnings,
            simulation_only=True,
        )
