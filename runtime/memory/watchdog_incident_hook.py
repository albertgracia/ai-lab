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
        sev = "critical" if status == "critical" else "warning"
        msg = f"Cluster status is {status}"
        dedup_key = ""
        try:
            from runtime.incidents.incident_dedup import check_and_tag
            dedup_result = check_and_tag(
                event_type="cluster_degraded",
                source="watchdog",
                severity=sev,
                message=msg,
            )
            if dedup_result.get("deduped"):
                try:
                    from runtime.telemetry.prometheus_metrics import INCIDENT_DEDUP_SKIPPED_TOTAL
                    INCIDENT_DEDUP_SKIPPED_TOTAL.labels(event_type="cluster_degraded").inc()
                except Exception:
                    pass
                stored.append({"deduped": True, "dedup_key": dedup_result.get("dedup_key", "")})
            else:
                dedup_key = dedup_result.get("dedup_key", "")
                incident = {
                    "event_type": "cluster_degraded",
                    "severity": sev,
                    "status": status,
                    "message": msg,
                    "timestamp": timestamp,
                    "schema_version": INCIDENT_SCHEMA_VERSION,
                    "source": "watchdog",
                    "resolved": False,
                    "dedup_key": dedup_key,
                    "first_seen_at": timestamp,
                    "last_seen_at": timestamp,
                    "duplicate_count": 0,
                }
                if _try_store(incident):
                    try:
                        from runtime.telemetry.prometheus_metrics import INCIDENT_DEDUP_NEW_TOTAL
                        INCIDENT_DEDUP_NEW_TOTAL.labels(event_type="cluster_degraded").inc()
                    except Exception:
                        pass
                    stored.append(incident)
        except Exception:
            incident = {
                "event_type": "cluster_degraded",
                "severity": sev,
                "status": status,
                "message": msg,
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
