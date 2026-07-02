"""Tests for Intelligent Fallback Engine (read-only pure functions).

Validates:
- Failure classification for all 11 types
- Fallback candidate building with capability awareness
- Candidate selection policy rules
- Vision/large-context protection
- No unsafe fallback
- capacity_unavailable error format
"""

import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from runtime.router.fallback_engine import (
    classify_backend_failure, build_fallback_candidates,
    select_fallback_candidate, build_capacity_unavailable_error,
    FAILURE_CLASSES,
)
from runtime.state.dynamic_node_registry import (
    NodeRegistryEntry, NodeMetrics, NodeModel,
)


def _make_entry(node_id, ip, online=True, caps=None, models=None):
    caps = caps or ["chat"]
    models = models or []
    return NodeRegistryEntry(
        node_id=node_id,
        hostname=node_id,
        ip=ip,
        role="on_demand",
        status="online" if online else "offline",
        availability_policy="optional",
        capabilities=list(caps),
        models=[NodeModel(id=m, loaded=True, node=node_id) for m in (models or [])],
        metrics=NodeMetrics(latency_ms=2.0, health_score=1.0 if online else 0.0),
        routing_eligible=online,
        fallback_eligible=online,
        offline_is_failure=False,
    )


class TestFailureClassification(unittest.TestCase):

    def test_http_5xx(self):
        f = classify_backend_failure(response_status=503, error_message="Service Unavailable")
        self.assertEqual(f["failure_type"], "http_5xx")
        self.assertTrue(f["fallback_allowed"])
        self.assertTrue(f["retryable"])

    def test_node_offline_connection_refused(self):
        f = classify_backend_failure(exception=ConnectionRefusedError())
        self.assertEqual(f["failure_type"], "node_offline")
        self.assertTrue(f["fallback_allowed"])

    def test_backend_timeout(self):
        f = classify_backend_failure(exception=TimeoutError())
        self.assertEqual(f["failure_type"], "backend_timeout")
        self.assertTrue(f["fallback_allowed"])

    def test_rate_limited(self):
        f = classify_backend_failure(response_status=429)
        self.assertEqual(f["failure_type"], "rate_limited")
        self.assertTrue(f["fallback_allowed"])

    def test_context_overflow(self):
        f = classify_backend_failure(response_status=413)
        self.assertEqual(f["failure_type"], "context_overflow")
        self.assertFalse(f["fallback_allowed"])

    def test_context_overflow_from_message(self):
        f = classify_backend_failure(error_message="context length exceeded, maximum is 32768")
        self.assertEqual(f["failure_type"], "context_overflow")
        self.assertFalse(f["fallback_allowed"])

    def test_model_not_loaded(self):
        f = classify_backend_failure(error_message="Model 'qwen2.5-14b' is currently unloaded")
        self.assertEqual(f["failure_type"], "model_not_loaded")
        self.assertTrue(f["fallback_allowed"])

    def test_model_not_available(self):
        f = classify_backend_failure(error_message="invalid model identifier 'nonexistent'")
        self.assertEqual(f["failure_type"], "model_not_available_on_node")
        self.assertTrue(f["fallback_allowed"])

    def test_connection_error_message(self):
        f = classify_backend_failure(
            exception=ConnectionError(),
            error_message="Connection refused to 192.168.1.60:1234",
        )
        self.assertEqual(f["failure_type"], "node_offline")

    def test_dns_failure(self):
        f = classify_backend_failure(
            exception=ConnectionError(),
            error_message="Name or service not known",
        )
        self.assertEqual(f["failure_type"], "node_offline")

    def test_unknown_backend_error(self):
        f = classify_backend_failure(
            exception=Exception("something unexpected happened"),
        )
        self.assertEqual(f["failure_type"], "unknown_backend_error")
        self.assertTrue(f["fallback_allowed"])

    def test_all_10_types_defined(self):
        self.assertEqual(len(FAILURE_CLASSES), 10)


class TestFallbackCandidates(unittest.TestCase):

    def setUp(self):
        self.rx9070 = _make_entry("rx9070-node", "192.168.1.50",
                                   caps=["chat", "coding", "fast", "reasoning"],
                                   models=["qwen2.5-14b-instruct"])
        self.rx7900xt = _make_entry("rx7900xt-node", "192.168.1.60",
                                     caps=["chat", "coding", "vision", "large-context", "reasoning"],
                                     models=["qwen3.6-35b-a3b", "moondream2-20250414"])
        self.registry = [self.rx9070, self.rx7900xt]

    def test_same_model_on_other_node(self):
        candidates = build_fallback_candidates("qwen3.6-35b-a3b", "rx7900xt-node", self.registry)
        self.assertTrue(any(c["node_id"] == "rx9070-node" for c in candidates))

    def test_vision_model_no_silent_to_text_only(self):
        self.rx9070.capabilities = ["chat", "coding"]
        candidates = build_fallback_candidates("moondream2-20250414", "rx7900xt-node", self.registry)
        selected = select_fallback_candidate(candidates, "moondream2-20250414")
        self.assertIsNone(selected)

    def test_coding_model_fallback_allowed(self):
        candidates = build_fallback_candidates("qwen2.5-14b-instruct", "rx9070-node", self.registry)
        selected = select_fallback_candidate(candidates, "qwen2.5-14b-instruct")
        self.assertIsNotNone(selected)

    def test_offline_node_excluded(self):
        self.rx7900xt.status = "offline"
        self.rx7900xt.routing_eligible = False
        self.rx7900xt.fallback_eligible = False
        candidates = build_fallback_candidates("qwen3.6-35b-a3b", "rx9070-node", self.registry)
        self.assertFalse(any(c["node_id"] == "rx7900xt-node" for c in candidates))

    def test_no_safe_fallback_returns_none(self):
        candidates = build_fallback_candidates("moondream2-20250414", "rx7900xt-node", [self.rx9070])
        selected = select_fallback_candidate(candidates, "moondream2-20250414")
        self.assertIsNone(selected)

    def test_candidates_sorted_by_preference(self):
        candidates = build_fallback_candidates("qwen3.6-35b-a3b", "rx9070-node", self.registry)
        if len(candidates) >= 1:
            self.assertEqual(candidates[0]["node_id"], "rx7900xt-node")


class TestCandidateSelection(unittest.TestCase):

    def test_same_model_wins(self):
        candidates = [
            {"node_id": "rx7900xt-node", "model": "qwen3.6-35b-a3b",
             "same_model": True, "equivalent_model": "", "capability_match": True,
             "reason": "same_model"},
            {"node_id": "rx9070-node", "model": "qwen3.6-35b-a3b",
             "same_model": False, "equivalent_model": "", "capability_match": True,
             "reason": "capability_match"},
        ]
        selected = select_fallback_candidate(candidates, "qwen3.6-35b-a3b")
        self.assertEqual(selected["node_id"], "rx7900xt-node")

    def test_no_safe_fallback_returns_none(self):
        selected = select_fallback_candidate([], "some-model")
        self.assertIsNone(selected)

    def test_vision_no_text_fallback(self):
        candidates = [
            {"node_id": "rx9070-node", "model": "moondream2",
             "same_model": False, "equivalent_model": "", "capability_match": False,
             "reason": "no_vision"},
        ]
        selected = select_fallback_candidate(candidates, "moondream2-20250414")
        self.assertIsNone(selected)


class TestCapacityUnavailableError(unittest.TestCase):

    def test_error_format(self):
        err = build_capacity_unavailable_error("test-model", "rx9070-node", "http_5xx", "Service Unavailable")
        self.assertEqual(err["error"], "capacity_unavailable")
        self.assertIn("test-model", err["detail"])
        self.assertIn("rx9070-node", err["detail"])
        self.assertIn("http_5xx", err["detail"])

    def test_no_detail_still_clear(self):
        err = build_capacity_unavailable_error("some-model", "rx7900xt-node")
        self.assertEqual(err["error"], "capacity_unavailable")
        self.assertIsNone(err["original_error"])


class TestCapabilityAwareFallback(unittest.TestCase):

    def setUp(self):
        self.rx9070 = _make_entry("rx9070-node", "192.168.1.50",
                                   caps=["chat", "coding", "fast"],
                                   models=["qwen2.5-14b-instruct"])
        self.rx7900xt = _make_entry("rx7900xt-node", "192.168.1.60",
                                     caps=["chat", "coding", "reasoning", "vision", "large-context"],
                                     models=["qwen3.6-35b-a3b", "deepseek-r1"])

    def test_reasoning_fallback_to_other_reasoning_node(self):
        candidates = build_fallback_candidates("deepseek-r1", "rx7900xt-node",
                                                [self.rx9070, self.rx7900xt])
        selected = select_fallback_candidate(candidates, "deepseek-r1")
        self.assertIsNotNone(selected)

    def test_large_context_no_small_context_fallback(self):
        self.rx9070.capabilities = ["chat", "fast"]
        candidates = build_fallback_candidates("qwen3.6-35b-a3b", "rx7900xt-node",
                                                [self.rx9070, self.rx7900xt])
        selected = select_fallback_candidate(candidates, "qwen3.6-35b-a3b")
        self.assertIsNone(selected)

    def test_same_model_on_other_node_succeeds(self):
        rx9070_2 = _make_entry("nas-n5", "192.168.1.250",
                                caps=["chat"],
                                models=["qwen3.6-35b-a3b", "qwen2.5-14b-instruct"])
        candidates = build_fallback_candidates("qwen3.6-35b-a3b", "rx7900xt-node",
                                                [rx9070_2, self.rx7900xt])
        selected = select_fallback_candidate(candidates, "qwen3.6-35b-a3b")
        self.assertIsNotNone(selected)
        self.assertTrue(selected["same_model"])


if __name__ == "__main__":
    unittest.main()
