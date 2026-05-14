import json
import math
from pathlib import Path

from runtime.distributed.task_router import (
    select_node,
)

from runtime.memory.episodic_memory import (
    write_episode,
)


DISCOVERED_NODES_FILE = Path(
    "/opt/ai-lab/runtime/state/discovered_nodes.json"
)


TASK_MODEL_PREFERENCES = {
    "reasoning": [
        "qwen3.6",
        "qwen3.5",
        "qwen",
        "deepseek",
        "reasoning",
    ],
    "coding": [
        "coder",
        "deepseek-coder",
        "deepseek",
        "qwen",
        "code",
    ],
    "vision": [
        "vision",
        "moondream",
        "vl",
        "multimodal",
        "qwen",
    ],
    "memory": [
        "embed",
        "embedding",
        "nomic",
    ],
    "creative": [
        "qwen",
        "deepseek",
        "creative",
    ],
    "orchestration": [
        "qwen3.6",
        "qwen3.5",
        "qwen",
        "deepseek",
    ],
    "fast": [
        "4b",
        "8b",
        "9b",
        "mini",
        "small",
        "gemma",
        "phi",
    ],
}


def estimate_tokens(text):
    if not text:
        return 0

    return math.ceil(len(text) / 4)


def infer_model_context(model_name):
    name = model_name.lower()

    if "embed" in name or "embedding" in name or "nomic" in name:
        return 8192

    if "70b" in name or "72b" in name:
        return 32768

    if "35b" in name or "32b" in name:
        return 65536

    if "14b" in name:
        return 32768

    if "9b" in name or "8b" in name:
        return 32768

    if "4b" in name or "3b" in name or "1b" in name:
        return 16384

    if "long" in name or "128k" in name:
        return 131072

    if "64k" in name:
        return 65536

    if "32k" in name:
        return 32768

    if "16k" in name:
        return 16384

    return 8192


def infer_model_capabilities(model_name):
    name = model_name.lower()

    capabilities = set()

    if "embed" in name or "embedding" in name or "nomic" in name:
        capabilities.add("memory")
        capabilities.add("embeddings")

    if "coder" in name or "code" in name:
        capabilities.add("coding")
        capabilities.add("backend")

    if "deepseek" in name or "qwen" in name:
        capabilities.add("reasoning")

    if "vision" in name or "moondream" in name or "vl" in name:
        capabilities.add("vision")
        capabilities.add("multimodal")

    if "4b" in name or "8b" in name or "9b" in name or "mini" in name:
        capabilities.add("fast")

    if "35b" in name or "32b" in name or "long" in name:
        capabilities.add("large-context")

    if not capabilities:
        capabilities.add("general")

    return sorted(capabilities)


def load_discovered_models():
    if not DISCOVERED_NODES_FILE.exists():
        return {}

    try:
        data = json.loads(
            DISCOVERED_NODES_FILE.read_text(
                encoding="utf-8",
            )
        )
    except Exception:
        return {}

    models_by_host = {}

    for node in data.get("nodes", []):
        if not node.get("online"):
            continue

        host = node.get("host")

        models = node.get("models", [])

        models_by_host[host] = []

        for model in models:
            models_by_host[host].append(
                {
                    "id": model,
                    "context_window": infer_model_context(model),
                    "capabilities": infer_model_capabilities(model),
                }
            )

    return models_by_host


def model_supports_prompt(
    model,
    estimated_tokens,
    safety_margin=0.80,
):
    max_ctx = model.get(
        "context_window",
        8192,
    )

    safe_ctx = int(max_ctx * safety_margin)

    return estimated_tokens < safe_ctx


def score_model_for_task(
    model,
    task_type,
    estimated_tokens,
):
    model_id = model["id"]
    name = model_id.lower()

    if not model_supports_prompt(
        model,
        estimated_tokens,
    ):
        return 0

    score = 10

    context_window = model.get(
        "context_window",
        8192,
    )

    score += int(context_window / 8192)

    model_caps = model.get(
        "capabilities",
        [],
    )

    if task_type in model_caps:
        score += 40

    if task_type == "memory" and "embeddings" in model_caps:
        score += 60

    if task_type == "coding" and "backend" in model_caps:
        score += 25

    if task_type == "vision" and "multimodal" in model_caps:
        score += 35

    if task_type in ["reasoning", "orchestration"] and "large-context" in model_caps:
        score += 25

    preferences = TASK_MODEL_PREFERENCES.get(
        task_type,
        [],
    )

    for index, pattern in enumerate(preferences):
        if pattern in name:
            score += max(1, 30 - index * 4)

    return score


def normalize_route_models(route):
    discovered = load_discovered_models()

    host = route.get("host")

    discovered_models = discovered.get(host)

    if discovered_models:
        return discovered_models

    fallback_models = []

    for model_id in route.get("models", []):
        fallback_models.append(
            {
                "id": model_id,
                "context_window": infer_model_context(model_id),
                "capabilities": infer_model_capabilities(model_id),
            }
        )

    return fallback_models


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
                "model": model["id"],
                "score": score,
                "context_window": model["context_window"],
                "capabilities": model["capabilities"],
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
            event_type="dynamic_model_routing",
            summary=(
                f"No available node for dynamic model task "
                f"'{task_type}'."
            ),
            payload=result,
        )

        return result

    dynamic_models = normalize_route_models(route)

    selected, ranked = select_model_for_task(
        dynamic_models,
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
            "model_capabilities": selected["capabilities"],
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
                "No compatible discovered model "
                "for requested context size."
            ),
            "route_mode": route.get("mode"),
            "matched_task": route.get("matched_task"),
            "ranked_models": [],
        }

    write_episode(
        event_type="dynamic_model_routing",
        summary=(
            f"Dynamic capability-aware model routing executed "
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
        ("vision", short_prompt),
        ("reasoning", huge_prompt),
    ]

    print("AI-LAB DYNAMIC CAPABILITY-AWARE MODEL ROUTER")
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
            print("HOST:", result.get("host"))
            print("MODEL:", result.get("model"))
            print("MODEL SCORE:", result.get("model_score"))
            print("CTX:", result.get("model_context_window"))
            print("CAPS:", ", ".join(result.get("model_capabilities", [])))
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
                    "caps=",
                    ",".join(item["capabilities"]),
                )
        else:
            print("REASON:", result.get("reason"))
            print("NODE:", result.get("node"))
