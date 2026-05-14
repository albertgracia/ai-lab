import json
import time
from pathlib import Path

import requests

CLUSTER_STATE_FILE = Path("/opt/ai-lab/runtime/state/cluster_state.json")

DEFAULT_TIMEOUT = 5
BACKOFF_MULTIPLIER = 2
MAX_TIMEOUT = 30
MAX_CONSECUTIVE = 10
SKIP_AFTER_CONSECUTIVE = 5

CONSECUTIVE_FAILURES: dict = {}

NODES = [
    {"name": "nas-local", "host": "192.168.1.250", "port": 1234, "type": "lmstudio"},
    {"name": "rx7900xt-node", "host": "192.168.1.60", "port": 1234, "type": "lmstudio"},
    {"name": "rx9070-node", "host": "192.168.1.50", "port": 1234, "type": "lmstudio"},
]


def get_backoff_timeout(node_name: str) -> int:
    failures = CONSECUTIVE_FAILURES.get(node_name, 0)

    if failures >= SKIP_AFTER_CONSECUTIVE:
        return MAX_TIMEOUT

    if failures == 0:
        return DEFAULT_TIMEOUT

    return min(DEFAULT_TIMEOUT * (BACKOFF_MULTIPLIER ** (failures - 1)), MAX_TIMEOUT)


def should_skip_node(node_name: str) -> bool:
    failures = CONSECUTIVE_FAILURES.get(node_name, 0)
    return failures >= MAX_CONSECUTIVE


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

    node_name = node["name"]

    if should_skip_node(node_name):
        result["status"] = "backoff_skip"
        result["error"] = f"Skipped after {MAX_CONSECUTIVE} consecutive failures"
        return result

    timeout = get_backoff_timeout(node_name)

    try:
        url = f"http://{node['host']}:{node['port']}/v1/models"

        response = requests.get(url, timeout=timeout)

        latency = round((time.time() - start) * 1000, 2)

        if response.status_code == 200:
            data = response.json()

            models = []
            for model in data.get("data", []):
                model_id = model.get("id")
                if model_id:
                    models.append(model_id)

            CONSECUTIVE_FAILURES[node_name] = 0

            result.update({
                "online": True,
                "latency_ms": latency,
                "models": models,
                "last_seen": int(time.time()),
                "status": "online",
            })

    except Exception as exc:
        CONSECUTIVE_FAILURES[node_name] = CONSECUTIVE_FAILURES.get(node_name, 0) + 1
        result["error"] = str(exc)[:200]
        result["consecutive_failures"] = CONSECUTIVE_FAILURES[node_name]

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
        backoff = CONSECUTIVE_FAILURES.get(node["name"], 0)

        print(f"\nNode: {result['name']}")
        print(f"Host: {result['host']}")
        print(f"Status: {status_icon}")
        print(f"Backoff: {backoff} consecutive failures")

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
