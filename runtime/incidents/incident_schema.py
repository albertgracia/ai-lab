"""Incident governance schema builder for watchdog events.

Provides deterministic schema defaults and retention classification
for new incidents. Does NOT modify historical Qdrant data.
"""

import time
import uuid

SCHEMA_VERSION = "INCIDENTS-GOVERNANCE-SCHEMA-01"

RESOLUTION_STATUS_DEFAULT = "open"

RESOLUTION_STATUSES = frozenset({
    "open", "investigating", "mitigated", "resolved",
    "archived", "archived_duplicate", "false_positive", "obsolete",
})

RETENTION_CLASS_MAP = {
    "cluster_degraded": "degraded_signal",
    "service_degraded": "degraded_signal",
    "service_down": "down_signal",
    "service_recovered": "recovered_signal",
    "routing_error": "routing_error",
    "node_failure": "critical_keep",
    "high_latency": "operational_signal",
}

DEFAULT_RETENTION = "operational_signal"


def _generate_incident_id() -> str:
    return f"WD-{uuid.uuid4().hex[:12].upper()}"


def retention_class_for(event_type: str, severity: str = "") -> str:
    if severity == "critical":
        return "critical_keep"
    return RETENTION_CLASS_MAP.get(event_type, DEFAULT_RETENTION)


def build_incident(
    *,
    event_type: str,
    severity: str,
    message: str,
    source: str = "watchdog",
    timestamp: float | None = None,
    service: str = "",
    node: str = "",
    host: str = "",
    status: str = "",
    resolved: bool | None = None,
    dedup_key: str = "",
    schema_version: str = SCHEMA_VERSION,
) -> dict:
    """Build a governed incident payload with defaults.

    All fields safe; no prompts or responses included.
    Compatible with existing payload structure.
    """
    ts = timestamp if timestamp else time.time()
    sev = severity or "warning"
    is_critical = sev == "critical"

    retention = retention_class_for(event_type, sev)
    is_resolved = resolved if resolved is not None else False

    payload = {
        "incident_id": _generate_incident_id(),
        "schema_version": schema_version,
        "event_type": event_type,
        "timestamp": ts,
        "severity": sev,
        "source": source,
        "message": str(message)[:500],
        "resolved": is_resolved,
        "resolution_status": "resolved" if is_resolved else RESOLUTION_STATUS_DEFAULT,
        "retention_class": retention,
        "archived": False,
        "duplicate_count": 0,
        "first_seen_at": ts,
        "last_seen_at": ts,
        "affected_component": service or node or "",
    }

    if dedup_key:
        payload["dedup_key"] = dedup_key

    if service:
        payload["service"] = service
    if status:
        payload["status"] = status
    if node:
        payload["node"] = node
    if host:
        payload["host"] = host

    return payload
