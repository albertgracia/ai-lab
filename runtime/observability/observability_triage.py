"""AI-LAB Autonomous Observability Triage — read-only layer.

Collects live Prometheus targets, feeds into the existing triage engine,
links findings to operator intent, and produces structured triage reports.

NO auto-remediation. NO mutations. NO background loops. Read-only.
"""

import json
import os
import time
from typing import Any

OBSERVABILITY_TRIAGE_CONTRACT_VERSION = "OBSERVABILITY-TRIAGE-01"

_PROMETHEUS_URL = os.environ.get(
    "AI_LAB_PROMETHEUS_URL",
    "http://192.168.1.40:9090",
)

TRIAGE_SOURCE = "observability_triage"
SAFE_TO_AUTO_EXECUTE = False  # hardcoded false in this phase


def collect_prometheus_snapshot(
    prometheus_url: str = _PROMETHEUS_URL,
) -> dict[str, Any]:
    """Fetch live Prometheus targets and return a structured snapshot.

    Returns a dict with:
      - status: ok | error
      - active_total: int
      - down_total: int
      - targets: list of structured target entries
      - error: str (if status=error)
      - fetch_time_ms: float
    """
    try:
        from runtime.observability.prometheus_audit import fetch_prometheus_targets

        raw = fetch_prometheus_targets(prometheus_url)
    except Exception as exc:
        return {
            "status": "error",
            "error": f"fetch_failed:{exc}",
            "active_total": 0,
            "down_total": 0,
            "targets": [],
            "fetch_time_ms": 0,
        }

    if raw.get("status") != "ok":
        return {
            "status": "error",
            "error": raw.get("error", "unknown"),
            "active_total": 0,
            "down_total": 0,
            "targets": [],
            "fetch_time_ms": raw.get("fetch_time_ms", 0),
        }

    active = raw.get("active", [])
    targets = []
    down_count = 0
    for t in active:
        labels = t.get("labels", {}) or {}
        health = t.get("health", "unknown")
        last_scrape = t.get("lastScrape", "") or ""
        scrape_duration = t.get("lastScrapeDuration", 0) or 0
        target_url = t.get("scrapeUrl", "") or ""
        if health == "down":
            down_count += 1
        targets.append({
            "job": labels.get("job", "unknown"),
            "instance": labels.get("instance", "unknown"),
            "health": health,
            "last_scrape": last_scrape,
            "scrape_duration_ms": scrape_duration,
            "url": target_url,
        })

    return {
        "status": "ok",
        "active_total": len(active),
        "down_total": down_count,
        "targets": targets,
        "fetch_time_ms": raw.get("fetch_time_ms", 0),
    }


def _classify_triage_severity(
    prometheus_snapshot: dict[str, Any],
    triage_incidents: list[dict[str, Any]],
) -> str:
    """Classify overall observability triage severity."""
    if prometheus_snapshot.get("status") == "error":
        return "high"

    down_total = prometheus_snapshot.get("down_total", 0)
    active_total = prometheus_snapshot.get("active_total", 0)

    for inc in triage_incidents:
        if inc.get("severity") in ("critical",):
            return "critical"

    if down_total > 3:
        return "critical"
    if down_total > 1:
        return "high"
    if active_total == 0:
        return "high"

    for inc in triage_incidents:
        if inc.get("severity") in ("high",):
            return "high"
        if inc.get("severity") in ("warning",):
            return "medium"

    if down_total > 0:
        return "medium"

    return "info"


def _build_symptom(
    prometheus_snapshot: dict[str, Any],
    triage_incidents: list[dict[str, Any]],
    severity: str,
) -> str:
    """Build a human-readable symptom description."""
    active_total = prometheus_snapshot.get("active_total", 0)
    down_total = prometheus_snapshot.get("down_total", 0)
    error = prometheus_snapshot.get("error", "")

    if severity == "critical":
        if down_total > 3:
            return f"{down_total} Prometheus targets down — critical infrastructure degradation"
        if active_total == 0:
            return "No Prometheus targets reachable — observability plane offline"
        return "Critical active incidents detected in runtime triage"

    if severity == "high":
        if down_total > 1:
            return f"{down_total} Prometheus targets down — partial observability loss"
        if error:
            return f"Prometheus fetch failed: {error}"
        return "High-severity incidents active in runtime triage"

    if severity == "medium":
        if down_total > 0:
            return f"{down_total} Prometheus targets down — non-critical"
        return "Medium-severity incidents active in runtime triage"

    if active_total == 0:
        return "No Prometheus data available"
    return "All observability targets healthy — no active triage incidents"


def _build_evidence(
    prometheus_snapshot: dict[str, Any],
    triage_incidents: list[dict[str, Any]],
) -> list[str]:
    """Build evidence list from Prometheus snapshot and triage incidents."""
    evidence = []

    if prometheus_snapshot.get("status") == "error":
        evidence.append(f"prometheus_fetch_error:{prometheus_snapshot.get('error')}")
    else:
        evidence.append(
            f"prometheus_targets:active={prometheus_snapshot.get('active_total')},"
            f"down={prometheus_snapshot.get('down_total')},"
            f"fetch_ms={prometheus_snapshot.get('fetch_time_ms')}"
        )

    down_targets = [
        t for t in prometheus_snapshot.get("targets", []) if t.get("health") == "down"
    ]
    for t in down_targets:
        evidence.append(f"target_down:{t.get('job')}/{t.get('instance')}")

    for inc in triage_incidents[:5]:
        evidence.append(f"triage_incident:{inc.get('incident_id')}[{inc.get('severity')}]")

    return evidence[:20]


def _build_likely_causes(
    triage_incidents: list[dict[str, Any]],
    prometheus_snapshot: dict[str, Any],
) -> list[str]:
    """Extract likely root causes from triage incidents and Prometheus state."""
    causes: list[str] = []

    down_targets = [
        t for t in prometheus_snapshot.get("targets", []) if t.get("health") == "down"
    ]
    for t in down_targets:
        job = t.get("job", "unknown")
        causes.append(f"scrape_target_down:{job}")

    for inc in triage_incidents[:5]:
        for rc in inc.get("probable_root_causes", []):
            if rc not in causes:
                causes.append(rc)

    if prometheus_snapshot.get("status") == "error":
        causes.append("prometheus_unreachable")

    return causes[:8]


def _build_impact(
    prometheus_snapshot: dict[str, Any],
    triage_incidents: list[dict[str, Any]],
    severity: str,
) -> str:
    """Build impact description."""
    active_total = prometheus_snapshot.get("active_total", 0)
    down_total = prometheus_snapshot.get("down_total", 0)
    high_count = sum(1 for i in triage_incidents if i.get("severity") == "high")
    critical_count = sum(1 for i in triage_incidents if i.get("severity") == "critical")

    parts = []
    if down_total > 0:
        parts.append(f"{down_total}/{active_total} Prometheus targets down")
    if critical_count > 0 or high_count > 0:
        parts.append(f"{high_count} high, {critical_count} critical active incidents")
    if not parts:
        if severity == "info":
            return "No observable impact — routine health"
        return f"Severity level {severity} with no immediate impact vectors"
    return "; ".join(parts)


def _build_recommended_actions(
    prometheus_snapshot: dict[str, Any],
    triage_incidents: list[dict[str, Any]],
    severity: str,
) -> list[dict[str, Any]]:
    """Build recommended actions from triage incidents and Prometheus state."""
    actions: list[dict[str, Any]] = []

    down_targets = [
        t for t in prometheus_snapshot.get("targets", []) if t.get("health") == "down"
    ]
    for t in down_targets:
        job = t.get("job", "unknown")
        instance = t.get("instance", "unknown")
        actions.append({
            "action": f"investigate_down_target:{job}",
            "target": instance,
            "reason": f"Prometheus target {job}/{instance} is down",
            "requires_approval": True,
            "safe_to_auto_execute": SAFE_TO_AUTO_EXECUTE,
        })

    for inc in triage_incidents[:5]:
        for hint in inc.get("remediation_hints", [])[:2]:
            actions.append({
                "action": hint,
                "target": inc.get("category", "unknown"),
                "reason": f"triage incident {inc.get('incident_id')} ({inc.get('severity')})",
                "requires_approval": severity in ("high", "critical"),
                "safe_to_auto_execute": SAFE_TO_AUTO_EXECUTE,
            })

    if prometheus_snapshot.get("status") == "error":
        actions.append({
            "action": "verify_prometheus_connectivity",
            "target": _PROMETHEUS_URL,
            "reason": "Prometheus fetch failed — observability plane may be unavailable",
            "requires_approval": True,
            "safe_to_auto_execute": SAFE_TO_AUTO_EXECUTE,
        })

    if not actions:
        actions.append({
            "action": "continue_monitoring",
            "target": "observability",
            "reason": "No active findings requiring action",
            "requires_approval": False,
            "safe_to_auto_execute": SAFE_TO_AUTO_EXECUTE,
        })

    return actions[:10]


def _build_next_validation_commands(severity: str) -> list[str]:
    """Build next validation steps based on severity."""
    commands = [
        "curl -s http://192.168.1.30:8008/health | jq .",
        "curl -s 'http://192.168.1.40:9090/api/v1/targets' | jq '.data.activeTargets[] | {job: .labels.job, health}'",
    ]

    if severity in ("high", "critical"):
        commands.extend([
            "curl -s http://192.168.1.30:8008/runtime/triage/summary | jq .",
            "curl -s http://192.168.1.30:8008/slo/health | jq .",
            "curl -s http://192.168.1.40:9090/api/v1/alerts | jq '.data.alerts[] | {name: .labels.alertname, state}'",
        ])

    return commands


def build_observability_triage_report(
    prometheus_url: str = _PROMETHEUS_URL,
    operator_intent_text: str | None = None,
    *,
    now: float | None = None,
) -> dict[str, Any]:
    """Build a complete observability triage report.

    Collects live Prometheus targets, integrates with the runtime triage
    engine, and optionally links to operator intent reasoning.

    Returns structured dict matching the OBSERVABILITY-TRIAGE-01 schema.
    """
    ts = now if now is not None else time.time()

    prom_snapshot = collect_prometheus_snapshot(prometheus_url)

    triage_incidents: list[dict[str, Any]] = []
    triage_summary: dict[str, Any] = {}
    try:
        from runtime.triage.autonomous_triage import (
            build_runtime_triage_snapshot,
            get_active_triage_incidents,
            get_triage_summary,
        )
        build_runtime_triage_snapshot()
        triage_incidents = get_active_triage_incidents()
        triage_summary = get_triage_summary()
    except Exception:
        triage_summary = {"error": "triage_engine_unavailable"}

    operator_intent_result: dict[str, Any] | None = None
    if operator_intent_text:
        try:
            from runtime.operator_intent.operator_intent_reasoning import (
                analyze_operator_intent,
            )
            operator_intent_result = analyze_operator_intent(operator_intent_text)
        except Exception as exc:
            operator_intent_result = {"error": str(exc)}

    severity = _classify_triage_severity(prom_snapshot, triage_incidents)
    symptom = _build_symptom(prom_snapshot, triage_incidents, severity)
    evidence = _build_evidence(prom_snapshot, triage_incidents)
    likely_causes = _build_likely_causes(triage_incidents, prom_snapshot)
    impact = _build_impact(prom_snapshot, triage_incidents, severity)
    recommended_actions = _build_recommended_actions(
        prom_snapshot, triage_incidents, severity
    )
    next_validation_commands = _build_next_validation_commands(severity)

    triage_id = f"OBS-TRIAGE-{int(ts)}-{len(triage_incidents)}"

    components: list[str] = []
    if prom_snapshot.get("down_total", 0) > 0:
        components.append("prometheus_targets")
    if triage_incidents:
        domains = set()
        for inc in triage_incidents:
            domains.add(inc.get("category", "unknown"))
        components.extend(sorted(domains)[:5])

    sources_available: list[str] = ["prometheus_api"]
    if triage_summary and not triage_summary.get("error"):
        sources_available.append("runtime_triage")
    if operator_intent_result is not None and not operator_intent_result.get("error"):
        sources_available.append("operator_intent_reasoning")

    return {
        "triage_id": triage_id,
        "timestamp": ts,
        "source": TRIAGE_SOURCE,
        "component": components[0] if components else "observability",
        "components_affected": components,
        "status": "active" if severity != "info" else "healthy",
        "severity": severity,
        "symptom": symptom,
        "evidence": evidence,
        "evidence_summary": {
            "active_prometheus_targets": prom_snapshot.get("active_total", 0),
            "down_prometheus_targets": prom_snapshot.get("down_total", 0),
            "active_triage_incidents": len(triage_incidents),
            "prometheus_status": prom_snapshot.get("status", "unknown"),
            "sources_available": sources_available,
        },
        "likely_causes": likely_causes,
        "likely_root_causes": [
            {"cause": c, "confidence": "medium", "source": "heuristic"}
            for c in likely_causes
        ],
        "confidence": _calculate_triage_confidence(
            prom_snapshot, triage_incidents, operator_intent_result
        ),
        "impact": impact,
        "recommended_actions": recommended_actions,
        "requires_approval": severity in ("high", "critical"),
        "safe_to_auto_execute": SAFE_TO_AUTO_EXECUTE,
        "operator_intent_link": (
            {
                "input": operator_intent_text,
                "classification": operator_intent_result.get("intent"),
                "risk": operator_intent_result.get("risk"),
                "requires_approval": operator_intent_result.get("requires_approval"),
            }
            if operator_intent_result
            else None
        ),
        "next_validation_commands": next_validation_commands,
        "contract_version": OBSERVABILITY_TRIAGE_CONTRACT_VERSION,
        "prometheus_snapshot": {
            "status": prom_snapshot.get("status"),
            "active_total": prom_snapshot.get("active_total"),
            "down_total": prom_snapshot.get("down_total"),
            "fetch_time_ms": prom_snapshot.get("fetch_time_ms"),
        },
        "triage_summary": {
            "total_incidents": triage_summary.get("total_incidents", 0),
            "total_critical": triage_summary.get("total_critical", 0),
            "total_high": triage_summary.get("total_high", 0),
            "total_warning": triage_summary.get("total_warning", 0),
        },
    }


def _calculate_triage_confidence(
    prometheus_snapshot: dict[str, Any],
    triage_incidents: list[dict[str, Any]],
    operator_intent_result: dict[str, Any] | None,
) -> float:
    sources = prometheus_snapshot.get("status") == "ok"
    triage_available = bool(triage_incidents) or True
    operator_available = operator_intent_result is not None

    base = 0.5
    if sources:
        base += 0.2
    if triage_available:
        base += 0.15
    if operator_available:
        base += 0.15

    return min(1.0, base)
