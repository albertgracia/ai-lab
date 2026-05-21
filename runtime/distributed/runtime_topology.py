from __future__ import annotations

import json
import os
import time
from pathlib import Path

from runtime.maturity.descriptor import TopologyRole, FailureDomain, NodeTopology

STATE_DIR = Path("/opt/ai-lab/runtime/state")

_CONTROL_PLANE_HOST = "192.168.1.30"
_INFERENCE_BACKEND_HOST = "192.168.1.50"
_INVENTORY_HOSTS: frozenset[str] = frozenset({"192.168.1.60"})
_OBSERVABILITY_HOST = "192.168.1.40"


def _role_for_host(host: str) -> TopologyRole:
    if host == _CONTROL_PLANE_HOST:
        return TopologyRole.PRIMARY_CONTROL_PLANE
    if host == _INFERENCE_BACKEND_HOST:
        return TopologyRole.INFERENCE_BACKEND
    if host in _INVENTORY_HOSTS:
        return TopologyRole.INVENTORY_OFFLINE
    if host == _OBSERVABILITY_HOST:
        return TopologyRole.OBSERVABILITY_NODE
    return TopologyRole.INVENTORY_OFFLINE


def _failure_domain_for_host(host: str) -> FailureDomain:
    if host == _CONTROL_PLANE_HOST:
        return FailureDomain.CONTROL_PLANE
    if host == _INFERENCE_BACKEND_HOST:
        return FailureDomain.INFERENCE_GPU
    if host in _INVENTORY_HOSTS:
        return FailureDomain.INFERENCE_GPU
    if host == _OBSERVABILITY_HOST:
        return FailureDomain.OBSERVABILITY
    return FailureDomain.NETWORK


def _load_discovered_nodes() -> list[dict]:
    f = STATE_DIR / "discovered_nodes.json"
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text())
        return data.get("nodes", [])
    except Exception:
        return []


def build_topology_nodes() -> list[NodeTopology]:
    discovered = _load_discovered_nodes()
    seen_hosts: set[str] = set()

    nodes: list[NodeTopology] = []

    for entry in discovered:
        host = entry.get("host", "")
        seen_hosts.add(host)
        role = _role_for_host(host)
        nodes.append(NodeTopology(
            node_id=entry.get("host", host),
            host=host,
            port=entry.get("port"),
            role=role,
            failure_domain=_failure_domain_for_host(host),
            status=entry.get("status", "unknown"),
            online=entry.get("online", False),
            latency_ms=entry.get("latency_ms"),
            last_seen=entry.get("discovered_at", 0.0),
            models=entry.get("models", []),
            capabilities=entry.get("capabilities", []),
            error=entry.get("error", ""),
        ))

    static_hosts = {
        _CONTROL_PLANE_HOST: TopologyRole.PRIMARY_CONTROL_PLANE,
        _OBSERVABILITY_HOST: TopologyRole.OBSERVABILITY_NODE,
    }
    for host, role in static_hosts.items():
        if host not in seen_hosts:
            nodes.append(NodeTopology(
                node_id=host,
                host=host,
                role=role,
                failure_domain=_failure_domain_for_host(host),
                status="online" if host == _CONTROL_PLANE_HOST else "unknown",
                online=host == _CONTROL_PLANE_HOST,
                last_seen=time.time(),
            ))

    return nodes


TOPOLOGY_CACHE: list[dict] | None = None
TOPOLOGY_CACHE_TS: float = 0
TOPOLOGY_CACHE_TTL: float = 5.0


def get_topology() -> dict:
    global TOPOLOGY_CACHE, TOPOLOGY_CACHE_TS
    now = time.time()
    if TOPOLOGY_CACHE is not None and (now - TOPOLOGY_CACHE_TS) < TOPOLOGY_CACHE_TTL:
        return TOPOLOGY_CACHE

    nodes = build_topology_nodes()

    control_plane = next((n for n in nodes if n.role == TopologyRole.PRIMARY_CONTROL_PLANE), None)
    inference_nodes = [n for n in nodes if n.failure_domain == FailureDomain.INFERENCE_GPU]
    observability_nodes = [n for n in nodes if n.failure_domain == FailureDomain.OBSERVABILITY]

    online_inference = sum(1 for n in inference_nodes if n.online)
    total_inference = len(inference_nodes)

    result = {
        "role": control_plane.role.value if control_plane else "unknown",
        "failure_domain": control_plane.failure_domain.value if control_plane else "unknown",
        "generated_at": now,
        "control_plane": {
            "host": _CONTROL_PLANE_HOST,
            "online": control_plane.online if control_plane else True,
            "latency_ms": control_plane.latency_ms if control_plane else None,
        },
        "inference_backends": {
            "online": online_inference,
            "total": total_inference,
            "nodes": [n.to_dict() for n in inference_nodes],
        },
        "observability": {
            "host": _OBSERVABILITY_HOST,
            "nodes": [n.to_dict() for n in observability_nodes],
        },
        "nodes": [n.to_dict() for n in nodes],
    }

    TOPOLOGY_CACHE = result
    TOPOLOGY_CACHE_TS = now
    return result
