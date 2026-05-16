"""Qdrant collection schemas and initialization.

Defines the 6 cognitive collections with schemas, retention policies,
and event_type constraints. Called at router startup via
try/except ImportError.
"""

import time

# ── collection schemas (for documentation / validation) ──────────────

SCHEMA_VERSION = "1.0"

COLLECTION_SCHEMAS = {
    "routing_history": {
        "description": "Routing decisions with embeddings for semantic recall",
        "event_types": ["routing_success", "routing_failover", "routing_error"],
        "required_fields": [
            "schema_version", "event_type", "timestamp", "task_type",
            "model", "node", "host", "latency_ms", "success",
        ],
        "optional_fields": ["stream", "failover", "error", "session_id"],
    },
    "cognitive_history": {
        "description": "Context shaping snapshots for cognitive recall",
        "event_types": ["context_shaping", "budget_truncation", "memory_digest"],
        "required_fields": [
            "schema_version", "event_type", "timestamp", "task_type",
            "model", "context_size", "budget_used",
        ],
        "optional_fields": [
            "shaping_latency_ms", "files_used", "files_used_names",
            "working_memory_used",
        ],
    },
    "optimizer_history": {
        "description": "Adaptive runtime optimizer actions",
        "event_types": [
            "weight_adjustment", "policy_change", "snapshot_restore",
            "pending_review", "approved_action",
        ],
        "required_fields": [
            "schema_version", "event_type", "timestamp", "action",
            "previous_value", "new_value",
        ],
        "optional_fields": ["reason", "approved_by", "rollback_id"],
    },
    "incidents": {
        "description": "Watchdog failures, upstream errors, node offline events",
        "event_types": [
            "watchdog_failure", "502_upstream_error", "node_offline",
            "failover_triggered", "degraded_performance",
        ],
        "required_fields": [
            "schema_version", "event_type", "timestamp", "severity", "message",
        ],
        "optional_fields": ["node", "resolved", "resolution_timestamp", "error_code"],
    },
    "runtime_snapshots": {
        "description": "Periodic full-state captures for temporal recall",
        "event_types": ["periodic_snapshot", "pre_action_snapshot", "post_action_snapshot"],
        "required_fields": [
            "schema_version", "event_type", "timestamp", "state_json",
        ],
        "optional_fields": ["trigger", "action_id"],
    },
    "working_memory": {
        "description": "Persistent session working memory across restarts",
        "event_types": ["session_start", "session_turn", "session_end"],
        "required_fields": [
            "schema_version", "event_type", "timestamp", "session_id",
        ],
        "optional_fields": ["task", "digest", "context_aging"],
    },
}


def validate_payload(collection: str, payload: dict) -> list[str]:
    """Validate a payload against its collection schema.

    Returns a list of missing required fields (empty = valid).
    """
    schema = COLLECTION_SCHEMAS.get(collection)
    if not schema:
        return [f"Unknown collection: {collection}"]
    missing = []
    for field in schema["required_fields"]:
        if field not in payload:
            missing.append(field)
    # Ensure schema_version
    payload["schema_version"] = SCHEMA_VERSION
    return missing


def event_type_for(collection: str, category: str) -> str:
    """Map a rough category to a valid event_type for the collection.

    Falls back to the first event_type in the schema.
    """
    schema = COLLECTION_SCHEMAS.get(collection)
    if not schema:
        return "unknown"
    types = schema["event_types"]
    for t in types:
        if category in t:
            return t
    return types[0] if types else "unknown"
