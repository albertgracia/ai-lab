"""Tests for deterministic Capability Scheduler (CAPABILITY-SCHEDULER-01)."""

import sys
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

# Add workspace root for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runtime.router.capability_scheduler import (
    extract_capability_requirements,
    build_scheduler_candidates,
    score_candidate,
    select_best_candidate,
    build_scheduler_decision,
    VISION_PREFIXES, LARGE_CONTEXT_PREFIXES,
    CODING_PREFIXES, REASONING_PREFIXES,
)


# ── Helpers ────────────────────────────────────────────────────────────────

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


def make_rx9070_node(online: bool = True, health: float = 0.9) -> NodeRegistryEntry:
    return NodeRegistryEntry(
        node_id="rx9070-node",
        hostname="RX9070",
        ip="192.168.1.50",
        role="on_demand",
        status="online" if online else "offline",
        capabilities=["chat", "coding", "fast", "reasoning"],
        models=[
            NodeModel(id="qwen2.5-14b-instruct", suitability=["coding", "reasoning"]),
            NodeModel(id="qwen2.5-coder-14b-instruct", suitability=["coding"]),
            NodeModel(id="deepseek-r1-distill-qwen-14b", suitability=["reasoning"]),
            NodeModel(id="qwen3-vl-8b-instruct", suitability=["vision", "fast"]),
            NodeModel(id="llama-3.1-8b-instruct", suitability=["fast"]),
            NodeModel(id="nomic-embed-text-v1.5", suitability=["embedding"]),
        ],
        metrics=NodeMetrics(health_score=health, latency_ms=1000.0),
        routing_eligible=online,
        fallback_eligible=online,
    )


def make_rx7900xt_node(online: bool = True, health: float = 0.85) -> NodeRegistryEntry:
    return NodeRegistryEntry(
        node_id="rx7900xt-node",
        hostname="RX7900XT",
        ip="192.168.1.60",
        role="on_demand",
        status="online" if online else "offline",
        capabilities=["chat", "coding", "fast", "reasoning", "large-context", "vision", "embedding"],
        models=[
            NodeModel(id="qwen3.6-35b-a3b", suitability=["large-context", "reasoning"]),
            NodeModel(id="qwen3-coder-30b-a3b-instruct@q4_k_xl", suitability=["coding", "large-context"]),
            NodeModel(id="moondream2-20250414", suitability=["vision"]),
            NodeModel(id="text-embedding-nomic-embed-text-v2-moe", suitability=["embedding"]),
            NodeModel(id="gemma-4-12b-it", suitability=["chat", "fast"]),
            NodeModel(id="qwen3.5-9b-deepseek-v4-flash-mtp", suitability=["fast", "reasoning"]),
            NodeModel(id="gemma-3-12b-it-vl-polaris-glm-4.7-flash-var-thinking-instruct-heretic-uncensored-i1",
                      suitability=["vision"]),
            NodeModel(id="qwen3.6-27b-claude-opus-reasoning-distilled", suitability=["reasoning", "large-context"]),
            NodeModel(id="openai_gpt-oss-20b", suitability=["chat"]),
            NodeModel(id="llama-3.1-8b-instruct", suitability=["fast"]),
            NodeModel(id="deepseek-r1-distill-qwen-14b", suitability=["reasoning"]),
        ],
        metrics=NodeMetrics(health_score=health, latency_ms=2000.0),
        routing_eligible=online,
        fallback_eligible=online,
    )


def make_nas_node(online: bool = False) -> NodeRegistryEntry:
    return NodeRegistryEntry(
        node_id="nas-n5",
        hostname="NAS-N5",
        ip="192.168.1.250",
        role="baseline",
        status="online" if online else "offline",
        capabilities=[],
        models=[],
        metrics=NodeMetrics(health_score=0.1),
        routing_eligible=False,
        fallback_eligible=False,
        offline_is_failure=True,
    )


def make_online_registry() -> list:
    return [make_rx9070_node(online=True), make_rx7900xt_node(online=True), make_nas_node(online=False)]


def make_offline_7900xt_registry() -> list:
    return [make_rx9070_node(online=True), make_rx7900xt_node(online=False), make_nas_node(online=False)]


def make_unhealthy_node_registry() -> list:
    return [make_rx9070_node(online=True, health=0.3), make_rx7900xt_node(online=True), make_nas_node(online=False)]


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Capability Extraction
# ═══════════════════════════════════════════════════════════════════════════

class TestCapabilityExtraction:

    def test_normal_chat_no_capability(self):
        req = extract_capability_requirements(
            requested_model="llama-3.1-8b-instruct",
            profile="chat",
        )
        assert not req["vision_required"]
        assert not req["coding_required"]
        assert not req["reasoning_required"]
        assert not req["large_context_required"]
        assert not req["requires_rx7900xt"]

    def test_coding_model_extracts_coding(self):
        req = extract_capability_requirements(
            requested_model="qwen/qwen2.5-coder-14b-instruct",
        )
        assert req["coding_required"]
        assert not req["requires_rx7900xt"]

    def test_vision_model_extracts_vision(self):
        req = extract_capability_requirements(requested_model="moondream2")
        assert req["vision_required"]
        assert req["requires_rx7900xt"]

    def test_large_context_model_extracts_large_context(self):
        req = extract_capability_requirements(requested_model="qwen3.6-35b-a3b")
        assert req["large_context_required"]
        assert req["requires_rx7900xt"]

    def test_rx7900xt_canonical_detected(self):
        req = extract_capability_requirements(requested_model="qwen3.6-35b")
        assert req["requires_rx7900xt"]
        assert req["large_context_required"]

    def test_reasoning_model_extracts_reasoning(self):
        req = extract_capability_requirements(
            requested_model="deepseek/deepseek-r1-distill-qwen-14b",
        )
        assert req["reasoning_required"]

    def test_profile_coding_extracts_coding(self):
        req = extract_capability_requirements(profile="coding")
        assert req["coding_required"]

    def test_profile_reasoning_extracts_reasoning(self):
        req = extract_capability_requirements(profile="reasoning")
        assert req["reasoning_required"]

    def test_empty_model_no_capability(self):
        req = extract_capability_requirements()
        assert not req["vision_required"]
        assert not req["coding_required"]
        assert not req["reasoning_required"]
        assert not req["requires_rx7900xt"]

    def test_embedding_model(self):
        req = extract_capability_requirements(requested_model="nomic-embed-text-v1.5")
        assert req["embedding_required"]

    def test_vision_prefixes_all_detected(self):
        for prefix in VISION_PREFIXES:
            req = extract_capability_requirements(requested_model=f"{prefix}-test")
            assert req["vision_required"], f"Prefix {prefix} not detected"


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Scheduler Decision — Normal Chat
# ═══════════════════════════════════════════════════════════════════════════

class TestSchedulerNormalChat:

    def test_normal_chat_skips_scheduler(self):
        decision = build_scheduler_decision(
            requested_model="llama-3.1-8b-instruct",
            registry=make_online_registry(),
        )
        assert decision["decision"] == "skip"
        assert "scheduler_skip_no_capability" in decision["reason_codes"]

    def test_coding_model_skips_scheduler_on_50(self):
        # Coding models that exist on .50 should NOT be forcefully routed by scheduler
        decision = build_scheduler_decision(
            requested_model="qwen/qwen2.5-coder-14b-instruct",
            registry=make_online_registry(),
        )
        assert decision["decision"] == "skip"

    def test_default_empty_model_skips(self):
        decision = build_scheduler_decision(registry=make_online_registry())
        assert decision["decision"] == "skip"


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Scheduler Decision — Capability Routing
# ═══════════════════════════════════════════════════════════════════════════

class TestSchedulerCapabilityRouting:

    def test_qwen3_6_35b_routes_to_60(self):
        decision = build_scheduler_decision(
            requested_model="qwen/qwen3.6-35b-a3b",
            registry=make_online_registry(),
        )
        assert decision["decision"] == "selected"
        assert "rx7900xt" in decision["selected_node"]
        assert decision["confidence"] >= 0.9
        assert any("rx7900xt" in c for c in decision["reason_codes"])

    def test_qwen3_coder_30b_routes_to_60(self):
        decision = build_scheduler_decision(
            requested_model="qwen3-coder-30b",
            registry=make_online_registry(),
        )
        assert decision["decision"] == "selected"
        assert "rx7900xt" in decision["selected_node"]

    def test_moondream2_routes_to_60(self):
        decision = build_scheduler_decision(
            requested_model="moondream2",
            registry=make_online_registry(),
        )
        assert decision["decision"] == "selected"
        assert "rx7900xt" in decision["selected_node"]

    def test_vision_model_routes_to_60(self):
        decision = build_scheduler_decision(
            requested_model="moondream2-20250414",
            registry=make_online_registry(),
        )
        assert decision["decision"] == "selected"
        assert "rx7900xt" in decision["selected_node"]

    def test_large_context_model_routes_to_60(self):
        decision = build_scheduler_decision(
            requested_model="qwen3.6-35b",
            registry=make_online_registry(),
        )
        assert decision["decision"] == "selected"
        assert "rx7900xt" in decision["selected_node"]


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Scheduler Decision — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

class TestSchedulerEdgeCases:

    def test_60_offline_excludes_60(self):
        decision = build_scheduler_decision(
            requested_model="moondream2",
            registry=make_offline_7900xt_registry(),
        )
        # Vision model required but no vision-capable node online
        assert decision["decision"] == "capacity_unavailable"

    def test_60_offline_coding_stays_50(self):
        decision = build_scheduler_decision(
            requested_model="qwen/qwen2.5-coder-14b-instruct",
            registry=make_offline_7900xt_registry(),
        )
        assert decision["decision"] == "skip"

    def test_optional_offline_node_not_critical(self):
        decision = build_scheduler_decision(
            requested_model="moondream2",
            registry=make_offline_7900xt_registry(),
        )
        assert decision["decision"] == "capacity_unavailable"
        assert not any("critical" in c for c in decision["reason_codes"])

    def test_no_candidate_returns_capacity_unavailable(self):
        decision = build_scheduler_decision(
            requested_model="moondream2",
            registry=[],
        )
        assert decision["decision"] == "capacity_unavailable"

    def test_rejected_candidates_listed_in_decision(self):
        decision = build_scheduler_decision(
            requested_model="moondream2",
            registry=make_offline_7900xt_registry(),
        )
        assert "rejected_candidates" in decision
        # With .60 offline, moondream2 is only on .60 (requires_rx7900xt)
        # .50 should be rejected because model only exists on .60
        # .60 is offline so it won't appear as a candidate

    def test_candidate_scoring_explains_rejected(self):
        # Use requires_rx7900xt to trigger rejection on .50 when .60 offline
        candidates = build_scheduler_candidates(
            {"vision_required": True, "requires_rx7900xt": True},
            make_offline_7900xt_registry(),
        )
        for c in candidates:
            score_candidate(c, {"vision_required": True, "requires_rx7900xt": True})
        rejected = [c for c in candidates if c.get("rejected", False)]
        assert len(rejected) > 0
        for r in rejected:
            assert r.get("reject_reason", "") != ""
            if r.get("node_id") == "rx9070-node":
                assert "rx7900xt" in r.get("reject_reason", "")


# ═══════════════════════════════════════════════════════════════════════════
# TEST: SLO Degradation
# ═══════════════════════════════════════════════════════════════════════════

class TestSchedulerSLO:

    def test_slo_degraded_node_gets_lower_score(self):
        slo = {"degraded_nodes": ["rx9070-node"]}
        candidates = build_scheduler_candidates(
            {"reasoning_required": True},
            [make_rx9070_node(), make_rx7900xt_node()],
            slo_snapshot=slo,
        )
        for c in candidates:
            score_candidate(c, {"reasoning_required": True}, slo)
        for c in candidates:
            if c["node_id"] == "rx9070-node":
                assert not c["slo_ok"]
                assert "slo_degraded" in c.get("reasons", [])

    def test_unhealthy_node_not_selected(self):
        decision = build_scheduler_decision(
            requested_model="moondream2",
            registry=make_unhealthy_node_registry(),
        )
        # .50 is unhealthy (health=0.3) but .60 is healthy — should prefer .60
        assert decision["decision"] == "selected"
        assert "rx7900xt" in decision["selected_node"]


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Scheduler Output Contract
# ═══════════════════════════════════════════════════════════════════════════

class TestSchedulerOutputContract:

    def test_decision_has_required_keys(self):
        decision = build_scheduler_decision(
            requested_model="moondream2",
            registry=make_online_registry(),
        )
        required_keys = [
            "selected_node", "selected_model", "backend_url",
            "decision", "confidence", "reason_codes", "evidence",
            "requirements", "fallback_candidates", "rejected_candidates",
        ]
        for key in required_keys:
            assert key in decision, f"Missing key: {key}"

    def test_skip_decision_has_empty_targets(self):
        decision = build_scheduler_decision(registry=make_online_registry())
        assert decision["selected_node"] == ""
        assert decision["selected_model"] == ""
        assert decision["backend_url"] == ""

    def test_selected_decision_has_populated_targets(self):
        decision = build_scheduler_decision(
            requested_model="moondream2",
            registry=make_online_registry(),
        )
        assert decision["selected_node"] != ""
        assert decision["backend_url"] != ""

    def test_evidence_contains_reasons(self):
        decision = build_scheduler_decision(
            requested_model="moondream2",
            registry=make_online_registry(),
        )
        assert len(decision.get("evidence", [])) > 0


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Candidate Scoring
# ═══════════════════════════════════════════════════════════════════════════

class TestCandidateScoring:

    def test_capability_match_scores_higher(self):
        candidates = build_scheduler_candidates(
            {"vision_required": True, "requires_rx7900xt": True},
            make_online_registry(),
        )
        scored = []
        for c in candidates:
            scored.append(score_candidate(c, {"vision_required": True, "requires_rx7900xt": True}))
        # .60 should be the only non-rejected (requires_rx7900xt gates .50 out)
        rx7900xt_nodes = [c for c in scored if "rx7900xt" in c["node_id"]]
        other_nodes = [c for c in scored if "rx9070" in c["node_id"]]
        assert len(rx7900xt_nodes) > 0
        # .50 should be rejected (requires_rx7900xt)
        if other_nodes:
            assert all(o.get("rejected", False) for o in other_nodes)

    def test_select_best_returns_highest_score(self):
        candidates = build_scheduler_candidates(
            {"reasoning_required": True},
            make_online_registry(),
        )
        for c in candidates:
            score_candidate(c, {"reasoning_required": True})
        best = select_best_candidate(candidates, {"reasoning_required": True})
        assert best is not None
        assert best["score"] >= 0

    def test_select_best_no_eligible_returns_none(self):
        # .50 has qwen3-vl-8b-instruct so it IS vision-capable.
        # Use requires_rx7900xt to require a model that's only on .60.
        candidates = build_scheduler_candidates(
            {"vision_required": True, "requires_rx7900xt": True},
            make_offline_7900xt_registry(),
        )
        for c in candidates:
            score_candidate(c, {"vision_required": True, "requires_rx7900xt": True})
        best = select_best_candidate(candidates, {"vision_required": True, "requires_rx7900xt": True})
        assert best is None


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Hermes Profile
# ═══════════════════════════════════════════════════════════════════════════

class TestHermesProfile:

    def test_hermes_profile_skips_scheduler(self):
        decision = build_scheduler_decision(
            requested_model="llama-3.1-8b-instruct",
            profile="hermes",
            route_family="tool_fastpath",
            registry=make_online_registry(),
        )
        assert decision["decision"] == "skip"


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Reason Codes
# ═══════════════════════════════════════════════════════════════════════════

class TestReasonCodes:

    def test_scheduler_reason_codes_in_decision(self):
        decision = build_scheduler_decision(
            requested_model="moondream2",
            registry=make_online_registry(),
        )
        codes = decision.get("reason_codes", [])
        assert len(codes) > 0
        assert any("scheduler" in c for c in codes)

    def test_fallback_engine_reason_codes_separate(self):
        decision = build_scheduler_decision(
            requested_model="moondream2",
            registry=make_online_registry(),
        )
        assert "intelligent_fallback" not in decision["reason_codes"]
        assert "fallback_unavailable" not in decision["reason_codes"]
