"""FASE OBS-31A: Prometheus target audit and classification.

Audits scrape targets, classifies them into health categories,
and produces structured audit summaries aligned with runtime contracts.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PrometheusTargetStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    EXPECTED_OFFLINE = "expected_offline"
    STALE = "stale"
    ORPHAN = "orphan"
    DEPRECATED = "deprecated"
    UNKNOWN = "unknown"


# Known scrape targets documented in AGENTS.md / runtime infrastructure
_KNOWN_TARGETS: list[dict[str, Any]] = [
    {"job": "ai-lab-gateway", "endpoint": "192.168.1.30:8008/metrics", "role": "gateway", "expected_offline": False, "critical": True},
    {"job": "ai-lab-router", "endpoint": "192.168.1.30:8083/metrics", "role": "router", "expected_offline": False, "critical": False},
    {"job": "ai-lab-live-api", "endpoint": "192.168.1.30:8084/metrics", "role": "live-api", "expected_offline": False, "critical": False},
    {"job": "ai-lab-cadvisor", "endpoint": "192.168.1.30:8081", "role": "container", "expected_offline": False, "critical": False},
    {"job": "ai-lab-node", "endpoint": "192.168.1.30:9100", "role": "host", "expected_offline": False, "critical": False},
    {"job": "ai-lab-gpu-rx9070", "endpoint": "192.168.1.50:9182", "role": "gpu", "expected_offline": False, "critical": True},
    {"job": "ai-lab-gpu-metrics", "endpoint": "192.168.1.50:9183", "role": "gpu-compute", "expected_offline": False, "critical": True},
    {"job": "ai-lab-gpu-rx7900xt", "endpoint": "192.168.1.60:9182", "role": "gpu", "expected_offline": True, "critical": False},
    {"job": "ai-lab-gpu-metrics-rx7900xt", "endpoint": "192.168.1.60:9183", "role": "gpu-compute", "expected_offline": True, "critical": False},
    {"job": "cloudflare-tunnel", "endpoint": "cloudflare-tunnel:2000", "role": "tunnel", "expected_offline": False, "critical": False},
]


@dataclass
class TargetAuditEntry:
    job: str = ""
    endpoint: str = ""
    role: str = ""
    status: str = PrometheusTargetStatus.UNKNOWN.value
    expected_offline: bool = False
    critical: bool = False
    last_scrape_duration_ms: float = 0.0
    scrape_interval_seconds: int = 15
    error_message: str | None = None
    labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job": self.job,
            "endpoint": self.endpoint,
            "role": self.role,
            "status": self.status,
            "expected_offline": self.expected_offline,
            "critical": self.critical,
            "last_scrape_duration_ms": round(self.last_scrape_duration_ms, 1),
            "scrape_interval_seconds": self.scrape_interval_seconds,
            "error_message": self.error_message,
            "labels": self.labels,
        }


def classify_scrape_target(
    target: dict[str, Any],
    is_up: bool | None = None,
    scrape_duration_ms: float = 0.0,
    scrape_interval_seconds: int = 15,
    error: str | None = None,
) -> TargetAuditEntry:
    entry = TargetAuditEntry(
        job=target.get("job", "unknown"),
        endpoint=target.get("endpoint", ""),
        role=target.get("role", "unknown"),
        expected_offline=target.get("expected_offline", False),
        critical=target.get("critical", False),
        last_scrape_duration_ms=scrape_duration_ms,
        scrape_interval_seconds=scrape_interval_seconds,
        error_message=error,
    )

    if target.get("expected_offline", False):
        entry.status = PrometheusTargetStatus.EXPECTED_OFFLINE.value
        return entry

    if is_up is None or error:
        entry.status = PrometheusTargetStatus.STALE.value
        return entry

    if not is_up:
        entry.status = PrometheusTargetStatus.DEGRADED.value
        return entry

    if scrape_duration_ms > (scrape_interval_seconds * 1000 * 0.8):
        entry.status = PrometheusTargetStatus.DEGRADED.value
        return entry

    entry.status = PrometheusTargetStatus.HEALTHY.value
    return entry


def audit_prometheus_targets(
    up_map: dict[str, bool] | None = None,
    duration_map: dict[str, float] | None = None,
    error_map: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    up_map = up_map or {}
    duration_map = duration_map or {}
    error_map = error_map or {}

    for target in _KNOWN_TARGETS:
        job = target.get("job", "")
        is_up = up_map.get(job)
        duration = duration_map.get(job, 0.0)
        error = error_map.get(job)
        entry = classify_scrape_target(target, is_up, duration, error=error)
        results.append(entry.to_dict())

    return results


def build_prometheus_audit_summary(
    target_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if target_results is None:
        target_results = audit_prometheus_targets()

    counts: dict[str, int] = {}
    for r in target_results:
        status = r.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1

    critical_healthy = sum(
        1 for r in target_results
        if r.get("critical") and r.get("status") == "healthy"
    )
    critical_total = sum(1 for r in target_results if r.get("critical"))
    alignment_pct = round((critical_healthy / critical_total * 100) if critical_total else 100, 1)

    return {
        "contract_version": "OBS-31A",
        "timestamp": time.time(),
        "total_targets": len(target_results),
        "classification": {
            "healthy": counts.get("healthy", 0),
            "degraded": counts.get("degraded", 0),
            "expected_offline": counts.get("expected_offline", 0),
            "stale": counts.get("stale", 0),
            "orphan": counts.get("orphan", 0),
            "deprecated": counts.get("deprecated", 0),
            "unknown": counts.get("unknown", 0),
        },
        "critical_targets": {
            "healthy": critical_healthy,
            "total": critical_total,
            "alignment_pct": alignment_pct,
        },
        "targets": target_results,
    }
