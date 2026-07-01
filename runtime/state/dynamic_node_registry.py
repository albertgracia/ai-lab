"""Dynamic Node Registry — live runtime inventory of compute nodes.

Provides a single live source of truth about node availability,
capabilities, models, and metrics. Distinguishes required baseline
nodes from optional on-demand nodes.

This is NOT the scheduler. This is the registry that future
scheduler, routing, and fallback logic will consume.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Schema ─────────────────────────────────────────────────────────────────

@dataclass
class NodeModel:
    id: str
    backend_id: str = "lmstudio"
    context: int = 0
    loaded: bool = False
    node: str = ""
    suitability: list[str] = field(default_factory=list)


@dataclass
class NodeMetrics:
    latency_ms: float | None = None
    health_score: float = 0.0
    gpu_utilization: float | None = None
    vram_total: float | None = None
    vram_used: float | None = None
    scrape_health: str = "unknown"


@dataclass
class NodeRegistryEntry:
    node_id: str
    hostname: str = ""
    ip: str = ""
    role: str = "on_demand"
    status: str = "unknown"
    availability_policy: str = "optional"
    capabilities: list[str] = field(default_factory=list)
    models: list[NodeModel] = field(default_factory=list)
    metrics: NodeMetrics = field(default_factory=NodeMetrics)
    routing_eligible: bool = False
    fallback_eligible: bool = False
    offline_is_failure: bool = False
    last_seen: float = 0.0
    evidence: list[str] = field(default_factory=list)
    contract_version: str = "DYNAMIC-NODE-REGISTRY-01"


# ── Static node definitions (source of truth for identity) ────────────────

NODE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "node_id": "nas-n5",
        "hostname": "NAS-N5",
        "ip": "192.168.1.250",
        "role": "baseline",
        "availability_policy": "required",
        "offline_is_failure": True,
        "description": "NAS primary, usually always ON, LM Studio secondary",
    },
    {
        "node_id": "rx9070-node",
        "hostname": "RX9070",
        "ip": "192.168.1.50",
        "role": "on_demand",
        "availability_policy": "optional",
        "offline_is_failure": False,
        "description": "Gaming PC RX9070, started on demand for inference",
    },
    {
        "node_id": "rx7900xt-node",
        "hostname": "RX7900XT",
        "ip": "192.168.1.60",
        "role": "on_demand",
        "availability_policy": "optional",
        "offline_is_failure": False,
        "description": "Gaming PC RX7900XT, started on demand for more power",
    },
]


# ── Helpers ────────────────────────────────────────────────────────────────

def _gib(bytes_val: int | None) -> float | None:
    if bytes_val is None:
        return None
    return round(bytes_val / 1073741824, 2)


def _infer_capabilities_from_models(model_ids: list[str]) -> list[str]:
    caps: set[str] = set()
    joined = " ".join(model_ids).lower()
    if "embed" in joined:
        caps.add("embeddings")
    if "vision" in joined or "moondream" in joined:
        caps.add("vision")
    if "multimodal" in joined or "vl-" in joined or "vision" in joined:
        caps.add("multimodal")
    if "coder" in joined or "code" in joined:
        caps.add("coding")
    if "deepseek" in joined or "r1" in joined or "reason" in joined:
        caps.add("reasoning")
    if "32b" in joined or "35b" in joined or "30b" in joined:
        caps.add("large-context")
    if "8b" in joined or "9b" in joined or "4b" in joined or "fast" in joined:
        caps.add("fast")
    caps.add("chat")
    if not caps - {"chat"}:
        caps.add("general")
    return sorted(caps)


def _suitability_for(model_id: str) -> list[str]:
    mid = model_id.lower()
    tasks = []
    if "embed" in mid:
        tasks.append("embeddings")
    if "vision" in mid or "moondream" in mid or "vl-" in mid:
        tasks.append("vision")
    if "coder" in mid or "code" in mid:
        tasks.append("coding")
    if "deepseek" in mid or "r1" in mid:
        tasks.append("reasoning")
    if "32b" in mid or "35b" in mid or "30b" in mid:
        tasks.append("large-context")
    if "8b" in mid or "9b" in mid or "4b" in mid:
        tasks.append("fast")
    if not tasks:
        tasks.append("general")
    return tasks


# ── Data collection ────────────────────────────────────────────────────────

def _fetch_lmstudio_models(ip: str, port: int = 1234, timeout: float = 5.0) -> dict[str, Any]:
    import urllib.request
    url = f"http://{ip}:{port}/v1/models"
    start = time.time()
    result: dict[str, Any] = {
        "online": False,
        "latency_ms": None,
        "models": [],
        "error": None,
    }
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        result["latency_ms"] = round((time.time() - start) * 1000, 2)
        data = payload.get("data", payload)
        if isinstance(data, dict):
            data = [data]
        if isinstance(data, list):
            models = []
            for item in data:
                if isinstance(item, str):
                    models.append(item)
                elif isinstance(item, dict):
                    mid = item.get("id") or item.get("model") or item.get("name")
                    if mid:
                        models.append(mid)
            result["models"] = models
        result["online"] = True
    except Exception as exc:
        result["error"] = str(exc)
        result["latency_ms"] = round((time.time() - start) * 1000, 2)
    return result


def _fetch_prometheus_targets(prom_url: str = "http://192.168.1.40:9090/api/v1/targets",
                               timeout: float = 5.0) -> dict[str, Any]:
    import urllib.request
    try:
        req = urllib.request.Request(prom_url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _fetch_gpu_metrics(ip: str, port: int = 9182, timeout: float = 5.0) -> dict[str, Any]:
    import urllib.request
    url = f"http://{ip}:{port}/metrics"
    result: dict[str, Any] = {
        "up": False,
        "vram_total_gib": None,
        "vram_used_gib": None,
        "error": None,
    }
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        result["up"] = True
        vt = vu = None
        for line in text.split("\n"):
            if "windows_gpu_dedicated_video_memory_size_bytes" in line and not line.startswith("#"):
                try:
                    vt = int(float(line.split()[-1]))
                except (ValueError, IndexError):
                    pass
            if "windows_gpu_adapter_memory_dedicated_bytes" in line and not line.startswith("#"):
                try:
                    vu = int(float(line.split()[-1]))
                except (ValueError, IndexError):
                    pass
        result["vram_total_gib"] = _gib(vt)
        result["vram_used_gib"] = _gib(vu)
    except Exception as exc:
        result["error"] = str(exc)
    return result


def _check_lmstudio_health(ip: str, port: int = 1234, timeout: float = 3.0) -> dict[str, Any]:
    import urllib.request
    url = f"http://{ip}:{port}/v1/models"
    start = time.time()
    result: dict[str, Any] = {"online": False, "latency_ms": None, "error": None}
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            _ = resp.read()
        result["online"] = True
        result["latency_ms"] = round((time.time() - start) * 1000, 2)
    except Exception as exc:
        result["error"] = str(exc)
        result["latency_ms"] = round((time.time() - start) * 1000, 2)
    return result


# ── Core registry functions ───────────────────────────────────────────────

def collect_lmstudio_models(node_def: dict[str, Any]) -> list[NodeModel]:
    ip = node_def["ip"]
    raw = _fetch_lmstudio_models(ip)
    models: list[NodeModel] = []
    if raw.get("online"):
        for mid in raw.get("models", []):
            models.append(NodeModel(
                id=mid,
                backend_id="lmstudio",
                loaded=True,
                node=node_def["node_id"],
                suitability=_suitability_for(mid),
            ))
    return models


def collect_prometheus_node_state() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    prom = _fetch_prometheus_targets()
    if prom.get("status") != "success":
        return result
    active = prom.get("data", {}).get("activeTargets", [])
    for target in active:
        labels = {}
        raw_labels = target.get("labels", {})
        if isinstance(raw_labels, str):
            try:
                for part in raw_labels.strip("@{ ").rstrip(" }").split("; "):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        labels[k.strip()] = v.strip()
            except Exception:
                labels = {}
        else:
            labels = raw_labels
        instance = labels.get("instance", "")
        health = target.get("health", "unknown")
        job = labels.get("job", "")
        last_scrape = target.get("lastScrape", "")
        result[f"{job}@{instance}"] = {
            "instance": instance,
            "job": job,
            "health": health,
            "last_scrape": last_scrape,
            "scrape_duration": target.get("lastScrapeDuration"),
        }
    return result


def classify_node_availability(node_def: dict[str, Any]) -> str:
    return node_def.get("availability_policy", "optional")


def build_capability_matrix(entries: list[NodeRegistryEntry]) -> dict[str, list[str]]:
    matrix: dict[str, list[str]] = {}
    for entry in entries:
        if entry.status == "online" and entry.routing_eligible:
            caps = list(entry.capabilities)
            for model in entry.models:
                caps.extend(model.suitability)
            matrix[entry.node_id] = sorted(set(caps))
    return matrix


def select_eligible_nodes(entries: list[NodeRegistryEntry],
                           requirements: list[str] | None = None) -> list[NodeRegistryEntry]:
    eligible = [e for e in entries if e.routing_eligible and e.status == "online"]
    if not requirements:
        return eligible
    result: list[NodeRegistryEntry] = []
    for entry in eligible:
        entry_caps = set(entry.capabilities)
        for model in entry.models:
            entry_caps.update(model.suitability)
        if all(req in entry_caps for req in requirements):
            result.append(entry)
    return result


def build_node_registry() -> list[NodeRegistryEntry]:
    registry: list[NodeRegistryEntry] = []

    for node_def in NODE_DEFINITIONS:
        ip = node_def["ip"]
        policy = classify_node_availability(node_def)
        is_required = node_def.get("offline_is_failure", False)

        lmstudio = _check_lmstudio_health(ip)
        gpu = _fetch_gpu_metrics(ip)

        models = collect_lmstudio_models(node_def) if lmstudio.get("online") else []
        model_ids = [m.id for m in models]
        inferred_caps = _infer_capabilities_from_models(model_ids)

        is_online = lmstudio.get("online", False)
        latency = lmstudio.get("latency_ms")

        ev: list[str] = []
        if lmstudio.get("online"):
            ev.append("lmstudio_responds")
        if not lmstudio.get("online"):
            ev.append(f"lmstudio_offline:{lmstudio.get('error','timeout')}")
        if gpu.get("up"):
            ev.append("gpu_exporter_responds")
        if not gpu.get("up"):
            ev.append(f"gpu_exporter_offline:{gpu.get('error','timeout')}")

        metrics = NodeMetrics(
            latency_ms=latency,
            health_score=1.0 if is_online else 0.0,
            gpu_utilization=gpu.get("gpu_utilization"),
            vram_total=gpu.get("vram_total_gib"),
            vram_used=gpu.get("vram_used_gib"),
            scrape_health="up" if gpu.get("up") else "down",
        )

        routing_eligible = is_online
        fallback_eligible = is_online

        entry = NodeRegistryEntry(
            node_id=node_def["node_id"],
            hostname=node_def["hostname"],
            ip=ip,
            role=node_def["role"],
            status="online" if is_online else "offline",
            availability_policy=policy,
            capabilities=inferred_caps,
            models=models,
            metrics=metrics,
            routing_eligible=routing_eligible,
            fallback_eligible=fallback_eligible,
            offline_is_failure=is_required,
            last_seen=time.time(),
            evidence=ev,
        )
        registry.append(entry)

    return registry


# ── Serialization ─────────────────────────────────────────────────────────

def entry_to_dict(entry: NodeRegistryEntry) -> dict[str, Any]:
    return {
        "node_id": entry.node_id,
        "hostname": entry.hostname,
        "ip": entry.ip,
        "role": entry.role,
        "status": entry.status,
        "availability_policy": entry.availability_policy,
        "capabilities": list(entry.capabilities),
        "models": [
            {
                "id": m.id,
                "backend_id": m.backend_id,
                "context": m.context,
                "loaded": m.loaded,
                "node": m.node,
                "suitability": list(m.suitability),
            }
            for m in entry.models
        ],
        "metrics": {
            "latency_ms": entry.metrics.latency_ms,
            "health_score": entry.metrics.health_score,
            "gpu_utilization": entry.metrics.gpu_utilization,
            "vram_total_gib": entry.metrics.vram_total,
            "vram_used_gib": entry.metrics.vram_used,
            "scrape_health": entry.metrics.scrape_health,
        },
        "routing_eligible": entry.routing_eligible,
        "fallback_eligible": entry.fallback_eligible,
        "offline_is_failure": entry.offline_is_failure,
        "last_seen": entry.last_seen,
        "evidence": list(entry.evidence),
        "contract_version": entry.contract_version,
    }


def registry_to_dict(registry: list[NodeRegistryEntry]) -> dict[str, Any]:
    nodes_by_role: dict[str, list[dict[str, Any]]] = {}
    for entry in registry:
        role = entry.role
        if role not in nodes_by_role:
            nodes_by_role[role] = []
        nodes_by_role[role].append(entry_to_dict(entry))

    online = sum(1 for e in registry if e.status == "online")
    offline = sum(1 for e in registry if e.status == "offline")
    required_offline = sum(1 for e in registry if e.offline_is_failure and e.status == "offline")

    return {
        "contract_version": "DYNAMIC-NODE-REGISTRY-01",
        "timestamp": time.time(),
        "nodes_total": len(registry),
        "nodes_online": online,
        "nodes_offline": offline,
        "required_offline": required_offline,
        "required_offline_is_critical": required_offline > 0,
        "nodes_by_role": nodes_by_role,
        "nodes": [entry_to_dict(e) for e in registry],
    }
