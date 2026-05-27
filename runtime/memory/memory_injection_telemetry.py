"""Memory injection telemetry — bounded, fail-safe measurement of context injection.

Captures before/after context state during inject_agent_context,
estimates token impact, and feeds data into cognitive_history Qdrant events
and routing_history records.

Fail-safe: all public functions catch exceptions and return safe defaults.
"""

import math
import time
from typing import Any

TELEMETRY_VERSION = "1.0"
MAX_PAYLOAD_CHARS = 50000
ESTIMATE_RATIO = 4.0


def estimate_tokens(text: str) -> int:
    """Bounded token estimation: ceil(chars / 4).

    Falls back to 0 on any error.
    """
    try:
        return math.ceil(len(text) / ESTIMATE_RATIO)
    except Exception:
        return 0


def estimate_messages_tokens(messages: list[dict] | None) -> int:
    """Estimate tokens from a list of message dicts.

    Concatenates all 'content' and 'role' values.
    """
    if not messages:
        return 0
    try:
        text = ""
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", "")
                content = msg.get("content", "")
                if isinstance(content, str):
                    text += role + " " + content + " "
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and isinstance(part.get("text"), str):
                            text += part["text"] + " "
        return estimate_tokens(text)
    except Exception:
        return 0


def messages_chars(messages: list[dict] | None) -> int:
    """Count total chars in message contents."""
    if not messages:
        return 0
    try:
        total = 0
        for msg in messages:
            if isinstance(msg, dict):
                content = msg.get("content", "")
                if isinstance(content, str):
                    total += len(content)
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and isinstance(part.get("text"), str):
                            total += len(part["text"])
        return total
    except Exception:
        return 0


def estimate_system_prompt_tokens(system_prompt: str | None) -> int:
    """Estimate tokens from a system prompt string."""
    if not system_prompt:
        return 0
    return estimate_tokens(system_prompt)


def build_telemetry(
    *,
    memory_injected: bool = False,
    chars_injected: int = 0,
    collections_used: list[str] | None = None,
    matches_total: int = 0,
    avg_score: float | None = None,
    max_score: float | None = None,
    min_score: float | None = None,
    recall_source: str | None = None,
    context_budget_chars: int | None = None,
    context_budget_used_chars: int | None = None,
    context_truncated: bool = False,
    prompt_tokens_before: int | None = None,
    prompt_tokens_after: int | None = None,
    route_family: str = "unknown",
    model: str = "unknown",
    node: str | None = None,
    latency_ms: float | None = None,
    ttfb_ms: float | None = None,
    success: bool = True,
    timeout: bool = False,
    error_type: str | None = None,
    request_id: str | None = None,
    decision_id: str | None = None,
) -> dict:
    """Build a bounded telemetry dict.

    All fields safe; no prompts or responses included.
    """
    telemetry = {
        "telemetry_version": TELEMETRY_VERSION,
        "timestamp": time.time(),
        "memory_injected": bool(memory_injected),
        "chars_injected": int(chars_injected),
        "estimated_tokens_injected": estimate_tokens(str(chars_injected)) if chars_injected else 0,
        "collections_used": collections_used or [],
        "matches_total": int(matches_total),
        "avg_score": float(avg_score) if avg_score is not None else None,
        "max_score": float(max_score) if max_score is not None else None,
        "min_score": float(min_score) if min_score is not None else None,
        "recall_source": str(recall_source) if recall_source else None,
        "context_budget_chars": int(context_budget_chars) if context_budget_chars is not None else None,
        "context_budget_used_chars": int(context_budget_used_chars) if context_budget_used_chars is not None else None,
        "context_truncated": bool(context_truncated),
        "prompt_tokens_before_memory": int(prompt_tokens_before) if prompt_tokens_before is not None else None,
        "prompt_tokens_after_memory": int(prompt_tokens_after) if prompt_tokens_after is not None else None,
        "prompt_tokens_delta": None,
        "route_family": str(route_family),
        "model": str(model),
        "node": str(node) if node else None,
        "latency_ms": float(latency_ms) if latency_ms is not None else None,
        "ttfb_ms": float(ttfb_ms) if ttfb_ms is not None else None,
        "success": bool(success),
        "timeout": bool(timeout),
        "error_type": str(error_type) if error_type else None,
        "request_id": str(request_id) if request_id else None,
        "decision_id": str(decision_id) if decision_id else None,
    }
    if prompt_tokens_before is not None and prompt_tokens_after is not None:
        delta = prompt_tokens_after - prompt_tokens_before
        telemetry["prompt_tokens_delta"] = max(0, int(delta))
    return telemetry


def build_cognitive_history_payload(
    telemetry: dict,
    task_type: str = "unknown",
    context_size: int = 0,
    shaping_latency_ms: float = 0.0,
) -> dict:
    """Build a cognitive_history-compatible payload from telemetry data.

    Extends the standard cognitive_history payload with memory injection fields.
    """
    payload = {
        "schema_version": "1.0",
        "event_type": "context_shaping",
        "timestamp": telemetry.get("timestamp", time.time()),
        "task_type": task_type,
        "model": telemetry.get("model", "unknown"),
        "context_size": context_size,
        "shaping_latency_ms": shaping_latency_ms,
        "memory_injected": telemetry.get("memory_injected", False),
        "chars_injected": telemetry.get("chars_injected", 0),
        "estimated_tokens_injected": telemetry.get("estimated_tokens_injected", 0),
        "collections_used": telemetry.get("collections_used", []),
        "matches_total": telemetry.get("matches_total", 0),
        "avg_score": telemetry.get("avg_score"),
        "max_score": telemetry.get("max_score"),
        "min_score": telemetry.get("min_score"),
        "recall_source": telemetry.get("recall_source"),
        "context_budget_chars": telemetry.get("context_budget_chars"),
        "context_budget_used_chars": telemetry.get("context_budget_used_chars"),
        "context_truncated": telemetry.get("context_truncated", False),
        "prompt_tokens_delta": telemetry.get("prompt_tokens_delta"),
        "route_family": telemetry.get("route_family", "unknown"),
    }
    return payload


# ── in-memory store (for summary endpoint, bounded) ──────────────────
_last_event: dict | None = None
_event_count: int = 0
_chars_total: int = 0
_tokens_total: int = 0
_matched_total: int = 0


def record_telemetry_event(telemetry: dict) -> None:
    """Record a telemetry event for the summary endpoint.

    Bounded: only stores last event + running totals.
    """
    global _last_event, _event_count, _chars_total, _tokens_total, _matched_total
    try:
        _last_event = telemetry
        _event_count += 1
        _chars_total += telemetry.get("chars_injected", 0) or 0
        _tokens_total += telemetry.get("estimated_tokens_injected", 0) or 0
        _matched_total += telemetry.get("matches_total", 0) or 0
    except Exception:
        pass


def get_telemetry_summary() -> dict:
    """Return bounded summary of all memory injection events."""
    return {
        "telemetry_version": TELEMETRY_VERSION,
        "events_total": _event_count,
        "chars_injected_total": _chars_total,
        "estimated_tokens_injected_total": _tokens_total,
        "matches_total": _matched_total,
        "last_event": _last_event,
    }
