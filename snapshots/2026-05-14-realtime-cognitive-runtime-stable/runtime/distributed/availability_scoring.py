import json
from pathlib import Path

CLUSTER_STATE_FILE = Path("/opt/ai-lab/runtime/state/cluster_state.json")


def load_cluster_state():
    if not CLUSTER_STATE_FILE.exists():
        return {"nodes": []}

    with open(CLUSTER_STATE_FILE, "r") as f:
        return json.load(f)


def calculate_score(node: dict) -> float:
    if not node.get("online"):
        return 0

    latency = node.get("latency_ms") or 999
    model_count = len(node.get("models", []))

    latency_score = max(0, 100 - latency)
    model_score = model_count * 5

    total_score = latency_score + model_score

    return round(total_score, 2)


def build_rankings(nodes: list):
    ranked = []

    for node in nodes:
        score = calculate_score(node)

        node["availability_score"] = score

        ranked.append(node)

    ranked.sort(
        key=lambda x: x["availability_score"],
        reverse=True
    )

    return ranked


def print_rankings(nodes: list):
    print("\nAI-LAB AVAILABILITY SCORING")
    print("=" * 50)

    for idx, node in enumerate(nodes, start=1):
        print(f"\n#{idx} {node['name']}")
        print(f"Host: {node['host']}")
        print(f"Online: {node['online']}")
        print(f"Latency: {node.get('latency_ms')}")
        print(f"Models: {len(node.get('models', []))}")
        print(f"Score: {node['availability_score']}")


def main():
    cluster_state = load_cluster_state()

    ranked_nodes = build_rankings(
        cluster_state.get("nodes", [])
    )

    print_rankings(ranked_nodes)


if __name__ == "__main__":
    main()
