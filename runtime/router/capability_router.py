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


def choose_model(task_type="general"):
    """Return the best model_id (str) for *task_type*.

    Uses multi-factor capability scoring when the model registry is
    available; otherwise falls back to the original keyword‑based logic.
    """
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
