from __future__ import annotations

import sys
import time
from typing import Any

sys.path.insert(0, "/opt/ai-lab")

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
from runtime.topology.runtime_topology import (
    build_runtime_topology,
    build_dependency_graph,
    build_authority_graph,
    build_observability_graph,
    build_routing_graph,
    build_operational_graph,
    calculate_blast_radius,
    detect_topology_drift,
    calculate_topology_confidence,
)
from runtime.topology import (
    build_runtime_topology as build_topology,
    build_dependency_graph as build_dep,
    build_authority_graph as build_auth,
    calculate_blast_radius as calc_blast,
    detect_topology_drift as detect_drift,
    calculate_topology_confidence as calc_conf,
)


def _make_gpu_summary(gpu_id: str, *, active: bool = False, expected_offline: bool = False, confidence: str = "high") -> dict:
    return {
        "gpu_id": gpu_id,
        "name": gpu_id,
        "observed_state": "online" if active else ("expected_offline" if expected_offline else "unavailable"),
        "operational_state": "active" if active else ("inactive" if expected_offline else "down"),
        "inventory_expected_offline": expected_offline,
        "confidence": confidence,
        "freshness": {"status": "fresh" if active else "unknown"},
        "source_of_truth": ["sensor_fusion"],
    }


def _make_model_entry(model_id: str, group: str = "active") -> dict:
    return {"id": model_id, "name": model_id}


# ── Contract tests ──────────────────────────────────────────────

def test_topology_contract_version():
    assert TOPOLOGY_CONTRACT_VERSION == "31D"


def test_topology_node_contract_to_dict():
    node = TopologyNodeContract(
        node_id="ailab-gateway",
        node_type="gateway",
        operational_state="active",
        active=True,
        discoverable=True,
        routable=True,
        confidence="high",
        freshness="fresh",
        authority="entrypoint",
        inventory_only=False,
        entity_ref="ailab-gateway",
    )
    d = node.to_dict()
    assert d["node_id"] == "ailab-gateway"
    assert d["node_type"] == "gateway"
    assert d["operational_state"] == "active"
    assert d["active"] is True
    assert d["authority"] == "entrypoint"


def test_topology_edge_contract_to_dict():
    edge = TopologyEdgeContract(
        source_id="ailab-gateway",
        target_id="prometheus",
        relationship="emits_metrics_to",
        direction="forward",
        observed=True,
        confidence="high",
        weight=0.8,
    )
    d = edge.to_dict()
    assert d["source_id"] == "ailab-gateway"
    assert d["target_id"] == "prometheus"
    assert d["relationship"] == "emits_metrics_to"
    assert d["observed"] is True


def test_topology_graph_contract_to_dict():
    node = TopologyNodeContract(node_id="n1", node_type="gateway", operational_state="active", active=True, entity_ref="n1")
    edge = TopologyEdgeContract(source_id="n1", target_id="n2", relationship="routes_to", direction="forward", observed=True, confidence="high", weight=1.0)
    graph = TopologyGraphContract(nodes=[node.to_dict()], edges=[edge.to_dict()], degraded_paths=[])
    d = graph.to_dict()
    assert d["contract_version"] == TOPOLOGY_CONTRACT_VERSION
    assert len(d["nodes"]) == 1
    assert len(d["edges"]) == 1


def test_dependency_contract_to_dict():
    dep = DependencyContract(
        dependency_id="g1->m1",
        dependent="g1",
        dependency="m1",
        relationship_type="hosts_inference",
        critical=True,
        observed=True,
        confidence="high",
    )
    d = dep.to_dict()
    assert d["dependency_id"] == "g1->m1"
    assert d["critical"] is True


def test_authority_chain_contract_to_dict():
    chain = AuthorityChainContract(
        chain_id="auth_prometheus",
        source="prometheus",
        target="runtime",
        authority_type="source_of_truth",
        observed=True,
        confidence="high",
        hops=[{"node": "prometheus", "type": "datasource", "authority": "source_of_truth"}],
    )
    d = chain.to_dict()
    assert d["chain_id"] == "auth_prometheus"
    assert d["authority_type"] == "source_of_truth"


def test_blast_radius_contract_to_dict():
    blast = BlastRadiusContract(
        event_id="blast_test_123",
        event_type="prometheus_stale",
        source_node="prometheus",
        source_type="datasource",
        severity="medium",
        affected_nodes=["ailab-gateway", "ailab-router"],
        affected_domains=["gateway", "router"],
        impact_score=0.5,
        confidence="high",
        propagation_path=[],
    )
    d = blast.to_dict()
    assert d["severity"] == "medium"
    assert len(d["affected_nodes"]) == 2


def test_topology_confidence_contract_to_dict():
    conf = TopologyConfidenceContract(
        overall_score=85.0,
        observed_edges=10,
        total_edges=12,
        stale_entities=1,
        total_entities=15,
        inventory_only=2,
        degraded_observability=0,
        authority_valid=True,
        factors={"observed_edge_ratio": 0.83, "authority_bonus": 1.0},
    )
    d = conf.to_dict()
    assert d["overall_score"] == 85.0
    assert d["authority_valid"] is True


# ── Runtime topology builder tests ──────────────────────────────

def test_build_runtime_topology_returns_structure():
    topo = build_runtime_topology()
    assert isinstance(topo, dict)
    assert "nodes" in topo
    assert "edges" in topo
    assert "degraded_paths" in topo
    assert topo["contract_version"] == TOPOLOGY_CONTRACT_VERSION


def test_build_runtime_topology_has_expected_node_types():
    topo = build_runtime_topology()
    nodes = topo.get("nodes", [])
    node_types = {n.get("node_type") for n in nodes}
    assert "gateway" in node_types
    assert "router" in node_types
    assert "datasource" in node_types
    assert "runtime" in node_types or "exporter" in node_types


def test_build_runtime_topology_with_sensor_snapshot():
    snapshot = {
        "gpu_operational_summaries": [
            _make_gpu_summary("rx9070", active=True),
            _make_gpu_summary("rx7900xt", expected_offline=True),
        ],
        "models": {
            "active": [_make_model_entry("qwen2.5-coder-14b-instruct")],
            "loaded": [_make_model_entry("llama-3.1-8b-instruct")],
            "disabled": [_make_model_entry("qwen3.6-27b")],
        },
    }
    topo = build_runtime_topology(sensor_snapshot=snapshot)
    nodes = topo.get("nodes", [])
    node_ids = {n.get("node_id") for n in nodes}
    assert "rx9070" in node_ids
    assert "ailab-gateway" in node_ids
    assert "prometheus" in node_ids


def test_build_runtime_topology_degraded_paths():
    topo = build_runtime_topology()
    assert isinstance(topo.get("degraded_paths"), list)


def test_build_dependency_graph_returns_expected():
    dep = build_dependency_graph()
    assert dep["contract_version"] == TOPOLOGY_CONTRACT_VERSION
    assert "total_dependencies" in dep
    assert "dependencies" in dep
    assert dep["total_dependencies"] >= 3


def test_build_authority_graph_returns_chains():
    auth = build_authority_graph()
    assert "total_chains" in auth
    assert "authority_chains" in auth
    assert auth["total_chains"] >= 2
    types = {c.get("authority_type") for c in auth["authority_chains"]}
    assert "source_of_truth" in types or "entrypoint" in types


def test_build_observability_graph_returns_nodes():
    obs = build_observability_graph()
    assert "total_observability_nodes" in obs
    assert "total_observability_edges" in obs
    assert obs["total_observability_nodes"] >= 2


def test_build_routing_graph_returns_routable():
    routing = build_routing_graph()
    assert "total_routing_nodes" in routing
    assert "total_routing_edges" in routing
    assert routing["total_routing_nodes"] >= 2


def test_build_operational_graph_active_nodes():
    op = build_operational_graph()
    assert "total_active_nodes" in op
    assert "total_operational_edges" in op
    assert op["total_active_nodes"] >= 3


# ── Blast radius tests ──────────────────────────────────────────

def test_calculate_blast_radius_prometheus_stale():
    blast = calculate_blast_radius(event_type="prometheus_stale", source_node="prometheus")
    assert blast["event_type"] == "prometheus_stale"
    assert blast["source_node"] == "prometheus"
    assert isinstance(blast["affected_nodes"], list)
    assert isinstance(blast["propagation_path"], list)
    assert blast["severity"] in ("low", "medium", "high", "critical")


def test_calculate_blast_radius_gateway_down():
    blast = calculate_blast_radius(event_type="gateway_down", source_node="ailab-gateway")
    assert blast["event_type"] == "gateway_down"
    assert blast["severity"] == "critical"


def test_calculate_blast_radius_gpu_failure():
    blast = calculate_blast_radius(event_type="gpu_failure", source_node="rx9070")
    assert blast["event_type"] == "gpu_failure"
    assert isinstance(blast["impact_score"], float)
    assert 0.0 <= blast["impact_score"] <= 1.0


# ── Topology drift tests ────────────────────────────────────────

def test_detect_topology_drift_no_drift_expected():
    drifts = detect_topology_drift()
    assert isinstance(drifts, list)


def test_detect_topology_drift_with_inactive_discoverable():
    snapshot = {
        "gpu_operational_summaries": [
            _make_gpu_summary("rx9070", active=True),
        ],
        "models": {
            "active": [],
            "discovered": [{"id": "qwen3.6-27b", "name": "qwen3.6-27b", "deprecated": True}],
        },
    }
    drifts = detect_topology_drift(sensor_snapshot=snapshot)
    assert isinstance(drifts, list)


# ── Topology confidence tests ───────────────────────────────────

def test_calculate_topology_confidence_returns_score():
    conf = calculate_topology_confidence()
    assert "overall_score" in conf
    assert isinstance(conf["overall_score"], (int, float))
    assert 0 <= conf["overall_score"] <= 100


def test_calculate_topology_confidence_has_factors():
    conf = calculate_topology_confidence()
    assert "factors" in conf
    assert "observed_edge_ratio" in conf["factors"]
    assert "authority_bonus" in conf["factors"]


def test_calculate_topology_confidence_authority_valid():
    conf = calculate_topology_confidence()
    assert "authority_valid" in conf
    assert isinstance(conf["authority_valid"], bool)


# ── Module import tests ─────────────────────────────────────────

def test_topology_module_exports():
    from runtime.topology import (
        TOPOLOGY_CONTRACT_VERSION,
        build_runtime_topology,
        build_dependency_graph,
        build_authority_graph,
        build_observability_graph,
        build_routing_graph,
        build_operational_graph,
        calculate_blast_radius,
        detect_topology_drift,
        calculate_topology_confidence,
    )
    assert TOPOLOGY_CONTRACT_VERSION == "31D"
    assert callable(build_runtime_topology)
    assert callable(calculate_blast_radius)


def test_entity_registry_topology_integration():
    from runtime.entities import build_topology_graph, build_topology_summary
    graph = build_topology_graph()
    assert "nodes" in graph
    assert "edges" in graph
    summary = build_topology_summary()
    assert "total_nodes" in summary
    assert "total_edges" in summary
    assert summary["contract_version"] == "31D"
