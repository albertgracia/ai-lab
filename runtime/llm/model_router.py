from __future__ import annotations

import json
from pathlib import Path

from runtime.distributed.task_router import select_node as task_select_node
from runtime.models.model_discovery import discover_all_models

try:
    from runtime.models.model_registry import (
        MODEL_REGISTRY,
        best_for_task,
        get_best_model,
        get_model_metadata,
        get_model_scores,
        get_model_skills,
        merge_registry_with_discovery,
        normalize_model_id,
        score_model,
    )
    _USE_REGISTRY = True
except ImportError:
    MODEL_REGISTRY = {}
    def best_for_task(task_type, available_models=None):  # type: ignore[no-redef]
        return None
    def get_best_model(task_type, available_models=None):  # type: ignore[no-redef]
        return []
    def get_model_metadata(model_id: str):  # type: ignore[no-redef]
        return None
    def get_model_scores(model_id: str):  # type: ignore[no-redef]
        return {}
    def get_model_skills(model_id: str):  # type: ignore[no-redef]
        return []
    def merge_registry_with_discovery(model_id: str, discovered: dict):  # type: ignore[no-redef]
        return {"id": model_id, "source": "static"}
    def normalize_model_id(model_id: str):  # type: ignore[no-redef]
        return model_id
    def score_model(task_type, model_id, node_state=None):  # type: ignore[no-redef]
        return 0
    _USE_REGISTRY = False

try:
    from runtime.routing.adaptive_scoring import hybrid_score
    _USE_ADAPTIVE = True
except ImportError:
    _USE_ADAPTIVE = False


DEFAULT_MODELS = {
    "fast": "llama-3.1-8b-instruct",
    "coding": "llama-3.1-8b-instruct",
    "reasoning": "qwen2.5-coder-32b-instruct",
    "general": "llama-3.1-8b-instruct",
}


def infer_task(request_text=None, capability=None):
    """Classify request_text into a task type."""
    if capability:
        return capability
    text = (request_text or "").lower()
    if any(
        w in text
        for w in [
            "tool use",
            "tool-use",
            "tool_calls",
            "tool calls",
            "function_call",
            "function calling",
            "use tools",
        ]
    ):
        return "tool_use"
    if any(
        w in text
        for w in [
            "5 lineas",
            "5 líneas",
            "maximo 5",
            "máximo 5",
            "breve",
            "brevemente",
            "resumen corto",
        ]
    ):
        return "fast"
    if len(text) > 500:
        return "reasoning"
    if any(
        w in text
        for w in [
            "python",
            "code",
            "script",
            "bug",
            "api",
            "refactor",
            "debug",
            "fix",
            "execute_v1_policy",
            "whitelist",
        ]
    ):
        return "coding"
    if any(
        w in text
        for w in [
            "arquitectura",
            "architecture",
            "arquitect",
            "complex",
            "analyze",
            "analiza",
            "analisis",
            "análisis",
            "optimizar",
            "óptimo",
            "optimo",
            "infraestructura",
            "infrastructure",
            "informe",
            "report",
            "analisis",
            "diagnostico",
            "razonamiento",
            "reasoning",
            "estado actual",
            "resumen",
        ]
    ):
        return "reasoning"
    return "fast"


def _load_node_config() -> dict[str, dict]:
    nodes: dict[str, dict] = {}
    cfg = Path("/opt/ai-lab/config/inference_nodes.json")
    try:
        if cfg.exists():
            data = json.loads(cfg.read_text(encoding="utf-8"))
            for node_name, node in data.get("nodes", {}).items():
                nodes[node.get("host", "")] = {
                    "name": node_name,
                    "host": node.get("host", ""),
                    "port": node.get("port", 1234),
                    "vram_gb": node.get("vram_gb", 0),
                    "priority": node.get("priority", 0),
                    "enabled": bool(node.get("enabled", True)),
                    "role": node.get("role", ""),
                }
    except Exception:
        pass
    return nodes


def _get_real_models(node_name: str, node_host: str) -> list[str] | None:
    try:
        state_file = Path("/opt/ai-lab/runtime/state/cluster_state.json")
        if state_file.exists():
            state = json.loads(state_file.read_text(encoding="utf-8"))
            for n in state.get("discovered_nodes", []):
                if n.get("name") == node_name or n.get("host") == node_host:
                    models = n.get("models", [])
                    if models:
                        return models
    except Exception:
        pass

    try:
        import urllib.request

        url = f"http://{node_host}:1234/v1/models" if node_host else None
        if url:
            resp = urllib.request.urlopen(url, timeout=3)
            data = json.loads(resp.read())
            models = [m["id"] for m in data.get("data", []) if isinstance(m, dict) and m.get("id")]
            if models:
                return models
    except Exception:
        pass
    return None


def _task_match_score(task: str, meta: dict) -> float:
    model_type = meta.get("type") or "general"
    skills = set(meta.get("skills", []))
    if task == "fast":
        if model_type in ("fast", "general"):
            return 1.0
        if "fast" in skills or "chat" in skills:
            return 0.82
        return 0.45
    if task == "coding":
        if model_type == "coding":
            return 1.0
        if {"coding", "debugging", "refactor"} & skills:
            return 0.92
        if model_type == "reasoning":
            return 0.7
        return 0.35
    if task == "reasoning":
        if model_type == "reasoning":
            return 1.0
        if {"reasoning", "analysis", "architecture"} & skills:
            return 0.93
        if model_type == "coding":
            return 0.78
        return 0.4
    if task == "tool_use":
        if model_type == "tool_use":
            return 1.0
        if {"tool-use", "reasoning", "analysis", "architecture"} & skills:
            return 0.94
        if model_type in ("reasoning", "coding"):
            return 0.8
        return 0.35
    if task == "vision":
        return 1.0 if meta.get("vision") else 0.1
    if task == "embeddings":
        return 1.0 if meta.get("embedding") else 0.1
    return 1.0 if model_type in ("general", "fast") else 0.7


def _speed_score(task: str, meta: dict) -> float:
    size_b = int(meta.get("size_b") or 0)
    if size_b <= 0:
        return 0.45
    if task == "fast":
        return max(0.2, 1.0 - min(size_b, 32) / 40.0)
    if task == "coding":
        return min(1.0, 0.35 + min(size_b, 32) / 48.0)
    if task == "reasoning":
        return min(1.0, 0.4 + min(size_b, 32) / 40.0)
    if task == "tool_use":
        return min(1.0, 0.45 + min(size_b, 32) / 44.0)
    return min(1.0, 0.5 + min(size_b, 32) / 60.0)


def _performance_score(task: str, model_id: str, meta: dict, perf_map: dict) -> float:
    entry = perf_map.get(model_id) or perf_map.get(normalize_model_id(model_id), {})
    if isinstance(entry, dict) and entry:
        return min(1.0, max(0.0, float(entry.get("performance_index", 0)) / 100.0))

    size_b = int(meta.get("size_b") or 0)
    if task == "fast":
        return max(0.25, 1.0 - min(size_b, 32) / 36.0)
    if task in ("coding", "reasoning"):
        return min(1.0, 0.45 + min(size_b, 32) / 48.0)
    return 0.5


def select_node(request_text, capability=None):
    """Select the best node/model pair using live discovery plus fallbacks."""
    task = infer_task(request_text, capability)
    route = task_select_node(task)
    discovery = discover_all_models(force=False)
    discovered_nodes = discovery.get("nodes", []) if isinstance(discovery, dict) else []
    node_cfg = _load_node_config()

    perf_map = {}
    try:
        from runtime.routing.model_performance import get_model_performance
        perf_map = get_model_performance(task_type=task)
    except Exception:
        perf_map = {}

    health_map = {}
    try:
        from runtime.health.model_health import model_health_score
    except Exception:
        model_health_score = None  # type: ignore[assignment]

    candidates: list[dict] = []

    for node in discovered_nodes:
        if not node.get("online"):
            continue
        host = node.get("host", "")
        cfg = node_cfg.get(host, {})
        node_models = node.get("models", []) or []
        for item in node_models:
            model_id = item.get("id") if isinstance(item, dict) else item
            if not model_id:
                continue

            meta = get_model_metadata(model_id) if _USE_REGISTRY else None
            if not meta:
                continue
            merged = merge_registry_with_discovery(model_id, {**node, "node": cfg.get("name") or node.get("name") or host})

            if task not in ("vision", "embeddings", "tool_use"):
                if merged.get("embedding") or "embeddings" in merged.get("skills", []):
                    continue
                if merged.get("vision") or "vision" in merged.get("skills", []):
                    continue
                if merged.get("tool_use") or "tool-use" in merged.get("skills", []):
                    continue
            if task == "vision" and not (merged.get("vision") or "vision" in merged.get("skills", [])):
                continue
            if task == "embeddings" and not (merged.get("embedding") or "embeddings" in merged.get("skills", [])):
                continue
            if task == "tool_use" and not (merged.get("tool_use") or "tool-use" in merged.get("skills", [])):
                continue

            capability_score = float(score_model(task, model_id)) / 100.0 if _USE_REGISTRY else 0.0
            task_match_score = _task_match_score(task, merged)
            performance_score = _performance_score(task, model_id, merged, perf_map)
            node_availability_score = 1.0 if node.get("online") else 0.0
            speed_score = _speed_score(task, merged)
            health_score = (
                model_health_score(model_id, cfg.get("name") or node.get("name") or host)
                if model_health_score
                else 0.50
            )

            total = (
                capability_score * 0.40
                + task_match_score * 0.22
                + performance_score * 0.13
                + node_availability_score * 0.10
                + speed_score * 0.05
                + health_score * 0.10
            )

            max_vram = max((cfg.get("vram_gb", 0) or 0) for cfg in node_cfg.values()) if node_cfg else 0
            reason_codes = [
                "lmstudio_discovery",
                "node_online",
                "model_chat_eligible" if merged.get("chat_eligible", True) else "model_not_chat_eligible",
                f"task_match_{task}",
                merged.get("model_metadata_source", "heuristic") + "_metadata",
            ]
            if model_id in perf_map or normalize_model_id(model_id) in perf_map:
                reason_codes.append("performance_index_available")
            if max_vram and (cfg.get("vram_gb", 0) or 0) >= max_vram:
                reason_codes.append("higher_vram")

            candidates.append(
                {
                    "score": round(total * 100, 1),
                    "node": node,
                    "cfg": cfg,
                    "model_id": model_id,
                    "metadata": merged,
                    "reason_codes": list(dict.fromkeys(reason_codes)),
                }
            )

    if candidates:
        candidates.sort(
            key=lambda item: (
                item["score"],
                (item["cfg"].get("vram_gb", 0) or 0),
                -(item["node"].get("latency_ms") or 9999),
            ),
            reverse=True,
        )
        best = candidates[0]
        node = best["node"]
        cfg = best["cfg"]
        meta = best["metadata"]
        return {
            "name": cfg.get("name") or node.get("name") or node.get("host") or "unknown",
            "host": node.get("host", "192.168.1.50"),
            "port": int(node.get("port", 1234) or 1234),
            "model": best["model_id"],
            "capability": task,
            "available": True,
            "mode": route.get("mode", "primary") if route.get("available", True) else "fallback",
            "reason_codes": best["reason_codes"],
            "discovery_source": "lmstudio",
            "model_metadata_source": meta.get("model_metadata_source", meta.get("source", "heuristic")),
            "selected_model": best["model_id"],
            "selected_node": cfg.get("name") or node.get("name") or node.get("host") or "unknown",
            "selected_score": best["score"],
        }

    if not route.get("available") or not route.get("models"):
        host = "192.168.1.50"
        real_models = _get_real_models("", host) or ["llama-3.1-8b-instruct", "qwen2.5-coder-14b-instruct"]
        selected = DEFAULT_MODELS.get(task, real_models[0])
        try:
            if _USE_REGISTRY:
                best = best_for_task(task, real_models)
                if best:
                    selected = best
        except Exception:
            if task in ("coding", "reasoning") and "qwen2.5-coder-14b-instruct" in real_models:
                selected = "qwen2.5-coder-14b-instruct"
        return {
            "name": "rx9070-node",
            "host": host,
            "port": 1234,
            "model": selected,
            "capability": task,
            "available": True,
            "mode": route.get("mode", "primary"),
            "reason_codes": ["fallback", "registry_fallback"],
            "discovery_source": "static",
            "model_metadata_source": "registry",
        }

    models_on_node = route.get("models", [])
    _real = _get_real_models(route.get("name", ""), route.get("host", ""))
    if _real:
        models_on_node = _real

    preferred = DEFAULT_MODELS.get(task)
    selected = preferred

    if _USE_ADAPTIVE and models_on_node and _USE_REGISTRY:
        ranked = [(m, hybrid_score(task, m)) for m in models_on_node if m in MODEL_REGISTRY]
        ranked.sort(key=lambda x: x[1], reverse=True)
        if ranked:
            selected = ranked[0][0]
    elif _USE_REGISTRY and models_on_node:
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
        "mode": route.get("mode", "primary"),
        "reason_codes": ["task_router_fallback", "registry_fallback"],
        "discovery_source": "static",
        "model_metadata_source": "registry" if _USE_REGISTRY else "static",
    }
