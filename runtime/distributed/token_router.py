import math

from runtime.distributed.task_router import (
    select_node,
)

from runtime.memory.episodic_memory import (
    write_episode,
)


MODEL_CONTEXT_WINDOWS = {
    "deepseek-r1-distill-qwen-14b": 32768,
    "deepseek-r1-0528-qwen3-8b": 32768,
    "qwen3.6-35b-a3b-claude-4.6-opus-reasoning-distilled": 65536,
    "qwen3.5-9b-claude-4.6-opus-reasoning-distilled-v2": 65536,
    "text-embedding-nomic-embed-text-v1.5": 8192,
}


TASK_MODEL_PREFERENCES = {
    "reasoning": [
        "qwen3.6",
        "qwen3.5",
        "deepseek-r1",
        "qwen",
        "deepseek",
    ],
    "coding": [
        "coder",
        "deepseek",
        "qwen",
    ],
    "vision": [
        "vision",
        "moondream",
        "qwen",
        "deepseek",
    ],
    "memory": [
        "embed",
        "nomic",
    ],
    "creative": [
        "qwen",
        "deepseek",
    ],
    "orchestration": [
        "qwen3.6",
        "qwen3.5",
        "deepseek",
        "qwen",
    ],
    "fast": [
        "8b",
        "9b",
        "4b",
        "gemma",
        "phi",
    ],
}


def estimate_tokens(text):
    if not text:
        return 0

    return math.ceil(len(text) / 4)


def get_model_context(model_name):
    return MODEL_CONTEXT_WINDOWS.get(
        model_name,
        8192,
    )


def model_supports_prompt(
    model_name,
    estimated_tokens,
    safety_margin=0.80,
):
    max_ctx = get_model_context(model_name)

    safe_ctx = int(max_ctx * safety_margin)

    return estimated_tokens < safe_ctx


def score_model_for_task(
    model_name,
    task_type,
    estimated_tokens,
):
    name = model_name.lower()

    if not model_supports_prompt(
        model_name,
        estimated_tokens,
    ):
        return 0

    score = 10

    context_window = get_model_context(model_name)

    score += int(context_window / 8192)

    preferences = TASK_MODEL_PREFERENCES.get(
        task_type,
        [],
    )

    for index, pattern in enumerate(preferences):
        if pattern in name:
            score += max(1, 30 - index * 4)

    if task_type == "memory":
        if "embed" in name or "nomic" in name:
            score += 50

    if task_type == "fast":
        if "8b" in name or "9b" in name or "4b" in name:
            score += 30

    if task_type in ["reasoning", "orchestration"]:
        if "35b" in name or "32b" in name:
            score += 25
        if "14b" in name:
            score += 10

    if task_type == "coding":
        if "coder" in name:
            score += 50
        if "deepseek" in name:
            score += 20

    return score


def select_model_for_task(
    models,
    task_type,
    estimated_tokens,
):
    ranked = []

    for model in models:
        score = score_model_for_task(
            model,
            task_type,
            estimated_tokens,
        )

        if score <= 0:
            continue

        ranked.append(
            {
                "model": model,
                "score": score,
                "context_window": get_model_context(model),
            }
        )

    ranked.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    if not ranked:
        return None, []

    return ranked[0], ranked


def route_prompt(task_type, prompt):
    estimated_tokens = estimate_tokens(prompt)

    route = select_node(task_type)

    if not route.get("available"):
        result = {
            "available": False,
            "task_type": task_type,
            "reason": "no_available_node",
            "estimated_tokens": estimated_tokens,
        }

        write_episode(
            event_type="capability_aware_model_routing",
            summary=(
                f"No available node for token-aware task "
                f"'{task_type}'."
            ),
            payload=result,
        )

        return result

    models = route.get("models", [])

    selected, ranked = select_model_for_task(
        models,
        task_type,
        estimated_tokens,
    )

    if selected:
        result = {
            "available": True,
            "task_type": task_type,
            "node": route["selected_node"],
            "host": route["host"],
            "model": selected["model"],
            "model_score": selected["score"],
            "model_context_window": selected["context_window"],
            "estimated_tokens": estimated_tokens,
            "mode": "safe",
            "route_mode": route.get("mode"),
            "matched_task": route.get("matched_task"),
            "ranked_models": ranked,
        }

    else:
        result = {
            "available": False,
            "task_type": task_type,
            "node": route["selected_node"],
            "host": route["host"],
            "estimated_tokens": estimated_tokens,
            "mode": "context_overflow",
            "reason": (
                "No compatible model for requested context size."
            ),
            "route_mode": route.get("mode"),
            "matched_task": route.get("matched_task"),
            "ranked_models": [],
        }

    write_episode(
        event_type="capability_aware_model_routing",
        summary=(
            f"Capability-aware model routing executed "
            f"for task '{task_type}' with mode '{result['mode']}'."
        ),
        payload=result,
    )

    return result


if __name__ == "__main__":
    short_prompt = (
        "Analyze Docker logs and generate remediation plan."
    )

    huge_prompt = "A" * 400000

    tests = [
        ("reasoning", short_prompt),
        ("coding", short_prompt),
        ("memory", short_prompt),
        ("fast", short_prompt),
        ("reasoning", huge_prompt),
    ]

    print("AI-LAB CAPABILITY-AWARE MODEL ROUTER")
    print("==================================================")

    for task, prompt in tests:
        result = route_prompt(task, prompt)

        print()
        print("TASK:", task)
        print("ESTIMATED TOKENS:", result.get("estimated_tokens"))
        print("AVAILABLE:", result.get("available"))
        print("MODE:", result.get("mode"))

        if result.get("available"):
            print("NODE:", result.get("node"))
            print("MODEL:", result.get("model"))
            print("MODEL SCORE:", result.get("model_score"))
            print("CTX:", result.get("model_context_window"))
            print("ROUTE MODE:", result.get("route_mode"))

            print("TOP MODELS:")

            for item in result.get("ranked_models", [])[:5]:
                print(
                    " -",
                    item["model"],
                    "score=",
                    item["score"],
                    "ctx=",
                    item["context_window"],
                )
        else:
            print("REASON:", result.get("reason"))
            print("NODE:", result.get("node"))
