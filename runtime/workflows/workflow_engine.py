from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from runtime.planner.task_planner import create_task_plan
from runtime.memory.episodic_memory import write_episode


def create_workflow(user_goal: str) -> dict[str, Any]:
    task_plan = create_task_plan(user_goal)

    workflow = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "user_goal": user_goal,
        "intent": task_plan.intent,
        "mode": task_plan.mode,
        "profile": task_plan.profile,
        "status": "created",
        "steps": [
            {
                **asdict(step),
                "result": None,
            }
            for step in task_plan.steps
        ],
    }

    write_episode(
        event_type="workflow_created",
        summary=f"Created workflow for goal: {user_goal}",
        payload={
            "user_goal": user_goal,
            "intent": task_plan.intent,
            "mode": task_plan.mode,
            "profile": task_plan.profile,
            "steps": workflow["steps"],
        },
    )

    return workflow


def simulate_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    workflow["status"] = "simulated"

    for step in workflow["steps"]:
        step["status"] = "simulated"
        step["result"] = (
            f"Step '{step['title']}' validated in simulation mode."
        )

    write_episode(
        event_type="workflow_simulated",
        summary=f"Simulated workflow for goal: {workflow['user_goal']}",
        payload={
            "user_goal": workflow["user_goal"],
            "intent": workflow["intent"],
            "mode": workflow["mode"],
            "profile": workflow["profile"],
            "steps": workflow["steps"],
        },
    )

    return workflow


def print_workflow(workflow: dict[str, Any]):
    print("AI-LAB WORKFLOW")
    print("===============")
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
            f"status={step['status']}"
        )

        if step.get("result"):
            print(f"   result={step['result']}")


if __name__ == "__main__":
    goal = (
        "Implementa un workflow seguro para revisar estado Docker "
        "y documentar resultados"
    )

    workflow = create_workflow(goal)
    workflow = simulate_workflow(workflow)

    print_workflow(workflow)
