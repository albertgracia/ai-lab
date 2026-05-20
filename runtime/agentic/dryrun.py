"""FASE 28.0.4 — Dry-Run Engine.

Simulates the entire workflow WITHOUT any real execution.
Produces a detailed preview of what WOULD happen.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from runtime.agentic.planner import AgenticPlan, WorkflowAction
from runtime.agentic.risk_engine import RiskEngine, RiskAssessment


@dataclass
class DryRunResult:
    plan_id: str = ""
    plan_hash: str = ""
    simulation_only: bool = True
    generated_at: float = field(default_factory=time.time)
    overall_risk: str = ""
    risk_score: int = 0
    risk_reasons: list[str] = field(default_factory=list)
    requires_approval: bool = False
    approval_type: str = ""
    actions_preview: list[dict] = field(default_factory=list)
    would_change: list[dict] = field(default_factory=list)
    files_affected: list[str] = field(default_factory=list)
    services_affected: list[str] = field(default_factory=list)
    rollback_possible: bool = True
    rollback_caveats: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    estimated_total_ms: int = 0
    forbidden_actions: list[str] = field(default_factory=list)
    blocked: bool = False

    def to_dict(self) -> dict:
        return {
            "dry_run": True,
            "simulation_only": self.simulation_only,
            "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
            "generated_at": self.generated_at,
            "overall_risk": self.overall_risk,
            "risk_score": self.risk_score,
            "risk_reasons": self.risk_reasons,
            "requires_approval": self.requires_approval,
            "approval_type": self.approval_type,
            "actions_preview": self.actions_preview,
            "would_change": self.would_change,
            "files_affected": self.files_affected,
            "services_affected": self.services_affected,
            "rollback_possible": self.rollback_possible,
            "rollback_caveats": self.rollback_caveats,
            "warnings": self.warnings,
            "estimated_total_ms": self.estimated_total_ms,
            "forbidden_actions": self.forbidden_actions,
            "blocked": self.blocked,
        }


class DryRunEngine:
    """Simulates execution without touching the real system."""

    ESTIMATED_MS_PER_ACTION: dict[str, int] = {
        "read": 50,
        "edit": 100,
        "write": 100,
        "bash": 1000,
        "glob": 30,
        "grep": 40,
    }

    @staticmethod
    def run(plan: AgenticPlan) -> DryRunResult:
        risk = RiskEngine.assess(plan)

        actions_preview: list[dict] = []
        would_change: list[dict] = []
        files_affected: list[str] = []
        services_affected: list[str] = []
        rollback_caveats: list[str] = []
        warnings: list[str] = []
        estimated_ms = 0

        for action in plan.actions:
            tool_ms = DryRunEngine.ESTIMATED_MS_PER_ACTION.get(action.tool, 200)
            estimated_ms += tool_ms

            preview = {
                "action_id": action.action_id,
                "step": action.step,
                "intent": action.intent,
                "tool": action.tool,
                "target": action.target,
                "command": action.command,
                "risk": action.risk,
                "description": action.description,
                "estimated_ms": tool_ms,
                "rollback_possible": action.rollback_possible,
            }
            actions_preview.append(preview)

            if action.tool in ("write", "edit"):
                would_change.append({
                    "action_id": action.action_id,
                    "target": action.target,
                    "tool": action.tool,
                    "description": action.description,
                })
                if action.target and action.target not in files_affected:
                    files_affected.append(action.target)

            if action.tool == "read" and action.target:
                if action.target not in files_affected:
                    files_affected.append(action.target)

            if action.tool == "bash" and "systemctl" in (action.command or ""):
                svc = action.target or action.command.split()[-1] if action.command else "unknown"
                services_affected.append(svc)
                if not action.rollback_possible:
                    rollback_caveats.append(
                        f"Action {action.action_id}: restart de {svc} no tiene rollback automatico"
                    )

            if action.tool == "bash" and action.intent == "install_package":
                rollback_caveats.append(
                    f"Action {action.action_id}: instalacion de paquetes requiere rollback manual"
                )

        return DryRunResult(
            plan_id=plan.plan_id,
            plan_hash=plan.plan_hash,
            simulation_only=True,
            overall_risk=risk.overall_risk,
            risk_score=risk.risk_score,
            risk_reasons=risk.risk_reasons,
            requires_approval=risk.requires_approval,
            approval_type=risk.approval_type,
            actions_preview=actions_preview,
            would_change=would_change,
            files_affected=list(dict.fromkeys(files_affected)),
            services_affected=list(dict.fromkeys(services_affected)),
            rollback_possible=len(rollback_caveats) == 0,
            rollback_caveats=rollback_caveats,
            warnings=warnings,
            estimated_total_ms=estimated_ms,
            forbidden_actions=risk.forbidden_actions,
            blocked=risk.blocked,
        )
