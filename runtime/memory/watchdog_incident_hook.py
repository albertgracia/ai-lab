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


def _build(payload_kwargs: dict) -> dict | None:
    """Build a governed incident payload using schema builder.

    Fallback: returns None if schema builder is unavailable.
    """
    try:
        from runtime.incidents.incident_schema import build_incident
        return build_incident(**payload_kwargs)
    except Exception:
        return None


def _try_store(payload: dict) -> bool:
    try:
        from runtime.memory.qdrant_store import store_embedding
        return store_embedding("incidents", payload)
    except ImportError:
        return False
    except Exception:
        return False


def _record_metrics_skipped(event_type: str) -> None:
    try:
        from runtime.telemetry.prometheus_metrics import INCIDENT_DEDUP_SKIPPED_TOTAL
        INCIDENT_DEDUP_SKIPPED_TOTAL.labels(event_type=event_type).inc()
    except Exception:
        pass


def _record_metrics_new(event_type: str) -> None:
    try:
        from runtime.telemetry.prometheus_metrics import INCIDENT_DEDUP_NEW_TOTAL
        INCIDENT_DEDUP_NEW_TOTAL.labels(event_type=event_type).inc()
    except Exception:
        pass


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
            sev = "critical" if status == "critical" else "warning"
            base = dict(event_type="service_down", severity=sev, source="watchdog",
                        timestamp=timestamp, message=f"Service '{service}' is unreachable",
                        service=service, status="down", resolved=False)
            governed = _build(base)
            incident = governed if governed else {
                "event_type": "service_down", "severity": sev, "service": service,
                "status": "down", "message": f"Service '{service}' is unreachable",
                "timestamp": timestamp, "schema_version": INCIDENT_SCHEMA_VERSION,
                "source": "watchdog", "resolved": False,
            }
            if _try_store(incident):
                stored.append(incident)

        if prev_ok and not is_ok:
            base = dict(event_type="service_degraded", severity="warning", source="watchdog",
                        timestamp=timestamp,
                        message=f"Service '{service}' just went down (status={status})",
                        service=service, status="degraded", resolved=False)
            governed = _build(base)
            incident = governed if governed else {
                "event_type": "service_degraded", "severity": "warning", "service": service,
                "status": "degraded", "message": f"Service '{service}' just went down (status={status})",
                "timestamp": timestamp, "schema_version": INCIDENT_SCHEMA_VERSION,
                "source": "watchdog", "resolved": False,
            }
            if _try_store(incident):
                stored.append(incident)

        if not prev_ok and is_ok:
            base = dict(event_type="service_recovered", severity="info", source="watchdog",
                        timestamp=timestamp, message=f"Service '{service}' recovered",
                        service=service, status="recovered", resolved=True)
            governed = _build(base)
            incident = governed if governed else {
                "event_type": "service_recovered", "severity": "info", "service": service,
                "status": "recovered", "message": f"Service '{service}' recovered",
                "timestamp": timestamp, "schema_version": INCIDENT_SCHEMA_VERSION,
                "source": "watchdog", "resolved": True,
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
                _record_metrics_skipped("cluster_degraded")
                stored.append({"deduped": True, "dedup_key": dedup_result.get("dedup_key", "")})
            else:
                dedup_key = dedup_result.get("dedup_key", "")
                base = dict(event_type="cluster_degraded", severity=sev, source="watchdog",
                            timestamp=timestamp, message=msg, status=status,
                            resolved=False, dedup_key=dedup_key)
                governed = _build(base)
                incident = governed if governed else {
                    "event_type": "cluster_degraded", "severity": sev, "status": status,
                    "message": msg, "timestamp": timestamp,
                    "schema_version": INCIDENT_SCHEMA_VERSION, "source": "watchdog",
                    "resolved": False, "dedup_key": dedup_key,
                    "first_seen_at": timestamp, "last_seen_at": timestamp, "duplicate_count": 0,
                }
                if _try_store(incident):
                    _record_metrics_new("cluster_degraded")
                    stored.append(incident)
        except Exception:
            base = dict(event_type="cluster_degraded", severity=sev, source="watchdog",
                        timestamp=timestamp, message=msg, status=status, resolved=False)
            governed = _build(base)
            incident = governed if governed else {
                "event_type": "cluster_degraded", "severity": sev, "status": status,
                "message": msg, "timestamp": timestamp,
                "schema_version": INCIDENT_SCHEMA_VERSION, "source": "watchdog", "resolved": False,
            }
            if _try_store(incident):
                stored.append(incident)

    return stored


def record_node_incident(node: str, host: str, event: str, message: str,
                         severity: str = "warning") -> bool:
    """Record a node-level incident manually."""
    is_resolved = event in ("node_recovered", "service_recovered")
    base = dict(event_type=event, severity=severity, source="manual",
                timestamp=int(time.time()), message=message,
                node=node, host=host, resolved=is_resolved)
    governed = _build(base)
    payload = governed if governed else {
        "event_type": event, "severity": severity, "node": node, "host": host,
        "message": message, "timestamp": int(time.time()),
        "schema_version": INCIDENT_SCHEMA_VERSION, "source": "manual",
        "resolved": is_resolved,
    }
    return _try_store(payload)
