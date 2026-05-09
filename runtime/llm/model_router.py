import json
from pathlib import Path

SNAPSHOT = Path("/opt/ai-lab/runtime/state/system_snapshot.json")

NODES = {
    "main": {"name": "Main LM Studio", "host": "192.168.1.200", "port": 1234},
    "rx9070xt": {"name": "Gaming PC RX9070XT", "host": "192.168.1.50", "port": 1234},
    "rx7900xt": {"name": "Gaming PC RX7900XT", "host": "192.168.1.60", "port": 1234},
}

CAPABILITY_ORDER = {
    "fast": [
        ("rx9070xt", "google/gemma-4-e4b"),
        ("main", "google/gemma-4-e4b"),
    ],
    "reasoning": [
        ("rx9070xt", "qwen3-14b-claude-sonnet-4.5-reasoning-distill"),
        ("rx7900xt", "qwen3-14b-claude-sonnet-4.5-reasoning-distill"),
        ("rx7900xt", "deepseek-r1-0528-qwen3-8b"),
    ],
    "coding": [
        ("rx7900xt", "qwen2.5-coder-14b-instruct"),
        ("rx7900xt", "qwen2.5-coder-32b"),
        ("rx7900xt", "qwen/qwen2.5-coder-32b-instruct"),
    ],
    "embedding": [
        ("main", "text-embedding-nomic-embed-text-v1.5"),
        ("rx9070xt", "text-embedding-nomic-embed-text-v1.5"),
        ("rx7900xt", "text-embedding-nomic-embed-text-v1.5"),
    ],
}


def load_snapshot():
    if not SNAPSHOT.exists():
        return {}
    return json.loads(SNAPSHOT.read_text())


def node_online(snapshot, node_name):
    for item in snapshot.get("llm", {}).get("lmstudio_nodes", []):
        if item.get("node") == node_name:
            return item.get("online", False)
    return False


def model_available(snapshot, node_name, model):
    for item in snapshot.get("llm", {}).get("lmstudio_nodes", []):
        if item.get("node") == node_name:
            return model in item.get("models", [])
    return False


def get_gpu_free(snapshot, node_name):
    for item in snapshot.get("gpu", []):
        if item.get("node") == node_name:
            return item.get("vram", {}).get("vram_free_gib_estimated", 0)
    return 0


def infer_capability(request: str):
    q = request.lower()

    if any(x in q for x in ["codigo", "code", "python", "debug", "bug", "funcion", "script", "docker", "traefik"]):
        return "coding"

    if any(x in q for x in ["razona", "analiza", "arquitectura", "roadmap", "plan", "diseña", "estrategia"]):
        return "reasoning"

    if any(x in q for x in ["embedding", "vector", "qdrant"]):
        return "embedding"

    return "fast"


def select_node(request: str, capability: str | None = None):
    snapshot = load_snapshot()
    capability = capability or infer_capability(request)

    for key, model in CAPABILITY_ORDER.get(capability, CAPABILITY_ORDER["fast"]):
        node = NODES[key]
        node_name = node["name"]

        if not node_online(snapshot, node_name):
            continue

        if not model_available(snapshot, node_name, model):
            continue

        selected = dict(node)
        selected["model"] = model
        selected["capability"] = capability
        selected["vram_free_gib_estimated"] = get_gpu_free(snapshot, node_name)
        return selected

    fallback = dict(NODES["main"])
    fallback["model"] = "google/gemma-4-e4b"
    fallback["capability"] = capability
    fallback["vram_free_gib_estimated"] = 0
    return fallback


if __name__ == "__main__":
    import sys
    request = " ".join(sys.argv[1:]) or "quick summary"
    print(json.dumps(select_node(request), indent=2))
