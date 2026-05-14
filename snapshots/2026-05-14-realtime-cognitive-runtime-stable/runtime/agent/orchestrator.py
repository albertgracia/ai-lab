from datetime import datetime, timezone

from runtime.agent.intent_router import detect_intent
from runtime.agent.context_loader import build_agent_context
from runtime.audit.audit_logger import audit_event
from runtime.memory.episodic_memory import write_episode


def build_orchestration_plan(user_request: str) -> dict:
    route = detect_intent(user_request)
    context = build_agent_context(user_request)

    plan = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_request": user_request,
        "intent": route.intent,
        "mode": route.mode,
        "capabilities": route.capabilities,
        "context_tags": route.context_tags,
        "suggested_model": route.suggested_model,
        "score": route.score,
        "context_chars": len(context),
        "context_preview": context[:3000],
    }

    audit_event(
        "orchestration_plan_created",
        {
            "user_request": user_request,
            "intent": route.intent,
            "mode": route.mode,
            "capabilities": route.capabilities,
            "context_tags": route.context_tags,
            "suggested_model": route.suggested_model,
            "score": route.score,
            "context_chars": len(context),
        },
    )

    write_episode(
        event_type="orchestration_plan",
        summary=(
            f"Created orchestration plan for intent '{route.intent}' "
            f"in mode '{route.mode}'."
        ),
        payload={
            "user_request": user_request,
            "intent": route.intent,
            "mode": route.mode,
            "capabilities": route.capabilities,
            "context_tags": route.context_tags,
            "suggested_model": route.suggested_model,
            "score": route.score,
            "context_chars": len(context),
        },
    )

    return plan


def print_orchestration_plan(user_request: str):
    plan = build_orchestration_plan(user_request)

    print("AI-LAB ORCHESTRATION PLAN")
    print("=========================")
    print("REQUEST:", plan["user_request"])
    print("INTENT:", plan["intent"])
    print("MODE:", plan["mode"])
    print("CAPABILITIES:", ", ".join(plan["capabilities"]))
    print("TAGS:", ", ".join(plan["context_tags"]))
    print("MODEL:", plan["suggested_model"])
    print("SCORE:", plan["score"])
    print("CONTEXT CHARS:", plan["context_chars"])
    print()
    print("CONTEXT PREVIEW")
    print("---------------")
    print(plan["context_preview"])


if __name__ == "__main__":
    print_orchestration_plan(
        "Analiza la arquitectura cognitiva operacional local del AI-LAB y propone próximos pasos"
    )
