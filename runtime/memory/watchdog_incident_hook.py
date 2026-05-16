"""Watchdog Incident Hook — records runtime incidents to Qdrant.

Called automatically by the watchdog or Live API when:
  - A service check fails (gateway, router, live_api, docs)
  - Docker is down
  - GPU telemetry is offline
  - Node goes offline/backoff

Usage:
    from runtime.memory.watchdog_incident_hook import record_watchdog_incident
    record_watchdog_incident(watchdog_result)
"""

import time

INCIDENT_SCHEMA_VERSION = "1.0"

# Track previous check states to detect transitions
_previous_checks: dict[str, bool] = {}


def _try_store(payload: dict) -> bool:
    try:
        from runtime.memory.qdrant_store import store_embedding
        return store_embedding("incidents", payload)
    except ImportError:
        return False
    except Exception:
        return False


def record_watchdog_incident(watchdog_result: dict) -> list[dict]:
    """Record incidents from a watchdog check run.

    Args:
        watchdog_result: output of runtime_watchdog.run_watchdog()

    Returns:
        List of incident records that were stored
    """
    global _previous_checks

    status = watchdog_result.get("status", "good")
    checks = watchdog_result.get("checks", {})
    timestamp = watchdog_result.get("timestamp", int(time.time()))
    stored = []

    for service, is_ok in checks.items():
        prev_ok = _previous_checks.get(service, True)

        if not is_ok:
            severity = "critical" if status == "critical" else "warning"
            incident = {
                "event_type": "service_down",
                "severity": severity,
                "service": service,
                "status": "down",
                "message": f"Service '{service}' is unreachable",
                "timestamp": timestamp,
                "schema_version": INCIDENT_SCHEMA_VERSION,
                "source": "watchdog",
                "resolved": False,
            }
            if _try_store(incident):
                stored.append(incident)

        if prev_ok and not is_ok:
            incident = {
                "event_type": "service_degraded",
                "severity": "warning",
                "service": service,
                "status": "degraded",
                "message": f"Service '{service}' just went down (status={status})",
                "timestamp": timestamp,
                "schema_version": INCIDENT_SCHEMA_VERSION,
                "source": "watchdog",
                "resolved": False,
            }
            if _try_store(incident):
                stored.append(incident)

        if not prev_ok and is_ok:
            incident = {
                "event_type": "service_recovered",
                "severity": "info",
                "service": service,
                "status": "recovered",
                "message": f"Service '{service}' recovered",
                "timestamp": timestamp,
                "schema_version": INCIDENT_SCHEMA_VERSION,
                "source": "watchdog",
                "resolved": True,
            }
            if _try_store(incident):
                stored.append(incident)

        _previous_checks[service] = is_ok

    if status in ("degraded", "critical"):
        incident = {
            "event_type": "cluster_degraded",
            "severity": "critical" if status == "critical" else "warning",
            "status": status,
            "message": f"Cluster status is {status}",
            "timestamp": timestamp,
            "schema_version": INCIDENT_SCHEMA_VERSION,
            "source": "watchdog",
            "resolved": False,
        }
        if _try_store(incident):
            stored.append(incident)

    return stored


def record_node_incident(node: str, host: str, event: str, message: str,
                         severity: str = "warning") -> bool:
    """Record a node-level incident manually.

    Args:
        node: node name
        host: node host/IP
        event: event_type (node_offline, node_recovered, etc.)
        message: human-readable description
        severity: critical/warning/info
    """
    payload = {
        "event_type": event,
        "severity": severity,
        "node": node,
        "host": host,
        "message": message,
        "timestamp": int(time.time()),
        "schema_version": INCIDENT_SCHEMA_VERSION,
        "source": "manual",
        "resolved": event in ("node_recovered", "service_recovered"),
    }
    return _try_store(payload)
