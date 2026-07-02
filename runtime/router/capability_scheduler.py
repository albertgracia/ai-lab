"""Deterministic Capability Scheduler — selects node/model by capability.

This is NOT adaptive learning.
This is deterministic, explainable scheduling.

Every scheduling decision records:
- selected_node, selected_model, backend_url
- decision type: selected | fallback_selected | capacity_unavailable | blocked
- confidence, reason_codes[], evidence[], rejected_candidates[]

Consumes:
- Dynamic Node Registry (node availability, capabilities, models)
- Multi-Node Routing (backend URLs, model normalization)
- SLO state (degraded nodes penalized)
- Operator Intent (explicit capability requirements)

Does NOT replace:
- Deterministic multi-node routing for normal chat/coding
- Intelligent Fallback Engine for runtime failures
- Validation Authority for safety gates
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Vision model prefixes (must never route to text-only nodes) ──────────

VISION_PREFIXES: set[str] = {
    "moondream", "vision", "llava", "cogvlm", "qwen-vl",
    "qwen2-vl", "qwen3-vl", "vl-", "multimodal", "phi-vision",
}

LARGE_CONTEXT_PREFIXES: set[str] = {
    "30b", "32b", "35b", "70b", "120b", "xl",
}

CODING_PREFIXES: set[str] = {
    "coder", "code-", "deepseek-coder", "starcoder",
}

REASONING_PREFIXES: set[str] = {
    "deepseek", "r1", "reason", "think",
}

EMBEDDING_PREFIXES: set[str] = {
    "embed", "nomic-embed", "text-embedding",
}

# ── Models that should explicitly route to .60 (rx7900xt-node) ──────────

_RX7900XT_REQUIRED_MODELS: set[str] = {
    "qwen3-coder-30b-a3b-instruct@q3_k_s",
    "qwen3-coder-30b-a3b-instruct@q4_k_xl",
    "qwen3.6-27b-claude-opus-reasoning-distilled",
    "openai_gpt-oss-20b",
    "qwen3.6-35b-a3b",
    "qwen/qwen3.6-35b-a3b",
    "moondream2-20250414",
    "text-embedding-nomic-embed-text-v2-moe",
    "gemma-4-12b-it",
    "gemma-3-12b-it-vl-polaris-glm-4.7-flash-var-thinking-instruct-heretic-uncensored-i1",
    "qwen3.5-9b-deepseek-v4-flash-mtp",
}

_RX7900XT_CANONICAL: dict[str, str] = {
    "qwen3-coder-30b": "qwen3-coder-30b-a3b-instruct@q4_k_xl",
    "qwen/qwen3-coder-30b": "qwen3-coder-30b-a3b-instruct@q4_k_xl",
    "qwen3.6-35b": "qwen3.6-35b-a3b",
    "qwen/qwen3.6-35b": "qwen3.6-35b-a3b",
    "moondream2": "moondream2-20250414",
}


# ── Capability extraction ──────────────────────────────────────────────

def extract_capability_requirements(
    requested_model: str = "",
    profile: str = "",
    route_family: str = "",
    messages: list | None = None,
    operator_intent: dict | None = None,
) -> dict[str, Any]:
    """Extract deterministically what capability this request needs.

    Returns dict with boolean flags:
        vision_required, coding_required, reasoning_required,
        large_context_required, embedding_required, tool_required,
        explicit_model_routed, requires_rx7900xt
    """
    req: dict[str, Any] = {
        "vision_required": False,
        "coding_required": False,
        "reasoning_required": False,
        "large_context_required": False,
        "embedding_required": False,
        "tool_required": False,
        "explicit_model_routed": False,
        "requires_rx7900xt": False,
        "source": "model_route",
    }

    model_lower = requested_model.lower() if requested_model else ""

    # 1. Check explicit model prefixes
    if model_lower:
        req["explicit_model_routed"] = True
        for prefix in VISION_PREFIXES:
            if prefix in model_lower:
                req["vision_required"] = True
                break
        for prefix in LARGE_CONTEXT_PREFIXES:
            if prefix in model_lower:
                req["large_context_required"] = True
                break
        for prefix in CODING_PREFIXES:
            if prefix in model_lower:
                req["coding_required"] = True
                break
        for prefix in REASONING_PREFIXES:
            if prefix in model_lower:
                req["reasoning_required"] = True
                break
        for prefix in EMBEDDING_PREFIXES:
            if prefix in model_lower:
                req["embedding_required"] = True
                break

        # 2. Check if model is known to require .60
    if not model_lower:
        pass  # no explicit model → no rx7900xt requirement
    elif model_lower in {m.lower() for m in _RX7900XT_REQUIRED_MODELS}:
        req["requires_rx7900xt"] = True
    else:
        for canonical in _RX7900XT_CANONICAL:
            if canonical in model_lower:
                req["requires_rx7900xt"] = True
                break

    # 3. Check profile
    profile_lower = profile.lower() if profile else ""
    if "coding" in profile_lower or "code" in profile_lower:
        if not req["vision_required"]:
            req["coding_required"] = True
            req["source"] = "profile"
    if "reasoning" in profile_lower:
        req["reasoning_required"] = True
        req["source"] = "profile"

    # 4. Check route family
    if route_family in ("tool_fastpath",):
        req["tool_required"] = True

    # 5. Check operator intent
    if operator_intent:
        intent_caps = operator_intent.get("required_capabilities", [])
        if isinstance(intent_caps, list):
            for cap in intent_caps:
                cap_lower = cap.lower()
                if cap_lower == "vision":
                    req["vision_required"] = True
                elif cap_lower == "coding":
                    req["coding_required"] = True
                elif cap_lower == "reasoning":
                    req["reasoning_required"] = True
                elif cap_lower == "large_context":
                    req["large_context_required"] = True
                elif cap_lower == "embedding":
                    req["embedding_required"] = True

    # 6. Check messages for capability keywords (messages-based extraction)
    if messages and not any([req["vision_required"], req["coding_required"],
                             req["reasoning_required"], req["large_context_required"]]):
        text = _extract_text_from_messages(messages)
        if _contains_image(messages):
            req["vision_required"] = True
            req["source"] = "message_content"
        if _contains_coding_keywords(text) and not req["vision_required"]:
            req["coding_required"] = True
            req["source"] = "message_content"
        if _contains_reasoning_keywords(text) and not req["vision_required"]:
            req["reasoning_required"] = True
            req["source"] = "message_content"

    return req


def _extract_text_from_messages(messages: list | None) -> str:
    if not messages:
        return ""
    parts: list[str] = []
    for msg in messages:
        content = msg.get("content", "") if isinstance(msg, dict) else ""
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
        elif isinstance(content, str):
            parts.append(content)
    return " ".join(parts)


def _contains_image(messages: list | None) -> bool:
    if not messages:
        return False
    for msg in messages:
        content = msg.get("content", "") if isinstance(msg, dict) else ""
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") in ("image_url", "image"):
                    return True
    return False


_CODING_KEYWORDS: set[str] = {
    "code", "function", "bug", "stacktrace", "refactor",
    "test", "implement", "class", "def ", "import ",
    "pytest", "unittest", "api", "endpoint", "schema",
}

_REASONING_KEYWORDS: set[str] = {
    "plan", "diagnose", "analyze", "architecture", "why",
    "compare", "evaluate", "design", "strategy",
    "root cause", "trade-off", "decision",
}


def _contains_coding_keywords(text: str) -> bool:
    t = text.lower()
    for kw in _CODING_KEYWORDS:
        if kw in t:
            return True
    return False


def _contains_reasoning_keywords(text: str) -> bool:
    t = text.lower()
    for kw in _REASONING_KEYWORDS:
        if kw in t:
            return True
    return False


# ── Candidate building ────────────────────────────────────────────────

def build_scheduler_candidates(
    requirements: dict[str, Any],
    registry: list | None = None,
    slo_snapshot: dict | None = None,
) -> list[dict[str, Any]]:
    """Build list of eligible candidates from the Dynamic Node Registry.

    Each candidate dict:
        node_id, url, model, same_model, equivalent_model,
        capability_match, health_score, slo_ok, score, reasons[]
    """
    candidates: list[dict[str, Any]] = []
    if registry is None:
        try:
            from runtime.state.dynamic_node_registry import build_node_registry
            registry = build_node_registry()
        except Exception:
            return []

    if not registry:
        return candidates

    try:
        from runtime.router.multi_node_routing import BACKEND_URLS, normalize_model_for_backend
    except Exception:
        BACKEND_URLS = {}
        normalize_model_for_backend = lambda m, n: m  # type: ignore

    for entry in registry:
        node_id = entry.node_id if hasattr(entry, "node_id") else entry.get("node_id", "")
        if not node_id:
            continue

        status = entry.status if hasattr(entry, "status") else entry.get("status", "unknown")
        routing_eligible = (
            entry.routing_eligible if hasattr(entry, "routing_eligible")
            else entry.get("routing_eligible", False)
        )
        if status != "online" or not routing_eligible:
            continue

        url = BACKEND_URLS.get(node_id, f"http://{entry.ip}:1234/v1" if hasattr(entry, "ip") else "")

        # Collect models on this node
        node_models: list[str] = []
        models_list = entry.models if hasattr(entry, "models") else entry.get("models", [])
        for m in models_list:
            mid = m.id if hasattr(m, "id") else (m.get("id") if isinstance(m, dict) else str(m))
            if mid:
                node_models.append(mid)

        # Collect capabilities
        capabilities: set[str] = set()
        if hasattr(entry, "capabilities"):
            capabilities = set(entry.capabilities)
        elif isinstance(entry, dict):
            capabilities = set(entry.get("capabilities", []))
        for m in models_list:
            if hasattr(m, "suitability"):
                capabilities.update(m.suitability)
            elif isinstance(m, dict):
                capabilities.update(m.get("suitability", []))

        health_score = 0.8
        if hasattr(entry, "metrics") and entry.metrics:
            health_score = entry.metrics.health_score if hasattr(entry.metrics, "health_score") else 0.8
        elif isinstance(entry, dict) and entry.get("metrics"):
            health_score = entry["metrics"].get("health_score", 0.8)

        # Check capability match
        capability_match = _check_capability_match(requirements, capabilities, node_models)

        # Determine model to use on this node
        model_id = _resolve_model_for_node(requirements, node_models, node_id)

        candidate = {
            "node_id": node_id,
            "url": url,
            "model": model_id or "",
            "capability_match": capability_match,
            "model_available": bool(model_id),
            "health_score": health_score,
            "slo_ok": _check_slo_ok(node_id, slo_snapshot),
            "score": 0.0,
            "reasons": [],
            "rejected": False,
            "reject_reason": "",
        }
        candidates.append(candidate)

    # Sort: online, capability match first
    candidates.sort(key=lambda c: (
        0 if c["capability_match"] and c["model_available"] else
        1 if c["capability_match"] else
        2 if c["model_available"] else
        3,
    ))
    return candidates


def _check_capability_match(
    requirements: dict[str, Any],
    capabilities: set[str],
    node_models: list[str],
) -> bool:
    """Check whether a node's capabilities meet the requirements."""
    if requirements.get("vision_required"):
        if "vision" not in capabilities and not any("vl" in m.lower() or "vision" in m.lower() for m in node_models):
            return False
    if requirements.get("large_context_required"):
        if "large-context" not in capabilities and not any(
            any(p in m.lower() for p in LARGE_CONTEXT_PREFIXES) for m in node_models
        ):
            return False
    if requirements.get("coding_required"):
        if "coding" not in capabilities and not any(
            any(p in m.lower() for p in CODING_PREFIXES) for m in node_models
        ):
            return False
    if requirements.get("reasoning_required"):
        if "reasoning" not in capabilities and not any(
            any(p in m.lower() for p in REASONING_PREFIXES) for m in node_models
        ):
            return False
    if requirements.get("embedding_required"):
        if "embedding" not in capabilities and not any(
            any(p in m.lower() for p in EMBEDDING_PREFIXES) for m in node_models
        ):
            return False
    return True


def _resolve_model_for_node(
    requirements: dict[str, Any],
    node_models: list[str],
    node_id: str,
) -> str | None:
    """Resolve which model ID to use on this node."""
    # For vision/large-context requirements, find the right model
    if requirements.get("vision_required"):
        for m in node_models:
            if any(p in m.lower() for p in VISION_PREFIXES):
                return m
    if requirements.get("large_context_required"):
        for m in node_models:
            if any(p in m.lower() for p in LARGE_CONTEXT_PREFIXES):
                return m
    if requirements.get("embedding_required"):
        for m in node_models:
            if any(p in m.lower() for p in EMBEDDING_PREFIXES):
                return m
    if node_models:
        return node_models[0]
    return None


def _check_slo_ok(node_id: str, slo_snapshot: dict | None) -> bool:
    if slo_snapshot is None:
        return True
    degraded_nodes = slo_snapshot.get("degraded_nodes", [])
    if isinstance(degraded_nodes, list) and node_id in degraded_nodes:
        return False
    return True


# ── Deterministic scoring ─────────────────────────────────────────────

def score_candidate(
    candidate: dict[str, Any],
    requirements: dict[str, Any],
    slo_snapshot: dict | None = None,
) -> dict[str, Any]:
    """Score one candidate node. Returns the candidate dict with score + reasons.

    Scoring dimensions (each 0.0–1.0):
    - capability_match: 1.0 if match, 0.0 otherwise
    - model_available: 1.0 if model found, 0.0 otherwise
    - health: 0.0–1.0 from registry
    - slo: 1.0 if SLO ok, 0.0 if degraded
    - role_preference: 1.0 for on_demand, 0.8 for baseline

    Final score = weighted sum.
    """
    score = 0.0
    reasons: list[str] = []

    # Gating: requires_rx7900xt (model is ONLY on .60)
    if requirements.get("requires_rx7900xt"):
        if "rx7900xt" not in candidate["node_id"]:
            candidate["score"] = 0.0
            candidate["rejected"] = True
            candidate["reject_reason"] = "model_only_on_rx7900xt"
            candidate["reasons"] = ["rejected: model only available on rx7900xt"]
            return candidate
        score += 4.0
        reasons.append("rx7900xt_required_model")

    # Gating: capability match
    if requirements.get("vision_required") or requirements.get("large_context_required"):
        if not candidate["capability_match"]:
            candidate["score"] = 0.0
            candidate["rejected"] = True
            candidate["reject_reason"] = "capability_mismatch"
            candidate["reasons"] = ["rejected: no matching capability"]
            return candidate
        score += 3.0
        reasons.append("capability_match")

    # Gating: model availability
    if not candidate["model_available"] and (requirements.get("vision_required") or requirements.get("large_context_required")):
        candidate["score"] = 0.0
        candidate["rejected"] = True
        candidate["reject_reason"] = "model_not_available"
        candidate["reasons"] = ["rejected: no eligible model on node"]
        return candidate

    # Model available
    if candidate["model_available"]:
        score += 2.0
        reasons.append("model_available")

    # Capability match (bonus)
    if candidate["capability_match"]:
        score += 2.0
        reasons.append("capability_match")

    # Health score
    health = candidate.get("health_score", 0.8)
    score += health * 1.0
    if health < 0.5:
        reasons.append("health_degraded")
    elif health >= 0.9:
        reasons.append("health_ok")

    # SLO
    if candidate.get("slo_ok", True):
        score += 1.0
        reasons.append("slo_ok")
    else:
        score -= 1.0
        reasons.append("slo_degraded")

    # Role preference (on_demand preferred for GPU workloads)
    if "rx7900xt" in candidate["node_id"] or "rx9070" in candidate["node_id"]:
        score += 0.5
        reasons.append("preferred_role")

    candidate["score"] = round(score, 2)
    candidate["reasons"] = reasons
    return candidate


# ── Selection ─────────────────────────────────────────────────────────

def select_best_candidate(
    candidates: list[dict[str, Any]],
    requirements: dict[str, Any],
) -> dict[str, Any] | None:
    """Select the best candidate by score.

    Rules:
    1. Only non-rejected candidates are eligible.
    2. Vision/large-context must have capability_match = True.
    3. Highest score wins.
    4. If tie: prefer .60 for large/vision, .50 for normal.
    """
    eligible = [c for c in candidates if not c.get("rejected", False)]
    if not eligible:
        return None

    eligible.sort(key=lambda c: c.get("score", 0.0), reverse=True)

    best = eligible[0]

    # Tie-breaking: if same score and vision/large-context, prefer .60
    if len(eligible) > 1 and eligible[0]["score"] == eligible[1]["score"]:
        if requirements.get("vision_required") or requirements.get("large_context_required"):
            for c in eligible:
                if "rx7900xt" in c["node_id"] and c["capability_match"]:
                    best = c
                    break
        elif not requirements.get("vision_required") and not requirements.get("large_context_required"):
            for c in eligible:
                if "rx9070" in c["node_id"]:
                    best = c
                    break

    return best


# ── Full decision pipeline ────────────────────────────────────────────

def build_scheduler_decision(
    requested_model: str = "",
    profile: str = "",
    route_family: str = "",
    messages: list | None = None,
    registry: list | None = None,
    slo_snapshot: dict | None = None,
    operator_intent: dict | None = None,
) -> dict[str, Any]:
    """Build a full scheduler decision.

    Returns:
        selected_node, selected_model, backend_url, decision, confidence,
        reason_codes[], evidence[], fallback_candidates[], rejected_candidates[]
    """
    # 1. Extract requirements
    requirements = extract_capability_requirements(
        requested_model=requested_model,
        profile=profile,
        route_family=route_family,
        messages=messages,
        operator_intent=operator_intent,
    )

    # 2. If no capability requires specific routing, return "skip"
    # Only vision, large_context, and requires_rx7900xt trigger scheduling.
    # Coding, reasoning, embedding, and tool models exist on both .50 and .60
    # and should use multi-node routing + fallback, not the scheduler.
    has_capability = any([
        requirements.get("vision_required"),
        requirements.get("large_context_required"),
        requirements.get("requires_rx7900xt"),
    ])
    if not has_capability:
        return {
            "selected_node": "",
            "selected_model": "",
            "backend_url": "",
            "decision": "skip",
            "confidence": 1.0,
            "reason_codes": ["scheduler_skip_no_capability"],
            "evidence": [],
            "requirements": requirements,
            "fallback_candidates": [],
            "rejected_candidates": [],
        }

    # 3. Build candidates
    candidates = build_scheduler_candidates(requirements, registry, slo_snapshot)
    if not candidates:
        return {
            "selected_node": "",
            "selected_model": "",
            "backend_url": "",
            "decision": "capacity_unavailable",
            "confidence": 1.0,
            "reason_codes": ["scheduler_capacity_unavailable", "no_online_nodes"],
            "evidence": ["dynamic_node_registry"],
            "requirements": requirements,
            "fallback_candidates": [],
            "rejected_candidates": [],
        }

    # 4. Score candidates
    for c in candidates:
        score_candidate(c, requirements, slo_snapshot)

    # 5. Select best
    best = select_best_candidate(candidates, requirements)
    rejected = [c for c in candidates if c.get("rejected", False)]

    if best is None:
        return {
            "selected_node": "",
            "selected_model": "",
            "backend_url": "",
            "decision": "capacity_unavailable",
            "confidence": 0.9,
            "reason_codes": ["scheduler_capacity_unavailable", "all_candidates_rejected"],
            "evidence": [f"rejected: {r.get('reject_reason', 'unknown')}" for r in rejected],
            "requirements": requirements,
            "fallback_candidates": [],
            "rejected_candidates": rejected,
        }

    # 6. Determine decision type
    decision_type = "selected"
    reason_codes = [f"scheduler_{decision_type}"]

    if best.get("capability_match"):
        reason_codes.append(f"capability_match_on_{best['node_id']}")
    if best.get("model_available"):
        reason_codes.append(f"model_available_on_{best['node_id']}")

    evidence = best.get("reasons", [])
    if rejected:
        reason_codes.append("some_candidates_rejected")
        evidence.extend([f"rejected: {r.get('node_id', '?')} ({r.get('reject_reason', '?')})" for r in rejected])

    return {
        "selected_node": best["node_id"],
        "selected_model": best["model"],
        "backend_url": best["url"],
        "decision": decision_type,
        "confidence": 0.95 if best.get("capability_match") else 0.8,
        "reason_codes": reason_codes,
        "evidence": evidence,
        "requirements": requirements,
        "fallback_candidates": [c for c in candidates if not c.get("rejected") and c["node_id"] != best["node_id"]],
        "rejected_candidates": rejected,
    }
