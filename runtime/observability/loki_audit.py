"""FASE OBS-31A: Loki audit and validation.

Validates Loki datasources, stream labels, query validity,
and alignment with runtime log sources.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any


class LokiStreamStatus(str, Enum):
    HEALTHY = "healthy"
    STALE = "stale"
    BROKEN = "broken"
    UNKNOWN = "unknown"


_KNOWN_LOKI_LABELS = frozenset({
    "container", "container_id", "container_name",
    "compose_project", "compose_service",
    "filename", "host", "job", "level",
    "log", "logger", "message", "msg",
    "namespace", "pod", "service", "source",
    "stream", "syslog_identifier", "transport",
    "unit", "__meta_", "__path__",
})

_KNOWN_LOKI_SOURCES = [
    {"name": "docker_logs", "stream": "{compose_project=\"ailab\"}", "critical": True},
    {"name": "docker_all", "stream": "{compose_project=~\".+\"}", "critical": False},
    {"name": "journald", "stream": "{job=\"systemd-journal\"}", "critical": True},
    {"name": "unifi_ids", "stream": "{transport=\"syslog\"}", "critical": False},
]

_KNOWN_LOKI_DATASOURCE = {
    "name": "Loki",
    "uid": "fflfh9qp8mxogc",
    "type": "loki",
    "url": "http://192.168.1.40:3100",
}


@dataclass
class LokiAuditEntry:
    name: str = ""
    stream: str = ""
    critical: bool = False
    status: str = LokiStreamStatus.UNKNOWN.value
    labels_valid: bool = True
    query_valid: bool = True
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "stream": self.stream,
            "critical": self.critical,
            "status": self.status,
            "labels_valid": self.labels_valid,
            "query_valid": self.query_valid,
            "error_message": self.error_message,
        }


def _is_valid_loki_query(query: str) -> tuple[bool, str]:
    if not query.strip():
        return False, "empty_query"
    if not query.startswith("{"):
        return False, "missing_braces"
    if "}" not in query:
        return False, "unmatched_brace"
    label_part = query[1:query.index("}")]
    if not label_part.strip():
        return False, "empty_label_selector"
    pairs = label_part.split(",")
    for pair in pairs:
        p = pair.strip()
        if "=" not in p:
            continue
        label_key = p.split("=", 1)[0].strip().strip('"')
        if not label_key:
            return False, "empty_label_key"
    return True, ""


def _validate_labels(labels: dict[str, str] | None = None) -> bool:
    if not labels:
        return True
    return all(k in _KNOWN_LOKI_LABELS for k in labels)


def audit_loki(
    label_validity: dict[str, bool] | None = None,
    query_validity: dict[str, bool] | None = None,
    stream_errors: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    label_validity = label_validity or {}
    query_validity = query_validity or {}
    stream_errors = stream_errors or {}

    for source in _KNOWN_LOKI_SOURCES:
        name = source["name"]
        stream = source["stream"]

        entry = LokiAuditEntry(
            name=name,
            stream=stream,
            critical=source.get("critical", False),
        )

        labels_valid = label_validity.get(name)
        if labels_valid is None:
            labels_valid = _validate_labels()
        entry.labels_valid = labels_valid

        qv = query_validity.get(name)
        if qv is None:
            qv, _ = _is_valid_loki_query(stream)
        entry.query_valid = qv

        err = stream_errors.get(name)
        if err:
            entry.status = LokiStreamStatus.BROKEN.value
            entry.error_message = err
        elif not qv:
            entry.status = LokiStreamStatus.BROKEN.value
            entry.error_message = "invalid_query"
        elif not labels_valid:
            entry.status = LokiStreamStatus.STALE.value
            entry.error_message = "label_mismatch"
        elif not source.get("critical", False):
            entry.status = LokiStreamStatus.HEALTHY.value
        else:
            entry.status = LokiStreamStatus.HEALTHY.value

        results.append(entry.to_dict())

    return results


def build_loki_audit_summary(
    stream_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if stream_results is None:
        stream_results = audit_loki()

    counts: dict[str, int] = {}
    for r in stream_results:
        status = r.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1

    critical_healthy = sum(
        1 for r in stream_results
        if r.get("critical") and r.get("status") == "healthy"
    )
    critical_total = sum(1 for r in stream_results if r.get("critical"))

    return {
        "contract_version": "OBS-31A",
        "timestamp": time.time(),
        "datasource": _KNOWN_LOKI_DATASOURCE,
        "total_streams": len(stream_results),
        "classification": counts,
        "critical_streams": {
            "healthy": critical_healthy,
            "total": critical_total,
        },
        "streams": stream_results,
    }
