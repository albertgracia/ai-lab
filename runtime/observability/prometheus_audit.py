"""FASE OBS-31A.1: Prometheus Authority Audit.

Prometheus is source_of_truth for runtime telemetry.
Grafana only visualizes.
No data is NOT OK unless expected_offline or inventory_only.

Validates:
- targets up/down via live Prometheus API
- expected_offline vs unexpected_down
- scrape freshness
- duplicate targets
- label consistency
- critical ailab_* metric presence

Backward compatible with OBS-31A callers.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError


PROMETHEUS_AUDIT_CONTRACT_VERSION = "OBS-31A.1"
_PROMETHEUS_DEFAULT_URL = "http://192.168.1.40:9090"
_PROMETHEUS_TIMEOUT = 5

_CRITICAL_METRICS = frozenset({
    "ailab_requests_total",
    "ailab_first_token_latency_ms_count",
    "ailab_route_family_total",
    "ailab_slo_state",
    "ailab_degradation_level",
    "ailab_stream_chunks_total",
    "ailab_stream_finish_inconsistent_total",
    "ailab_hallucination_risk_count",
    "ailab_profile_total",
    "ailab_gpu_active_requests",
})


class TargetHealth(str, Enum):
    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


class PrometheusTargetStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    EXPECTED_OFFLINE = "expected_offline"
    UNEXPECTED_DOWN = "unexpected_down"
    STALE = "stale"
    ORPHAN = "orphan"
    DEPRECATED = "deprecated"
    UNKNOWN = "unknown"


class FreshnessLevel(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    AGED = "aged"
    UNKNOWN = "unknown"


class LabelSeverity(str, Enum):
    OK = "ok"
    MISSING = "missing"
    MISMATCH = "mismatch"


# ── Known target inventory ──

_KNOWN_TARGETS: list[dict[str, Any]] = [
    {"job": "ai-lab-gateway", "endpoint": "192.168.1.30:8008/metrics",
     "instances": ["192.168.1.30:8008"], "role": "gateway",
     "expected_offline": False, "critical": True,
     "expected_labels": {"cluster": "ai-lab", "env": "homelab"}},
    {"job": "ai-lab-router", "endpoint": "192.168.1.30:8083/metrics",
     "instances": ["192.168.1.30:8083"], "role": "router",
     "expected_offline": False, "critical": False,
     "expected_labels": {"cluster": "ai-lab", "env": "homelab"}},
    {"job": "ai-lab-live-api", "endpoint": "192.168.1.30:8084/metrics",
     "instances": ["192.168.1.30:8084"], "role": "live-api",
     "expected_offline": False, "critical": False,
     "expected_labels": {"cluster": "ai-lab", "env": "homelab"}},
    {"job": "ai-lab-cadvisor", "endpoint": "192.168.1.30:8081",
     "instances": ["192.168.1.30:8081"], "role": "containers",
     "expected_offline": False, "critical": False,
     "expected_labels": {"cluster": "ai-lab", "env": "homelab"}},
    {"job": "ai-lab-node", "endpoint": "192.168.1.30:9100",
     "instances": ["192.168.1.30:9100"], "role": "host",
     "expected_offline": False, "critical": False,
     "expected_labels": {"cluster": "ai-lab", "env": "homelab"}},
    {"job": "ai-lab-gpu-rx9070", "endpoint": "192.168.1.50:9182",
     "instances": ["192.168.1.50:9182"], "role": "gpu",
     "expected_offline": False, "critical": True,
     "expected_labels": {"cluster": "ai-lab", "env": "homelab", "gpu": "rx9070"}},
    {"job": "ai-lab-gpu-rx7900xt", "endpoint": "192.168.1.60:9182",
     "instances": ["192.168.1.60:9182"], "role": "gpu",
     "expected_offline": True, "critical": False,
     "expected_labels": {"cluster": "ai-lab", "env": "homelab", "gpu": "rx7900xt"}},
    {"job": "ai-lab-gpu-metrics", "endpoint": "192.168.1.50:9183",
     "instances": ["192.168.1.50:9183", "192.168.1.60:9183"],
     "role": "gpu-compute", "expected_offline": False, "critical": True,
     "expected_labels": {"cluster": "ai-lab", "env": "homelab"},
     "note": "multi_instance_job"},
    {"job": "cloudflare-tunnel", "endpoint": "cloudflare-tunnel:2000",
     "instances": ["cloudflare-tunnel:2000"], "role": "tunnel",
     "expected_offline": False, "critical": False,
     "expected_labels": {"cluster": "ai-lab", "env": "homelab"}},
    {"job": "docker", "endpoint": "cadvisor:8080",
     "instances": ["cadvisor:8080"], "role": "docker",
     "expected_offline": False, "critical": False,
     "expected_labels": {}},
    {"job": "unpoller", "endpoint": "192.168.1.40:9130",
     "instances": ["192.168.1.40:9130"], "role": "unifi",
     "expected_offline": False, "critical": False,
     "expected_labels": {}},
    {"job": "smartctl-exporter", "endpoint": "192.168.1.200:9633",
     "instances": ["192.168.1.200:9633"], "role": "storage",
     "expected_offline": False, "critical": False,
     "expected_labels": {}},
    {"job": "ubuntu-server", "endpoint": "192.168.1.40:9100",
     "instances": ["192.168.1.40:9100"], "role": "host",
     "expected_offline": False, "critical": False,
     "expected_labels": {}},
    {"job": "serv2025-hyperv2", "endpoint": "192.168.1.100:9182",
     "instances": ["192.168.1.100:9182"], "role": "windows",
     "expected_offline": False, "critical": False,
     "expected_labels": {}},
    {"job": "serv2025-market", "endpoint": "192.168.1.150:9182",
     "instances": ["192.168.1.150:9182"], "role": "windows",
     "expected_offline": False, "critical": False,
     "expected_labels": {}},
    {"job": "windows11-nas", "endpoint": "192.168.1.200:9182",
     "instances": ["192.168.1.200:9182"], "role": "windows",
     "expected_offline": False, "critical": False,
     "expected_labels": {}},
]


# ── Dataclasses ──

@dataclass
class TargetAuditEntry:
    job: str = ""
    instance: str = ""
    role: str = ""
    status: str = PrometheusTargetStatus.UNKNOWN.value
    expected_offline: bool = False
    critical: bool = False
    health: str = TargetHealth.UNKNOWN.value
    freshness: str = FreshnessLevel.UNKNOWN.value
    last_scrape_ts: str = ""
    last_scrape_age_seconds: float = 0.0
    last_scrape_duration_ms: float = 0.0
    scrape_interval_seconds: int = 15
    error_message: str | None = None
    labels: dict[str, str] = field(default_factory=dict)
    label_issues: list[dict[str, str]] = field(default_factory=list)
    duplicate: bool = False
    duplicate_instances: list[str] = field(default_factory=list)
    inventory_only: bool = False

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "job": self.job,
            "instance": self.instance,
            "role": self.role,
            "status": self.status,
            "expected_offline": self.expected_offline,
            "critical": self.critical,
            "health": self.health,
            "freshness": self.freshness,
            "last_scrape_age_seconds": round(self.last_scrape_age_seconds, 1),
            "last_scrape_duration_ms": round(self.last_scrape_duration_ms, 1),
            "scrape_interval_seconds": self.scrape_interval_seconds,
            "error_message": self.error_message,
            "labels": self.labels,
            "label_issues": self.label_issues,
            "duplicate": self.duplicate,
            "inventory_only": self.inventory_only,
        }
        if self.duplicate:
            d["duplicate_instances"] = self.duplicate_instances
        return d


# ── Prometheus API client ──

def fetch_prometheus_targets(
    prometheus_url: str = _PROMETHEUS_DEFAULT_URL,
    timeout: int = _PROMETHEUS_TIMEOUT,
) -> dict[str, Any]:
    start = time.time()
    try:
        req = Request(f"{prometheus_url}/api/v1/targets", method="GET",
                      headers={"Accept": "application/json"})
        with urlopen(req, timeout=timeout) as conn:
            raw = json.loads(conn.read().decode("utf-8"))
        elapsed = round((time.time() - start) * 1000, 1)
        if raw.get("status") != "success":
            return {"status": "error", "error": f"api_status:{raw.get('status')}",
                    "fetch_time_ms": elapsed, "active": [], "dropped": []}
        data = raw.get("data", {})
        return {"status": "ok", "fetch_time_ms": elapsed,
                "active": data.get("activeTargets", []),
                "dropped": data.get("droppedTargets", []),
                "raw": raw}
    except URLError as exc:
        elapsed = round((time.time() - start) * 1000, 1)
        return {"status": "error", "error": f"connection_failed:{exc.reason}",
                "fetch_time_ms": elapsed, "active": [], "dropped": []}
    except (json.JSONDecodeError, OSError) as exc:
        elapsed = round((time.time() - start) * 1000, 1)
        return {"status": "error", "error": f"fetch_failed:{exc}",
                "fetch_time_ms": elapsed, "active": [], "dropped": []}


# ── Freshness calculation ──

def calculate_freshness(
    last_scrape_str: str = "",
    scrape_interval_seconds: int = 15,
) -> str:
    if not last_scrape_str:
        return FreshnessLevel.UNKNOWN.value
    try:
        if last_scrape_str.endswith("Z"):
            last_scrape_str = last_scrape_str[:-1] + "+00:00"
        last = datetime.fromisoformat(last_scrape_str)
        age = (datetime.now(timezone.utc) - last).total_seconds()
    except (ValueError, TypeError):
        return FreshnessLevel.UNKNOWN.value
    if age < scrape_interval_seconds * 2:
        return FreshnessLevel.FRESH.value
    if age < scrape_interval_seconds * 5:
        return FreshnessLevel.STALE.value
    return FreshnessLevel.AGED.value


def get_scrape_age_seconds(last_scrape_str: str = "") -> float:
    if not last_scrape_str:
        return 0.0
    try:
        if last_scrape_str.endswith("Z"):
            last_scrape_str = last_scrape_str[:-1] + "+00:00"
        last = datetime.fromisoformat(last_scrape_str)
        return round((datetime.now(timezone.utc) - last).total_seconds(), 1)
    except (ValueError, TypeError):
        return 0.0


# ── Duplicate detection ──

def detect_duplicate_jobs(
    active_targets: list[dict[str, Any]],
) -> dict[str, list[str]]:
    jobs: dict[str, list[str]] = {}
    for t in active_targets:
        job = t.get("labels", {}).get("job", "unknown")
        inst = t.get("labels", {}).get("instance", "")
        if job not in jobs:
            jobs[job] = []
        jobs[job].append(inst)
    return {job: insts for job, insts in jobs.items() if len(insts) > 1}


# ── Label validation ──

def validate_target_labels(
    live_labels: dict[str, str],
    expected_labels: dict[str, str],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for key, expected_val in expected_labels.items():
        actual_val = live_labels.get(key, "")
        if not actual_val:
            issues.append({"label": key, "severity": LabelSeverity.MISSING.value,
                           "expected": expected_val, "actual": ""})
        elif actual_val != expected_val:
            issues.append({"label": key, "severity": LabelSeverity.MISMATCH.value,
                           "expected": expected_val, "actual": actual_val})
    for key in ("instance", "job"):
        if key not in live_labels:
            issues.append({"label": key, "severity": LabelSeverity.MISSING.value,
                           "expected": key, "actual": ""})
    return issues


# ── Backward-compatible classify_scrape_target ──

def classify_scrape_target(
    target: dict[str, Any],
    is_up: bool | None = None,
    scrape_duration_ms: float = 0.0,
    scrape_interval_seconds: int = 15,
    error: str | None = None,
    live_target: dict[str, Any] | None = None,
) -> TargetAuditEntry:
    """Classify a scrape target.

    Old API (OBS-31A): pass target dict + is_up/duration/error kwargs.
    New API (OBS-31A.1): pass target dict + live_target dict from Prometheus API.
    """
    if live_target is not None:
        return _classify_from_live(target, live_target)
    if is_up is not None or error is not None or scrape_duration_ms > 0:
        return _classify_legacy(target, is_up, scrape_duration_ms, scrape_interval_seconds, error)
    return _orphan_entry(target)


def _orphan_entry(target: dict[str, Any]) -> TargetAuditEntry:
    entry = TargetAuditEntry(
        job=target.get("job", "unknown"),
        instance=(target.get("endpoint", "") or "").split("/")[0],
        role=target.get("role", "unknown"),
        expected_offline=target.get("expected_offline", False),
        critical=target.get("critical", False),
    )
    if target.get("expected_offline", False):
        entry.status = PrometheusTargetStatus.EXPECTED_OFFLINE.value
    else:
        entry.status = PrometheusTargetStatus.ORPHAN.value
        entry.inventory_only = True
    return entry


def _classify_legacy(
    target: dict[str, Any],
    is_up: bool | None = None,
    scrape_duration_ms: float = 0.0,
    scrape_interval_seconds: int = 15,
    error: str | None = None,
) -> TargetAuditEntry:
    entry = TargetAuditEntry(
        job=target.get("job", "unknown"),
        instance=target.get("endpoint", "").split("/")[0],
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


def _classify_from_live(
    known_target: dict[str, Any],
    live_target: dict[str, Any],
) -> TargetAuditEntry:
    job = known_target.get("job", "unknown")
    expected_offline = known_target.get("expected_offline", False)
    critical = known_target.get("critical", False)
    role = known_target.get("role", "unknown")
    expected_labels = known_target.get("expected_labels", {})

    entry = TargetAuditEntry(
        job=job,
        role=role,
        expected_offline=expected_offline,
        critical=critical,
    )

    labels = live_target.get("labels", {})
    entry.instance = labels.get("instance", "")
    entry.labels = dict(labels)
    entry.last_scrape_duration_ms = live_target.get("lastScrapeDuration", 0.0) * 1000
    entry.scrape_interval_seconds = _parse_interval(live_target.get("scrapeInterval", "15s"))
    entry.error_message = live_target.get("lastError", "") or None
    entry.last_scrape_ts = live_target.get("lastScrape", "")
    entry.last_scrape_age_seconds = get_scrape_age_seconds(entry.last_scrape_ts)
    entry.freshness = calculate_freshness(entry.last_scrape_ts, entry.scrape_interval_seconds)
    entry.label_issues = validate_target_labels(labels, expected_labels)

    health = live_target.get("health", "unknown")
    entry.health = health if health in ("up", "down") else TargetHealth.UNKNOWN.value

    if expected_offline:
        entry.status = (PrometheusTargetStatus.EXPECTED_OFFLINE.value
                        if health == "down" else PrometheusTargetStatus.HEALTHY.value)
        return entry
    if health == "down":
        entry.status = PrometheusTargetStatus.UNEXPECTED_DOWN.value
        return entry
    if health != "up":
        entry.status = PrometheusTargetStatus.STALE.value
        return entry
    if entry.last_scrape_duration_ms > entry.scrape_interval_seconds * 1000 * 0.8:
        entry.status = PrometheusTargetStatus.DEGRADED.value
        return entry
    if entry.freshness == FreshnessLevel.AGED.value:
        entry.status = PrometheusTargetStatus.STALE.value
        return entry
    entry.status = PrometheusTargetStatus.HEALTHY.value
    return entry


def _parse_interval(interval_str: str) -> int:
    if not interval_str:
        return 15
    if interval_str.endswith("s"):
        try:
            return int(interval_str[:-1])
        except ValueError:
            return 15
    if interval_str.endswith("m"):
        try:
            return int(interval_str[:-1]) * 60
        except ValueError:
            return 15
    try:
        return int(interval_str)
    except (ValueError, TypeError):
        return 15


# ── Backward-compatible audit_prometheus_targets ──

def audit_prometheus_targets(
    up_map: dict[str, bool] | None = None,
    duration_map: dict[str, float] | None = None,
    error_map: dict[str, str] | None = None,
    prometheus_url: str | None = None,
) -> list[dict[str, Any]]:
    """Audit known targets.

    Old API: pass up_map/duration_map/error_map for testing (returns list[dict]).
    New API: pass prometheus_url for live audit (returns same list[dict] structure).
    """
    if prometheus_url is not None or (up_map is None and duration_map is None and error_map is None):
        return _run_live_audit(prometheus_url or _PROMETHEUS_DEFAULT_URL)

    results: list[dict[str, Any]] = []
    up_map = up_map or {}
    duration_map = duration_map or {}
    error_map = error_map or {}

    for target in _KNOWN_TARGETS:
        job = target.get("job", "")
        is_up = up_map.get(job)
        duration = duration_map.get(job, 0.0)
        error = error_map.get(job)
        entry = _classify_legacy(target, is_up=is_up, scrape_duration_ms=duration, error=error)
        results.append(entry.to_dict())

    return results


def _run_live_audit(prometheus_url: str) -> list[dict[str, Any]]:
    live = fetch_prometheus_targets(prometheus_url)
    if live.get("status") != "ok":
        return [{"job": t.get("job", "?"),
                  "status": "expected_offline" if t.get("expected_offline") else "stale",
                  "error": f"prometheus_unreachable:{live.get('error')}",
                  "expected_offline": t.get("expected_offline", False),
                  "critical": t.get("critical", False)}
                 for t in _KNOWN_TARGETS]

    active = live.get("active", [])
    known_map: dict[str, list[dict[str, Any]]] = {}
    for kt in _KNOWN_TARGETS:
        job = kt.get("job", "")
        known_map.setdefault(job, []).append(kt)

    live_by_job: dict[str, list[dict[str, Any]]] = {}
    for t in active:
        job = t.get("labels", {}).get("job", "unknown")
        live_by_job.setdefault(job, []).append(t)

    duplicates = detect_duplicate_jobs(active)
    seen_known: set[str] = set()
    results: list[dict[str, Any]] = []

    for kt in _KNOWN_TARGETS:
        job = kt.get("job", "")
        seen_known.add(job)
        has_duplicates = job in duplicates and len(known_map.get(job, [])) == 1
        live_for_job = live_by_job.get(job, [])

        if has_duplicates:
            for lt in live_for_job:
                entry = classify_scrape_target(kt, live_target=lt)
                entry.duplicate = True
                entry.duplicate_instances = duplicates[job]
                results.append(entry.to_dict())
            continue

        lt = live_for_job[0] if live_for_job else None
        entry = classify_scrape_target(kt, live_target=lt) if lt else classify_scrape_target(kt, is_up=None)
        if job in duplicates and not has_duplicates:
            entry.duplicate = True
            entry.duplicate_instances = duplicates.get(job, [])
        results.append(entry.to_dict())

    for t in active:
        job = t.get("labels", {}).get("job", "unknown")
        if job not in seen_known:
            seen_known.add(job)
            results.append({
                "job": job,
                "instance": t.get("labels", {}).get("instance", ""),
                "role": "unknown",
                "status": "orphan",
                "expected_offline": False,
                "critical": False,
                "health": t.get("health", "unknown"),
                "error_message": t.get("lastError", "") or None,
                "last_scrape_age_seconds": 0,
                "label_issues": [{"label": "job", "severity": "orphan",
                                  "expected": "known_inventory", "actual": job}],
            })

    return results


# ── Critical ailab_* metric validation ──

def check_critical_metrics(
    prometheus_url: str = _PROMETHEUS_DEFAULT_URL,
    timeout: int = _PROMETHEUS_TIMEOUT,
) -> dict[str, Any]:
    results: dict[str, bool] = {}
    for metric in _CRITICAL_METRICS:
        try:
            req = Request(f"{prometheus_url}/api/v1/query?query=count({metric})",
                          method="GET", headers={"Accept": "application/json"})
            with urlopen(req, timeout=timeout) as conn:
                raw = json.loads(conn.read().decode("utf-8"))
            exists = (raw.get("status") == "success"
                      and len(raw.get("data", {}).get("result", [])) > 0)
        except (URLError, json.JSONDecodeError, OSError):
            exists = False
        results[metric] = exists
    found = sum(1 for v in results.values() if v)
    total = len(results)
    return {
        "contract_version": PROMETHEUS_AUDIT_CONTRACT_VERSION,
        "total_checked": total,
        "found": found,
        "missing": total - found,
        "coverage_pct": round((found / total * 100) if total else 0, 1),
        "metrics": results,
    }


# ── Full authority audit ──

def run_prometheus_authority_audit(
    prometheus_url: str | None = None,
) -> dict[str, Any]:
    url = prometheus_url or _PROMETHEUS_DEFAULT_URL
    live = fetch_prometheus_targets(url)
    targets = audit_prometheus_targets(prometheus_url=url)

    if live.get("status") != "ok" and not targets:
        return {
            "contract_version": PROMETHEUS_AUDIT_CONTRACT_VERSION,
            "timestamp": time.time(),
            "prometheus_url": url,
            "status": "error",
            "error": live.get("error", "unknown"),
            "fetch_time_ms": live.get("fetch_time_ms", 0),
            "total_prometheus_targets": 0,
            "total_known_targets": len(_KNOWN_TARGETS),
            "unexpected_down_count": 0,
            "total_duplicate_jobs": 0,
            "classification": {},
            "critical_targets": {"healthy": 0, "total": 0, "alignment_pct": 0},
            "unexpected_down": [],
            "targets": targets,
        }

    duplicates = detect_duplicate_jobs(live.get("active", []))
    counts: dict[str, int] = {}
    unexpected_down: list[dict[str, Any]] = []
    for r in targets:
        s = r.get("status", "unknown")
        counts[s] = counts.get(s, 0) + 1
        if s == PrometheusTargetStatus.UNEXPECTED_DOWN.value:
            unexpected_down.append({
                "job": r.get("job", ""),
                "instance": r.get("instance", ""),
                "critical": r.get("critical", False),
                "error": r.get("error_message", ""),
                "last_scrape_age_seconds": r.get("last_scrape_age_seconds", 0),
            })

    critical_healthy = sum(1 for r in targets if r.get("critical") and r.get("status") == "healthy")
    critical_total = sum(1 for r in targets if r.get("critical"))

    freshness: dict[str, int] = {}
    label_issues = 0
    label_targets = 0
    for r in targets:
        f = r.get("freshness", "unknown")
        freshness[f] = freshness.get(f, 0) + 1
        issues = r.get("label_issues", [])
        if issues:
            label_targets += 1
            label_issues += len(issues)

    critical_metrics = check_critical_metrics(url)

    return {
        "contract_version": PROMETHEUS_AUDIT_CONTRACT_VERSION,
        "timestamp": time.time(),
        "prometheus_url": url,
        "status": "ok",
        "fetch_time_ms": live.get("fetch_time_ms", 0),
        "total_prometheus_targets": len(live.get("active", [])),
        "total_known_targets": len(_KNOWN_TARGETS),
        "total_orphan_targets": sum(1 for r in targets if r.get("status") == "orphan"),
        "expected_offline_found": sum(1 for r in targets if r.get("status") == "expected_offline"),
        "unexpected_down_count": len(unexpected_down),
        "total_duplicate_jobs": len(duplicates),
        "classification": counts,
        "critical_targets": {
            "healthy": critical_healthy,
            "total": critical_total,
            "alignment_pct": round((critical_healthy / critical_total * 100)
                                    if critical_total else 0, 1),
        },
        "unexpected_down": unexpected_down,
        "duplicate_jobs": {j: insts for j, insts in duplicates.items()},
        "freshness_summary": freshness,
        "label_summary": {"total_issues": label_issues, "targets_with_issues": label_targets},
        "critical_metrics": critical_metrics,
        "targets": targets,
    }


# ── Summary builder (OBS-31A compatible) ──

def build_prometheus_audit_summary(
    target_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if target_results is None:
        target_results = audit_prometheus_targets(prometheus_url=_PROMETHEUS_DEFAULT_URL)

    counts: dict[str, int] = {}
    for r in target_results:
        status = r.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1

    critical_healthy = sum(1 for r in target_results
                           if r.get("critical") and r.get("status") == "healthy")
    critical_total = sum(1 for r in target_results if r.get("critical"))
    alignment_pct = round((critical_healthy / critical_total * 100)
                           if critical_total else 100, 1)

    return {
        "contract_version": "OBS-31A",
        "timestamp": time.time(),
        "total_targets": len(target_results),
        "classification": {
            "healthy": counts.get("healthy", 0),
            "degraded": counts.get("degraded", 0),
            "expected_offline": counts.get("expected_offline", 0),
            "unexpected_down": counts.get("unexpected_down", 0),
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
