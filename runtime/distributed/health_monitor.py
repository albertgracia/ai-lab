import json
import time
from pathlib import Path

import requests

CLUSTER_STATE_FILE = Path("/opt/ai-lab/runtime/state/cluster_state.json")

DEFAULT_TIMEOUT = 5

NODES = [
    {
        "name": "nas-local",
        "host": "192.168.1.250",
        "port": 1234,
        "type": "lmstudio",
    },
    {
        "name": "rx7900xt-node",
        "host": "192.168.1.60",
        "port": 1234,
        "type": "lmstudio",
    },
    {
        "name": "rx9070-node",
        "host": "192.168.1.50",
        "port": 1234,
        "type": "lmstudio",
    },
]


def check_node(node: dict) -> dict:
    start = time.time()

    result = {
        "name": node["name"],
        "host": node["host"],
        "online": False,
        "latency_ms": None,
        "models": [],
        "last_seen": None,
        "status": "offline",
    }

    try:
        url = f"http://{node['host']}:{node['port']}/v1/models"

        response = requests.get(url, timeout=DEFAULT_TIMEOUT)

        latency = round((time.time() - start) * 1000, 2)

        if response.status_code == 200:
            data = response.json()

            models = []

            for model in data.get("data", []):
                model_id = model.get("id")

                if model_id:
                    models.append(model_id)

            result.update(
                {
                    "online": True,
                    "latency_ms": latency,
                    "models": models,
                    "last_seen": int(time.time()),
                    "status": "online",
                }
            )

    except Exception:
        pass

    return result


def load_cluster_state() -> dict:
    if CLUSTER_STATE_FILE.exists():
        try:
            with open(CLUSTER_STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass

    return {"nodes": []}


def save_cluster_state(state: dict):
    CLUSTER_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(CLUSTER_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def main():
    cluster_state = load_cluster_state()

    updated_nodes = []

    print("\nAI-LAB HEALTH MONITOR")
    print("=" * 40)

    for node in NODES:
        result = check_node(node)

        updated_nodes.append(result)

        status_icon = "ONLINE" if result["online"] else "OFFLINE"

        print(f"\nNode: {result['name']}")
        print(f"Host: {result['host']}")
        print(f"Status: {status_icon}")

        if result["online"]:
            print(f"Latency: {result['latency_ms']} ms")
            print(f"Models: {len(result['models'])}")

    cluster_state["nodes"] = updated_nodes
    cluster_state["updated_at"] = int(time.time())

    save_cluster_state(cluster_state)

    print("\nCluster state updated.")
    print(f"Saved to: {CLUSTER_STATE_FILE}")


if __name__ == "__main__":
    main()
