"""Intelligent Fallback Engine — deterministic, explicit, explainable.

Classifies backend failures, builds fallback candidates respecting
capability constraints, and selects the safest fallback option.

This is NOT a scheduler. This is NOT auto-start for nodes.
Every fallback decision is logged and observable.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Failure classification ────────────────────────────────────────────────

FAILURE_CLASSES: dict[str, dict[str, Any]] = {
    "node_offline": {
        "retryable": False,
        "fallback_allowed": True,
        "requires_same_model": False,
        "safe_degrade_allowed": True,
        "confidence": "high",
        "description": "Backend node does not respond to health check",
    },
    "backend_timeout": {
        "retryable": True,
        "fallback_allowed": True,
        "requires_same_model": False,
        "safe_degrade_allowed": True,
        "confidence": "high",
        "description": "Request to backend timed out (connect or read)",
    },
    "backend_connection_error": {
        "retryable": True,
        "fallback_allowed": True,
        "requires_same_model": False,
        "safe_degrade_allowed": True,
        "confidence": "high",
        "description": "Connection refused, DNS failure, or transport error",
    },
    "model_not_loaded": {
        "retryable": True,
        "fallback_allowed": True,
        "requires_same_model": False,
        "safe_degrade_allowed": True,
        "confidence": "medium",
        "description": "Model is listed but not loaded on the backend",
    },
    "model_not_available_on_node": {
        "retryable": False,
        "fallback_allowed": True,
        "requires_same_model": False,
        "safe_degrade_allowed": True,
        "confidence": "high",
        "description": "Model does not exist on this backend node",
    },
    "http_5xx": {
        "retryable": True,
        "fallback_allowed": True,
        "requires_same_model": False,
        "safe_degrade_allowed": True,
        "confidence": "medium",
        "description": "Backend returned HTTP 5xx server error",
    },
    "context_overflow": {
        "retryable": False,
        "fallback_allowed": False,
        "requires_same_model": True,
        "safe_degrade_allowed": False,
        "confidence": "high",
        "description": "Prompt exceeds model context window",
    },
    "rate_limited": {
        "retryable": True,
        "fallback_allowed": True,
        "requires_same_model": False,
        "safe_degrade_allowed": True,
        "confidence": "medium",
        "description": "Backend rate-limited the request",
    },
    "capacity_unavailable": {
        "retryable": False,
        "fallback_allowed": False,
        "requires_same_model": False,
        "safe_degrade_allowed": False,
        "confidence": "high",
        "description": "No node can serve this model or capability",
    },
    "unknown_backend_error": {
        "retryable": False,
        "fallback_allowed": True,
        "requires_same_model": False,
        "safe_degrade_allowed": False,
        "confidence": "low",
        "description": "Unclassified backend error",
    },
}

# Models known to require vision capability
_VISION_MODEL_PREFIXES: set[str] = {
    "moondream", "vision", "llava", "cogvlm", "qwen-vl",
    "qwen2-vl", "qwen3-vl", "vl-", "multimodal",
}

# Models known to require large context
_LARGE_CONTEXT_PREFIXES: set[str] = {
    "32b", "35b", "30b", "70b", "120b",
}

# Models known to be coding-capable
_CODING_MODEL_PREFIXES: set[str] = {
    "coder", "code", "deepseek-coder", "starcoder",
}

# Models known to be reasoning-capable
_REASONING_MODEL_PREFIXES: set[str] = {
    "deepseek", "r1", "reason", "think",
}


def _model_requires_vision(model_id: str) -> bool:
    mid = model_id.lower()
    for prefix in _VISION_MODEL_PREFIXES:
        if prefix in mid:
            return True
    return False


def _model_requires_large_context(model_id: str) -> bool:
    mid = model_id.lower()
    for prefix in _LARGE_CONTEXT_PREFIXES:
        if prefix in mid:
            return True
    return False


def _model_is_coding(model_id: str) -> bool:
    mid = model_id.lower()
    for prefix in _CODING_MODEL_PREFIXES:
        if prefix in mid:
            return True
    return False


def _model_is_reasoning(model_id: str) -> bool:
    mid = model_id.lower()
    for prefix in _REASONING_MODEL_PREFIXES:
        if prefix in mid:
            return True
    return False


def _node_has_capability(registry_entry: dict | Any, capability: str) -> bool:
    caps = set()
    if hasattr(registry_entry, "capabilities"):
        caps = set(registry_entry.capabilities)
        for m in getattr(registry_entry, "models", []):
            caps.update(getattr(m, "suitability", []))
    elif isinstance(registry_entry, dict):
        caps = set(registry_entry.get("capabilities", []))
        for m in registry_entry.get("models", []):
            if isinstance(m, dict):
                caps.update(m.get("suitability", []))
    return capability in caps


def classify_backend_failure(
    response_status: int | None = None,
    response_body: dict | str | None = None,
    exception: Exception | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    """Classify a backend failure into a failure type with metadata.

    Args:
        response_status: HTTP status code from backend (e.g. 503, 429)
        response_body: Parsed or raw response body
        exception: Python exception object
        error_message: Pre-extracted error message string

    Returns:
        dict with keys: failure_type, retryable, fallback_allowed,
        requires_same_model, safe_degrade_allowed, confidence, reason
    """
    msg = error_message or ""
    if response_body:
        if isinstance(response_body, dict):
            msg = (
                response_body.get("error", {}).get("message", "")
                or response_body.get("message", "")
                or str(response_body)
            )
        else:
            msg = str(response_body)
    if exception:
        msg = msg or str(exception)

    msg_lower = msg.lower()

    # Connection/network errors
    if isinstance(exception, (ConnectionRefusedError, ConnectionError)):
        return _build_failure("node_offline", reason=f"connection_refused: {msg}")
    if isinstance(exception, TimeoutError):
        return _build_failure("backend_timeout", reason=f"timeout: {msg}")

    # Exception-based classification (RequestException wraps connection errors)
    if exception is not None:
        exc_str = str(exception).lower()
        if "nodename nor servname provided" in exc_str or "name or service not known" in exc_str:
            return _build_failure("node_offline", reason=f"dns_resolution_failed: {msg}")
        if "connection refused" in exc_str:
            return _build_failure("node_offline", reason=f"connection_refused: {msg}")
        if "timeout" in exc_str or "timed out" in exc_str:
            return _build_failure("backend_timeout", reason=f"timeout: {msg}")
        if "connection" in exc_str and ("reset" in exc_str or "aborted" in exc_str):
            return _build_failure("backend_connection_error", reason=f"connection_reset: {msg}")
        if "unloaded" in exc_str:
            return _build_failure("model_not_loaded", reason=f"model_unloaded: {msg}")
        if "model" in exc_str and ("not found" in exc_str or "no model" in exc_str):
            return _build_failure("model_not_available_on_node", reason=f"model_missing: {msg}")
        return _build_failure("unknown_backend_error", reason=msg[:200])

    # Response-based classification
    if response_status == 429:
        return _build_failure("rate_limited", reason="rate_limit_exceeded")
    if response_status == 413:
        return _build_failure("context_overflow", reason="request_too_large")
    if response_status and 500 <= response_status < 600:
        return _build_failure("http_5xx", reason=f"http_{response_status}: {msg[:200]}")

    # Model-specific error messages
    if "unloaded" in msg_lower or "no models loaded" in msg_lower:
        return _build_failure("model_not_loaded", reason=f"model_unloaded: {msg[:200]}")
    if "invalid model" in msg_lower or "model not found" in msg_lower:
        return _build_failure("model_not_available_on_node", reason=f"model_missing: {msg[:200]}")
    if "context" in msg_lower and ("exceed" in msg_lower or "too long" in msg_lower or "overflow" in msg_lower):
        return _build_failure("context_overflow", reason=f"context_overflow: {msg[:200]}")
    if "rate" in msg_lower and ("limit" in msg_lower or "throttl" in msg_lower):
        return _build_failure("rate_limited", reason=f"rate_limited: {msg[:200]}")

    return _build_failure("unknown_backend_error", reason=msg[:200])


def _build_failure(failure_type: str, reason: str = "") -> dict[str, Any]:
    cls = FAILURE_CLASSES.get(failure_type, FAILURE_CLASSES["unknown_backend_error"])
    return {
        "failure_type": failure_type,
        "retryable": cls["retryable"],
        "fallback_allowed": cls["fallback_allowed"],
        "requires_same_model": cls["requires_same_model"],
        "safe_degrade_allowed": cls["safe_degrade_allowed"],
        "confidence": cls["confidence"],
        "reason": reason,
    }


# ── Fallback candidate building ──────────────────────────────────────────

def build_fallback_candidates(
    requested_model: str,
    failed_node_id: str | None = None,
    registry: list | None = None,
) -> list[dict[str, Any]]:
    """Build ordered fallback candidates respecting capability constraints.

    Returns list of dicts with keys:
        node_id, url, model (the model ID to use on that node),
        same_model (bool), capability_match (bool), reason (str)
    """
    candidates: list[dict[str, Any]] = []
    if registry is None:
        try:
            from runtime.state.dynamic_node_registry import build_node_registry
            registry = build_node_registry()
        except Exception:
            registry = []

    is_vision = _model_requires_vision(requested_model)
    is_large_context = _model_requires_large_context(requested_model)
    is_coding = _model_is_coding(requested_model)
    is_reasoning = _model_is_reasoning(requested_model)

    for entry in registry:
        node_id = entry.node_id if hasattr(entry, "node_id") else entry.get("node_id", "")
        if not node_id or node_id == failed_node_id:
            continue

        status = entry.status if hasattr(entry, "status") else entry.get("status", "unknown")
        fallback_eligible = (
            entry.fallback_eligible if hasattr(entry, "fallback_eligible")
            else entry.get("fallback_eligible", False)
        )
        if status != "online" or not fallback_eligible:
            continue

        url = ""
        try:
            from runtime.router.multi_node_routing import BACKEND_URLS
            url = BACKEND_URLS.get(node_id, f"http://{entry.ip}:1234/v1" if hasattr(entry, "ip") else "")
        except Exception:
            url = f"http://{entry.ip}:1234/v1" if hasattr(entry, "ip") else ""

        # Collect models on this node
        node_models: list[str] = []
        models_list = entry.models if hasattr(entry, "models") else entry.get("models", [])
        for m in models_list:
            mid = m.id if hasattr(m, "id") else (m.get("id") if isinstance(m, dict) else str(m))
            if mid:
                node_models.append(mid)

        # Check for exact same model
        same_model = requested_model in node_models

        # Check for equivalent model (canonical mapping)
        equivalent_model = ""
        if not same_model:
            try:
                from runtime.router.multi_node_routing import normalize_model_for_backend
                normalized = normalize_model_for_backend(requested_model, node_id)
                if normalized and normalized != requested_model and normalized in node_models:
                    equivalent_model = normalized
            except Exception:
                pass

        model_to_use = requested_model if same_model else (equivalent_model if equivalent_model else "")

        # Check capability match
        capability_match = True
        if is_vision:
            capability_match = _node_has_capability(entry, "vision")
        elif is_large_context:
            capability_match = _node_has_capability(entry, "large-context")
        elif is_coding:
            capability_match = _node_has_capability(entry, "coding")
        elif is_reasoning:
            capability_match = _node_has_capability(entry, "reasoning")

        # Determine reason
        if same_model:
            reason = f"same_model_available_on_{node_id}"
        elif equivalent_model:
            reason = f"equivalent_model_{equivalent_model}_on_{node_id}"
        elif capability_match:
            reason = f"capability_match_on_{node_id}"
        else:
            reason = f"no_model_match_on_{node_id}"

        candidates.append({
            "node_id": node_id,
            "url": url,
            "model": model_to_use or requested_model,
            "same_model": same_model,
            "equivalent_model": equivalent_model,
            "capability_match": capability_match,
            "reason": reason,
        })

    # Sort: same_model first, then equivalent, then capability_match
    candidates.sort(key=lambda c: (
        0 if c["same_model"] else (1 if c["equivalent_model"] else (2 if c["capability_match"] else 3)),
    ))
    return candidates


# ── Candidate selection ──────────────────────────────────────────────────

def select_fallback_candidate(
    candidates: list[dict[str, Any]],
    requested_model: str,
) -> dict[str, Any] | None:
    """Select the best fallback candidate applying policy rules.

    Rules:
    1. Same model on another online node → use it
    2. Equivalent alias exists → use it
    3. Vision model → only vision-capable fallback
    4. Large-context model → only large-context-capable fallback
    5. Coding model → prefer coding-capable fallback
    6. Reasoning model → prefer reasoning-capable fallback
    7. No safe fallback → None (caller returns capacity_unavailable)
    8. Never fallback vision → text-only silently
    9. Never fallback large-context → small-context silently
    10. Always record fallback reason
    """
    if not candidates:
        return None

    is_vision = _model_requires_vision(requested_model)
    is_large_context = _model_requires_large_context(requested_model)

    for c in candidates:
        # Rule 1: same model
        if c["same_model"]:
            return c
        # Rule 2: equivalent model
        if c["equivalent_model"]:
            return c
        # Rule 3+4: capability check
        if is_vision or is_large_context:
            if not c["capability_match"]:
                continue
            return c
        # Rule 5+6: prefer capability match
        if c["capability_match"]:
            return c

    # Last resort: if no capability match but fallback is safe (non-vision, non-large-context)
    if not is_vision and not is_large_context:
        for c in candidates:
            if not c["capability_match"]:
                candidates_available = c
                break
        else:
            return None
        return candidates[0]

    return None


# ── Error response builder ──────────────────────────────────────────────

def build_capacity_unavailable_error(
    requested_model: str,
    failed_node_id: str | None = None,
    failure_type: str = "unknown_backend_error",
    detail: str = "",
) -> dict[str, Any]:
    """Build a clear capacity_unavailable error response."""
    return {
        "error": "capacity_unavailable",
        "detail": (
            f"Model '{requested_model}' failed on "
            f"{failed_node_id or 'preferred node'} ({failure_type}) "
            f"with no safe fallback available."
        ),
        "original_error": detail[:500] if detail else None,
    }
