from runtime.distributed.live_rerouter import (
    TASK_CAPABILITY_MAP,
    select_with_fallback,
    enrich_scores,
    get_online_nodes,
    load_cluster_state,
)

from runtime.memory.episodic_memory import (
    write_episode,
)


def select_node(task_type):
    cluster = load_cluster_state()

    nodes = enrich_scores(
        cluster.get("nodes", [])
    )

    online_nodes = get_online_nodes(nodes)

    selected = select_with_fallback(
        task_type,
        online_nodes,
    )

    required_caps = TASK_CAPABILITY_MAP.get(
        task_type,
        ["fast"],
    )

    if not selected:
        result = {
            "task_type": task_type,
            "required_capabilities": required_caps,
            "selected_node": None,
            "host": None,
            "score": 0,
            "models": [],
            "mode": "unavailable",
            "matched_task": None,
            "available": False,
        }

        write_episode(
            event_type="distributed_task_unavailable",
            summary=f"No available node for task '{task_type}'.",
            payload=result,
        )

        return result

    node_models = []

    for node in online_nodes:
        if node["name"] == selected["node"]:
            node_models = node.get("models", [])
            break

    result = {
        "task_type": task_type,
        "required_capabilities": required_caps,
        "selected_node": selected["node"],
        "host": selected["host"],
        "score": selected["score"],
        "models": node_models,
        "mode": selected.get("mode", "primary"),
        "matched_task": selected.get("matched_task", task_type),
        "original_task": selected.get("original_task"),
        "available": True,
    }

    write_episode(
        event_type="distributed_task_routed",
        summary=(
            f"Task '{task_type}' routed "
            f"to node '{result['selected_node']}' "
            f"in {result['mode']} mode."
        ),
        payload=result,
    )

    return result


def print_route(task_type):
    route = select_node(task_type)

    print()
    print("====================")
    print("TASK:", route["task_type"])
    print("AVAILABLE:", route["available"])
    print("NODE:", route["selected_node"])
    print("HOST:", route["host"])
    print("SCORE:", route["score"])
    print("MODE:", route["mode"])
    print("MATCHED TASK:", route["matched_task"])

    if route.get("original_task"):
        print("ORIGINAL TASK:", route["original_task"])

    print("REQUIRED CAPS:")

    for cap in route["required_capabilities"]:
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
