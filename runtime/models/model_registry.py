"""MODEL-REGISTRY-CANONICAL-01: canonical model registry for AI-LAB.

This module is the single source of truth for *model identities*.

Hard rules:
- Deterministic, import-safe, lightweight.
- No network calls, no persistence, no dynamic discovery.
- Fail-safe helpers: never raise for unknown inputs.

Notes:
- The bottom of this file contains the legacy capability-scoring registry.
  It remains for backward compatibility with existing routing/scoring.
  New code should prefer the canonical helpers defined near the top.

Architecture:
    model_registry.py
        └── imported by capability_router.py (with fallback)
        └── imported by model_router.py (with fallback)

All existing APIs are preserved.  If this module fails to load,
the original routing behaviour is used as fallback.
"""

# ── canonical registry (single source of truth) ───────────────────────────

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ModelRole(str, Enum):
    CODER = "CODER"
    FASTPATH = "FASTPATH"
    EMBEDDING = "EMBEDDING"
    REASONING = "REASONING"
    ORCHESTRATION = "ORCHESTRATION"


@dataclass(frozen=True)
class ModelDescriptor:
    canonical_id: str
    role: ModelRole
    provider: str
    aliases: tuple[str, ...] = ()
    deprecated_aliases: tuple[str, ...] = ()
    routable: bool = True
    supports_streaming: bool = True
    supports_tools: bool = False
    supports_embeddings: bool = False
    preferred_runtime: str = "lmstudio"
    cognitive_domain: str = "runtime"
    status: str = "active"  # active|disabled|inventory

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "role": self.role.value,
            "provider": self.provider,
            "aliases": list(self.aliases or ()),
            "deprecated_aliases": list(self.deprecated_aliases or ()),
            "routable": bool(self.routable),
            "supports_streaming": bool(self.supports_streaming),
            "supports_tools": bool(self.supports_tools),
            "supports_embeddings": bool(self.supports_embeddings),
            "preferred_runtime": self.preferred_runtime,
            "cognitive_domain": self.cognitive_domain,
            "status": self.status,
        }


# Canonical models (must remain stable identifiers)
MODEL_QWEN_14B = "qwen/qwen2.5-coder-14b-instruct"
MODEL_LLAMA_8B = "llama-3.1-8b-instruct"
MODEL_NOMIC_EMBED = "text-embedding-nomic-embed-text-v1.5"

DEPRECATED_QWEN_14B_ALIAS = "lmstudio-community/qwen2.5-coder-14b-instruct"
TOLERATED_QWEN_14B_ALIAS = "qwen2.5-coder-14b-instruct"


_CANONICAL_MODELS: tuple[ModelDescriptor, ...] = (
    ModelDescriptor(
        canonical_id=MODEL_QWEN_14B,
        role=ModelRole.CODER,
        provider="qwen",
        aliases=(TOLERATED_QWEN_14B_ALIAS,),
        deprecated_aliases=(DEPRECATED_QWEN_14B_ALIAS,),
        routable=True,
        supports_streaming=True,
        supports_tools=False,
        supports_embeddings=False,
        preferred_runtime="lmstudio",
        cognitive_domain="coding",
        status="active",
    ),
    ModelDescriptor(
        canonical_id=MODEL_LLAMA_8B,
        role=ModelRole.FASTPATH,
        provider="meta",
        aliases=(),
        deprecated_aliases=(),
        routable=True,
        supports_streaming=True,
        supports_tools=False,
        supports_embeddings=False,
        preferred_runtime="lmstudio",
        cognitive_domain="fastpath",
        status="active",
    ),
    ModelDescriptor(
        canonical_id=MODEL_NOMIC_EMBED,
        role=ModelRole.EMBEDDING,
        provider="nomic",
        aliases=(),
        deprecated_aliases=(),
        routable=False,
        supports_streaming=False,
        supports_tools=False,
        supports_embeddings=True,
        preferred_runtime="lmstudio",
        cognitive_domain="embeddings",
        status="active",
    ),
)


_DESCRIPTOR_BY_CANONICAL: dict[str, ModelDescriptor] = {m.canonical_id: m for m in _CANONICAL_MODELS}

# Build alias maps deterministically.
_ALIAS_TO_CANONICAL: dict[str, str] = {}
_DEPRECATED_ALIAS_SET: set[str] = set()
for m in _CANONICAL_MODELS:
    _ALIAS_TO_CANONICAL[m.canonical_id.lower()] = m.canonical_id
    for a in m.aliases:
        _ALIAS_TO_CANONICAL[str(a).lower()] = m.canonical_id
    for da in m.deprecated_aliases:
        _ALIAS_TO_CANONICAL[str(da).lower()] = m.canonical_id
        _DEPRECATED_ALIAS_SET.add(str(da).lower())


def normalize_model_id(model_id: str | None) -> str:
    """Normalize any incoming model_id into a canonical_id when possible.

    Examples:
    - qwen2.5-coder-14b-instruct -> qwen/qwen2.5-coder-14b-instruct
    - qwen/qwen2.5-coder-14b-instruct -> qwen/qwen2.5-coder-14b-instruct
    - lmstudio-community/qwen2.5-coder-14b-instruct -> qwen/qwen2.5-coder-14b-instruct (deprecated alias)
    """

    mid = (model_id or "").strip()
    if not mid:
        return ""
    key = mid.lower()
    return _ALIAS_TO_CANONICAL.get(key, mid)


def is_deprecated_model(model_id: str | None) -> bool:
    mid = (model_id or "").strip().lower()
    if not mid:
        return False
    return mid in _DEPRECATED_ALIAS_SET


def get_canonical_model(model_id: str | None) -> str:
    """Return the canonical model id (or empty string if input is empty)."""

    return normalize_model_id(model_id)


def get_model_role(model_id: str | None) -> str:
    canonical = normalize_model_id(model_id)
    desc = _DESCRIPTOR_BY_CANONICAL.get(canonical)
    return desc.role.value if desc else "UNKNOWN"


def get_routable_models() -> list[str]:
    # Deterministic ordering.
    out = [m.canonical_id for m in _CANONICAL_MODELS if bool(m.routable)]
    out.sort()
    return out


def get_preferred_model_for_role(role: str | ModelRole) -> str:
    r = role.value if isinstance(role, ModelRole) else str(role or "").upper()
    for m in _CANONICAL_MODELS:
        if m.role.value == r and m.routable:
            return m.canonical_id
    # Fail-safe fallback (no routing decisions): return empty.
    return ""


def build_public_registry_snapshot() -> dict[str, Any]:
    models = [m.to_public_dict() for m in sorted(_CANONICAL_MODELS, key=lambda x: x.canonical_id)]
    deprecated = sorted({a for m in _CANONICAL_MODELS for a in (m.deprecated_aliases or ())})
    tolerated = sorted({a for m in _CANONICAL_MODELS for a in (m.aliases or ())})
    routable = sorted([m.canonical_id for m in _CANONICAL_MODELS if m.routable])
    return {
        "contract_version": "MODEL-REGISTRY-CANONICAL-01",
        "canonical_models": models,
        "routable_models": routable,
        "aliases_tolerated": tolerated,
        "aliases_deprecated": deprecated,
        "total": int(len(models)),
        "routable_total": int(len(routable)),
        "deprecated_total": int(len(deprecated)),
    }


# ── legacy capability scoring registry (kept for backward compatibility) ───
# Every model currently loaded on our GPU nodes.
# Add / update here when you load new models in LM Studio.

LEGACY_MODEL_REGISTRY = {
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
        "skills": ["coding", "debugging", "refactor", "testing", "fast", "general", "chat"],
        "scores": {"reasoning": 7, "coding": 9, "speed": 9, "memory": 8},
        "context_window": 32_768,
        "latency_profile": "medium",
        "gpu": "RX9070",
        "gpu_ip": "192.168.1.50",
        "node": "rx9070-node",
        "priority": 20,
    },
    "qwen3.6-27b": {
        "display_name": "Qwen 3.6 27B",
        "skills": ["tool-use", "reasoning", "analysis", "architecture", "coding"],
        "tool_use": True,
        "scores": {"reasoning": 10, "coding": 10, "speed": 10, "memory": 10},
        "context_window": 32_768,
        "latency_profile": "fast",
        "gpu": "RX9070",
        "gpu_ip": "192.168.1.50",
        "node": "rx9070-node",
        "priority": 40,
        "enabled": False,
        "disabled_reason": "FASE29.3: three-model-runtime simplification",
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

MODEL_REGISTRY = LEGACY_MODEL_REGISTRY  # backward compat alias
model_registry = LEGACY_MODEL_REGISTRY

MODEL_ALIASES = {
    "Qwen2.5-Coder-32B-Instruct-GGUF-Q4_K_M": "qwen2.5-coder-32b-instruct",
    # lmstudio-community publisher → canon interno
    # FASE 30I-F0: deprecated for operational runtime, hidden from operational inventory
    "lmstudio-community/qwen2.5-coder-14b-instruct": "qwen2.5-coder-14b-instruct",
    "lmstudio-community/qwen2.5-coder-32b-instruct": "qwen2.5-coder-32b-instruct",
    "lmstudio-community/qwen3.6-27b": "qwen3.6-27b",
    # qwen/ prefix (LM Studio native) → canon interno
    "qwen/qwen2.5-coder-14b-instruct": "qwen2.5-coder-14b-instruct",
    "qwen/qwen2.5-coder-32b-instruct": "qwen2.5-coder-32b-instruct",
    "qwen/qwen3.6-27b": "qwen3.6-27b",
}


# ── task → dimension mapping ─────────────────────────────────────────────
# Weight per scoring dimension for each task type.
# The model's raw score in that dimension is multiplied by the weight.
# Sum of weighted scores × 10 = final capability score (0-100).

TASK_MODEL_SCORING = {
    "coding":    {"coding": 1.0, "speed": 0.3, "reasoning": 0.5, "memory": 0.2},
    "reasoning": {"reasoning": 1.0, "coding": 0.4, "speed": 0.1, "memory": 0.3},
    "fast":      {"speed": 1.0, "coding": 0.4, "reasoning": 0.2, "memory": 0.1},
    "tool_use":   {"reasoning": 0.8, "coding": 0.5, "speed": 0.2, "memory": 0.3},
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
    canonical = normalize_legacy_model_id(model_id)
    model = LEGACY_MODEL_REGISTRY.get(model_id) or LEGACY_MODEL_REGISTRY.get(canonical)
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
    candidates = available_models or list(LEGACY_MODEL_REGISTRY.keys())
    # FASE 29.3: filter out disabled models
    candidates = [m for m in candidates if LEGACY_MODEL_REGISTRY.get(m, {}).get("enabled", True)]
    scored = [(mid, score_model(task_type, mid)) for mid in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def best_for_task(task_type, available_models=None):
    """Convenience: return the single best model_id (or None)."""
    ranked = get_best_model(task_type, available_models)
    return ranked[0][0] if ranked else None


def normalize_legacy_model_id(model_id: str) -> str:
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
    canonical = normalize_legacy_model_id(model_id)
    if canonical in LEGACY_MODEL_REGISTRY:
        meta = dict(LEGACY_MODEL_REGISTRY[canonical])
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
    canonical = normalize_legacy_model_id(model_id)
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
