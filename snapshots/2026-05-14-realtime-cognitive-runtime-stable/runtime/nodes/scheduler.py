import json
from pathlib import Path

CLUSTER_STATE = Path("/opt/ai-lab/runtime/state/cluster_state.json")


def load_cluster_state():
    if not CLUSTER_STATE.exists():
        return None

    with open(CLUSTER_STATE, "r", encoding="utf-8") as f:
        return json.load(f)


def online_nodes():
    state = load_cluster_state()

    if not state:
        return []

    return [
        node
        for node in state["nodes"]
        if node.get("online")
    ]


def node_by_name(nodes, name):
    for node in nodes:
        if node["name"] == name:
            return node

    return None


def fallback_node(nodes):
    return sorted(
        nodes,
        key=lambda x: (
            x.get("latency_ms", 9999),
            -x.get("priority", 0)
        )
    )[0]


def select_best_node(task: str):
    nodes = online_nodes()

    if not nodes:
        return None

    rx7900 = node_by_name(nodes, "rx7900xt-node")
    rx9070 = node_by_name(nodes, "rx9070-node")
    nas = node_by_name(nodes, "nas-local")

    # CODING
    if task == "coding":
        if rx7900:
            return rx7900

    # DEEP REASONING
    if task == "deep-reasoning":
        if rx7900:
            return rx7900

    # FAST / DISTILLED REASONING
    if task == "reasoning":
        if rx9070:
            return rx9070

    # EMBEDDINGS
    if task == "embeddings":
        if rx9070:
            return rx9070

    # FAST LIGHT TASKS
    if task == "fast":
        if nas:
            return nas

    return fallback_node(nodes)


if __name__ == "__main__":
    tasks = [
        "coding",
        "deep-reasoning",
        "reasoning",
        "embeddings",
        "fast"
    ]

    for task in tasks:
        node = select_best_node(task)

        print("\n====================")
        print("TASK:", task)

        if node:
            print("NODE:", node["name"])
            print("GPU:", node["gpu"])
            print("LATENCY:", node["latency_ms"])
