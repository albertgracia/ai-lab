"""FASE OBS-31A.2: Grafana dashboard inventory.

Central inventory of all known Grafana dashboards with full metadata:
uid, title, datasource, tags, folder, panel_count, refresh_interval,
runtime_domain, owner, deprecated, experimental, inventory_aligned.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


GRAFANA_INVENTORY_CONTRACT_VERSION = "OBS-31A.2"


class DashboardHealth(str, Enum):
    HEALTHY = "healthy"
    STALE = "stale"
    BROKEN = "broken"
    LEGACY = "legacy"
    EXPERIMENTAL = "experimental"
    INVENTORY_DRIFT = "inventory_drift"
    RUNTIME_MISMATCH = "runtime_mismatch"
    DEPRECATED = "deprecated"
    UNKNOWN = "unknown"


class DatasourceType(str, Enum):
    PROMETHEUS = "prometheus"
    LOKI = "loki"
    TESTDATA = "testdata"
    UNKNOWN = "unknown"


_KNOWN_DATASOURCE_UID = "PBFA97CFB590B2093"
_KNOWN_LOKI_UID = "fflfh9qp8mxogc"

_KNOWN_DATASOURCES = [
    {"name": "Prometheus", "uid": _KNOWN_DATASOURCE_UID, "type": "prometheus",
     "url": "http://192.168.1.40:9090", "default": True, "accessible": True},
    {"name": "Loki", "uid": _KNOWN_LOKI_UID, "type": "loki",
     "url": "http://192.168.1.40:3100", "default": False, "accessible": True},
]


_AI_LAB_DASHBOARDS: list[dict[str, Any]] = [
    {"uid": "ai-lab-overview", "title": "AI-LAB Overview",
     "runtime_domain": "overview", "criticality": "critical",
     "semantic_owner": "runtime", "datasource_uid": _KNOWN_DATASOURCE_UID,
     "panel_count": 8, "refresh_interval": "30s", "tags": ["ai-lab", "overview"],
     "deprecated": False, "experimental": False,
     "inventory_aligned": True, "runtime_aligned": True},
    {"uid": "ai-lab-runtime", "title": "AI-LAB Runtime",
     "runtime_domain": "runtime", "criticality": "critical",
     "semantic_owner": "runtime", "datasource_uid": _KNOWN_DATASOURCE_UID,
     "panel_count": 12, "refresh_interval": "30s", "tags": ["ai-lab", "runtime"],
     "deprecated": False, "experimental": False,
     "inventory_aligned": True, "runtime_aligned": True},
    {"uid": "ai-lab-infra", "title": "AI-LAB Infrastructure",
     "runtime_domain": "infrastructure", "criticality": "high",
     "semantic_owner": "infrastructure", "datasource_uid": _KNOWN_DATASOURCE_UID,
     "panel_count": 6, "refresh_interval": "60s", "tags": ["ai-lab", "infra"],
     "deprecated": False, "experimental": False,
     "inventory_aligned": True, "runtime_aligned": True},
    {"uid": "ai-lab-gpus", "title": "AI-LAB GPUs",
     "runtime_domain": "gpu", "criticality": "critical",
     "semantic_owner": "gpu", "datasource_uid": _KNOWN_DATASOURCE_UID,
     "panel_count": 10, "refresh_interval": "15s", "tags": ["ai-lab", "gpu"],
     "deprecated": False, "experimental": False,
     "inventory_aligned": True, "runtime_aligned": True},
    {"uid": "ailab-runtime-protection", "title": "AI-LAB Runtime Protection",
     "runtime_domain": "slo", "criticality": "critical",
     "semantic_owner": "slo", "datasource_uid": _KNOWN_DATASOURCE_UID,
     "panel_count": 14, "refresh_interval": "15s", "tags": ["ai-lab", "slo"],
     "deprecated": False, "experimental": False,
     "inventory_aligned": True, "runtime_aligned": True},
]


_LEGACY_DASHBOARDS: list[dict[str, Any]] = [
    {"uid": "alpt7gt", "title": "Labrazahome Time-Series Analysis",
     "runtime_domain": "legacy", "criticality": "low",
     "semantic_owner": "infrastructure", "datasource_uid": _KNOWN_DATASOURCE_UID,
     "panel_count": 0, "tags": ["legacy", "labrazahome"], "deprecated": True},
    {"uid": "al6k9h6", "title": "Labrazahome Logs",
     "runtime_domain": "legacy", "criticality": "low",
     "semantic_owner": "infrastructure", "datasource_uid": _KNOWN_LOKI_UID,
     "panel_count": 0, "tags": ["legacy", "labrazahome"], "deprecated": True},
    {"uid": "aldh6t8", "title": "Windows Server NAS N5",
     "runtime_domain": "legacy", "criticality": "low",
     "semantic_owner": "infrastructure", "datasource_uid": _KNOWN_DATASOURCE_UID,
     "panel_count": 0, "tags": ["legacy", "windows"], "deprecated": True},
    {"uid": "alw8vm9", "title": "UniFi Cloud Gateway Fiber",
     "runtime_domain": "legacy", "criticality": "low",
     "semantic_owner": "infrastructure", "datasource_uid": _KNOWN_DATASOURCE_UID,
     "panel_count": 0, "tags": ["legacy", "unifi"], "deprecated": True},
    {"uid": "al79ptk", "title": "UniFi Access Points WiFi",
     "runtime_domain": "legacy", "criticality": "low",
     "semantic_owner": "infrastructure", "datasource_uid": _KNOWN_DATASOURCE_UID,
     "panel_count": 0, "tags": ["legacy", "unifi"], "deprecated": True},
    {"uid": "al2m9l8", "title": "UniFi Switch USW Flex 2.5G 8 PoE",
     "runtime_domain": "legacy", "criticality": "low",
     "semantic_owner": "infrastructure", "datasource_uid": _KNOWN_DATASOURCE_UID,
     "panel_count": 0, "tags": ["legacy", "unifi"], "deprecated": True},
]

_ALL_DASHBOARDS = _AI_LAB_DASHBOARDS + _LEGACY_DASHBOARDS


def build_dashboard_inventory() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for d in _ALL_DASHBOARDS:
        entry: dict[str, Any] = {
            "uid": d["uid"],
            "title": d["title"],
            "runtime_domain": d.get("runtime_domain", ""),
            "criticality": d.get("criticality", "low"),
            "semantic_owner": d.get("semantic_owner", ""),
            "datasource_uid": d.get("datasource_uid", _KNOWN_DATASOURCE_UID),
            "panel_count": d.get("panel_count", 0),
            "refresh_interval": d.get("refresh_interval", "60s"),
            "tags": d.get("tags", []),
            "deprecated": d.get("deprecated", False),
            "experimental": d.get("experimental", False),
            "inventory_aligned": d.get("inventory_aligned", True),
            "runtime_aligned": d.get("runtime_aligned", True),
            "health": classify_dashboard_health(d),
        }
        results.append(entry)
    return results


def classify_dashboard_health(dashboard: dict[str, Any]) -> str:
    if dashboard.get("deprecated", False):
        return DashboardHealth.DEPRECATED.value
    if dashboard.get("experimental", False):
        return DashboardHealth.EXPERIMENTAL.value
    if not dashboard.get("inventory_aligned", True):
        return DashboardHealth.INVENTORY_DRIFT.value
    if not dashboard.get("runtime_aligned", True):
        return DashboardHealth.RUNTIME_MISMATCH.value
    return DashboardHealth.HEALTHY.value


def get_dashboard_by_uid(uid: str) -> dict[str, Any] | None:
    for d in _ALL_DASHBOARDS:
        if d["uid"] == uid:
            return dict(d)
    return None


def get_dashboards_by_domain(domain: str) -> list[dict[str, Any]]:
    return [d for d in _ALL_DASHBOARDS if d.get("runtime_domain") == domain]


def get_dashboards_by_owner(owner: str) -> list[dict[str, Any]]:
    return [d for d in _ALL_DASHBOARDS if d.get("semantic_owner") == owner]


def build_inventory_summary() -> dict[str, Any]:
    inventory = build_dashboard_inventory()
    counts: dict[str, int] = {}
    for d in inventory:
        h = d.get("health", "unknown")
        counts[h] = counts.get(h, 0) + 1

    return {
        "contract_version": GRAFANA_INVENTORY_CONTRACT_VERSION,
        "timestamp": time.time(),
        "total_dashboards": len(inventory),
        "ai_lab_dashboards": len(_AI_LAB_DASHBOARDS),
        "legacy_dashboards": len(_LEGACY_DASHBOARDS),
        "health_summary": counts,
        "critical_healthy": sum(1 for d in inventory
                                  if d.get("criticality") in ("critical", "high")
                                  and d.get("health") == "healthy"),
        "critical_total": sum(1 for d in inventory
                               if d.get("criticality") in ("critical", "high")),
        "dashboards": inventory,
    }
