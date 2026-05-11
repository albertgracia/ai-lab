from pathlib import Path
import json


SNAPSHOT_PATH = Path(
    "/opt/ai-lab-data/snapshots/current/system_snapshot.json"
)

DEFAULT_REASONING_MODEL = "qwen3-14b-claude-sonnet-4.5-reasoning-distill@q4_k_m"
DEFAULT_FAST_MODEL = "google/gemma-4-e4b"

NODE_PRIORITY = [
    "Main LM Studio",
    "Gaming PC RX9070XT",
    "Gaming PC RX7900XT",
]


def load_snapshot():
    try:
        with open(SNAPSHOT_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def get_online_lmstudio_nodes():
    snapshot = load_snapshot()
    llm = snapshot.get("llm", {})
    nodes = llm.get("lmstudio_nodes", [])

    online = [
        node
        for node in nodes
        if node.get("online") is True
    ]

    return sorted(
        online,
        key=lambda n: NODE_PRIORITY.index(n.get("node"))
        if n.get("node") in NODE_PRIORITY
        else 999
    )


def select_node_for_model(model=None):
    online_nodes = get_online_lmstudio_nodes()

    if not online_nodes:
        raise RuntimeError("No LM Studio nodes online")

    if model:
        for node in online_nodes:
            if model in node.get("models", []):
                return node

    return online_nodes[0]


def select_chat_model(node, preferred_model=None):
    models = node.get("models", [])

    if preferred_model and preferred_model in models:
        return preferred_model

    chat_models = [
        m for m in models
        if "embed" not in m.lower()
    ]

    if chat_models:
        return chat_models[0]

    if models:
        return models[0]

    raise RuntimeError(
        f"No models available on node {node.get('node')}"
    )


def select_node(request_text=None, capability=None, model=None, **kwargs):
    preferred_model = model

    if capability in ("reasoning", "coding", "auto", None):
        preferred_model = DEFAULT_REASONING_MODEL

    if capability == "fast":
        preferred_model = DEFAULT_FAST_MODEL

    node = select_node_for_model(preferred_model)
    selected_model = select_chat_model(node, preferred_model)

    return {
        "name": node.get("node") or node.get("name") or "LM Studio",
        "host": node.get("host"),
        "port": node.get("port", 1234),
        "model": selected_model,
        "capability": capability or "auto",
    }


def get_base_url(model=None):
    node = select_node_for_model(model)
    host = node.get("host")
    port = node.get("port", 1234)

    if not host:
        raise RuntimeError("LM Studio node missing host")

    return f"http://{host}:{port}/v1"
