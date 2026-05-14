from runtime.nodes.scheduler import select_best_node


DEFAULT_MODELS = {
    "fast": "google/gemma-4-e4b",
    "coding": "qwen2.5-coder-32b",
    "reasoning": "qwen3.5-9b-claude-4.6-opus-reasoning-distilled-v2",
    "deep-reasoning": "qwen3-14b-claude-sonnet-4.5-reasoning-distill",
    "embeddings": "text-embedding-nomic-embed-text-v1.5",
}


def infer_task(request_text=None, capability=None):
    text = (request_text or "").lower()

    if capability == "fast":
        return "fast"

    if capability == "coding":
        return "coding"

    if capability == "reasoning":
        return "reasoning"

    if any(word in text for word in [
        "codigo",
        "código",
        "python",
        "typescript",
        "astro",
        "fastapi",
        "bug",
        "script",
        "refactor",
        "api",
    ]):
        return "coding"

    if any(word in text for word in [
        "arquitectura",
        "architecture",
        "multi-agent",
        "orquestacion",
        "orchestration",
        "runtime",
        "cluster",
        "distribuido",
        "distributed",
    ]):
        return "deep-reasoning"

    if any(word in text for word in [
        "audita",
        "seguridad",
        "security",
        "analiza",
        "razona",
        "plan",
        "estrategia",
    ]):
        return "reasoning"

    return "fast"


def choose_model_for_node(node, task):
    available = node.get("models", [])

    preferred = DEFAULT_MODELS.get(task)

    if preferred and preferred in available:
        return preferred

    if task == "coding":
        for candidate in [
            "qwen2.5-coder-32b",
            "qwen/qwen2.5-coder-32b-instruct",
            "lmstudio-community/qwen2.5-coder-32b-instruct",
            "qwen2.5-coder-14b-instruct",
            "deepseek-coder-v2-lite-instruct",
        ]:
            if candidate in available:
                return candidate

    if task in ("reasoning", "deep-reasoning"):
        for candidate in [
            "qwen3.6-35b-a3b-claude-4.6-opus-reasoning-distilled",
            "qwen3.5-9b-claude-4.6-opus-reasoning-distilled-v2",
            "qwen3-14b-claude-sonnet-4.5-reasoning-distill",
            "deepseek-r1-0528-qwen3-8b",
            "google/gemma-4-26b-a4b",
        ]:
            if candidate in available:
                return candidate

    if task == "fast":
        for candidate in [
            "google/gemma-4-e4b",
            "llama-3.2-1b-instruct",
        ]:
            if candidate in available:
                return candidate

    if available:
        return available[0]

    raise RuntimeError(f"No models available on node {node.get('name')}")


def select_node(request_text=None, capability=None, model=None, **kwargs):
    task = infer_task(
        request_text=request_text,
        capability=capability,
    )

    node = select_best_node(task)

    if not node:
        raise RuntimeError("No distributed AI-LAB nodes online")

    selected_model = model or choose_model_for_node(
        node,
        task,
    )

    return {
        "name": node.get("name"),
        "host": node.get("host"),
        "port": 1234,
        "model": selected_model,
        "capability": capability or task,
        "gpu": node.get("gpu"),
        "task": task,
    }


def get_base_url(model=None):
    node = select_best_node("fast")

    if not node:
        raise RuntimeError("No distributed AI-LAB nodes online")

    return f"http://{node['host']}:1234/v1"
