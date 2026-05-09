import json
import requests
from pathlib import Path


CONFIG_PATH = Path("/opt/ai-lab/config/inference_nodes.json")


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def node_alive(host, port):
    try:
        r = requests.get(
            f"http://{host}:{port}/v1/models",
            timeout=3
        )

        return r.status_code == 200

    except Exception:
        return False


def select_node(user_request: str):
    config = load_config()

    nodes = config["nodes"]
    rules = config["routing_rules"]

    request_lower = user_request.lower()

    # -----------------------------
    # HEAVY ROUTING
    # -----------------------------
    for keyword in rules["heavy_keywords"]:
        if keyword in request_lower:

            node = nodes.get("rx7900xt")

            if node and node["enabled"]:
                if node_alive(node["host"], node["port"]):
                    return node

    # -----------------------------
    # FAST ROUTING
    # -----------------------------
    for keyword in rules["fast_keywords"]:
        if keyword in request_lower:

            node = nodes.get("rx9070xt")

            if node and node["enabled"]:
                if node_alive(node["host"], node["port"]):
                    return node

    # -----------------------------
    # DEFAULT FALLBACK
    # -----------------------------
    default_name = config["default_node"]

    node = nodes[default_name]

    return node
