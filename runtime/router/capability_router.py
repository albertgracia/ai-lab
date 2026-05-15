# ── capability router ────────────────────────────────────────────────────
# Uses model_registry for multi-factor scoring when available.
# Falls back to original hardcoded logic if the registry fails to load.

# ---- original static capabilities (preserved as fallback) ---------------
MODEL_CAPABILITIES = {
    "llama-3.1-8b-instruct": {
        "reasoning": 5, "coding": 7, "speed": 10, "memory": 8, "node": "rx9070",
    },
    "qwen2.5-coder-32b-instruct": {
        "reasoning": 9, "coding": 10, "speed": 4, "memory": 5, "node": "rx7900xt",
    },
}

# ---- try loading the new model registry ---------------------------------
_USE_REGISTRY = False
try:
    from runtime.models.model_registry import (
        MODEL_REGISTRY, get_best_model, best_for_task,
    )
    _USE_REGISTRY = True
except ImportError:
    pass

# ---- try loading adaptive scoring (hybrid capability + performance) -----
_USE_ADAPTIVE = False
try:
    from runtime.routing.adaptive_scoring import hybrid_score
    _USE_ADAPTIVE = True
except ImportError:
    pass


def choose_model(task_type="general"):
    """Return the best model_id (str) for *task_type*.

    Priority:
      1. Adaptive hybrid scoring (capability + historical performance)
      2. Static capability scoring (model registry)
      3. Original hardcoded fallback
    """
    # ── adaptive path (best) ─────────────────────────────────────────
    if _USE_ADAPTIVE and _USE_REGISTRY:
        ranked = [(m, hybrid_score(task_type, m)) for m in MODEL_REGISTRY]
        ranked.sort(key=lambda x: x[1], reverse=True)
        if ranked and ranked[0][1] > 0:
            return ranked[0][0]

    # ── registry path ────────────────────────────────────────────────
    if _USE_REGISTRY:
        model_id = best_for_task(task_type)
        if model_id:
            return model_id

    # ── fallback (original behaviour) ─────────────────────────────────
    if task_type == "coding":
        return "llama-3.1-8b-instruct"
    if task_type == "reasoning":
        return "qwen2.5-coder-32b-instruct"
    if task_type == "fast":
        return "llama-3.1-8b-instruct"
    return "llama-3.1-8b-instruct"
