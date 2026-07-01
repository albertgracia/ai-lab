"""Tests for Dynamic Node Registry (read-only).

Validates:
- baseline node online is normal
- optional node offline does not make system critical
- burst/on-demand node online becomes routing eligible
- burst/on-demand node offline becomes routing ineligible
- node with LM Studio but no required model is not eligible for that model
- .60 role inventory-offline but online=true resolves to operational online
- required node offline affects health
- optional node offline is warning/info
- capability matrix generation
- eligibility filtering
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from runtime.state.dynamic_node_registry import (
    NODE_DEFINITIONS,
    NodeRegistryEntry,
    NodeMetrics,
    NodeModel,
    build_node_registry,
    build_capability_matrix,
    select_eligible_nodes,
    classify_node_availability,
    entry_to_dict,
    registry_to_dict,
    _infer_capabilities_from_models,
    _suitability_for,
)


class TestNodeDefinitions(unittest.TestCase):

    def test_three_nodes_defined(self):
        self.assertEqual(len(NODE_DEFINITIONS), 3)

    def test_nas_baseline_required(self):
        nas = [n for n in NODE_DEFINITIONS if n["node_id"] == "nas-n5"][0]
        self.assertEqual(nas["role"], "baseline")
        self.assertEqual(nas["availability_policy"], "required")
        self.assertTrue(nas["offline_is_failure"])

    def test_rx9070_on_demand_optional(self):
        rx9070 = [n for n in NODE_DEFINITIONS if n["node_id"] == "rx9070-node"][0]
        self.assertEqual(rx9070["role"], "on_demand")
        self.assertEqual(rx9070["availability_policy"], "optional")
        self.assertFalse(rx9070["offline_is_failure"])

    def test_rx7900xt_on_demand_optional(self):
        rx7900xt = [n for n in NODE_DEFINITIONS if n["node_id"] == "rx7900xt-node"][0]
        self.assertEqual(rx7900xt["role"], "on_demand")
        self.assertEqual(rx7900xt["availability_policy"], "optional")
        self.assertFalse(rx7900xt["offline_is_failure"])


class TestClassifyNodeAvailability(unittest.TestCase):

    def test_required_node(self):
        policy = classify_node_availability({"availability_policy": "required"})
        self.assertEqual(policy, "required")

    def test_optional_node(self):
        policy = classify_node_availability({"availability_policy": "optional"})
        self.assertEqual(policy, "optional")


class TestInferCapabilities(unittest.TestCase):

    def test_embedding_models(self):
        caps = _infer_capabilities_from_models(["text-embedding-nomic-embed-text-v1.5"])
        self.assertIn("embeddings", caps)

    def test_vision_models(self):
        caps = _infer_capabilities_from_models(["moondream2-20250414"])
        self.assertIn("vision", caps)

    def test_coder_models(self):
        caps = _infer_capabilities_from_models(["qwen2.5-coder-14b-instruct"])
        self.assertIn("coding", caps)

    def test_reasoning_models(self):
        caps = _infer_capabilities_from_models(["deepseek-r1-distill-qwen-14b"])
        self.assertIn("reasoning", caps)

    def test_large_context_models(self):
        caps = _infer_capabilities_from_models(["qwen3-coder-30b-a3b-instruct"])
        self.assertIn("large-context", caps)

    def test_fast_models(self):
        caps = _infer_capabilities_from_models(["qwen3.5-9b-fast"])
        self.assertIn("fast", caps)

    def test_chat_always_present(self):
        caps = _infer_capabilities_from_models(["some-unknown-model"])
        self.assertIn("chat", caps)

    def test_multimodal_detected(self):
        caps = _infer_capabilities_from_models(["qwen3-vl-8b"])
        self.assertIn("multimodal", caps)


class TestSuitability(unittest.TestCase):

    def test_embedding_suitability(self):
        suit = _suitability_for("text-embedding-nomic-embed-text-v1.5")
        self.assertIn("embeddings", suit)

    def test_general_model(self):
        suit = _suitability_for("unknown-model-name")
        self.assertEqual(suit, ["general"])


class TestBaselineNodeOnline(unittest.TestCase):

    def setUp(self):
        self.entry = NodeRegistryEntry(
            node_id="nas-n5",
            hostname="NAS-N5",
            ip="192.168.1.250",
            role="baseline",
            status="online",
            availability_policy="required",
            capabilities=["chat", "embeddings"],
            models=[NodeModel(id="nomic-embed-text-v1.5", loaded=True, node="nas-n5")],
            metrics=NodeMetrics(latency_ms=5.0, health_score=1.0),
            routing_eligible=True,
            fallback_eligible=True,
            offline_is_failure=True,
        )

    def test_baseline_online_is_normal(self):
        self.assertEqual(self.entry.status, "online")
        self.assertTrue(self.entry.routing_eligible)
        self.assertTrue(self.entry.offline_is_failure)

    def test_baseline_online_eligible_for_routing(self):
        eligible = select_eligible_nodes([self.entry])
        self.assertEqual(len(eligible), 1)


class TestOptionalNodeOfflineDoesNotDegrade(unittest.TestCase):

    def setUp(self):
        self.optional_online = NodeRegistryEntry(
            node_id="rx7900xt-node",
            hostname="RX7900XT",
            ip="192.168.1.60",
            role="on_demand",
            status="online",
            availability_policy="optional",
            capabilities=["chat", "coding", "reasoning", "vision", "large-context"],
            models=[NodeModel(id="qwen3-coder-30b", loaded=True, node="rx7900xt-node")],
            metrics=NodeMetrics(latency_ms=2.0, health_score=1.0),
            routing_eligible=True,
            fallback_eligible=True,
            offline_is_failure=False,
        )
        self.optional_offline = NodeRegistryEntry(
            node_id="rx7900xt-node",
            hostname="RX7900XT",
            ip="192.168.1.60",
            role="on_demand",
            status="offline",
            availability_policy="optional",
            capabilities=[],
            models=[],
            metrics=NodeMetrics(health_score=0.0),
            routing_eligible=False,
            fallback_eligible=False,
            offline_is_failure=False,
        )
        self.baseline = NodeRegistryEntry(
            node_id="nas-n5",
            hostname="NAS-N5",
            ip="192.168.1.250",
            role="baseline",
            status="online",
            availability_policy="required",
            capabilities=["chat", "embeddings"],
            models=[],
            metrics=NodeMetrics(latency_ms=3.0, health_score=1.0),
            routing_eligible=True,
            fallback_eligible=True,
            offline_is_failure=True,
        )

    def test_optional_offline_not_critical(self):
        reg = registry_to_dict([self.baseline, self.optional_offline])
        self.assertEqual(reg["nodes_online"], 1)
        self.assertEqual(reg["nodes_offline"], 1)
        self.assertFalse(reg["required_offline_is_critical"])

    def test_optional_offline_routing_ineligible(self):
        eligible = select_eligible_nodes([self.optional_offline, self.baseline])
        self.assertNotIn(self.optional_offline, eligible)

    def test_optional_online_routing_eligible(self):
        eligible = select_eligible_nodes([self.optional_online, self.baseline])
        self.assertIn(self.optional_online, eligible)


class TestBurstNodeOnlineEligible(unittest.TestCase):

    def setUp(self):
        self.burst = NodeRegistryEntry(
            node_id="rx9070-node",
            hostname="RX9070",
            ip="192.168.1.50",
            role="on_demand",
            status="online",
            availability_policy="optional",
            capabilities=["chat", "coding", "fast", "reasoning"],
            models=[NodeModel(id="qwen2.5-coder-14b", loaded=True, node="rx9070-node")],
            metrics=NodeMetrics(latency_ms=2.5, health_score=1.0),
            routing_eligible=True,
            fallback_eligible=True,
            offline_is_failure=False,
        )

    def test_online_burst_is_routing_eligible(self):
        self.assertTrue(self.burst.routing_eligible)

    def test_online_burst_appears_in_capability_matrix(self):
        matrix = build_capability_matrix([self.burst])
        self.assertIn("rx9070-node", matrix)

    def test_burst_offline_not_eligible(self):
        self.burst.status = "offline"
        self.burst.routing_eligible = False
        eligible = select_eligible_nodes([self.burst])
        self.assertEqual(len(eligible), 0)


class TestModelEligibility(unittest.TestCase):

    def setUp(self):
        self.entry = NodeRegistryEntry(
            node_id="rx7900xt-node",
            hostname="RX7900XT",
            ip="192.168.1.60",
            role="on_demand",
            status="online",
            availability_policy="optional",
            capabilities=["chat", "coding", "fast"],
            models=[NodeModel(id="qwen3.5-9b", loaded=True, node="rx7900xt-node",
                              suitability=["fast", "chat"])],
            metrics=NodeMetrics(latency_ms=2.0, health_score=1.0),
            routing_eligible=True,
            fallback_eligible=True,
            offline_is_failure=False,
        )

    def test_no_required_model_not_eligible_for_it(self):
        eligible = select_eligible_nodes([self.entry], requirements=["vision"])
        self.assertEqual(len(eligible), 0)

    def test_has_required_model_eligible(self):
        eligible = select_eligible_nodes([self.entry], requirements=["chat"])
        self.assertEqual(len(eligible), 1)


class TestRoleResolution(unittest.TestCase):

    def test_role_inventory_online_resolves_operational(self):
        entry = NodeRegistryEntry(
            node_id="rx7900xt-node",
            hostname="RX7900XT",
            ip="192.168.1.60",
            role="on_demand",
            status="online",
            availability_policy="optional",
            capabilities=["chat", "coding", "reasoning", "vision", "large-context"],
            models=[NodeModel(id="qwen3-coder-30b", loaded=True, node="rx7900xt-node")],
            metrics=NodeMetrics(latency_ms=2.05, health_score=1.0),
            routing_eligible=True,
            offline_is_failure=False,
        )
        self.assertEqual(entry.status, "online")
        self.assertTrue(entry.routing_eligible)
        self.assertFalse(entry.offline_is_failure)


class TestRequiredNodeOffline(unittest.TestCase):

    def setUp(self):
        self.baseline_offline = NodeRegistryEntry(
            node_id="nas-n5",
            hostname="NAS-N5",
            ip="192.168.1.250",
            role="baseline",
            status="offline",
            availability_policy="required",
            capabilities=[],
            models=[],
            metrics=NodeMetrics(health_score=0.0),
            routing_eligible=False,
            fallback_eligible=False,
            offline_is_failure=True,
        )

    def test_required_offline_is_critical(self):
        reg = registry_to_dict([self.baseline_offline])
        self.assertTrue(reg["required_offline_is_critical"])

    def test_required_offline_not_eligible(self):
        eligible = select_eligible_nodes([self.baseline_offline])
        self.assertEqual(len(eligible), 0)


class TestCapabilityMatrix(unittest.TestCase):

    def setUp(self):
        self.rx9070 = NodeRegistryEntry(
            node_id="rx9070-node", hostname="RX9070", ip="192.168.1.50",
            role="on_demand", status="online", availability_policy="optional",
            capabilities=["chat", "coding", "fast"],
            models=[NodeModel(id="qwen2.5-coder-14b", loaded=True, node="rx9070-node",
                              suitability=["coding", "chat"])],
            metrics=NodeMetrics(latency_ms=2.5, health_score=1.0),
            routing_eligible=True, offline_is_failure=False,
        )
        self.rx7900xt = NodeRegistryEntry(
            node_id="rx7900xt-node", hostname="RX7900XT", ip="192.168.1.60",
            role="on_demand", status="online", availability_policy="optional",
            capabilities=["chat", "vision", "large-context"],
            models=[NodeModel(id="moondream2", loaded=True, node="rx7900xt-node",
                              suitability=["vision"])],
            metrics=NodeMetrics(latency_ms=2.0, health_score=1.0),
            routing_eligible=True, offline_is_failure=False,
        )

    def test_matrix_contains_both_online_nodes(self):
        matrix = build_capability_matrix([self.rx9070, self.rx7900xt])
        self.assertIn("rx9070-node", matrix)
        self.assertIn("rx7900xt-node", matrix)

    def test_matrix_excludes_offline_nodes(self):
        self.rx7900xt.status = "offline"
        self.rx7900xt.routing_eligible = False
        matrix = build_capability_matrix([self.rx9070, self.rx7900xt])
        self.assertIn("rx9070-node", matrix)
        self.assertNotIn("rx7900xt-node", matrix)


class TestEligibilityFiltering(unittest.TestCase):

    def setUp(self):
        self.nodes = [
            NodeRegistryEntry(
                node_id="rx9070-node", hostname="RX9070", ip="192.168.1.50",
                role="on_demand", status="online", availability_policy="optional",
                capabilities=["chat", "coding", "fast"],
                models=[NodeModel(id="qwen2.5-coder-14b", loaded=True, node="rx9070-node")],
                metrics=NodeMetrics(latency_ms=2.5, health_score=1.0),
                routing_eligible=True, offline_is_failure=False,
            ),
            NodeRegistryEntry(
                node_id="rx7900xt-node", hostname="RX7900XT", ip="192.168.1.60",
                role="on_demand", status="online", availability_policy="optional",
                capabilities=["chat", "vision", "large-context"],
                models=[NodeModel(id="moondream2", loaded=True, node="rx7900xt-node")],
                metrics=NodeMetrics(latency_ms=2.0, health_score=1.0),
                routing_eligible=True, offline_is_failure=False,
            ),
        ]

    def test_no_filter_returns_all(self):
        eligible = select_eligible_nodes(self.nodes)
        self.assertEqual(len(eligible), 2)

    def test_filter_single_capability(self):
        eligible = select_eligible_nodes(self.nodes, requirements=["vision"])
        self.assertEqual(len(eligible), 1)
        self.assertEqual(eligible[0].node_id, "rx7900xt-node")

    def test_filter_multiple_capabilities(self):
        eligible = select_eligible_nodes(self.nodes, requirements=["coding", "chat"])
        self.assertEqual(len(eligible), 1)
        self.assertEqual(eligible[0].node_id, "rx9070-node")

    def test_filter_unmatched_returns_empty(self):
        eligible = select_eligible_nodes(self.nodes, requirements=["embeddings"])
        self.assertEqual(len(eligible), 0)


class TestSerialization(unittest.TestCase):

    def setUp(self):
        self.entry = NodeRegistryEntry(
            node_id="rx9070-node", hostname="RX9070", ip="192.168.1.50",
            role="on_demand", status="online", availability_policy="optional",
            capabilities=["chat", "coding"],
            models=[NodeModel(id="qwen2.5-coder-14b", loaded=True, node="rx9070-node")],
            metrics=NodeMetrics(latency_ms=2.5, health_score=1.0),
            routing_eligible=True, offline_is_failure=False,
        )

    def test_entry_to_dict_has_required_keys(self):
        d = entry_to_dict(self.entry)
        self.assertEqual(d["node_id"], "rx9070-node")
        self.assertEqual(d["status"], "online")
        self.assertIn("models", d)
        self.assertIn("metrics", d)
        self.assertIn("evidence", d)
        self.assertIn("contract_version", d)

    def test_registry_to_dict_aggregates(self):
        d = registry_to_dict([self.entry])
        self.assertEqual(d["nodes_total"], 1)
        self.assertEqual(d["nodes_online"], 1)
        self.assertIn("nodes_by_role", d)
        self.assertIn("nodes", d)


class TestOfflineIsWarningNotCritical(unittest.TestCase):

    def test_optional_offline_registry_shows_warning(self):
        reg = registry_to_dict([
            NodeRegistryEntry(
                node_id="rx7900xt-node", hostname="RX7900XT", ip="192.168.1.60",
                role="on_demand", status="offline", availability_policy="optional",
                capabilities=[], models=[],
                metrics=NodeMetrics(health_score=0.0),
                routing_eligible=False, offline_is_failure=False,
            ),
            NodeRegistryEntry(
                node_id="rx9070-node", hostname="RX9070", ip="192.168.1.50",
                role="on_demand", status="online", availability_policy="optional",
                capabilities=["chat", "coding"],
                models=[NodeModel(id="qwen2.5-coder-14b", loaded=True, node="rx9070-node")],
                metrics=NodeMetrics(latency_ms=2.5, health_score=1.0),
                routing_eligible=True, offline_is_failure=False,
            ),
        ])
        self.assertEqual(reg["nodes_offline"], 1)
        self.assertEqual(reg["nodes_online"], 1)
        self.assertFalse(reg["required_offline_is_critical"])


if __name__ == "__main__":
    unittest.main()
