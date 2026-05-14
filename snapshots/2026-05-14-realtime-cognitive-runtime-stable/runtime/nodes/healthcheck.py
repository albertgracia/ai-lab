import json
import time
from pathlib import Path

import requests

from runtime.nodes.node_registry import enabled_nodes

OUTPUT_FILE = Path("/opt/ai-lab/runtime/state/cluster_state.json")


def check_node(node):
    url = f"http://{node['host']}:{node['port']}/v1/models"

    started = time.time()

    try:
        response = requests.get(url, timeout=10)

        latency_ms = round((time.time() - started) * 1000, 2)

        if response.status_code != 200:
            return {
                "name": node["name"],
                "online": False,
                "error": f"HTTP {response.status_code}"
            }

        data = response.json()

        models = [
            model["id"]
            for model in data.get("data", [])
        ]

        return {
            "name": node["name"],
            "host": node["host"],
            "gpu": node["gpu"],
            "online": True,
            "latency_ms": latency_ms,
            "models": models,
            "capabilities": node.get("capabilities", []),
            "priority": node.get("priority", 0),
            "vram_gb": node.get("vram_gb", 0)
        }

    except Exception as exc:
        return {
            "name": node["name"],
            "online": False,
            "error": str(exc)
        }


def build_cluster_state():
    nodes = enabled_nodes()

    results = []

    for node in nodes:
        results.append(check_node(node))

    cluster_state = {
        "timestamp": int(time.time()),
        "online_nodes": len([
            n for n in results
            if n.get("online")
        ]),
        "total_nodes": len(results),
        "nodes": results
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cluster_state, f, indent=2)

    return cluster_state


if __name__ == "__main__":
    state = build_cluster_state()

    print(json.dumps(state, indent=2))
