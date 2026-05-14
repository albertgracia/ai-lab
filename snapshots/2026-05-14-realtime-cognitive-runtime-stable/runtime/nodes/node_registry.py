import json
from pathlib import Path

NODES_FILE = Path("/opt/ai-lab/runtime/nodes/nodes.json")


def load_nodes():
    if not NODES_FILE.exists():
        return []

    with open(NODES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def enabled_nodes():
    return [
        node
        for node in load_nodes()
        if node.get("enabled", True)
    ]


def nodes_with_capability(capability: str):
    return [
        node
        for node in enabled_nodes()
        if capability in node.get("capabilities", [])
    ]


if __name__ == "__main__":
    print(json.dumps(enabled_nodes(), indent=2))
