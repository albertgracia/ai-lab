import json
import time
from pathlib import Path

import requests


LMSTUDIO_PORT = 1234

DISCOVERY_TARGETS = [
    "192.168.1.50",
    "192.168.1.60",
    "192.168.1.250",
]

STATE_PATH = Path(
    "/opt/ai-lab/runtime/state/discovered_nodes.json"
)


def infer_capabilities(models):
    caps = set()

    joined = " ".join(models).lower()

    if "embed" in joined:
        caps.add("memory")
        caps.add("embeddings")

    if "vision" in joined or "moondream" in joined:
        caps.add("vision")
        caps.add("multimodal")

    if "coder" in joined or "code" in joined:
        caps.add("coding")
        caps.add("backend")

    if "deepseek" in joined or "qwen" in joined:
        caps.add("reasoning")

    if "35b" in joined or "32b" in joined:
        caps.add("large-context")

    if "9b" in joined or "8b" in joined or "4b" in joined:
        caps.add("fast")

    if not caps:
        caps.add("general")

    return sorted(caps)


def discover_lmstudio_node(ip):
    url = f"http://{ip}:{LMSTUDIO_PORT}/v1/models"

    result = {
        "host": ip,
        "port": LMSTUDIO_PORT,
        "backend": "lmstudio",
        "online": False,
        "latency_ms": None,
        "models": [],
        "capabilities": [],
        "discovered_at": int(time.time()),
    }

    try:
        start = time.time()

        response = requests.get(
            url,
            timeout=5,
        )

        latency_ms = round(
            (time.time() - start) * 1000,
            2,
        )

        if response.status_code != 200:
            result["status"] = "http_error"
            result["http_status"] = response.status_code
            return result

        data = response.json()

        models = []

        for item in data.get("data", []):
            model_id = item.get("id")

            if model_id:
                models.append(model_id)

        result.update(
            {
                "online": True,
                "latency_ms": latency_ms,
                "models": models,
                "capabilities": infer_capabilities(models),
                "status": "online",
            }
        )

        return result

    except Exception as exc:
        result["status"] = "offline"
        result["error"] = str(exc)
        return result


def run_discovery():
    nodes = []

    for ip in DISCOVERY_TARGETS:
        node = discover_lmstudio_node(ip)
        nodes.append(node)

    STATE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "updated_at": int(time.time()),
        "backend": "lmstudio",
        "nodes": nodes,
    }

    with open(
        STATE_PATH,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            payload,
            f,
            indent=2,
        )

    return nodes


def print_results(nodes):
    print()
    print("AI-LAB LM STUDIO NODE DISCOVERY")
    print("==================================================")

    for node in nodes:
        print()
        print("HOST:", node["host"])
        print("PORT:", node["port"])
        print("BACKEND:", node["backend"])
        print("ONLINE:", node["online"])
        print("STATUS:", node.get("status"))

        if node["online"]:
            print("LATENCY:", node["latency_ms"])
            print("CAPABILITIES:")

            for cap in node["capabilities"]:
                print(" -", cap)

            print("MODELS:")

            for model in node["models"][:10]:
                print(" -", model)

        else:
            if node.get("error"):
                print("ERROR:", node["error"])


if __name__ == "__main__":
    discovered = run_discovery()
    print_results(discovered)
