from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List

from runtime.agent.intent_router import detect_intent
from runtime.memory.episodic_memory import write_episode


@dataclass
class TaskStep:
    order: int
    title: str
    mode: str
    profile: str
    capability_required: str
    status: str = "pending"


@dataclass
class TaskPlan:
    created_at: str
    user_goal: str
    intent: str
    mode: str
    profile: str
    steps: List[TaskStep]


def infer_profile(mode: str, intent: str) -> str:
    if mode == "execute":
        return "pilot"

    if intent in {"coding", "architecture", "research", "security"}:
        return "sandbox"

    return "pilot"


def build_steps(user_goal: str, intent: str, mode: str, profile: str) -> list[TaskStep]:
    steps = [
        TaskStep(
            order=1,
            title="Understand user goal and classify intent",
            mode="plan",
            profile="sandbox",
            capability_required="analyze",
        ),
        TaskStep(
            order=2,
            title="Load semantic context and relevant operational memory",
            mode="plan",
            profile="sandbox",
            capability_required="rag",
        ),
        TaskStep(
            order=3,
            title="Generate implementation or operational plan",
            mode="plan",
            profile=profile,
            capability_required="plan",
        ),
    ]

    if intent == "coding":
        steps.append(
            TaskStep(
                order=4,
                title="Prepare code changes in build mode",
                mode="build",
                profile="sandbox",
                capability_required="write",
            )
        )
        steps.append(
            TaskStep(
                order=5,
                title="Validate changes with safe tests",
                mode="execute",
                profile="pilot",
                capability_required="shell",
            )
        )

    elif intent == "operations":
        steps.append(
            TaskStep(
                order=4,
                title="Run read-only operational diagnostics",
                mode="execute",
                profile="pilot",
                capability_required="shell",
            )
        )
        steps.append(
            TaskStep(
                order=5,
                title="Request approval before any state-changing action",
                mode="plan",
                profile="production",
                capability_required="plan",
            )
        )

    elif intent == "security":
        steps.append(
            TaskStep(
                order=4,
                title="Map risk, policies and attack surface",
                mode="plan",
                profile="sandbox",
                capability_required="analyze",
            )
        )
        steps.append(
            TaskStep(
                order=5,
                title="Produce remediation plan without execution",
                mode="plan",
                profile="production",
                capability_required="plan",
            )
        )

    else:
        steps.append(
            TaskStep(
                order=4,
                title="Document recommended next actions",
                mode="plan",
                profile=profile,
                capability_required="plan",
            )
        )

    return steps


def create_task_plan(user_goal: str) -> TaskPlan:
    route = detect_intent(user_goal)
    profile = infer_profile(route.mode, route.intent)

    steps = build_steps(
        user_goal=user_goal,
        intent=route.intent,
        mode=route.mode,
        profile=profile,
    )

    plan = TaskPlan(
        created_at=datetime.now(timezone.utc).isoformat(),
        user_goal=user_goal,
        intent=route.intent,
        mode=route.mode,
        profile=profile,
        steps=steps,
    )

    write_episode(
        event_type="task_plan_created",
        summary=f"Created task plan for intent '{route.intent}'.",
        payload={
            "user_goal": user_goal,
            "intent": route.intent,
            "mode": route.mode,
            "profile": profile,
            "steps": [asdict(step) for step in steps],
        },
    )

    return plan


def print_task_plan(user_goal: str):
    plan = create_task_plan(user_goal)

    print("AI-LAB TASK PLAN")
    print("================")
    print("GOAL:", plan.user_goal)
    print("INTENT:", plan.intent)
    print("MODE:", plan.mode)
    print("PROFILE:", plan.profile)
    print()

    for step in plan.steps:
        print(f"{step.order}. {step.title}")
        print(f"   mode={step.mode} profile={step.profile} capability={step.capability_required} status={step.status}")


if __name__ == "__main__":
    print_task_plan(
        "Implementa un workflow seguro para revisar estado Docker y documentar resultados"
    )
