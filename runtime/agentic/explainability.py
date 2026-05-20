"""FASE 28.0.5 — Human Explainability Layer.

Generates natural-language summaries of agentic plans BEFORE asking for approval.
Reduces approval fatigue and prevents blind approvals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from runtime.agentic.planner import AgenticPlan
from runtime.agentic.dryrun import DryRunResult


@dataclass
class ExplainabilityReport:
    plan_id: str = ""
    goal: str = ""
    summary: str = ""
    actions_narrative: list[str] = field(default_factory=list)
    risk_level: str = "LOW"
    risk_reasons: list[str] = field(default_factory=list)
    files_affected: list[str] = field(default_factory=list)
    services_affected: list[str] = field(default_factory=list)
    rollback_available: bool = True
    rollback_method: str = ""
    rollback_caveats: list[str] = field(default_factory=list)
    approval_type: str = ""
    approval_ttl: str = ""
    dry_run_ok: bool = True
    governance_ok: bool = True
    simulation_only: bool = True
    blocked: bool = False
    blocked_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "summary": self.summary,
            "actions_narrative": self.actions_narrative,
            "risk_level": self.risk_level,
            "risk_reasons": self.risk_reasons,
            "files_affected": self.files_affected,
            "services_affected": self.services_affected,
            "rollback_available": self.rollback_available,
            "rollback_method": self.rollback_method,
            "rollback_caveats": self.rollback_caveats,
            "approval_type": self.approval_type,
            "approval_ttl": self.approval_ttl,
            "dry_run_ok": self.dry_run_ok,
            "governance_ok": self.governance_ok,
            "simulation_only": self.simulation_only,
            "blocked": self.blocked,
            "blocked_reasons": self.blocked_reasons,
        }

    def to_markdown(self) -> str:
        lines: list[str] = []
        lines.append("🤖 **AI-LAB Agent propone el siguiente workflow:**")
        lines.append("")

        if self.blocked:
            lines.append("🚫 **WORKFLOW BLOQUEADO**")
            for reason in self.blocked_reasons:
                lines.append(f"- {reason}")
            lines.append("")
            return "\n".join(lines)

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("📋 RESUMEN")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"Objetivo: {self.goal}")
        lines.append("")
        lines.append("Acciones propuestas:")
        for action in self.actions_narrative:
            lines.append(f"  {action}")
        lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"⚠️  RIESGO: {self.risk_level}")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        if self.risk_reasons:
            lines.append("Razones de riesgo:")
            for reason in self.risk_reasons:
                lines.append(f"  - {reason}")
            lines.append("")

        if self.files_affected:
            lines.append("Archivos afectados:")
            for f in self.files_affected:
                lines.append(f"  {'✎' if any('change' in a.lower() for a in self.actions_narrative) else '📄'} {f}")
            lines.append("")

        if self.services_affected:
            lines.append("Servicios afectados:")
            for s in self.services_affected:
                lines.append(f"  ↻ {s}")
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("🔙 ROLLBACK")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"Rollback posible: {'SÍ' if self.rollback_available else 'NO'}")
        if self.rollback_method:
            lines.append(f"Método: {self.rollback_method}")
        if self.rollback_caveats:
            lines.append("Notas:")
            for caveat in self.rollback_caveats:
                lines.append(f"  - {caveat}")
        lines.append("")

        if self.requires_approval():
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append("🔐 APPROVAL REQUERIDO")
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append(f"Tipo: {self.approval_type}")
            lines.append(f"Expira en: {self.approval_ttl}")
            lines.append("")

        if self.simulation_only:
            lines.append("💡 *Modo simulación — no se ejecutará nada real.*")
            lines.append("")

        return "\n".join(lines)

    def requires_approval(self) -> bool:
        return self.approval_type not in ("", "none")


TTL_MAP: dict[str, str] = {
    "workspace_write": "5 minutos",
    "runtime_write": "2 minutos",
    "privileged": "1 minuto",
    "none": "N/A",
}


class ExplainabilityEngine:
    """Generates human-readable explanations of agentic plans."""

    @staticmethod
    def explain(plan: AgenticPlan, dry_run: DryRunResult) -> ExplainabilityReport:
        goal = plan.intents[0]["goal"] if plan.intents else "Sin objetivo definido"

        actions_narrative: list[str] = []
        for i, action in enumerate(plan.actions, 1):
            actions_narrative.append(f"{i}. {action.description}")

        report = ExplainabilityReport(
            plan_id=plan.plan_id,
            goal=goal,
            summary=f"{len(plan.actions)} acciones para: {goal[:80]}",
            actions_narrative=actions_narrative,
            risk_level=dry_run.overall_risk,
            risk_reasons=dry_run.risk_reasons,
            files_affected=dry_run.files_affected,
            services_affected=dry_run.services_affected,
            rollback_available=dry_run.rollback_possible,
            rollback_method="Restaurar archivos desde snapshots pre-ejecucion",
            rollback_caveats=dry_run.rollback_caveats,
            approval_type=dry_run.approval_type,
            approval_ttl=TTL_MAP.get(dry_run.approval_type, "N/A"),
            dry_run_ok=True,
            governance_ok=not dry_run.blocked,
            simulation_only=True,
            blocked=dry_run.blocked,
            blocked_reasons=[f"Accion prohibida: {aid}" for aid in dry_run.forbidden_actions],
        )
        return report
