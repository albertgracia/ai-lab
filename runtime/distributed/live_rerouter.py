import json
from pathlib import Path


CLUSTER_STATE_FILE = Path(
    "/opt/ai-lab/runtime/state/cluster_state.json"
)


TASK_CAPABILITY_MAP = {
    "reasoning": ["reasoning", "large-context"],
    "coding": ["coding", "backend"],
    "vision": ["vision", "multimodal"],
    "memory": ["memory", "embeddings"],
    "creative": ["creative", "frontend", "vision"],
    "orchestration": ["orchestration", "multi-agent", "reasoning"],
    "fast": ["fast", "fallback"],
}


TASK_FALLBACK_MAP = {
    "reasoning": ["memory", "vision", "fast"],
    "coding": ["reasoning", "memory", "vision", "fast"],
    "vision": ["memory", "fast"],
    "memory": ["vision", "fast"],
    "creative": ["vision", "memory", "fast"],
    "orchestration": ["reasoning", "memory", "fast"],
    "fast": ["memory", "vision"],
}


NODE_CAPABILITIES = {
    "rx9070-node": [
        "fast",
        "coding",
        "general",
        "memory",
    ],
    "rx7900xt-node": [
        "reasoning",
        "coding",
        "large-context",
        "multi-agent",
    ],
}


def load_cluster_state():
    if not CLUSTER_STATE_FILE.exists():
        return {"nodes": []}

    with open(CLUSTER_STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_online_nodes(nodes):
    return [
        node
        for node in nodes
        if node.get("online")
    ]


def get_required_capabilities(task_type):
    return TASK_CAPABILITY_MAP.get(
        task_type,
        ["fast"],
    )


def node_supports_task(node_name, task_type):
    required = get_required_capabilities(task_type)

    capabilities = NODE_CAPABILITIES.get(
        node_name,
        [],
    )

    for capability in required:
        if capability in capabilities:
            return True

    return False


def enrich_scores(nodes):
    for node in nodes:
        latency = node.get("latency_ms") or 999
        models = len(node.get("models", []))

        if not node.get("online"):
            node["availability_score"] = 0
            continue

        score = (100 - latency) + (models * 5)

        node["availability_score"] = round(score, 2)

    return nodes


def select_best_node_for_task(task_type, nodes):
    candidates = []

    for node in nodes:
        node_name = node["name"]

        if not node_supports_task(node_name, task_type):
            continue

        candidates.append(
            {
                "node": node_name,
                "host": node["host"],
                "score": node.get("availability_score", 0),
                "mode": "primary",
                "matched_task": task_type,
            }
        )

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    if candidates:
        return candidates[0]

    return None


def select_with_fallback(task_type, nodes):
    primary = select_best_node_for_task(
        task_type,
        nodes,
    )

    if primary:
        return primary

    for fallback_task in TASK_FALLBACK_MAP.get(task_type, []):
        fallback = select_best_node_for_task(
            fallback_task,
            nodes,
        )

        if fallback:
            fallback["mode"] = "fallback"
            fallback["original_task"] = task_type
            fallback["matched_task"] = fallback_task
            return fallback

    return None


def main():
    cluster_state = load_cluster_state()

    nodes = enrich_scores(
        cluster_state.get("nodes", [])
    )

    online_nodes = get_online_nodes(nodes)

    print()
    print("AI-LAB LIVE REROUTER")
    print("=" * 50)

    for task_type in TASK_CAPABILITY_MAP.keys():
        selected = select_with_fallback(
            task_type,
            online_nodes,
        )

        print()
        print(f"Task: {task_type}")

        if not selected:
            print("No available node")
            continue

        print(f"Selected Node: {selected['node']}")
        print(f"Host: {selected['host']}")
        print(f"Score: {selected['score']}")
        print(f"Mode: {selected['mode']}")
        print(f"Matched Task: {selected['matched_task']}")

        if selected.get("original_task"):
            print(f"Original Task: {selected['original_task']}")


if __name__ == "__main__":
    main()
