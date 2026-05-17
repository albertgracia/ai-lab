"""LM Studio model discovery with short-lived in-memory cache."""

from __future__ import annotations

import copy
import json
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

_CACHE_LOCK = threading.Lock()
_DISCOVERY_CACHE: dict[str, Any] = {
    "timestamp": 0,
    "ttl_seconds": 60,
    "nodes": [],
    "nodes_scanned": 0,
    "models_found": 0,
    "online_nodes": 0,
    "total_nodes": 0,
}


def _default_nodes() -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []

    cfg_path = Path("/opt/ai-lab/config/inference_nodes.json")
    try:
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            for node_name, node in cfg.get("nodes", {}).items():
                nodes.append(
                    {
                        "name": node_name,
                        "host": node.get("host", ""),
                        "port": node.get("port", 1234),
                        "enabled": bool(node.get("enabled", True)),
                    }
                )
    except Exception:
        pass

    if nodes:
        return nodes

    state_path = Path("/opt/ai-lab/runtime/state/cluster_state.json")
    try:
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding="utf-8"))
            for node in state.get("discovered_nodes", []) or state.get("nodes", []):
                nodes.append(
                    {
                        "name": node.get("name") or node.get("host", ""),
                        "host": node.get("host", ""),
                        "port": node.get("port", 1234),
                        "enabled": True,
                    }
                )
    except Exception:
        pass

    return nodes


def _fetch_node_models(node: dict[str, Any], timeout: float = 2.0) -> dict[str, Any]:
    start = time.time()
    host = node.get("host", "")
    port = int(node.get("port", 1234) or 1234)
    result: dict[str, Any] = {
        "name": node.get("name") or host or "unknown",
        "host": host,
        "port": port,
        "online": False,
        "latency_ms": None,
        "models": [],
        "error": None,
        "source": "lmstudio_discovery",
    }

    if not host:
        result["error"] = "missing host"
        return result

    url = f"http://{host}:{port}/v1/models"
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
        data = payload.get("data", payload)
        if isinstance(data, dict):
            data = [data]

        models: list[dict[str, Any]] = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    model_id = item
                    model_obj = "model"
                elif isinstance(item, dict):
                    model_id = item.get("id") or item.get("model") or item.get("name")
                    model_obj = item.get("object", "model")
                else:
                    continue
                if not model_id:
                    continue
                models.append({"id": model_id, "object": model_obj, "source": "lmstudio_discovery"})

        result["online"] = True
        result["latency_ms"] = round((time.time() - start) * 1000, 2)
        result["models"] = models
        return result
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = str(exc)
        result["error"] = f"HTTP {exc.code}: {body[:300]}"
    except Exception as exc:
        result["error"] = str(exc)

    result["latency_ms"] = round((time.time() - start) * 1000, 2)
    return result


def discover_node_models(node: dict[str, Any], timeout: float = 2.0) -> dict[str, Any]:
    try:
        return _fetch_node_models(node, timeout=timeout)
    except Exception as exc:
        return {
            "name": node.get("name") or node.get("host", "unknown"),
            "host": node.get("host", ""),
            "port": int(node.get("port", 1234) or 1234),
            "online": False,
            "latency_ms": None,
            "models": [],
            "error": str(exc),
            "source": "lmstudio_discovery",
        }


def discover_all_models(nodes: list[dict[str, Any]] | None = None, force: bool = False) -> dict[str, Any]:
    ttl_seconds = 60
    now = int(time.time())

    with _CACHE_LOCK:
        cache_age = now - int(_DISCOVERY_CACHE.get("timestamp", 0) or 0)
        if not force and _DISCOVERY_CACHE.get("nodes") and cache_age < ttl_seconds:
            return copy.deepcopy(_DISCOVERY_CACHE)

    candidate_nodes = nodes or _default_nodes()
    if not candidate_nodes:
        snapshot = {
            "timestamp": now,
            "ttl_seconds": ttl_seconds,
            "nodes": [],
            "nodes_scanned": 0,
            "models_found": 0,
            "online_nodes": 0,
            "total_nodes": 0,
        }
        with _CACHE_LOCK:
            _DISCOVERY_CACHE.update(snapshot)
        return copy.deepcopy(snapshot)

    results: list[dict[str, Any]] = []
    max_workers = min(8, max(len(candidate_nodes), 1))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(discover_node_models, node, 2.0): node for node in candidate_nodes}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                node = futures[future]
                results.append(
                    {
                        "name": node.get("name") or node.get("host", "unknown"),
                        "host": node.get("host", ""),
                        "port": int(node.get("port", 1234) or 1234),
                        "online": False,
                        "latency_ms": None,
                        "models": [],
                        "error": str(exc),
                        "source": "lmstudio_discovery",
                    }
                )

    snapshot = {
        "timestamp": now,
        "ttl_seconds": ttl_seconds,
        "nodes": sorted(results, key=lambda item: item.get("host", "")),
        "nodes_scanned": len(candidate_nodes),
        "models_found": sum(len(node.get("models", [])) for node in results),
        "online_nodes": sum(1 for node in results if node.get("online")),
        "total_nodes": len(candidate_nodes),
    }

    with _CACHE_LOCK:
        _DISCOVERY_CACHE.update(snapshot)

    return copy.deepcopy(snapshot)


def get_cached_discovery() -> dict[str, Any]:
    with _CACHE_LOCK:
        return copy.deepcopy(_DISCOVERY_CACHE)


def clear_discovery_cache() -> None:
    with _CACHE_LOCK:
        _DISCOVERY_CACHE.update(
            {
                "timestamp": 0,
                "ttl_seconds": 60,
                "nodes": [],
                "nodes_scanned": 0,
                "models_found": 0,
                "online_nodes": 0,
                "total_nodes": 0,
            }
        )
