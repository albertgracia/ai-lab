from runtime.distributed.task_router import select_node as task_select_node

DEFAULT_MODELS = {
    "fast": "llama-3.1-8b-instruct",
    "coding": "llama-3.1-8b-instruct",
    "reasoning": "qwen2.5-coder-32b-instruct",
    "general": "llama-3.1-8b-instruct",
}


def infer_task(request_text=None, capability=None):
    if capability:
        return capability
    text = (request_text or "").lower()
    if any(w in text for w in ["python", "code", "script", "bug", "api", "refactor"]):
        return "coding"
    if any(w in text for w in ["arquitectura", "architecture", "complex", "analyze", "optimizar"]):
        return "reasoning"
    return "fast"


def select_node(request_text, capability=None):
    task = infer_task(request_text, capability)
    route = task_select_node(task)

    if not route.get("available") or not route.get("models"):
        return {"name": "rx9070-node", "host": "192.168.1.50", "port": 1234, "model": DEFAULT_MODELS.get(task, "llama-3.1-8b-instruct"), "capability": task, "available": True}

    preferred = DEFAULT_MODELS.get(task)
    models = route.get("models", [])

    if preferred and preferred in models:
        selected = preferred
    elif models:
        selected = models[0]
    else:
        selected = DEFAULT_MODELS.get(task, "llama-3.1-8b-instruct")

    return {
        "name": route.get("selected_node", "rx9070-node"),
        "host": route.get("host", "192.168.1.50"),
        "port": 1234,
        "model": selected,
        "capability": task,
        "available": True,
    }
