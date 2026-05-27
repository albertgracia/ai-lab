"""Qdrant hook for routing events.

Called from routing_history.py via try/except ImportError.
Embeds and stores each routing event asynchronously.
"""

import time

try:
    from runtime.memory.qdrant_store import store_operational_embedding, get_embedding
    from runtime.memory.qdrant_collections import event_type_for, validate_payload
    _HAVE_QDRANT = True
except ImportError:
    _HAVE_QDRANT = False
    store_operational_embedding = None
    event_type_for = None
    validate_payload = None


def on_routing_event(event_data: dict) -> None:
    """Hook: called after each routing event is recorded to JSONL.

    Stores embedding in Qdrant routing_history collection.
    Non-blocking: failures caught and ignored.
    """
    if not _HAVE_QDRANT:
        return
    try:
        payload = {
            "schema_version": "1.0",
            "event_type": event_type_for("routing_history", "routing"),
            "timestamp": event_data.get("timestamp", time.time()),
            "task_type": event_data.get("task_type", "unknown"),
            "model": event_data.get("model", "unknown"),
            "node": event_data.get("node", "unknown"),
            "host": event_data.get("host", "unknown"),
            "latency_ms": event_data.get("latency_ms", 0),
            "success": event_data.get("success", False),
            "stream": event_data.get("stream", False),
            "failover": event_data.get("failover", False),
            "error": event_data.get("error"),
        }
        store_operational_embedding("routing_history", payload)
    except Exception:
        pass


def on_cognitive_event(event_data: dict) -> None:
    """Hook: called after each cognitive snapshot.

    Stores embedding in Qdrant cognitive_history collection.
    Includes memory injection telemetry fields when available.
    """
    if not _HAVE_QDRANT:
        return
    try:
        payload = {
            "schema_version": "1.0",
            "event_type": event_type_for("cognitive_history", "context_shaping"),
            "timestamp": event_data.get("timestamp", time.time()),
            "task_type": event_data.get("task_type", "unknown"),
            "model": event_data.get("model", "unknown"),
            "context_size": event_data.get("context_size", 0),
            "budget_used": event_data.get("budget_used", 0),
            "shaping_latency_ms": event_data.get("shaping_latency_ms", 0),
            "files_used": event_data.get("files_used", 0),
            "files_used_names": event_data.get("files_used_names", []),
            "working_memory_used": event_data.get("working_memory_used", False),
            "memory_injected": event_data.get("memory_injected", False),
            "chars_injected": event_data.get("chars_injected", 0),
            "estimated_tokens_injected": event_data.get("estimated_tokens_injected", 0),
            "collections_used": event_data.get("collections_used", []),
            "matches_total": event_data.get("matches_total", 0),
            "avg_score": event_data.get("avg_score"),
            "max_score": event_data.get("max_score"),
            "min_score": event_data.get("min_score"),
            "recall_source": event_data.get("recall_source"),
            "context_budget_chars": event_data.get("context_budget_chars"),
            "context_budget_used_chars": event_data.get("context_budget_used_chars"),
            "context_truncated": event_data.get("context_truncated", False),
            "prompt_tokens_delta": event_data.get("prompt_tokens_delta"),
            "route_family": event_data.get("route_family", "unknown"),
        }
        store_operational_embedding("cognitive_history", payload)
    except Exception:
        pass
