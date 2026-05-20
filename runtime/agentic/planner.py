"""FASE 28.1 — Planner Runtime Skeleton.

Extiende FASE 28.0.2 con DAG real, dependencias deterministas,
permission scopes, max_nodes, max_depth y governance hooks.

CRITICAL: En FASE 28.1 SOLO se generan planes readonly.
NO ejecucion real, NO writes, NO restarts.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from runtime.agentic.intents import ActionIntent, KNOWN_INTENTS, RiskHint
from runtime.agentic.permissions import PermissionScope, classify_permission_scope


PLAN_ID_SEED = "ai-lab-agentic-v1"

MAX_PLAN_NODES = 8
MAX_PLAN_DEPTH = 3

BLOCKED_INTENTS_IN_PLANNER: set[str] = {
    "modify_config", "create_file",
    "restart_service", "install_package", "run_command",
}

_KNOWN_CHECK_INTENTS = {
    "check_gateway_health", "check_runtime_status", "inspect_streams",
    "check_gpu_status", "analyze_timeouts", "check_models",
    "inspect_slo_state", "check_services",
}


@dataclass
class WorkflowAction:
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    step: int = 0
    dependencies: list[str] = field(default_factory=list)
    intent: str = ""
    tool: str = ""
    command: str = ""
    target: str = ""
    risk: str = RiskHint.LOW.value
    permission_scope: str = PermissionScope.READONLY.value
    rollback_possible: bool = True
    rollback_hint: str = ""
    expected_output: str = ""
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "step": self.step,
            "dependencies": self.dependencies,
            "intent": self.intent,
            "tool": self.tool,
            "command": self.command,
            "target": self.target,
            "risk": self.risk,
            "permission_scope": self.permission_scope,
            "rollback_possible": self.rollback_possible,
            "rollback_hint": self.rollback_hint,
            "expected_output": self.expected_output,
            "description": self.description,
        }


@dataclass
class AgenticPlan:
    plan_id: str = ""
    plan_hash: str = ""
    request_id: str = ""
    intents: list[dict] = field(default_factory=list)
    actions: list[WorkflowAction] = field(default_factory=list)
    is_simulation: bool = True
    dag_edges: list[tuple[str, str]] = field(default_factory=list)
    permission_scope: str = PermissionScope.READONLY.value
    requires_approval: bool = False
    max_nodes: int = MAX_PLAN_NODES
    max_depth: int = MAX_PLAN_DEPTH
    governance_result: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
            "request_id": self.request_id,
            "intents": self.intents,
            "actions": [a.to_dict() for a in self.actions],
            "action_count": len(self.actions),
            "dag_edges": self.dag_edges,
            "permission_scope": self.permission_scope,
            "requires_approval": self.requires_approval,
            "max_nodes": self.max_nodes,
            "max_depth": self.max_depth,
            "governance_result": self.governance_result,
            "is_simulation": self.is_simulation,
        }


def _compute_depth(action_id: str, edges: list[tuple[str, str]], depth_cache: dict) -> int:
    if action_id in depth_cache:
        return depth_cache[action_id]
    max_dep = 0
    for src, dst in edges:
        if dst == action_id:
            dep = _compute_depth(src, edges, depth_cache) + 1
            if dep > max_dep:
                max_dep = dep
    depth_cache[action_id] = max_dep
    return max_dep


def build_dag(actions: list[WorkflowAction]) -> list[tuple[str, str]]:
    edges: list[tuple[str, str]] = []
    action_ids = {a.action_id for a in actions}
    for action in actions:
        for dep_id in action.dependencies:
            if dep_id in action_ids:
                edges.append((dep_id, action.action_id))
    return edges


class Planner:
    """Normalizes ActionIntents into a deterministic AgenticPlan."""

    @staticmethod
    def generate_plan_id(intents: list[ActionIntent]) -> str:
        seed = json.dumps([i.to_dict() for i in intents], sort_keys=True)
        h = hashlib.sha256(f"{PLAN_ID_SEED}:{seed}".encode()).hexdigest()[:12]
        return f"plan-{h}"

    @staticmethod
    def plan(intents: list[ActionIntent], request_id: str = "") -> AgenticPlan | None:
        if not intents:
            return None

        # Reject blocked intents in 28.1
        for intent in intents:
            if intent.intent in BLOCKED_INTENTS_IN_PLANNER:
                return None
            if intent.intent not in KNOWN_INTENTS:
                return None

        plan_id = Planner.generate_plan_id(intents)
        actions: list[WorkflowAction] = []
        step = 0

        for intent in intents:
            info = KNOWN_INTENTS.get(intent.intent, {})
            base_risk = info.get("risk", RiskHint.LOW)
            default_scope = classify_permission_scope(intent.intent, "read", intent.target).value

            if intent.intent in ("read_config", "read_state", "read_logs", "validate_syntax"):
                step += 1
                actions.append(WorkflowAction(
                    step=step,
                    intent=intent.intent,
                    tool="read",
                    target=intent.target,
                    risk=base_risk.value,
                    permission_scope=default_scope,
                    expected_output="file contents or state data",
                    description=f"Leer {intent.target}",
                ))

            elif intent.intent == "observe_runtime":
                step += 1
                actions.append(WorkflowAction(
                    step=step,
                    intent=intent.intent,
                    tool="read",
                    target="/opt/ai-lab/runtime/state/cluster_state.json",
                    risk=RiskHint.LOW.value,
                    permission_scope=default_scope,
                    expected_output="runtime state snapshot",
                    description="Consultar estado del runtime",
                ))

            elif intent.intent in _KNOWN_CHECK_INTENTS:
                step += 1
                actions.append(WorkflowAction(
                    step=step,
                    intent=intent.intent,
                    tool="check",
                    target=intent.target or intent.intent.replace("_", " "),
                    risk=RiskHint.LOW.value,
                    permission_scope=default_scope,
                    expected_output=f"{intent.intent} check results",
                    description=f"Verificar {intent.intent.replace('_', ' ')}",
                ))

            else:
                step += 1
                actions.append(WorkflowAction(
                    step=step,
                    intent=intent.intent,
                    tool="read",
                    target=intent.target or ".",
                    risk=RiskHint.LOW.value,
                    permission_scope=default_scope,
                    description=f"Accion: {intent.goal[:100]}",
                ))

            if step >= MAX_PLAN_NODES:
                break

        # Enforce max depth: truncate deep dependency chains
        dag_edges = build_dag(actions)
        depth_cache: dict[str, int] = {}
        pruned: set[str] = set()
        for action in actions:
            d = _compute_depth(action.action_id, dag_edges, depth_cache)
            if d > MAX_PLAN_DEPTH:
                pruned.add(action.action_id)
        if pruned:
            actions = [a for a in actions if a.action_id not in pruned]
            dag_edges = build_dag(actions)

        plan_hash = hashlib.sha256(
            json.dumps([a.to_dict() for a in actions], sort_keys=True).encode()
        ).hexdigest()[:16]

        plan_scope = PermissionScope.READONLY.value
        for action in actions:
            action_scope = classify_permission_scope(action.intent, action.tool, action.target).value
            if action_scope != PermissionScope.READONLY.value:
                plan_scope = PermissionScope.FORBIDDEN.value
                break

        return AgenticPlan(
            plan_id=plan_id,
            plan_hash=plan_hash,
            request_id=request_id,
            intents=[i.to_dict() for i in intents],
            actions=actions,
            dag_edges=dag_edges,
            permission_scope=plan_scope,
            requires_approval=False,
            is_simulation=True,
        )
