"""FASE 28.1 — Governance Pre-Hooks.

Interfaces de governance que se activaran en FASE 28.2+.
En FASE 28.1 solo validan e informan, NO ejecutan policies destructivas.

Reglas 28.1:
- permission_scope != READONLY → allowed=False
- patrones prohibidos → allowed=False
- intents no reconocidos → allowed=False
- requires_approval=False (planes readonly no requieren aprobacion)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from runtime.agentic.planner import AgenticPlan, WorkflowAction
from runtime.agentic.permissions import (
    PermissionScope,
    classify_permission_scope,
    is_scope_allowed_in_phase,
)

_FORBIDDEN_ACTION_TOKENS: set[str] = {
    "rm -rf", "mkfs", "shutdown", "reboot", "dd if=",
    "chmod", "sudo", "systemctl stop", "systemctl disable",
    "docker stop", "docker rm", "docker kill",
    "curl | bash", "curl | sh",
    "ignore previous",
}

_RECURSION_TOKENS: set[str] = {
    "planner", "self-modify", "self-heal",
}

_CURRENT_PHASE = "28.1"


@dataclass
class GovernanceResult:
    plan_id: str = ""
    allowed: bool = True
    permission_scope: str = PermissionScope.READONLY.value
    blocked_reasons: list[str] = field(default_factory=list)
    requires_approval: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "allowed": self.allowed,
            "permission_scope": self.permission_scope,
            "blocked_reasons": self.blocked_reasons,
            "requires_approval": self.requires_approval,
            "warnings": self.warnings,
        }


def _check_forbidden_tokens(text: str, tokens: set[str]) -> list[str]:
    found: list[str] = []
    lower = text.lower()
    for token in tokens:
        if token in lower:
            found.append(token)
    return found


def detect_forbidden_actions(plan: AgenticPlan) -> list[str]:
    blocked_ids: list[str] = []
    for action in plan.actions:
        cmd = (action.command or "").lower()
        target = (action.target or "").lower()
        desc = (action.description or "").lower()
        combined = f"{cmd} {target} {desc}"

        found = _check_forbidden_tokens(combined, _FORBIDDEN_ACTION_TOKENS)
        if found:
            blocked_ids.append(action.action_id)

        found_rec = _check_forbidden_tokens(combined, _RECURSION_TOKENS)
        if found_rec:
            blocked_ids.append(action.action_id)

    return blocked_ids


def classify_permissions(plan: AgenticPlan) -> PermissionScope:
    overall = PermissionScope.READONLY
    for action in plan.actions:
        scope = classify_permission_scope(action.intent, action.tool, action.target)
        if scope == PermissionScope.FORBIDDEN:
            return PermissionScope.FORBIDDEN
        if scope != PermissionScope.READONLY:
            overall = scope
    return overall


def validate_plan_against_policy(plan: AgenticPlan) -> GovernanceResult:
    result = GovernanceResult(plan_id=plan.plan_id)

    # 1. Permission scope check
    scope = classify_permissions(plan)
    result.permission_scope = scope.value

    if not is_scope_allowed_in_phase(scope, _CURRENT_PHASE):
        result.allowed = False
        result.blocked_reasons.append(
            f"scope_not_allowed_in_phase_{_CURRENT_PHASE}: {scope.value}"
        )

    # 2. Forbidden actions detection
    forbidden = detect_forbidden_actions(plan)
    if forbidden:
        result.allowed = False
        result.blocked_reasons.append(f"forbidden_actions_detected: {forbidden}")

    # 3. Intent not recognized
    if not plan.actions:
        result.allowed = False
        result.blocked_reasons.append("intent_not_recognized")

    # 4. Max nodes enforcement
    if len(plan.actions) > plan.max_nodes:
        result.warnings.append(f"plan_truncated_to_max_{plan.max_nodes}_nodes")

    # 5. In 28.1, readonly plans don't need approval
    result.requires_approval = False

    return result
