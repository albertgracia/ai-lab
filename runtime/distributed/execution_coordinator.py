import time
import random

from runtime.distributed.task_router import (
    select_node,
)

from runtime.distributed.token_router import (
    estimate_tokens,
    select_model_for_task,
)

from runtime.memory.episodic_memory import (
    write_episode,
)


DEFAULT_TASK_PROMPTS = {
    "reasoning": "Analyze the current AI-LAB state and produce an operational plan.",
    "coding": "Prepare safe code changes and validate them conceptually.",
    "vision": "Analyze visual or multimodal input.",
    "memory": "Retrieve relevant semantic and episodic memory context.",
    "creative": "Generate a creative or frontend-oriented output.",
    "orchestration": "Coordinate workflow execution across distributed nodes.",
    "fast": "Perform a lightweight operational task.",
}


def get_task_prompt(task_type, prompt=None):
    if prompt:
        return prompt

    return DEFAULT_TASK_PROMPTS.get(
        task_type,
        "Execute distributed AI-LAB task.",
    )


def select_token_safe_model(route, prompt, task_type):
    estimated_tokens = estimate_tokens(prompt)

    selected, ranked = select_model_for_task(
        route.get("models", []),
        task_type,
        estimated_tokens,
    )

    if selected:
        return {
            "available": True,
            "model": selected["model"],
            "model_score": selected["score"],
            "model_context_window": selected["context_window"],
            "estimated_tokens": estimated_tokens,
            "ranked_models": ranked,
        }

    return {
        "available": False,
        "model": None,
        "estimated_tokens": estimated_tokens,
        "ranked_models": ranked,
        "reason": "context_overflow",
    }


def simulate_node_execution(task_type, route, prompt):
    if not route.get("available"):
        return {
            "success": False,
            "node": None,
            "reason": "no_available_node",
        }

    token_check = select_token_safe_model(
        route,
        prompt,
        task_type,
    )

    if not token_check["available"]:
        return {
            "success": False,
            "node": route.get("selected_node"),
            "reason": "context_overflow",
            "estimated_tokens": token_check["estimated_tokens"],
            "ranked_models": token_check.get("ranked_models", []),
        }

    node = route["selected_node"]
    model = token_check["model"]

    latency = random.uniform(0.2, 1.4)

    time.sleep(latency)

    failure_chance = 0.15

    if random.random() < failure_chance:
        return {
            "success": False,
            "node": node,
            "model": model,
            "model_score": token_check.get("model_score"),
            "reason": "simulated_execution_failure",
            "estimated_tokens": token_check["estimated_tokens"],
        }

    return {
        "success": True,
        "node": node,
        "model": model,
        "model_score": token_check.get("model_score"),
        "model_context_window": token_check.get("model_context_window"),
        "latency": round(latency, 2),
        "estimated_tokens": token_check["estimated_tokens"],
        "output": (
            f"Task '{task_type}' executed successfully "
            f"on '{node}' using model '{model}'."
        ),
    }


def execute_with_failover(task_type, prompt=None, retries=2):
    task_prompt = get_task_prompt(
        task_type,
        prompt,
    )

    attempts = []

    for attempt in range(1, retries + 2):
        route = select_node(task_type)

        result = simulate_node_execution(
            task_type,
            route,
            task_prompt,
        )

        attempts.append({
            "attempt": attempt,
            "route": route,
            "result": result,
        })

        if result["success"]:
            final = {
                "task_type": task_type,
                "success": True,
                "attempts": attempts,
                "final_node": result["node"],
                "final_model": result["model"],
                "model_score": result.get("model_score"),
                "model_context_window": result.get("model_context_window"),
                "estimated_tokens": result["estimated_tokens"],
                "final_output": result["output"],
            }

            write_episode(
                event_type="distributed_execution_success",
                summary=(
                    f"Distributed task '{task_type}' executed "
                    f"on '{result['node']}' using '{result['model']}'."
                ),
                payload=final,
            )

            return final

        if result.get("reason") == "context_overflow":
            break

    final = {
        "task_type": task_type,
        "success": False,
        "attempts": attempts,
        "final_node": None,
        "final_model": None,
        "final_output": None,
        "reason": attempts[-1]["result"].get("reason") if attempts else "unknown",
    }

    write_episode(
        event_type="distributed_execution_failed",
        summary=(
            f"Distributed task '{task_type}' failed "
            f"after retries or token validation."
        ),
        payload=final,
    )

    return final


def print_execution(task_type, prompt=None):
    result = execute_with_failover(
        task_type,
        prompt=prompt,
    )

    print()
    print("==================================================")
    print("TASK:", task_type)
    print("SUCCESS:", result["success"])
    print("FINAL NODE:", result["final_node"])
    print("FINAL MODEL:", result.get("final_model"))

    if result.get("reason"):
        print("REASON:", result["reason"])

    print()

    for item in result["attempts"]:
        route = item["route"]
        exec_result = item["result"]

        print(f"Attempt #{item['attempt']}")
        print("Route:", route["selected_node"])
        print("Mode:", route["mode"])
        print("Success:", exec_result["success"])

        if exec_result.get("estimated_tokens") is not None:
            print("Estimated Tokens:", exec_result["estimated_tokens"])

        if not exec_result["success"]:
            print("Reason:", exec_result["reason"])
        else:
            print("Model:", exec_result["model"])
            print("Latency:", exec_result["latency"])
            print("Output:", exec_result["output"])

        print()


if __name__ == "__main__":
    print()
    print("AI-LAB TOKEN-SAFE DISTRIBUTED EXECUTION")
    print("==================================================")

    tasks = [
        "reasoning",
        "coding",
        "vision",
        "memory",
        "creative",
    ]

    for task in tasks:
        print_execution(task)

    huge_prompt = "A" * 400000

    print_execution(
        "reasoning",
        prompt=huge_prompt,
    )
