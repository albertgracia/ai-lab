import json
from pathlib import Path

from runtime.memory.episodic_memory import write_episode


CLUSTER_STATE = Path(
    "/opt/ai-lab/runtime/state/cluster_state.json"
)


def load_cluster_state():

    with open(
        CLUSTER_STATE,
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def get_online_nodes(cluster):

    return [
        node
        for node in cluster.get("nodes", [])
        if node.get("online")
    ]


def classify_nodes(nodes):

    summary = {
        "reasoning": [],
        "coding": [],
        "fast": [],
        "memory": [],
        "multi_agent": [],
        "orchestration": [],
        "fallback": [],
        "backend": [],
    }

    for node in nodes:

        caps = node.get(
            "capabilities",
            []
        )

        for capability in summary:

            if capability in caps:
                summary[capability].append(node)

    return summary


def build_cluster_plan():

    cluster = load_cluster_state()

    online_nodes = get_online_nodes(cluster)

    summary = classify_nodes(
        online_nodes
    )

    total_vram = sum(
        node.get("vram_gb", 0)
        for node in online_nodes
    )

    avg_latency = 0

    if online_nodes:

        avg_latency = round(
            sum(
                node.get("latency_ms", 0)
                for node in online_nodes
            ) / len(online_nodes),
            2,
        )

    plan = {
        "online_nodes": len(online_nodes),
        "total_nodes": cluster.get(
            "total_nodes",
            len(online_nodes),
        ),
        "total_vram_gb": total_vram,
        "average_latency_ms": avg_latency,
        "capability_summary": {
            key: len(value)
            for key, value in summary.items()
        },
        "nodes": online_nodes,
    }

    write_episode(
        event_type="distributed_cluster_plan",
        summary=(
            f"Distributed cognition cluster analyzed "
            f"with {plan['online_nodes']} online nodes "
            f"and {total_vram} GB VRAM."
        ),
        payload=plan,
    )

    return plan


def print_cluster_plan():

    plan = build_cluster_plan()

    print("AI-LAB DISTRIBUTED COGNITION")
    print("============================")
    print("ONLINE NODES:", plan["online_nodes"])
    print("TOTAL VRAM:", plan["total_vram_gb"], "GB")
    print(
        "AVG LATENCY:",
        plan["average_latency_ms"],
        "ms",
    )

    print()
    print("CAPABILITIES")
    print("------------")

    for cap, count in plan[
        "capability_summary"
    ].items():

        print(f"{cap}: {count}")

    print()
    print("NODES")
    print("-----")

    for node in plan["nodes"]:

        print()

        print(
            f"{node['name']} "
            f"({node['host']})"
        )

        print(
            f"GPU: {node.get('gpu')}"
        )

        print(
            f"VRAM: {node.get('vram_gb')} GB"
        )

        print(
            f"LATENCY: "
            f"{node.get('latency_ms')} ms"
        )

        print(
            f"PRIORITY: "
            f"{node.get('priority')}"
        )

        print("CAPABILITIES:")

        for cap in node.get(
            "capabilities",
            []
        ):
            print(f" - {cap}")

        print("MODELS:")

        for model in node.get(
            "models",
            []
        ):
            print(f" - {model}")


if __name__ == "__main__":
    print_cluster_plan()
