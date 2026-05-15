from runtime.distributed.task_router import select_node as task_select_node

# ---- default models (fallback) -------------------------------------------
DEFAULT_MODELS = {
    "fast": "llama-3.1-8b-instruct",
    "coding": "llama-3.1-8b-instruct",
    "reasoning": "qwen2.5-coder-32b-instruct",
    "general": "llama-3.1-8b-instruct",
}

# ---- try loading the new model registry ----------------------------------
_USE_REGISTRY = False
try:
    from runtime.models.model_registry import MODEL_REGISTRY, best_for_task, get_best_model
    _USE_REGISTRY = True
except ImportError:
    pass

# ---- try loading adaptive scoring ----------------------------------------
_USE_ADAPTIVE = False
try:
    from runtime.routing.adaptive_scoring import hybrid_score
    _USE_ADAPTIVE = True
except ImportError:
    pass


def infer_task(request_text=None, capability=None):
    """Classify *request_text* into a task type.
    
    Uses keyword matching.  The registry does not replace this yet —
    task classification stays simple until we add intent-based scoring.
    """
    if capability:
        return capability
    text = (request_text or "").lower()
    if any(w in text for w in ["python", "code", "script", "bug", "api", "refactor"]):
        return "coding"
    if any(w in text for w in ["arquitectura", "architecture", "complex", "analyze", "optimizar"]):
        return "reasoning"
    return "fast"


def select_node(request_text, capability=None):
    """Select best GPU node + model for the request.

    Uses the model registry for model selection within a node when
    available; otherwise falls back to DEFAULT_MODELS.
    """
    task = infer_task(request_text, capability)
    route = task_select_node(task)

    # ---- fallback node if nothing available -------------------------------
    if not route.get("available") or not route.get("models"):
        return {
            "name": "rx9070-node",
            "host": "192.168.1.50",
            "port": 1234,
            "model": DEFAULT_MODELS.get(task, "llama-3.1-8b-instruct"),
            "capability": task,
            "available": True,
        }

    # ---- model selection --------------------------------------------------
    models_on_node = route.get("models", [])
    preferred = DEFAULT_MODELS.get(task)

    selected = preferred          # sensible default

    if _USE_ADAPTIVE and models_on_node and _USE_REGISTRY:
        # Hybrid scoring: capability + historical performance
        ranked = [(m, hybrid_score(task, m)) for m in models_on_node if m in MODEL_REGISTRY]
        ranked.sort(key=lambda x: x[1], reverse=True)
        if ranked:
            selected = ranked[0][0]
    elif _USE_REGISTRY and models_on_node:
        # Capability-only scoring
        best = best_for_task(task, models_on_node)
        if best:
            selected = best
    elif preferred and preferred in models_on_node:
        selected = preferred
    elif models_on_node:
        selected = models_on_node[0]
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
