from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from runtime.planner.task_planner import create_task_plan
from runtime.memory.episodic_memory import write_episode
from runtime.distributed.task_router import select_node


CAPABILITY_TO_DISTRIBUTED_TASK = {
    "analyze": "reasoning",
    "plan": "reasoning",
    "rag": "memory",
    "read": "fast",
    "search": "memory",
    "write": "coding",
    "shell": "orchestration",
    "tools": "orchestration",
}


def map_capability_to_task(capability: str) -> str:
    return CAPABILITY_TO_DISTRIBUTED_TASK.get(
        capability,
        "fast",
    )


def create_workflow(user_goal: str) -> dict[str, Any]:
    task_plan = create_task_plan(user_goal)

    steps = []

    for step in task_plan.steps:
        step_dict = {
            **asdict(step),
            "result": None,
            "distributed_task": map_capability_to_task(
                step.capability_required
            ),
            "distributed_route": None,
        }

        steps.append(step_dict)

    workflow = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "user_goal": user_goal,
        "intent": task_plan.intent,
        "mode": task_plan.mode,
        "profile": task_plan.profile,
        "status": "created",
        "steps": steps,
    }

    write_episode(
        event_type="workflow_created",
        summary=f"Created workflow for goal: {user_goal}",
        payload=workflow,
    )

    return workflow


def route_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    workflow["status"] = "routed"

    unavailable_steps = 0
    fallback_steps = 0

    for step in workflow["steps"]:
        route = select_node(
            step["distributed_task"]
        )

        step["distributed_route"] = route

        if not route.get("available"):
            step["status"] = "unavailable"
            unavailable_steps += 1

        elif route.get("mode") == "fallback":
            step["status"] = "routed_fallback"
            fallback_steps += 1

        else:
            step["status"] = "routed"

    if unavailable_steps:
        workflow["status"] = "degraded_unavailable"
    elif fallback_steps:
        workflow["status"] = "degraded_routed"

    write_episode(
        event_type="workflow_routed",
        summary=(
            f"Workflow routed for goal '{workflow['user_goal']}' "
            f"with status '{workflow['status']}'."
        ),
        payload={
            "user_goal": workflow["user_goal"],
            "intent": workflow["intent"],
            "mode": workflow["mode"],
            "profile": workflow["profile"],
            "status": workflow["status"],
            "fallback_steps": fallback_steps,
            "unavailable_steps": unavailable_steps,
            "steps": workflow["steps"],
        },
    )

    return workflow


def simulate_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    if workflow["status"] == "degraded_unavailable":
        simulation_status = "simulated_with_unavailable_steps"
    elif workflow["status"] == "degraded_routed":
        simulation_status = "simulated_degraded"
    else:
        simulation_status = "simulated"

    workflow["status"] = simulation_status

    for step in workflow["steps"]:
        route = step.get("distributed_route") or {}

        if not route.get("available"):
            step["result"] = (
                f"Step '{step['title']}' cannot be simulated: "
                "no available node."
            )
            continue

        node = route.get("selected_node")
        route_mode = route.get("mode")

        step["result"] = (
            f"Step '{step['title']}' validated in simulation mode "
            f"on node '{node}' using route mode '{route_mode}'."
        )

    write_episode(
        event_type="workflow_simulated",
        summary=(
            f"Simulated workflow for goal '{workflow['user_goal']}' "
            f"with status '{workflow['status']}'."
        ),
        payload={
            "user_goal": workflow["user_goal"],
            "intent": workflow["intent"],
            "mode": workflow["mode"],
            "profile": workflow["profile"],
            "status": workflow["status"],
            "steps": workflow["steps"],
        },
    )

    return workflow


def print_workflow(workflow: dict[str, Any]):
    print("AI-LAB LIVE DISTRIBUTED WORKFLOW")
    print("================================")
    print("GOAL:", workflow["user_goal"])
    print("INTENT:", workflow["intent"])
    print("MODE:", workflow["mode"])
    print("PROFILE:", workflow["profile"])
    print("STATUS:", workflow["status"])
    print()

    for step in workflow["steps"]:
        print(f"{step['order']}. {step['title']}")
        print(
            f"   mode={step['mode']} "
            f"profile={step['profile']} "
            f"capability={step['capability_required']} "
            f"distributed_task={step['distributed_task']} "
            f"status={step['status']}"
        )

        route = step.get("distributed_route")

        if route:
            print(
                f"   available={route.get('available')} "
                f"route={route.get('selected_node')} "
                f"host={route.get('host')} "
                f"score={route.get('score')} "
                f"route_mode={route.get('mode')} "
                f"matched_task={route.get('matched_task')}"
            )

            if route.get("original_task"):
                print(
                    f"   original_task={route.get('original_task')}"
                )

        if step.get("result"):
            print(f"   result={step['result']}")


if __name__ == "__main__":
    goal = (
        "Implementa un workflow seguro para revisar estado Docker "
        "y documentar resultados"
    )

    workflow = create_workflow(goal)
    workflow = route_workflow(workflow)
    workflow = simulate_workflow(workflow)

    print_workflow(workflow)
