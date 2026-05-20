"""FASE 28.1 — Planner Runtime Skeleton tests.

Ejecutar: python3 -m pytest tests/test_planner_28_1.py -v
O: python3 tests/test_planner_28_1.py
"""

import sys
import json
sys.path.insert(0, "/opt/ai-lab")

from runtime.agentic.intents import ActionIntent, IntentParser
from runtime.agentic.planner import Planner, MAX_PLAN_NODES, MAX_PLAN_DEPTH, BLOCKED_INTENTS_IN_PLANNER
from runtime.agentic.governance_hooks import (
    validate_plan_against_policy,
    classify_permissions,
    detect_forbidden_actions,
    GovernanceResult,
)
from runtime.agentic.permissions import (
    PermissionScope,
    classify_permission_scope,
    is_scope_allowed_in_phase,
)
from runtime.agentic.workflow_state import WorkflowState, VALID_TRANSITIONS


PASS = 0
FAIL = 0


def _check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}: {detail}")


# ── 1. Plan readonly válido ──────────────────────────────────

def test_readonly_plan_valid():
    intents = [ActionIntent(intent="check_gateway_health", goal="revisa el gateway")]
    plan = Planner.plan(intents)
    _check("plan created", plan is not None)
    if plan:
        _check("plan has plan_id", bool(plan.plan_id))
        _check("plan has actions", len(plan.actions) > 0)
        _check("dag_edges is list", isinstance(plan.dag_edges, list))
        _check("permission_scope is readonly", plan.permission_scope == PermissionScope.READONLY.value)
        _check("is_simulation", plan.is_simulation)
        _check("requires_approval is False", not plan.requires_approval)


# ── 2. DAG dependencies ──────────────────────────────────────

def test_readonly_dependencies():
    intents = [
        ActionIntent(intent="check_runtime_status", goal="revisa el runtime"),
    ]
    plan = Planner.plan(intents)
    _check("plan created with deps", plan is not None and len(plan.actions) > 0)
    if plan:
        deps_valid = all(
            isinstance(a.dependencies, list)
            for a in plan.actions
        )
        _check("all actions have dependencies list", deps_valid)
        edges_valid = all(
            len(e) == 2 and isinstance(e[0], str) and isinstance(e[1], str)
            for e in plan.dag_edges
        )
        _check("dag_edges are valid tuples", edges_valid)


# ── 3. Ambiguous prompt ──────────────────────────────────────

def test_ambiguous_prompt():
    intents = [ActionIntent(intent="unknown_intent_xyz", goal="haz algo")]
    plan = Planner.plan(intents)
    _check("ambiguous intent returns None", plan is None)


# ── 4. Malicious write ───────────────────────────────────────

def test_malicious_write():
    intents = [ActionIntent(intent="modify_config", goal="escribe en /etc/config", target="/etc/config")]
    plan = Planner.plan(intents)
    _check("write intent blocked in planner", plan is None)


# ── 5. Sudo attempt ──────────────────────────────────────────

def test_sudo_attempt():
    intent = ActionIntent(intent="modify_config", goal="sudo systemctl restart ailab-gateway")
    scope = classify_permission_scope(intent.intent, "bash", intent.target)
    _check("sudo intent classified as FORBIDDEN", scope == PermissionScope.FORBIDDEN)
    allowed = is_scope_allowed_in_phase(scope, "28.1")
    _check("FORBIDDEN not allowed in 28.1", not allowed)


# ── 6. Docker mutation ───────────────────────────────────────

def test_docker_mutation():
    goal = "docker rm container"
    from runtime.agentic.intents import FORBIDDEN_INTENT_PATTERNS
    found = any(p in goal.lower() for p in FORBIDDEN_INTENT_PATTERNS)
    _check("docker rm detected in forbidden patterns", found)


# ── 7. Planner recursion ─────────────────────────────────────

def test_recursive_planner():
    goal = "usa el planner para crear otro planner"
    from runtime.agentic.intents import FORBIDDEN_INTENT_PATTERNS
    found = any(p in goal.lower() for p in FORBIDDEN_INTENT_PATTERNS)
    _check("planner recursion detected in forbidden patterns", found)


# ── 8. Permission scope classify ──────────────────────────────

def test_permission_scope_readonly():
    scope = classify_permission_scope("check_gateway_health", "check", "")
    _check("check_gateway_health is READONLY", scope == PermissionScope.READONLY)
    scope2 = classify_permission_scope("read_config", "read", "/opt/ai-lab/config/")
    _check("read_config is READONLY", scope2 == PermissionScope.READONLY)


# ── 9. Permission scope forbidden ────────────────────────────

def test_permission_scope_forbidden():
    scope = classify_permission_scope("restart_service", "bash", "ailab-gateway")
    _check("restart_service is FORBIDDEN", scope == PermissionScope.FORBIDDEN)
    scope2 = classify_permission_scope("install_package", "bash", "")
    _check("install_package is FORBIDDEN", scope2 == PermissionScope.FORBIDDEN)
    scope3 = classify_permission_scope("modify_config", "edit", "/etc/config")
    _check("modify_config with edit is FORBIDDEN", scope3 == PermissionScope.FORBIDDEN)


# ── 10. Max nodes enforced ───────────────────────────────────

def test_max_nodes_enforced():
    many_intents = [
        ActionIntent(intent="check_gateway_health", goal="a"),
        ActionIntent(intent="check_runtime_status", goal="b"),
        ActionIntent(intent="inspect_streams", goal="c"),
        ActionIntent(intent="check_gpu_status", goal="d"),
        ActionIntent(intent="analyze_timeouts", goal="e"),
        ActionIntent(intent="check_models", goal="f"),
        ActionIntent(intent="inspect_slo_state", goal="g"),
        ActionIntent(intent="check_services", goal="h"),
        ActionIntent(intent="check_gateway_health", goal="i"),
        ActionIntent(intent="check_runtime_status", goal="j"),
        ActionIntent(intent="inspect_streams", goal="k"),
    ]
    plan = Planner.plan(many_intents)
    _check("plan created", plan is not None)
    if plan:
        _check(f"actions <= {MAX_PLAN_NODES}", len(plan.actions) <= MAX_PLAN_NODES)
        _check(f"actions == {MAX_PLAN_NODES} (full)", len(plan.actions) == MAX_PLAN_NODES)


# ── 11. Max depth enforced ───────────────────────────────────

def test_max_depth_enforced():
    intents = [
        ActionIntent(intent="check_gateway_health", goal="a"),
        ActionIntent(intent="check_runtime_status", goal="b"),
    ]
    plan = Planner.plan(intents)
    _check("plan created", plan is not None)
    if plan:
        from runtime.agentic.planner import _compute_depth
        depth_cache: dict = {}
        max_d = 0
        for action in plan.actions:
            d = _compute_depth(action.action_id, plan.dag_edges, depth_cache)
            if d > max_d:
                max_d = d
        _check(f"max_depth <= {MAX_PLAN_DEPTH}", max_d <= MAX_PLAN_DEPTH)


# ── 12. Governance result structure ──────────────────────────

def test_governance_result():
    intents = [ActionIntent(intent="check_gateway_health", goal="gateway status")]
    plan = Planner.plan(intents)
    _check("plan created", plan is not None)
    if plan:
        gov = validate_plan_against_policy(plan)
        _check("GovernanceResult type", isinstance(gov, GovernanceResult))
        _check("gov.allowed", gov.allowed)
        _check("gov.permission_scope == readonly", gov.permission_scope == PermissionScope.READONLY.value)
        _check("gov.requires_approval == False", not gov.requires_approval)
        _check("gov.blocked_reasons is empty", len(gov.blocked_reasons) == 0)
        _check("gov.to_dict works", isinstance(gov.to_dict(), dict))


# ── 13. Workflow state transitions ──────────────────────────

def test_workflow_state_governed():
    from runtime.agentic.workflow_state import WorkflowTimeline
    tl = WorkflowTimeline(plan_id="test-1")
    ok = tl.transition(WorkflowState.EVALUATED)
    _check("PLANNING -> EVALUATED", ok)
    ok = tl.transition(WorkflowState.GOVERNED)
    _check("EVALUATED -> GOVERNED", ok)
    _check("current_state is GOVERNED", tl.current_state == WorkflowState.GOVERNED)


def test_workflow_state_reserved():
    _check("GOVERNED is defined", WorkflowState.GOVERNED.value == "governed")
    _check("READY_FOR_EXECUTION is defined", WorkflowState.READY_FOR_EXECUTION.value == "ready_for_execution")
    _check("EXECUTING_RESERVED is defined", WorkflowState.EXECUTING_RESERVED.value == "executing_reserved")
    _check("ROLLBACK_RESERVED is defined", WorkflowState.ROLLBACK_RESERVED.value == "rollback_reserved")
    _check("EXECUTING_RESERVED has no transitions", VALID_TRANSITIONS[WorkflowState.EXECUTING_RESERVED] == set())
    _check("ROLLBACK_RESERVED has no transitions", VALID_TRANSITIONS[WorkflowState.ROLLBACK_RESERVED] == set())


# ── Main ─────────────────────────────────────────────────────

def main():
    print("FASE 28.1 — Planner Runtime Skeleton Tests")
    print("=" * 50)

    test_readonly_plan_valid()
    test_readonly_dependencies()
    test_ambiguous_prompt()
    test_malicious_write()
    test_sudo_attempt()
    test_docker_mutation()
    test_recursive_planner()
    test_permission_scope_readonly()
    test_permission_scope_forbidden()
    test_max_nodes_enforced()
    test_max_depth_enforced()
    test_governance_result()
    test_workflow_state_governed()
    test_workflow_state_reserved()

    print("=" * 50)
    print(f"Resultado: {PASS} passed, {FAIL} failed")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
