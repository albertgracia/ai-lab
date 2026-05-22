from __future__ import annotations

import time
from typing import Any

from runtime.topology.contracts import (
    TOPOLOGY_CONTRACT_VERSION,
    TopologyNodeContract,
    TopologyEdgeContract,
    TopologyGraphContract,
    DependencyContract,
    AuthorityChainContract,
    BlastRadiusContract,
    TopologyConfidenceContract,
)

_PRIMARY_RUNTIME_IP = "192.168.1.30"
_INFERENCE_BACKEND_IP = "192.168.1.50"
_INVENTORY_IP = "192.168.1.60"
_OBSERVABILITY_IP = "192.168.1.40"
_NAS_IP = "192.168.1.200"


def _confidence_value(conf: str) -> float:
    return {"high": 1.0, "medium": 0.6, "low": 0.2, "unknown": 0.0}.get(conf, 0.0)


def _ensure_list(val: Any) -> list:
    if isinstance(val, list):
        return val
    if isinstance(val, dict):
        return [val]
    return []


def _entity_registry_or_fallback(sensor_snapshot: dict | None, extra_ctx: dict | None) -> list[dict]:
    try:
        from runtime.entities import build_entity_registry
        return build_entity_registry(sensor_snapshot=sensor_snapshot, extra_ctx=extra_ctx)
    except ImportError:
        return []


# ── Node builders ──────────────────────────────────────────────

def _build_gpu_nodes(registry: list[dict]) -> list[dict]:
    nodes = []
    for e in registry:
        if e.get("entity_type") != "gpu":
            continue
        istate = e.get("inventory_state", "inventory")
        inv_only = istate in ("expected_offline", "inventory") and not e.get("routable", False)
        node = TopologyNodeContract(
            node_id=e["entity_id"],
            node_type="gpu",
            operational_state=e.get("operational_state", "inactive"),
            active=e.get("operational_state") == "active",
            discoverable=inv_only or e.get("operational_state") in ("active", "idle"),
            routable=e.get("routable", False),
            confidence=e.get("confidence", "unknown"),
            freshness=e.get("freshness", "unknown"),
            authority="source_of_truth" if not inv_only else "inventory",
            inventory_only=inv_only,
            entity_ref=e["entity_id"],
        ).to_dict()
        nodes.append(node)
    return nodes


def _build_model_nodes(registry: list[dict]) -> list[dict]:
    nodes = []
    for e in registry:
        if e.get("entity_type") != "model":
            continue
        active = e.get("operational_state") == "active"
        deprecated = e.get("deprecated", False)
        disabled = e.get("operational_state") == "inactive" and not deprecated
        node = TopologyNodeContract(
            node_id=e["entity_id"],
            node_type="model",
            operational_state=e.get("operational_state", "inactive"),
            active=active,
            discoverable=not deprecated,
            routable=e.get("routable", False),
            confidence=e.get("confidence", "unknown"),
            freshness=e.get("freshness", "unknown"),
            authority="routing_policy" if active else ("deprecated" if deprecated else "disabled"),
            inventory_only=deprecated or disabled,
            entity_ref=e["entity_id"],
        ).to_dict()
        nodes.append(node)
    return nodes


def _build_service_nodes() -> list[dict]:
    services = [
        ("ailab-gateway", "gateway", "192.168.1.30:8008", "active", True, "entrypoint"),
        ("ailab-router", "router", "192.168.1.30:8083", "active", True, "internal_api"),
        ("ailab-live-api", "service", "192.168.1.30:8084", "active", True, "internal_api"),
        ("ailab-docs", "service", "192.168.1.30:4322", "active", False, "support"),
        ("ailab-metrics", "service", "192.168.1.30:3010", "active", False, "support"),
        ("ailab-heartbeat", "service", "192.168.1.30", "active", False, "support"),
        ("ailab-runner", "service", "192.168.1.30", "active", False, "support"),
    ]
    nodes = []
    for sid, stype, host, state, active, authority in services:
        node = TopologyNodeContract(
            node_id=sid,
            node_type=stype,
            operational_state=state,
            active=active,
            discoverable=True,
            routable=active,
            confidence="high",
            freshness="fresh",
            authority=authority,
            inventory_only=False,
            entity_ref=sid,
        ).to_dict()
        nodes.append(node)
    return nodes


def _build_observability_nodes() -> list[dict]:
    targets = [
        ("prometheus", "datasource", _OBSERVABILITY_IP, "source_of_truth"),
        ("grafana", "datasource", _OBSERVABILITY_IP, "visualization"),
    ]
    nodes = []
    for tid, ttype, tip, authority in targets:
        node = TopologyNodeContract(
            node_id=tid,
            node_type=ttype,
            operational_state="active",
            active=True,
            discoverable=True,
            routable=False,
            confidence="high" if authority == "source_of_truth" else "medium",
            freshness="fresh",
            authority=authority,
            inventory_only=False,
            entity_ref=tid,
        ).to_dict()
        nodes.append(node)
    return nodes


def _build_host_nodes() -> list[dict]:
    hosts = [
        ("192.168.1.30", "ubuntu-ialab", "primary_control_plane", True),
        ("192.168.1.50", "lmstudio-backend", "inference_gpu", True),
        ("192.168.1.60", "rx7900xt-node", "inventory", False),
        ("192.168.1.40", "observability-node", "observability", True),
        ("192.168.1.200", "nas-storage", "storage", True),
    ]
    nodes = []
    for ip, hostname, role, active in hosts:
        node = TopologyNodeContract(
            node_id=ip,
            node_type="runtime" if role == "primary_control_plane" else "storage" if role == "storage" else "exporter",
            operational_state="active" if active else "inactive",
            active=active,
            discoverable=True,
            routable=active,
            confidence="high",
            freshness="fresh",
            authority=role,
            inventory_only=not active,
            entity_ref=ip,
        ).to_dict()
        nodes.append(node)
    return nodes


# ── Edge builders ──────────────────────────────────────────────

def _build_gpu_model_edges(registry: list[dict]) -> list[dict]:
    edges = []
    gpu_ids = {e["entity_id"] for e in registry if e.get("entity_type") == "gpu" and e.get("operational_state") == "active"}
    model_ids = {e["entity_id"] for e in registry if e.get("entity_type") == "model" and e.get("operational_state") == "active"}
    for gid in gpu_ids:
        for mid in model_ids:
            edges.append(TopologyEdgeContract(
                source_id=gid,
                target_id=mid,
                relationship="hosts_inference",
                direction="forward",
                observed=True,
                confidence="high",
                weight=1.0,
            ).to_dict())
    return edges


def _build_service_edges() -> list[dict]:
    return [
        TopologyEdgeContract(source_id="ailab-gateway", target_id="ailab-router", relationship="routes_to", direction="forward", observed=True, confidence="high", weight=1.0).to_dict(),
        TopologyEdgeContract(source_id="ailab-gateway", target_id="prometheus", relationship="emits_metrics_to", direction="forward", observed=True, confidence="high", weight=0.8).to_dict(),
        TopologyEdgeContract(source_id="ailab-router", target_id="prometheus", relationship="emits_metrics_to", direction="forward", observed=True, confidence="high", weight=0.8).to_dict(),
        TopologyEdgeContract(source_id="ailab-live-api", target_id="prometheus", relationship="emits_metrics_to", direction="forward", observed=True, confidence="high", weight=0.8).to_dict(),
        TopologyEdgeContract(source_id="prometheus", target_id="grafana", relationship="feeds_visualization", direction="forward", observed=True, confidence="high", weight=1.0).to_dict(),
    ]


def _build_host_edges() -> list[dict]:
    return [
        TopologyEdgeContract(source_id="ailab-gateway", target_id="192.168.1.30", relationship="runs_on", direction="forward", observed=True, confidence="high", weight=1.0).to_dict(),
        TopologyEdgeContract(source_id="ailab-router", target_id="192.168.1.30", relationship="runs_on", direction="forward", observed=True, confidence="high", weight=1.0).to_dict(),
        TopologyEdgeContract(source_id="192.168.1.30", target_id="192.168.1.50", relationship="forwards_inference_to", direction="forward", observed=True, confidence="high", weight=1.0).to_dict(),
        TopologyEdgeContract(source_id="192.168.1.30", target_id=_OBSERVABILITY_IP, relationship="sends_metrics_to", direction="forward", observed=True, confidence="high", weight=1.0).to_dict(),
        TopologyEdgeContract(source_id="prometheus", target_id=_OBSERVABILITY_IP, relationship="runs_on", direction="forward", observed=True, confidence="high", weight=1.0).to_dict(),
        TopologyEdgeContract(source_id="grafana", target_id=_OBSERVABILITY_IP, relationship="runs_on", direction="forward", observed=True, confidence="high", weight=1.0).to_dict(),
    ]


def _build_authority_edges() -> list[dict]:
    return [
        TopologyEdgeContract(source_id="prometheus", target_id="ailab-gateway", relationship="source_of_truth_for_metrics", direction="reverse", observed=True, confidence="high", weight=1.0).to_dict(),
        TopologyEdgeContract(source_id="prometheus", target_id="ailab-router", relationship="source_of_truth_for_metrics", direction="reverse", observed=True, confidence="high", weight=1.0).to_dict(),
        TopologyEdgeContract(source_id="prometheus", target_id="ailab-live-api", relationship="source_of_truth_for_metrics", direction="reverse", observed=True, confidence="high", weight=1.0).to_dict(),
        TopologyEdgeContract(source_id="grafana", target_id="prometheus", relationship="visualizes_from", direction="reverse", observed=True, confidence="high", weight=1.0).to_dict(),
    ]


# ── Degraded path detection ────────────────────────────────────

def _detect_degraded_paths(nodes: list[dict], edges: list[dict]) -> list[dict]:
    degraded = []
    node_map = {n["node_id"]: n for n in nodes}
    for edge in edges:
        src = node_map.get(edge["source_id"])
        tgt = node_map.get(edge["target_id"])
        if not src or not tgt:
            continue
        if src.get("operational_state") != "active" and edge.get("relationship") in ("routes_to", "forwards_inference_to", "feeds_visualization"):
            degraded.append({
                "source": edge["source_id"],
                "target": edge["target_id"],
                "relationship": edge["relationship"],
                "reason": f"{edge['source_id']} is {src.get('operational_state', 'inactive')}",
                "impact": "propagated_degradation",
            })
    return degraded


# ── Public API ─────────────────────────────────────────────────

def build_runtime_topology(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = _entity_registry_or_fallback(sensor_snapshot, extra_ctx)
    nodes = []
    nodes.extend(_build_gpu_nodes(registry))
    nodes.extend(_build_model_nodes(registry))
    nodes.extend(_build_service_nodes())
    nodes.extend(_build_observability_nodes())
    nodes.extend(_build_host_nodes())
    edges = []
    edges.extend(_build_gpu_model_edges(registry))
    edges.extend(_build_service_edges())
    edges.extend(_build_host_edges())
    edges.extend(_build_authority_edges())
    degraded_paths = _detect_degraded_paths(nodes, edges)
    graph = TopologyGraphContract(
        nodes=nodes,
        edges=edges,
        degraded_paths=degraded_paths,
    )
    return graph.to_dict()


def build_dependency_graph(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    topology = build_runtime_topology(sensor_snapshot, extra_ctx)
    edges = topology.get("edges", [])
    nodes = topology.get("nodes", [])
    node_map = {n["node_id"]: n for n in nodes}
    dependencies = []
    for edge in edges:
        if edge.get("relationship") in ("routes_to", "forwards_inference_to", "feeds_visualization", "hosts_inference", "emits_metrics_to"):
            dep = DependencyContract(
                dependency_id=f"{edge['source_id']}->{edge['target_id']}",
                dependent=edge["source_id"],
                dependency=edge["target_id"],
                relationship_type=edge["relationship"],
                critical=edge["relationship"] in ("routes_to", "forwards_inference_to"),
                observed=edge.get("observed", False),
                confidence=edge.get("confidence", "unknown"),
            ).to_dict()
            dependencies.append(dep)
    return {
        "total_dependencies": len(dependencies),
        "dependencies": dependencies,
        "contract_version": TOPOLOGY_CONTRACT_VERSION,
    }


def build_authority_graph(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    topology = build_runtime_topology(sensor_snapshot, extra_ctx)
    nodes = topology.get("nodes", [])
    authority_nodes = [n for n in nodes if n.get("authority") in ("source_of_truth", "routing_policy", "entrypoint", "internal_api")]
    chains = []
    for node in authority_nodes:
        chain = AuthorityChainContract(
            chain_id=f"authority_{node['node_id']}",
            source=node["node_id"],
            target="runtime",
            authority_type=node["authority"],
            observed=True,
            confidence=node.get("confidence", "unknown"),
            hops=[{"node": node["node_id"], "type": node["node_type"], "authority": node["authority"]}],
        ).to_dict()
        chains.append(chain)
    return {
        "total_chains": len(chains),
        "authority_chains": chains,
        "contract_version": TOPOLOGY_CONTRACT_VERSION,
    }


def build_observability_graph(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    topology = build_runtime_topology(sensor_snapshot, extra_ctx)
    edges = topology.get("edges", [])
    nodes = topology.get("nodes", [])
    obs_edges = [e for e in edges if e.get("relationship") in ("emits_metrics_to", "feeds_visualization", "sends_metrics_to")]
    obs_nodes = [n for n in nodes if n.get("node_type") in ("datasource", "exporter", "gateway", "router", "service")]
    return {
        "total_observability_nodes": len(obs_nodes),
        "total_observability_edges": len(obs_edges),
        "nodes": obs_nodes,
        "edges": obs_edges,
        "contract_version": TOPOLOGY_CONTRACT_VERSION,
    }


def build_routing_graph(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    topology = build_runtime_topology(sensor_snapshot, extra_ctx)
    edges = topology.get("edges", [])
    nodes = topology.get("nodes", [])
    routing_edges = [e for e in edges if e.get("relationship") in ("routes_to", "forwards_inference_to", "hosts_inference")]
    routing_nodes = [n for n in nodes if n.get("routable") or n.get("node_type") in ("gateway", "router", "model")]
    return {
        "total_routing_nodes": len(routing_nodes),
        "total_routing_edges": len(routing_edges),
        "nodes": routing_nodes,
        "edges": routing_edges,
        "contract_version": TOPOLOGY_CONTRACT_VERSION,
    }


def build_operational_graph(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    topology = build_runtime_topology(sensor_snapshot, extra_ctx)
    nodes = topology.get("nodes", [])
    edges = topology.get("edges", [])
    active_nodes = [n for n in nodes if n.get("active")]
    dep_edges = [e for e in edges if e.get("relationship") in ("routes_to", "forwards_inference_to", "hosts_inference", "runs_on")]
    return {
        "total_active_nodes": len(active_nodes),
        "total_operational_edges": len(dep_edges),
        "active_nodes": active_nodes,
        "operational_edges": dep_edges,
        "contract_version": TOPOLOGY_CONTRACT_VERSION,
    }


def calculate_blast_radius(
    event_type: str = "prometheus_stale",
    source_node: str = "prometheus",
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    topology = build_runtime_topology(sensor_snapshot, extra_ctx)
    nodes = topology.get("nodes", [])
    edges = topology.get("edges", [])

    affected: set[str] = set()
    affected_domains: set[str] = set()
    propagation: list[dict] = []
    visited: set[str] = set()

    def follow_impact(node_id: str, depth: int = 0) -> None:
        if node_id in visited or depth > 4:
            return
        visited.add(node_id)
        for edge in edges:
            if edge.get("source_id") == node_id and edge.get("relationship") in ("routes_to", "feeds_visualization", "hosts_inference", "emits_metrics_to", "forwards_inference_to"):
                target = edge["target_id"]
                if target not in visited:
                    propagation.append({"from": node_id, "to": target, "relationship": edge["relationship"], "depth": depth + 1})
                    affected.add(target)
                    # map targets to domains
                    for n in nodes:
                        if n["node_id"] == target:
                            affected_domains.add(n.get("node_type", "unknown"))
                    follow_impact(target, depth + 1)

    follow_impact(source_node)

    severity_map = {"prometheus_stale": "medium", "gpu_failure": "high", "gateway_down": "critical", "network_partition": "high", "storage_full": "medium", "degradation": "low"}
    severity = severity_map.get(event_type, "low")

    report = BlastRadiusContract(
        event_id=f"blast_{event_type}_{int(time.time())}",
        event_type=event_type,
        source_node=source_node,
        source_type=next((n.get("node_type", "unknown") for n in nodes if n["node_id"] == source_node), "unknown"),
        severity=severity,
        affected_nodes=list(affected),
        affected_domains=list(affected_domains),
        impact_score=min(1.0, len(affected) / max(len(nodes), 1)),
        confidence="high" if affected else "low",
        propagation_path=propagation,
    )
    return report.to_dict()


def detect_topology_drift(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    topology = build_runtime_topology(sensor_snapshot, extra_ctx)
    nodes = topology.get("nodes", [])
    drifts = []
    for node in nodes:
        active = node.get("active", False)
        discoverable = node.get("discoverable", False)
        operational = node.get("operational_state", "inactive")
        confidence = node.get("confidence", "unknown")
        if active and not discoverable:
            drifts.append({"node_id": node["node_id"], "drift": "active_but_not_discoverable", "severity": "medium"})
        if discoverable and operational == "inactive" and not node.get("inventory_only"):
            drifts.append({"node_id": node["node_id"], "drift": "discoverable_but_inactive", "severity": "low"})
        if active and confidence == "low":
            drifts.append({"node_id": node["node_id"], "drift": "active_with_low_confidence", "severity": "medium"})
    return drifts


def calculate_topology_confidence(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    topology = build_runtime_topology(sensor_snapshot, extra_ctx)
    nodes = topology.get("nodes", [])
    edges = topology.get("edges", [])
    degraded_paths = topology.get("degraded_paths", [])

    total_entities = len(nodes)
    total_edges = len(edges)
    observed_edges = sum(1 for e in edges if e.get("observed"))
    stale_entities = sum(1 for n in nodes if n.get("freshness") in ("stale", "expired", "unavailable"))
    inventory_only = sum(1 for n in nodes if n.get("inventory_only"))
    degraded_obs = len(degraded_paths)
    has_authority = any(n.get("authority") == "source_of_truth" and n.get("operational_state") == "active" for n in nodes)

    factors: dict[str, float] = {}

    obs_ratio = observed_edges / max(total_edges, 1)
    factors["observed_edge_ratio"] = round(obs_ratio, 2)

    stale_penalty = max(0.0, 1.0 - (stale_entities / max(total_entities, 1)))
    factors["stale_penalty"] = round(stale_penalty, 2)

    inventory_penalty = max(0.0, 1.0 - (inventory_only / max(total_entities, 1)))
    factors["inventory_penalty"] = round(inventory_penalty, 2)

    degraded_penalty = max(0.0, 1.0 - (degraded_obs / max(total_edges, 1)))
    factors["degraded_penalty"] = round(degraded_penalty, 2)

    authority_bonus = 1.0 if has_authority else 0.5
    factors["authority_bonus"] = authority_bonus

    overall = round((obs_ratio * 0.3 + stale_penalty * 0.2 + inventory_penalty * 0.15 + degraded_penalty * 0.2 + authority_bonus * 0.15) * 100, 1)

    report = TopologyConfidenceContract(
        overall_score=overall,
        observed_edges=observed_edges,
        total_edges=total_edges,
        stale_entities=stale_entities,
        total_entities=total_entities,
        inventory_only=inventory_only,
        degraded_observability=degraded_obs,
        authority_valid=has_authority,
        factors=factors,
    )
    return report.to_dict()
