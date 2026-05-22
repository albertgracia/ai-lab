"""FASE 32B: Grafana Semantic Cleanup.

Transforms Grafana from a legacy dashboard collection into a
runtime-semantic observability layer aligned with AI-LAB cognition:
topology, entities, governance, degraded mode, inventory, maturity.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from runtime.observability.grafana_inventory import (
    GRAFANA_INVENTORY_CONTRACT_VERSION,
    DashboardHealth,
    _AI_LAB_DASHBOARDS,
    _LEGACY_DASHBOARDS,
    _ALL_DASHBOARDS,
    _KNOWN_DATASOURCE_UID,
    _KNOWN_DATASOURCES,
    build_dashboard_inventory,
)

GRAFANA_SEMANTIC_CONTRACT_VERSION = "32B"

GRAFANA_DASHBOARDS_DIR = Path("/opt/ai-lab/stacks/observability/grafana/provisioning/dashboards")

_FAKE_GPU_PATTERNS = re.compile(
    r"(?i)\b(a100|h100|h200|b100|b200|nvidia\s+a100|nvidia\s+h100|"
    r"rtx\s*5070|rtx\s*5080|rtx\s*5090|rtx\s*4090|tesla|t4|l4|v100|"
    r"mi250|mi300|mi350|l40s|a10|a16)\b"
)

_STALE_METRIC_PATTERNS = re.compile(
    r"(?i)\b(ailab_gpu_legacy|ailab_old_metric|prometheus_http_requests_total|"
    r"go_memstats|process_cpu_seconds_total|node_ntp|node_timex)\b"
)

_DATASOURCE_NAMES = {"prometheus": "PBFA97CFB590B2093", "loki": "fflfh9qp8mxogc"}

_DASHBOARD_TAXONOMIES = [
    "runtime", "topology", "governance", "gpu", "routing",
    "observability", "storage", "archive", "grounding", "reporting",
    "legacy", "experimental",
]

_RUNTIME_ENDPOINTS = [
    "/runtime/entities", "/runtime/topology", "/runtime/reports/discipline",
    "/runtime/reports/evidence", "/runtime/observability/audit",
    "/runtime/observability/targets", "/runtime/observability/dashboards",
    "/runtime/observability/metrics", "/runtime/observability/drift",
    "/runtime/observability/runtime-alignment", "/runtime/observability/cross-validate",
    "/runtime/observability/remediation-plan", "/runtime/observability/technical-debt",
    "/runtime/observability/execute-quick-wins", "/runtime/observability/execution-status",
    "/runtime/maturity", "/runtime/ui-alignment", "/runtime/sensors",
    "/runtime/cognitive-summary", "/runtime/grounding",
]


def _ensure_list(val: Any) -> list:
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [val]
    return []


def _load_dashboard_json_files() -> list[dict[str, Any]]:
    dashboards: list[dict[str, Any]] = []
    if not GRAFANA_DASHBOARDS_DIR.exists():
        return dashboards
    for fpath in sorted(GRAFANA_DASHBOARDS_DIR.rglob("*.json")):
        try:
            data = json.loads(fpath.read_text(errors="ignore"))
            data["_source_file"] = str(fpath.relative_to(GRAFANA_DASHBOARDS_DIR))
            dashboards.append(data)
        except (json.JSONDecodeError, OSError):
            pass
    return dashboards


def build_dashboard_inventory_32b() -> list[dict[str, Any]]:
    file_dashboards = _load_dashboard_json_files()
    inventory = build_dashboard_inventory()
    file_uids = {d.get("uid", "") for d in file_dashboards}

    for entry in inventory:
        uid = entry.get("uid", "")
        if uid in file_uids:
            entry["file_present"] = True
        else:
            entry["file_present"] = False

    for fd in file_dashboards:
        uid = fd.get("uid", "")
        if not any(e.get("uid") == uid for e in inventory):
            title = fd.get("title", fd.get("_source_file", "?"))
            tags = fd.get("tags", [])
            inventory.append({
                "uid": uid,
                "title": title,
                "runtime_domain": "legacy",
                "criticality": "low",
                "semantic_owner": "unknown",
                "datasource_uid": _KNOWN_DATASOURCE_UID,
                "panel_count": len(fd.get("panels", [])),
                "tags": tags,
                "deprecated": True,
                "experimental": False,
                "inventory_aligned": False,
                "runtime_aligned": False,
                "health": "deprecated",
                "file_present": True,
            })

    return inventory


def detect_fake_gpu_panels(
    dashboards: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if dashboards is None:
        dashboards = _load_dashboard_json_files()
    for db in dashboards:
        uid = db.get("uid", db.get("_source_file", "?"))
        db_json = json.dumps(db)
        matches = _FAKE_GPU_PATTERNS.findall(db_json)
        if matches:
            found.append({
                "dashboard_uid": uid,
                "dashboard_title": db.get("title", uid),
                "fake_gpus": sorted(set(matches)),
                "count": len(set(matches)),
                "severity": "critical",
            })
    return found


def detect_stale_panels(
    dashboards: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if dashboards is None:
        dashboards = _load_dashboard_json_files()
    for db in dashboards:
        uid = db.get("uid", db.get("_source_file", "?"))
        db_json = json.dumps(db)
        stale_matches = _STALE_METRIC_PATTERNS.findall(db_json)
        if stale_matches:
            found.append({
                "dashboard_uid": uid,
                "dashboard_title": db.get("title", uid),
                "stale_metrics": sorted(set(stale_matches)),
                "count": len(set(stale_matches)),
                "severity": "medium",
            })
    return found


def detect_orphan_datasources(
    dashboards: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if dashboards is None:
        dashboards = _load_dashboard_json_files()
    known_uids = {ds["uid"] for ds in _KNOWN_DATASOURCES}
    known_dashboard_uids = {db.get("uid", "") for db in dashboards}
    skip_patterns = re.compile(r'^(--\s*\w+\s*--|grafana|\$\{ds_\w+\})$', re.IGNORECASE)
    seen_refs: set[str] = set()
    for db in dashboards:
        uid = db.get("uid", db.get("_source_file", "?"))
        db_json = json.dumps(db)
        for pattern in (r'"uid"\s*:\s*"([^"]+)"', r'"datasource"\s*:\s*\{[^}]*"uid"\s*:\s*"([^"]+)"'):
            refs = set(re.findall(pattern, db_json))
            for ref in refs:
                if not ref:
                    continue
                if skip_patterns.match(ref):
                    continue
                if ref in known_dashboard_uids:
                    continue
                if ref in known_uids or ref == _KNOWN_DATASOURCE_UID:
                    continue
                dedup_key = f"{uid}:{ref}"
                if dedup_key in seen_refs:
                    continue
                seen_refs.add(dedup_key)
                found.append({
                    "dashboard_uid": uid,
                    "dashboard_title": db.get("title", uid),
                    "orphan_datasource_uid": ref,
                    "severity": "high",
                })
    return found


def detect_metric_drift(
    dashboards: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if dashboards is None:
        dashboards = _load_dashboard_json_files()
    for db in dashboards:
        uid = db.get("uid", db.get("_source_file", "?"))
        db_json = json.dumps(db)
        metric_refs = set(re.findall(r'(?i)ailab_\w+', db_json))
        if metric_refs:
            found.append({
                "dashboard_uid": uid,
                "dashboard_title": db.get("title", uid),
                "metric_count": len(metric_refs),
                "metrics": sorted(metric_refs),
            })
    return found


def detect_topology_dashboard_alignment(
    dashboards: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if dashboards is None:
        dashboards = _load_dashboard_json_files()
    for db in dashboards:
        uid = db.get("uid", db.get("_source_file", "?"))
        title = (db.get("title", "") or "").lower()
        db_json = json.dumps(db).lower()
        if "topology" not in title and "topology" not in db_json:
            continue
        issues = []
        if "rx9070xt" in db_json:
            issues.append("RX9070XT name drift (should be RX9070)")
        if "rtx5070" in db_json or "a100" in db_json:
            issues.append("fake GPU in topology dashboard")
        if issues:
            found.append({
                "dashboard_uid": uid,
                "dashboard_title": db.get("title", uid),
                "issues": issues,
                "severity": "medium",
            })
    return found


def calculate_grafana_alignment_score(
    total_dashboards: int = 0,
    fake_panels: int = 0,
    stale_panels: int = 0,
    orphan_datasources: int = 0,
    metric_drifts: int = 0,
    topology_issues: int = 0,
    runtime_aligned_count: int = 0,
) -> dict[str, Any]:
    total = max(total_dashboards, 1)
    penalties = 0.0
    details: dict[str, Any] = {}

    if fake_panels > 0:
        p = min(1.0, fake_panels * 0.25)
        penalties += p
        details["fake_panels_penalty"] = round(p, 2)
    else:
        details["fake_panels_penalty"] = 0.0

    if stale_panels > 0:
        p = min(1.0, stale_panels * 0.1)
        penalties += p
        details["stale_panels_penalty"] = round(p, 2)
    else:
        details["stale_panels_penalty"] = 0.0

    if orphan_datasources > 0:
        p = min(1.0, orphan_datasources * 0.2)
        penalties += p
        details["orphan_datasources_penalty"] = round(p, 2)
    else:
        details["orphan_datasources_penalty"] = 0.0

    if metric_drifts > 0:
        p = min(1.0, metric_drifts * 0.05)
        penalties += p
        details["metric_drift_penalty"] = round(p, 2)
    else:
        details["metric_drift_penalty"] = 0.0

    if topology_issues > 0:
        p = min(1.0, topology_issues * 0.15)
        penalties += p
        details["topology_issues_penalty"] = round(p, 2)
    else:
        details["topology_issues_penalty"] = 0.0

    alignment_bonus = min(1.0, runtime_aligned_count / total)
    details["runtime_alignment_bonus"] = round(alignment_bonus, 2)

    base_score = 100.0
    raw = base_score - (penalties * 100.0 / total)
    overall = min(100.0, max(0.0, raw * (0.7 + 0.3 * alignment_bonus)))

    if overall >= 90:
        level = "high"
    elif overall >= 70:
        level = "medium"
    elif overall >= 50:
        level = "low"
    else:
        level = "critical"

    return {
        "overall_score": round(overall, 1),
        "level": level,
        "factors": details,
        "penalties": {
            "fake_panels": fake_panels,
            "stale_panels": stale_panels,
            "orphan_datasources": orphan_datasources,
            "metric_drifts": metric_drifts,
            "topology_issues": topology_issues,
        },
        "runtime_aligned_count": runtime_aligned_count,
        "total_dashboards": total,
    }


def build_grafana_semantic_summary(
    inventory: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if inventory is None:
        inventory = build_dashboard_inventory_32b()

    dashboards = _load_dashboard_json_files()

    fake_gpu = detect_fake_gpu_panels(dashboards)
    stale = detect_stale_panels(dashboards)
    orphan = detect_orphan_datasources(dashboards)
    metric_drift = detect_metric_drift(dashboards)
    topology = detect_topology_dashboard_alignment(dashboards)

    runtime_aligned = sum(1 for d in inventory if d.get("runtime_aligned", False))
    total_dbs = len(inventory)

    score = calculate_grafana_alignment_score(
        total_dashboards=total_dbs,
        fake_panels=len(fake_gpu),
        stale_panels=len(stale),
        orphan_datasources=len(orphan),
        metric_drifts=len(metric_drift),
        topology_issues=len(topology),
        runtime_aligned_count=runtime_aligned,
    )

    return {
        "timestamp": time.time(),
        "contract_version": GRAFANA_SEMANTIC_CONTRACT_VERSION,
        "grafana_alignment_score": score,
        "inventory": {
            "total_dashboards_file": len(dashboards),
            "total_inventory": total_dbs,
            "runtime_aligned": runtime_aligned,
            "legacy": sum(1 for d in inventory if d.get("deprecated", False)),
            "experimental": sum(1 for d in inventory if d.get("experimental", False)),
            "active": sum(1 for d in inventory if not d.get("deprecated", False) and not d.get("experimental", False)),
        },
        "issues": {
            "fake_gpu_panels": fake_gpu,
            "stale_panels": stale,
            "orphan_datasources": orphan,
            "metric_drift": metric_drift,
            "topology_issues": topology,
        },
        "summary": {
            "total_fake_gpu_panels": len(fake_gpu),
            "total_stale_panels": len(stale),
            "total_orphan_datasources": len(orphan),
            "total_metric_drifts": len(metric_drift),
            "total_topology_issues": len(topology),
            "total_issues": len(fake_gpu) + len(stale) + len(orphan) + len(metric_drift) + len(topology),
        },
    }
