from runtime.distributed.cognitive_cluster import (
    load_cluster_state,
    get_online_nodes,
)

from runtime.memory.episodic_memory import (
    write_episode,
)


# ============================================================
# CAPABILITY MAP
# ============================================================

TASK_CAPABILITY_MAP = {

    "reasoning": [
        "reasoning",
        "large-context",
    ],

    "coding": [
        "coding",
        "backend",
    ],

    "vision": [
        "vision",
        "multimodal",
        "image",
    ],

    "memory": [
        "memory",
        "embeddings",
    ],

    "creative": [
        "creative",
        "frontend",
    ],

    "orchestration": [
        "orchestration",
        "multi-agent",
    ],

    "fast": [
        "fast",
        "fallback",
        "lightweight",
    ],
}


# ============================================================
# ROUTER
# ============================================================

def score_node(node, required_caps):

    node_caps = node.get(
        "capabilities",
        []
    )

    score = 0

    for cap in required_caps:

        if cap in node_caps:
            score += 10

    score += node.get(
        "priority",
        0
    )

    latency = node.get(
        "latency_ms",
        999
    )

    score -= latency

    return round(score, 2)


def select_node(task_type):

    cluster = load_cluster_state()

    nodes = get_online_nodes(cluster)

    required_caps = TASK_CAPABILITY_MAP.get(
        task_type,
        ["fast"]
    )

    ranked = []

    for node in nodes:

        score = score_node(
            node,
            required_caps,
        )

        ranked.append(
            {
                "node": node,
                "score": score,
            }
        )

    ranked.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    best = ranked[0]

    result = {
        "task_type": task_type,
        "required_capabilities": required_caps,
        "selected_node": best["node"]["name"],
        "host": best["node"]["host"],
        "score": best["score"],
        "models": best["node"].get(
            "models",
            []
        ),
    }

    write_episode(
        event_type="distributed_task_routed",
        summary=(
            f"Task '{task_type}' routed "
            f"to node '{result['selected_node']}'."
        ),
        payload=result,
    )

    return result


# ============================================================
# DEMO
# ============================================================

def print_route(task_type):

    route = select_node(task_type)

    print()
    print("====================")
    print("TASK:", route["task_type"])
    print(
        "NODE:",
        route["selected_node"]
    )
    print(
        "HOST:",
        route["host"]
    )
    print(
        "SCORE:",
        route["score"]
    )

    print("REQUIRED CAPS:")

    for cap in route[
        "required_capabilities"
    ]:
        print(" -", cap)

    print("MODELS:")

    for model in route["models"][:6]:
        print(" -", model)


if __name__ == "__main__":

    tasks = [
        "reasoning",
        "coding",
        "vision",
        "memory",
        "creative",
        "orchestration",
        "fast",
    ]

    print("AI-LAB DISTRIBUTED TASK ROUTER")
    print("==============================")

    for task in tasks:
        print_route(task)
