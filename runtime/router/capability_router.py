# ── capability router ────────────────────────────────────────────────────
# Uses model_registry for multi-factor scoring when available.
# Falls back to original hardcoded logic if the registry fails to load.

# ---- original static capabilities (preserved as fallback) ---------------
MODEL_CAPABILITIES = {
    "llama-3.1-8b-instruct": {
        "reasoning": 5, "coding": 7, "speed": 10, "memory": 8, "node": "rx9070",
    },
    "qwen2.5-coder-14b-instruct": {
        "reasoning": 8, "coding": 10, "speed": 8, "memory": 9, "node": "rx9070",
    },
    "qwen3.6-27b": {
        "reasoning": 10, "coding": 10, "speed": 6, "memory": 10, "node": "rx9070",
    },
    "qwen2.5-coder-32b-instruct": {
        "reasoning": 9, "coding": 10, "speed": 4, "memory": 5, "node": "rx7900xt",
    },
}

# ---- try loading the new model registry ---------------------------------
_USE_REGISTRY = False
try:
    from runtime.models.model_registry import (
        MODEL_REGISTRY, best_for_task, score_model,
    )
    from runtime.models.model_classifier import classify_model
    _USE_REGISTRY = True
except ImportError:
    pass

try:
    from runtime.models.model_discovery import discover_all_models
    _USE_DISCOVERY = True
except ImportError:
    discover_all_models = None  # type: ignore[assignment]
    _USE_DISCOVERY = False

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
    candidates = []

    if _USE_DISCOVERY:
        try:
            discovery = discover_all_models(force=False)
            for node in discovery.get("nodes", []):
                if not node.get("online"):
                    continue
                for model in node.get("models", []):
                    model_id = model.get("id") if isinstance(model, dict) else model
                    if model_id:
                        candidates.append(model_id)
        except Exception:
            pass

    if _USE_REGISTRY:
        candidates.extend(MODEL_REGISTRY.keys())

    if candidates:
        if task_type == "tool_use":
            tool_candidates = []
            for model_id in candidates:
                meta = None
                if model_id in MODEL_REGISTRY:
                    meta = MODEL_REGISTRY[model_id]
                else:
                    try:
                        meta = classify_model(model_id)
                    except Exception:
                        meta = None
                if meta and (meta.get("tool_use") or "tool-use" in meta.get("skills", [])):
                    tool_candidates.append(model_id)
            if tool_candidates:
                candidates = tool_candidates

        ranked = []
        seen = set()
        for model_id in candidates:
            if model_id in seen:
                continue
            seen.add(model_id)
            if _USE_ADAPTIVE and _USE_REGISTRY and model_id in MODEL_REGISTRY:
                score = hybrid_score(task_type, model_id)
            else:
                score = score_model(task_type, model_id)
            ranked.append((model_id, score))
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
        return "qwen2.5-coder-14b-instruct"
    if task_type == "reasoning":
        return "qwen2.5-coder-32b-instruct"
    if task_type == "fast":
        return "qwen2.5-coder-14b-instruct"
    return "qwen2.5-coder-14b-instruct"
