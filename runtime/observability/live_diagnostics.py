"""FASE OBS-34B: Live Observability Diagnostics.

Turns the real observability platform (Prometheus/Grafana/Loki) into a
diagnosticable, explainable, authority-aware domain.

RULE-OBS34B-1: Prometheus remains absolute authority.
RULE-OBS34B-2: Grafana never defines truth.
RULE-OBS34B-3: DOWN expected_offline != incident.
RULE-OBS34B-4: Inventory entities do not degrade runtime.
RULE-OBS34B-5: no_route_to_host must be explicitly classified.
RULE-OBS34B-6: Exporter flapping degrades confidence.
RULE-OBS34B-7: Stale metrics degrade observability authority.
RULE-OBS34B-8: Diagnostics must be explainable.
RULE-OBS34B-9: Unknown > inventado.

Safety: read-only diagnostics only. No remediation execution.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any


OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION = "OBS-34B"


def _strict_mode() -> bool:
    return os.environ.get("STRICT_VALIDATION_MODE", "false").lower() in ("true", "1", "yes")


def _now() -> float:
    return 0.0 if _strict_mode() else time.time()


def _hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _classify_network_error(err: str) -> str:
    """Classify a network/transport error from a stable string representation."""
    e = (err or "").lower()
    if "no route to host" in e or "errno 113" in e:
        return "no_route_to_host"
    if "name or service not known" in e or "nodename nor servname" in e or "temporary failure in name resolution" in e:
        return "dns_failure"
    if "connection refused" in e or "errno 111" in e:
        return "tcp_refused"
    if "connecttimeout" in e or "readtimeout" in e or "timed out" in e or "timeout" in e:
        return "timeout"
    if "network is unreachable" in e:
        return "unreachable_network"
    return "unknown"


def _safe_import_requests():
    try:
        import requests  # type: ignore
        return requests
    except Exception:
        return None


def _network_enabled(extra_ctx: dict[str, Any] | None = None) -> bool:
    extra_ctx = extra_ctx or {}
    if bool(extra_ctx.get("enable_network")):
        return True
    return os.environ.get("AI_LAB_ENABLE_LIVE_OBSERVABILITY_NETWORK", "false").lower() in ("true", "1", "yes")


def _fetch_json(url: str, timeout_s: int = 5, headers: dict[str, str] | None = None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Fetch JSON from a URL. Returns (json_or_none, diag)."""
    requests = _safe_import_requests()
    if requests is None:
        return None, {"status": "error", "error_type": "requests_unavailable", "error": "requests import failed"}

    start = time.time()
    try:
        r = requests.get(url, timeout=timeout_s, headers=headers or {"Accept": "application/json"})
        elapsed_ms = round((time.time() - start) * 1000, 1)
        if r.status_code >= 400:
            return None, {
                "status": "error",
                "error_type": "http_error",
                "http_status": r.status_code,
                "error": (r.text or "")[:240],
                "fetch_time_ms": elapsed_ms,
            }
        try:
            data = r.json()
        except Exception as exc:
            return None, {
                "status": "error",
                "error_type": "invalid_json",
                "error": str(exc),
                "fetch_time_ms": elapsed_ms,
            }
        return data, {"status": "ok", "fetch_time_ms": elapsed_ms}
    except Exception as exc:
        elapsed_ms = round((time.time() - start) * 1000, 1)
        et = _classify_network_error(str(exc))
        return None, {
            "status": "error",
            "error_type": et,
            "error": str(exc),
            "fetch_time_ms": elapsed_ms,
        }


def _prometheus_base_url(extra_ctx: dict[str, Any] | None = None) -> str:
    extra_ctx = extra_ctx or {}
    return str(extra_ctx.get("prometheus_url") or os.environ.get("AI_LAB_PROMETHEUS_URL") or "http://192.168.1.40:9090")


def _grafana_base_url(extra_ctx: dict[str, Any] | None = None) -> str:
    extra_ctx = extra_ctx or {}
    return str(extra_ctx.get("grafana_url") or os.environ.get("AI_LAB_GRAFANA_URL") or "http://192.168.1.40:3000")


def _loki_base_url(extra_ctx: dict[str, Any] | None = None) -> str:
    extra_ctx = extra_ctx or {}
    return str(extra_ctx.get("loki_url") or os.environ.get("AI_LAB_LOKI_URL") or "http://192.168.1.40:3100")


def diagnose_prometheus_authority(
    extra_ctx: dict[str, Any] | None = None,
    live_targets: dict[str, Any] | None = None,
    live_config: dict[str, Any] | None = None,
    live_runtimeinfo: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Diagnose Prometheus authority via live endpoints.

    If live_* payloads are provided, no network calls are made.
    """
    extra_ctx = extra_ctx or {}
    base = _prometheus_base_url(extra_ctx)

    fetch: dict[str, Any] = {"prometheus_url": base, "targets": {}, "config": {}, "runtimeinfo": {}}

    if live_targets is None:
        if _network_enabled(extra_ctx):
            live_targets, fetch["targets"] = _fetch_json(f"{base}/api/v1/targets", timeout_s=int(extra_ctx.get("prometheus_timeout_s", 5) or 5))
        else:
            live_targets = None
            fetch["targets"] = {"status": "skipped", "reason": "network_disabled"}
    else:
        fetch["targets"] = {"status": "fixture"}

    if live_config is None:
        if _network_enabled(extra_ctx):
            live_config, fetch["config"] = _fetch_json(f"{base}/api/v1/status/config", timeout_s=int(extra_ctx.get("prometheus_timeout_s", 5) or 5))
        else:
            live_config = None
            fetch["config"] = {"status": "skipped", "reason": "network_disabled"}
    else:
        fetch["config"] = {"status": "fixture"}

    if live_runtimeinfo is None:
        if _network_enabled(extra_ctx):
            live_runtimeinfo, fetch["runtimeinfo"] = _fetch_json(f"{base}/api/v1/status/runtimeinfo", timeout_s=int(extra_ctx.get("prometheus_timeout_s", 5) or 5))
        else:
            live_runtimeinfo = None
            fetch["runtimeinfo"] = {"status": "skipped", "reason": "network_disabled"}
    else:
        fetch["runtimeinfo"] = {"status": "fixture"}

    ok = bool(live_targets and live_targets.get("status") == "success")
    authority_state = "healthy" if ok else "degraded"

    targets_data = (live_targets or {}).get("data", {}) if isinstance(live_targets, dict) else {}
    active_targets = targets_data.get("activeTargets", []) if isinstance(targets_data, dict) else []
    dropped_targets = targets_data.get("droppedTargets", []) if isinstance(targets_data, dict) else []

    scrape_down = 0
    scrape_up = 0
    scrape_unknown = 0
    no_route = 0
    timeouts = 0

    for t in active_targets or []:
        health = (t.get("health") or "").lower()
        if health == "up":
            scrape_up += 1
        elif health == "down":
            scrape_down += 1
        else:
            scrape_unknown += 1

        le = str(t.get("lastError") or "")
        if le:
            et = _classify_network_error(le)
            if et == "no_route_to_host":
                no_route += 1
            if et == "timeout":
                timeouts += 1

    # Staleness: conservative marker. We avoid clock parsing to keep determinism from payload.
    stale_targets = sum(1 for t in (active_targets or []) if (t.get("health") or "").lower() != "up")

    runtimeinfo = (live_runtimeinfo or {}).get("data", {}) if isinstance(live_runtimeinfo, dict) else {}

    return {
        "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
        "authority": {
            "type": "prometheus",
            "absolute": True,
            "state": authority_state,
            "confidence": "high" if ok else "low",
            "explainable": True,
        },
        "fetch": fetch,
        "targets": {
            "active_total": len(active_targets or []),
            "dropped_total": len(dropped_targets or []),
            "scrape_up": scrape_up,
            "scrape_down": scrape_down,
            "scrape_unknown": scrape_unknown,
            "stale_candidates": stale_targets,
            "no_route_to_host": no_route,
            "timeouts": timeouts,
        },
        "runtimeinfo": {
            "version": runtimeinfo.get("version"),
            "revision": runtimeinfo.get("revision"),
            "goVersion": runtimeinfo.get("goVersion"),
        },
        "notes": ["prometheus is authority", "grafana is visualization-only"],
        "generated_at": _now(),
    }


def diagnose_grafana_platform(
    extra_ctx: dict[str, Any] | None = None,
    live_health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Grafana diagnostics (non-authority)."""
    extra_ctx = extra_ctx or {}
    base = _grafana_base_url(extra_ctx)

    fetch = {"grafana_url": base, "health": {}}
    if live_health is None:
        if _network_enabled(extra_ctx):
            live_health, fetch["health"] = _fetch_json(f"{base}/api/health", timeout_s=int(extra_ctx.get("grafana_timeout_s", 5) or 5))
        else:
            live_health = None
            fetch["health"] = {"status": "skipped", "reason": "network_disabled"}
    else:
        fetch["health"] = {"status": "fixture"}

    semantic = {}
    try:
        from runtime.observability.grafana_semantic_validator import build_grafana_semantic_summary
        semantic = build_grafana_semantic_summary()
    except Exception as exc:
        semantic = {"error": str(exc)}

    up = bool(live_health and live_health.get("database") == "ok")
    return {
        "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
        "authority": {"type": "grafana", "absolute": False, "state": "non_authority", "confidence": "high", "explainable": True},
        "platform": {"up": up, "health": live_health or {}},
        "semantic": semantic,
        "fetch": fetch,
        "generated_at": _now(),
    }


def diagnose_loki_platform(
    extra_ctx: dict[str, Any] | None = None,
    live_ready: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Loki diagnostics (observability dependency, not truth authority)."""
    extra_ctx = extra_ctx or {}
    base = _loki_base_url(extra_ctx)

    fetch = {"loki_url": base, "ready": {}}
    if live_ready is None:
        if _network_enabled(extra_ctx):
            data, diag = _fetch_json(f"{base}/ready", timeout_s=int(extra_ctx.get("loki_timeout_s", 5) or 5))
            if diag.get("status") == "ok":
                live_ready = {"status": "ok"}
            else:
                live_ready = {"status": "error", "detail": diag}
            fetch["ready"] = diag
            _ = data
        else:
            live_ready = None
            fetch["ready"] = {"status": "skipped", "reason": "network_disabled"}
    else:
        fetch["ready"] = {"status": "fixture"}
    loki_audit = {}
    try:
        from runtime.observability.loki_audit import build_loki_audit_summary
        loki_audit = build_loki_audit_summary()
    except Exception as exc:
        loki_audit = {"error": str(exc)}

    up = bool((live_ready or {}).get("status") == "ok")
    return {
        "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
        "authority": {"type": "loki", "absolute": False, "state": "dependency", "confidence": "medium", "explainable": True},
        "platform": {"up": up, "ready": live_ready or {}},
        "audit": loki_audit,
        "fetch": fetch,
        "generated_at": _now(),
    }


def detect_exporter_flapping(
    flapping_changes: dict[str, int] | None = None,
    threshold_changes: int = 4,
) -> dict[str, Any]:
    """Detect flapping from a deterministic changes map.

    flapping_changes: {"job|instance": changes(up[window])}
    """
    flapping_changes = flapping_changes or {}
    flapping = {k: int(v) for k, v in flapping_changes.items() if int(v) >= threshold_changes}
    max_changes = max([int(v) for v in flapping_changes.values()], default=0)
    score = round(min(1.0, max_changes / max(threshold_changes, 1)) * 100, 1) if flapping_changes else 0.0
    return {
        "threshold_changes": threshold_changes,
        "flapping_total": len(flapping),
        "max_changes": max_changes,
        "flapping_score": score,
        "flapping": [{"target": k, "changes": v} for k, v in sorted(flapping.items())],
        "explainable": True,
    }


def diagnose_exporters(
    prometheus_targets: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
    flapping_changes: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Classify exporters from Prometheus /targets response."""
    extra_ctx = extra_ctx or {}
    prometheus_targets = prometheus_targets or {}

    try:
        from runtime.observability.prometheus_audit import _KNOWN_TARGETS
    except Exception:
        _KNOWN_TARGETS = []

    known_by_job = {t.get("job"): t for t in (_KNOWN_TARGETS or []) if t.get("job")}

    data = (prometheus_targets or {}).get("data", {}) if isinstance(prometheus_targets, dict) else {}
    active = data.get("activeTargets", []) if isinstance(data, dict) else []

    expected_offline_jobs = {j for j, meta in known_by_job.items() if meta.get("expected_offline")}

    classified: list[dict[str, Any]] = []
    unreachable_total = 0
    no_route_total = 0
    legacy_down_total = 0

    flap = detect_exporter_flapping(flapping_changes or {})
    flap_targets = {f.get("target") for f in flap.get("flapping", [])}

    for t in active or []:
        labels = t.get("labels", {}) or {}
        job = labels.get("job", "unknown")
        instance = labels.get("instance", "")
        health = (t.get("health") or "unknown").lower()
        last_error = str(t.get("lastError") or "")
        err_type = _classify_network_error(last_error) if last_error else ""

        known = known_by_job.get(job) or {}
        expected_offline = bool(known.get("expected_offline", False))
        critical = bool(known.get("critical", False))
        role = known.get("role", labels.get("role", "unknown"))

        key = f"{job}|{instance}" if instance else job

        if expected_offline and health == "down":
            status = "EXPECTED_OFFLINE"
            severity = "info"
            runtime_impact = "none"
            authority_impact = "none"
        elif key in flap_targets:
            status = "FLAPPING"
            severity = "medium"
            runtime_impact = "low"
            authority_impact = "medium"
        elif health == "up":
            status = "ACTIVE_HEALTHY"
            severity = "info"
            runtime_impact = "none"
            authority_impact = "none"
        elif health == "down" and err_type == "no_route_to_host":
            status = "UNREACHABLE"
            severity = "low" if not critical else "high"
            runtime_impact = "none" if not critical else "moderate"
            authority_impact = "minimal" if not critical else "high"
            unreachable_total += 1
            no_route_total += 1
        elif health == "down" and err_type in ("timeout", "tcp_refused", "dns_failure", "unreachable_network"):
            status = "ACTIVE_DEGRADED"
            severity = "medium" if critical else "low"
            runtime_impact = "moderate" if critical else "low"
            authority_impact = "medium" if critical else "minimal"
            unreachable_total += 1
        elif health == "down" and job not in known_by_job:
            status = "LEGACY_DOWN"
            severity = "low"
            runtime_impact = "none"
            authority_impact = "minimal"
            legacy_down_total += 1
        else:
            status = "UNKNOWN"
            severity = "low"
            runtime_impact = "unknown"
            authority_impact = "unknown"

        classified.append({
            "job": job,
            "instance": instance,
            "role": role,
            "expected_offline": expected_offline,
            "critical": critical,
            "health": health,
            "status": status,
            "severity": severity,
            "runtime_impact": runtime_impact,
            "authority_impact": authority_impact,
            "error_type": err_type,
            "last_error": last_error[:240] if last_error else None,
            "explainable": True,
        })

    summary = {
        "expected_offline_jobs": sorted(expected_offline_jobs),
        "active_total": len(active or []),
        "unreachable_total": unreachable_total,
        "no_route_to_host_total": no_route_total,
        "legacy_down_total": legacy_down_total,
        "flapping": flap,
    }

    return {
        "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
        "classification": classified,
        "summary": summary,
        "generated_at": _now(),
    }


def diagnose_scrape_health(prometheus_targets: dict[str, Any] | None = None) -> dict[str, Any]:
    prometheus_targets = prometheus_targets or {}
    data = (prometheus_targets or {}).get("data", {}) if isinstance(prometheus_targets, dict) else {}
    active = data.get("activeTargets", []) if isinstance(data, dict) else []

    failures = []
    duration_anomalies = []
    for t in active or []:
        labels = t.get("labels", {}) or {}
        job = labels.get("job", "unknown")
        instance = labels.get("instance", "")
        health = (t.get("health") or "unknown").lower()
        if health == "down":
            failures.append({
                "job": job,
                "instance": instance,
                "error_type": _classify_network_error(str(t.get("lastError") or "")),
                "last_error": str(t.get("lastError") or "")[:200] or None,
            })
        try:
            interval = str(t.get("scrapeInterval") or "15s")
            interval_s = int(interval[:-1]) if interval.endswith("s") and interval[:-1].isdigit() else 15
            dur_s = float(t.get("lastScrapeDuration") or 0.0)
            if interval_s > 0 and dur_s > (interval_s * 0.8):
                duration_anomalies.append({
                    "job": job,
                    "instance": instance,
                    "scrape_interval_s": interval_s,
                    "last_scrape_duration_s": round(dur_s, 4),
                    "ratio": round(dur_s / interval_s, 3),
                })
        except Exception:
            pass

    return {
        "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
        "scrape_failures_total": len(failures),
        "scrape_duration_anomalies_total": len(duration_anomalies),
        "failures": failures,
        "duration_anomalies": duration_anomalies,
        "explainable": True,
        "generated_at": _now(),
    }


def diagnose_datasource_health(grafana_diag: dict[str, Any] | None = None) -> dict[str, Any]:
    grafana_diag = grafana_diag or {}
    semantic = grafana_diag.get("semantic", {}) or {}
    orphan = semantic.get("orphan_datasources", []) or []
    metric_drift = semantic.get("metric_drift", []) or []
    stale_panels = semantic.get("stale_panels", []) or []
    fake = semantic.get("fake_gpu_panels", []) or []
    return {
        "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
        "datasource_drift_total": len(orphan),
        "metric_drift_total": len(metric_drift),
        "stale_panels_total": len(stale_panels),
        "fake_gpu_panels_total": len(fake),
        "orphan_datasources": orphan,
        "explainable": True,
        "generated_at": _now(),
    }


def detect_authority_staleness(prom_diag: dict[str, Any] | None = None) -> dict[str, Any]:
    prom_diag = prom_diag or {}
    targets = prom_diag.get("targets", {}) or {}
    stale = int(targets.get("stale_candidates", 0) or 0)
    down = int(targets.get("scrape_down", 0) or 0)
    state = "fresh" if stale == 0 and down == 0 else "stale" if stale > 0 else "degraded"
    return {
        "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
        "authority_staleness_total": stale,
        "scrape_down_total": down,
        "authority_freshness": state,
        "explainable": True,
    }


def detect_scrape_instability(scrape_diag: dict[str, Any] | None = None, flapping: dict[str, Any] | None = None) -> dict[str, Any]:
    scrape_diag = scrape_diag or {}
    flapping = flapping or {}
    failures = int(scrape_diag.get("scrape_failures_total", 0) or 0)
    anomalies = int(scrape_diag.get("scrape_duration_anomalies_total", 0) or 0)
    flap_total = int((flapping.get("flapping") or {}).get("flapping_total", 0) or 0)
    score = (failures * 10) + (anomalies * 3) + (flap_total * 5)
    level = "stable" if score == 0 else "degraded" if score < 15 else "unstable"
    return {
        "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
        "instability_score": score,
        "instability_level": level,
        "components": {"failures": failures, "duration_anomalies": anomalies, "flapping": flap_total},
        "explainable": True,
    }


def detect_observability_incidents(
    prom_diag: dict[str, Any] | None = None,
    exporters_diag: dict[str, Any] | None = None,
    grafana_diag: dict[str, Any] | None = None,
    loki_diag: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    prom_diag = prom_diag or {}
    exporters_diag = exporters_diag or {}
    grafana_diag = grafana_diag or {}
    loki_diag = loki_diag or {}

    incidents: list[dict[str, Any]] = []

    auth = prom_diag.get("authority", {}) or {}
    if auth.get("state") != "healthy":
        incidents.append({
            "incident_id": "OBS-INCIDENT-AUTHORITY",
            "severity": "critical",
            "domain": "observability",
            "authority_impact": "high",
            "runtime_impact": "high",
            "explainable": True,
            "containment_policy": "observability_conservative_mode",
            "recommended_action": "verificar Prometheus (/api/v1/targets, runtimeinfo) y conectividad",
            "details": {"prometheus_state": auth.get("state"), "confidence": auth.get("confidence")},
        })

    staleness = detect_authority_staleness(prom_diag)
    if staleness.get("authority_freshness") in ("stale", "degraded"):
        incidents.append({
            "incident_id": "OBS-INCIDENT-STALE",
            "severity": "medium" if staleness.get("scrape_down_total", 0) == 0 else "high",
            "domain": "observability",
            "authority_impact": "medium",
            "runtime_impact": "moderate",
            "explainable": True,
            "containment_policy": "observability_conservative_mode",
            "recommended_action": "revisar targets stale/down y scrape intervals",
            "details": staleness,
        })

    exp = exporters_diag.get("classification", []) or []
    unreachable = [e for e in exp if e.get("status") in ("UNREACHABLE", "ACTIVE_DEGRADED") and not e.get("expected_offline")]
    if unreachable:
        nr = [e for e in unreachable if e.get("error_type") == "no_route_to_host"]
        incidents.append({
            "incident_id": "OBS-INCIDENT-SCRAPE",
            "severity": "high" if any(e.get("critical") for e in unreachable) else "medium",
            "domain": "observability",
            "authority_impact": "medium",
            "runtime_impact": "moderate" if any(e.get("critical") for e in unreachable) else "low",
            "explainable": True,
            "containment_policy": "observability_conservative_mode",
            "recommended_action": "revisar conectividad/exporters DOWN y errores lastError",
            "details": {
                "unreachable_total": len(unreachable),
                "no_route_to_host_total": len(nr),
                "examples": unreachable[:3],
            },
        })

    flap = (exporters_diag.get("summary", {}) or {}).get("flapping", {}) or {}
    if int(flap.get("flapping_total", 0) or 0) > 0:
        incidents.append({
            "incident_id": "OBS-INCIDENT-FLAPPING",
            "severity": "medium",
            "domain": "observability",
            "authority_impact": "medium",
            "runtime_impact": "low",
            "explainable": True,
            "containment_policy": "observability_conservative_mode",
            "recommended_action": "revisar targets con flapping (changes(up) alto)",
            "details": flap,
        })

    ds = diagnose_datasource_health(grafana_diag)
    if int(ds.get("datasource_drift_total", 0) or 0) > 0:
        incidents.append({
            "incident_id": "OBS-INCIDENT-DATASOURCE",
            "severity": "medium",
            "domain": "grafana",
            "authority_impact": "minimal",
            "runtime_impact": "low",
            "explainable": True,
            "containment_policy": "none",
            "recommended_action": "corregir orphan datasources en dashboards provisionados (no afecta authority)",
            "details": ds,
        })

    if not bool((loki_diag.get("platform", {}) or {}).get("up")):
        incidents.append({
            "incident_id": "OBS-INCIDENT-TOPOLOGY",
            "severity": "low",
            "domain": "loki",
            "authority_impact": "minimal",
            "runtime_impact": "low",
            "explainable": True,
            "containment_policy": "none",
            "recommended_action": "verificar Loki /ready y datasource",
            "details": {"loki": loki_diag.get("platform", {})},
        })

    if not incidents:
        incidents.append({
            "incident_id": "OBS-INCIDENT-NONE",
            "severity": "info",
            "domain": "observability",
            "authority_impact": "none",
            "runtime_impact": "none",
            "explainable": True,
            "containment_policy": "none",
            "recommended_action": "ninguna accion necesaria",
        })

    return incidents


def build_observability_incident_summary(incidents: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    incidents = incidents or []
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    ordered = sorted(incidents, key=lambda i: severity_order.get(i.get("severity", "info"), 99))
    active = [i for i in ordered if i.get("incident_id") != "OBS-INCIDENT-NONE"]
    return {
        "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
        "incidents_total": len(active),
        "incidents": ordered,
        "highest_severity": (active[0].get("severity") if active else "info"),
        "explainable": True,
    }


def calculate_live_observability_score(
    prom_diag: dict[str, Any] | None = None,
    exporters_diag: dict[str, Any] | None = None,
    datasource_diag: dict[str, Any] | None = None,
    loki_diag: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prom_diag = prom_diag or {}
    exporters_diag = exporters_diag or {}
    datasource_diag = datasource_diag or {}
    loki_diag = loki_diag or {}

    auth_state = (prom_diag.get("authority", {}) or {}).get("state", "degraded")
    base = 1.0 if auth_state == "healthy" else 0.2

    exp_sum = exporters_diag.get("summary", {}) or {}
    unreachable = int(exp_sum.get("unreachable_total", 0) or 0)
    no_route = int(exp_sum.get("no_route_to_host_total", 0) or 0)
    flapping_score = float((exp_sum.get("flapping", {}) or {}).get("flapping_score", 0.0) or 0.0)

    ds_drift = int(datasource_diag.get("datasource_drift_total", 0) or 0)
    loki_up = bool((loki_diag.get("platform", {}) or {}).get("up"))

    score = base
    score -= min(0.6, unreachable * 0.05)
    score -= min(0.3, no_route * 0.05)
    score -= min(0.3, (flapping_score / 100.0) * 0.3)
    score -= min(0.2, ds_drift * 0.02)
    if not loki_up:
        score -= 0.05

    final = round(max(0.0, min(1.0, score)) * 100, 1)
    level = "high" if final >= 85 else "medium" if final >= 65 else "low" if final >= 40 else "critical"

    return {
        "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
        "live_observability_score": final,
        "live_observability_level": level,
        "components": {
            "authority_state": auth_state,
            "unreachable_exporters": unreachable,
            "no_route_to_host": no_route,
            "flapping_score": flapping_score,
            "datasource_drift": ds_drift,
            "loki_up": loki_up,
        },
        "generated_at": _now(),
    }


def run_live_observability_diagnostics(
    extra_ctx: dict[str, Any] | None = None,
    live_prometheus_targets: dict[str, Any] | None = None,
    live_prometheus_config: dict[str, Any] | None = None,
    live_prometheus_runtimeinfo: dict[str, Any] | None = None,
    live_grafana_health: dict[str, Any] | None = None,
    live_loki_ready: dict[str, Any] | None = None,
    flapping_changes: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Run full live observability diagnostics.

    For tests: pass live_* fixtures to avoid network.
    """
    extra_ctx = extra_ctx or {}

    prom = diagnose_prometheus_authority(
        extra_ctx=extra_ctx,
        live_targets=live_prometheus_targets,
        live_config=live_prometheus_config,
        live_runtimeinfo=live_prometheus_runtimeinfo,
    )
    graf = diagnose_grafana_platform(extra_ctx=extra_ctx, live_health=live_grafana_health)
    loki = diagnose_loki_platform(extra_ctx=extra_ctx, live_ready=live_loki_ready)

    exporters = diagnose_exporters(live_prometheus_targets or {}, extra_ctx=extra_ctx, flapping_changes=flapping_changes)
    scrape = diagnose_scrape_health(live_prometheus_targets or {})
    ds = diagnose_datasource_health(graf)
    staleness = detect_authority_staleness(prom)
    instability = detect_scrape_instability(scrape, (exporters.get("summary", {}) or {}).get("flapping", {}))

    incidents = detect_observability_incidents(prom, exporters, graf, loki)
    incident_summary = build_observability_incident_summary(incidents)

    score = calculate_live_observability_score(prom, exporters, ds, loki)

    survivability = {
        "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
        "authority_survivability": "stable" if prom.get("authority", {}).get("state") == "healthy" else "degraded",
        "scrape_survivability": "stable" if scrape.get("scrape_failures_total", 0) == 0 else "degraded",
        "exporter_survivability": "stable" if exporters.get("summary", {}).get("unreachable_total", 0) == 0 else "degraded",
        "grafana_survivability": "supported",
        "loki_survivability": "stable" if (loki.get("platform", {}) or {}).get("up") else "degraded",
        "diagnostics_confidence": prom.get("authority", {}).get("confidence", "unknown"),
        "explainable": True,
    }

    result = {
        "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
        "generated_at": _now(),
        "prometheus": prom,
        "grafana": graf,
        "loki": loki,
        "exporters": exporters,
        "scrape": scrape,
        "datasources": ds,
        "authority_staleness": staleness,
        "scrape_instability": instability,
        "incidents": incident_summary,
        "survivability": survivability,
        "score": score,
        "strict_mode": _strict_mode(),
    }

    result["deterministic_signature"] = _hash({
        "prometheus": prom,
        "exporters": exporters,
        "scrape": scrape,
        "datasources": ds,
        "incidents": incident_summary,
        "survivability": survivability,
        "score": score,
    })

    return result
