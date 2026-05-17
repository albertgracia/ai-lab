"""Model Registry — capability scoring, multi-factor routing intelligence.

Architecture:
    model_registry.py
        └── imported by capability_router.py (with fallback)
        └── imported by model_router.py (with fallback)

All existing APIs are preserved.  If this module fails to load,
the original routing behaviour is used as fallback.
"""

# ── model registry ────────────────────────────────────────────────────────
# Every model currently loaded on our GPU nodes.
# Add / update here when you load new models in LM Studio.

MODEL_REGISTRY = {
    # ── RX9070 (192.168.1.50) · 16 GB VRAM ────────────────────────────
    "llama-3.1-8b-instruct": {
        "display_name": "Llama 3.1 8B",
        "skills": ["fast", "general", "chat", "summarisation"],
        "scores": {"reasoning": 5, "coding": 7, "speed": 10, "memory": 8},
        "context_window": 128_000,
        "latency_profile": "fast",
        "gpu": "RX9070",
        "gpu_ip": "192.168.1.50",
        "node": "rx9070-node",
        "priority": 10,
    },
    "qwen2.5-coder-14b-instruct": {
        "display_name": "Qwen 2.5 Coder 14B",
        "skills": ["coding", "debugging", "refactor", "testing"],
        "scores": {"reasoning": 7, "coding": 9, "speed": 6, "memory": 6},
        "context_window": 32_768,
        "latency_profile": "medium",
        "gpu": "RX9070",
        "gpu_ip": "192.168.1.50",
        "node": "rx9070-node",
        "priority": 20,
    },
    "deepseek-r1-qwen3-8b": {
        "display_name": "DeepSeek R1 (Qwen3 8B)",
        "skills": ["reasoning", "analysis", "chain-of-thought"],
        "scores": {"reasoning": 8, "coding": 6, "speed": 5, "memory": 6},
        "context_window": 32_768,
        "latency_profile": "medium",
        "gpu": "RX9070",
        "gpu_ip": "192.168.1.50",
        "node": "rx9070-node",
        "priority": 30,
    },
    "text-embedding-nomic-embed-text-v1.5": {
        "display_name": "Nomic Embeddings v1.5",
        "skills": ["embeddings", "semantic-search", "rag"],
        "scores": {"reasoning": 0, "coding": 2, "speed": 10, "memory": 9},
        "context_window": 8_192,
        "latency_profile": "fast",
        "gpu": "RX9070",
        "gpu_ip": "192.168.1.50",
        "node": "rx9070-node",
        "priority": 5,
    },

    # ── RX7900XT (192.168.1.60) · 20 GB VRAM ─────────────────────────
    "qwen2.5-coder-32b-instruct": {
        "display_name": "Qwen 2.5 Coder 32B",
        "skills": ["coding", "architecture", "reasoning", "analysis"],
        "scores": {"reasoning": 9, "coding": 10, "speed": 4, "memory": 5},
        "context_window": 65_536,
        "latency_profile": "slow",
        "gpu": "RX7900XT",
        "gpu_ip": "192.168.1.60",
        "node": "rx7900xt-node",
        "priority": 10,
    },
    "deepseek-r1": {
        "display_name": "DeepSeek R1",
        "skills": ["reasoning", "architecture", "analysis", "chain-of-thought"],
        "scores": {"reasoning": 10, "coding": 7, "speed": 3, "memory": 4},
        "context_window": 65_536,
        "latency_profile": "slow",
        "gpu": "RX7900XT",
        "gpu_ip": "192.168.1.60",
        "node": "rx7900xt-node",
        "priority": 20,
    },
    "gemma-4-26b": {
        "display_name": "Gemma 4 26B",
        "skills": ["reasoning", "general", "analysis"],
        "scores": {"reasoning": 8, "coding": 6, "speed": 5, "memory": 7},
        "context_window": 32_768,
        "latency_profile": "medium",
        "gpu": "RX7900XT",
        "gpu_ip": "192.168.1.60",
        "node": "rx7900xt-node",
        "priority": 30,
    },
    "qwen3-14b-claude-sonnet-4.5-reasoning-distill": {
        "display_name": "Qwen3 14B (Reasoning Distill)",
        "skills": ["reasoning", "coding", "analysis", "refactor"],
        "scores": {"reasoning": 9, "coding": 8, "speed": 5, "memory": 6},
        "context_window": 32_768,
        "latency_profile": "medium",
        "gpu": "RX7900XT",
        "gpu_ip": "192.168.1.60",
        "node": "rx7900xt-node",
        "priority": 25,
    },
    "moondream2-20250414": {
        "display_name": "Moondream2 (Vision)",
        "skills": ["vision", "captioning", "ocr", "vqa"],
        "scores": {"reasoning": 1, "coding": 0, "speed": 8, "memory": 3},
        "context_window": 4_096,
        "latency_profile": "fast",
        "gpu": "RX7900XT",
        "gpu_ip": "192.168.1.60",
        "node": "rx7900xt-node",
        "priority": 5,
    },
    "text-embedding-nomic-embed-text-v2-moe": {
        "display_name": "Nomic Embed v2 MoE",
        "skills": ["embeddings", "semantic-search", "rag"],
        "scores": {"reasoning": 0, "coding": 1, "speed": 10, "memory": 9},
        "context_window": 8_192,
        "latency_profile": "fast",
        "gpu": "RX7900XT",
        "gpu_ip": "192.168.1.60",
        "node": "rx7900xt-node",
        "priority": 5,
    },
    "flux": {
        "display_name": "FLUX (Image Gen)",
        "skills": ["image-generation", "creative"],
        "scores": {"reasoning": 0, "coding": 0, "speed": 2, "memory": 2},
        "context_window": 2_048,
        "latency_profile": "slow",
        "gpu": "RX7900XT",
        "gpu_ip": "192.168.1.60",
        "node": "rx7900xt-node",
        "priority": 5,
    },
}

model_registry = MODEL_REGISTRY

MODEL_ALIASES = {
    "Qwen2.5-Coder-32B-Instruct-GGUF-Q4_K_M": "qwen2.5-coder-32b-instruct",
}


# ── task → dimension mapping ─────────────────────────────────────────────
# Weight per scoring dimension for each task type.
# The model's raw score in that dimension is multiplied by the weight.
# Sum of weighted scores × 10 = final capability score (0-100).

TASK_MODEL_SCORING = {
    "coding":    {"coding": 1.0, "speed": 0.3, "reasoning": 0.5, "memory": 0.2},
    "reasoning": {"reasoning": 1.0, "coding": 0.4, "speed": 0.1, "memory": 0.3},
    "fast":      {"speed": 1.0, "coding": 0.4, "reasoning": 0.2, "memory": 0.1},
    "general":   {"coding": 0.5, "reasoning": 0.5, "speed": 0.5, "memory": 0.3},
    "memory":    {"memory": 1.0, "speed": 0.5, "coding": 0.2, "reasoning": 0.2},
    "vision":    {"coding": 0.0, "reasoning": 0.0, "speed": 0.5, "memory": 0.5},
    "embeddings":{"memory": 1.0, "speed": 0.8, "coding": 0.1, "reasoning": 0.1},
}


# ── public API ────────────────────────────────────────────────────────────

def score_model(task_type, model_id, node_state=None):
    """Return a 0‑100 capability score for *model_id* performing *task_type*.

    Parameters
    ----------
    task_type : str   – e.g. "coding", "reasoning", "fast", "general"
    model_id  : str   – key in MODEL_REGISTRY
    node_state: dict | None – optional live state for future VRAM/latency
                               adjustments (reserved, not used yet)

    Returns
    -------
    int  (0‑100)
    """
    canonical = normalize_model_id(model_id)
    model = MODEL_REGISTRY.get(model_id) or MODEL_REGISTRY.get(canonical)
    if not model:
        try:
            from runtime.models.model_classifier import score_unknown_model
            return score_unknown_model(task_type, model_id)
        except ImportError:
            return 0

    weights = TASK_MODEL_SCORING.get(task_type, TASK_MODEL_SCORING["general"])
    total_weight = sum(weights.values()) or 1.0
    raw = sum(model["scores"].get(dim, 0) * weight
              for dim, weight in weights.items())
    # normalise: max possible = 10 (best score) × total_weight
    maximum = 10.0 * total_weight
    ratio = raw / maximum if maximum > 0 else 0
    return min(round(ratio * 100, 1), 100)


def get_best_model(task_type, available_models=None):
    """Return sorted list of *(model_id, score)* tuples for *task_type*.

    Parameters
    ----------
    task_type : str
    available_models : list[str] | None  – if set, only score these model IDs

    Returns
    -------
    list[tuple[str, int]]  (best first)
    """
    candidates = available_models or list(MODEL_REGISTRY.keys())
    scored = [(mid, score_model(task_type, mid)) for mid in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def best_for_task(task_type, available_models=None):
    """Convenience: return the single best model_id (or None)."""
    ranked = get_best_model(task_type, available_models)
    return ranked[0][0] if ranked else None


def normalize_model_id(model_id: str) -> str:
    if not model_id:
        return model_id
    if model_id in MODEL_ALIASES:
        return MODEL_ALIASES[model_id]
    lowered = model_id.strip().lower()
    for alias, canonical in MODEL_ALIASES.items():
        if lowered == alias.lower():
            return canonical
    if "/" in lowered:
        tail = lowered.split("/")[-1]
        if tail:
            return tail
    return lowered


def get_model_metadata(model_id: str):
    canonical = normalize_model_id(model_id)
    if canonical in MODEL_REGISTRY:
        meta = dict(MODEL_REGISTRY[canonical])
        meta["id"] = canonical
        meta["source"] = "registry"
        return meta

    try:
        from runtime.models.model_classifier import classify_model
        meta = classify_model(canonical)
        meta["source"] = "heuristic"
        return meta
    except ImportError:
        return None


def get_model_scores(model_id: str):
    meta = get_model_metadata(model_id)
    if not meta:
        return {}

    if meta.get("source") == "registry":
        scores = dict(meta.get("scores", {}))
        scores["capability_score"] = round(sum(scores.values()) / max(len(scores), 1), 1)
        scores["source"] = "registry"
        return scores

    try:
        from runtime.models.model_classifier import score_unknown_model
        size_b = int(meta.get("size_b") or 0)
        return {
            "reasoning": 9 if meta.get("type") == "reasoning" else 6,
            "coding": 9 if meta.get("type") == "coding" else 6,
            "speed": 10 if meta.get("type") in ("fast", "general") else 5,
            "memory": 8 if size_b <= 9 else 6 if size_b <= 14 else 5,
            "capability_score": score_unknown_model("general", model_id),
            "source": "heuristic",
        }
    except ImportError:
        return meta.get("scores", {}) if isinstance(meta, dict) else {}


def get_model_skills(model_id: str) -> list[str]:
    meta = get_model_metadata(model_id)
    if not meta:
        return []
    return list(meta.get("skills", []))


def merge_registry_with_discovery(model_id: str, discovered: dict) -> dict:
    canonical = normalize_model_id(model_id)
    meta = get_model_metadata(canonical) or {"id": canonical, "source": "heuristic"}
    merged = dict(meta)
    discovered = discovered or {}
    merged.update({
        "id": canonical,
        "discovered_id": model_id,
        "source": meta.get("source", "heuristic") if meta else "heuristic",
        "discovery_source": discovered.get("source", "lmstudio_discovery"),
    })
    if discovered:
        merged["node"] = discovered.get("node") or discovered.get("name")
        merged["host"] = discovered.get("host")
        merged["port"] = discovered.get("port")
        merged["online"] = discovered.get("online", False)
        merged["latency_ms"] = discovered.get("latency_ms")
        merged["discovered"] = discovered
    merged["model_metadata_source"] = "registry" if meta.get("source") == "registry" else "heuristic"
    return merged
