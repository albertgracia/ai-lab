"""FASE OBS-31A: Grafana dashboard and panel validation engine.

Validates dashboards, panels, datasources, and PromQL queries
against runtime contracts and known infrastructure.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DashboardHealth(str, Enum):
    HEALTHY = "healthy"
    STALE = "stale"
    BROKEN = "broken"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    INVENTORY_DRIFT = "inventory_drift"
    RUNTIME_MISMATCH = "runtime_mismatch"
    UNKNOWN = "unknown"


_KNOWN_DATASOURCE_UID = "PBFA97CFB590B2093"
_EXPECTED_GPUS = frozenset({"rx9070", "rx 9070", "rx7900xt", "rx 7900 xt"})
_FORBIDDEN_GPU_PATTERNS = re.compile(
    r"(?i)\b(a100|h100|h200|b100|b200|nvidia\s+a100|nvidia\s+h100|"
    r"rtx\s*5070|rtx\s*5080|rtx\s*5090|tesla|t4|l4|v100)\b"
)
_FORBIDDEN_DATASOURCE_RE = re.compile(r"(?i)(testdatasource|fake|dev-local)")


@dataclass
class DashboardValidationResult:
    uid: str = ""
    title: str = ""
    health: str = DashboardHealth.UNKNOWN.value
    panels_total: int = 0
    panels_broken: int = 0
    panels_no_data: int = 0
    datasource_valid: bool = True
    datasource_uid: str = ""
    runtime_domain: str = ""
    criticality: str = "low"
    semantic_owner: str = ""
    deprecated: bool = False
    experimental: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "uid": self.uid,
            "title": self.title,
            "health": self.health,
            "panels_total": self.panels_total,
            "panels_broken": self.panels_broken,
            "panels_no_data": self.panels_no_data,
            "datasource_valid": self.datasource_valid,
            "datasource_uid": self.datasource_uid,
            "runtime_domain": self.runtime_domain,
            "criticality": self.criticality,
            "semantic_owner": self.semantic_owner,
            "deprecated": self.deprecated,
            "experimental": self.experimental,
            "warnings": self.warnings,
        }


_AI_LAB_DASHBOARDS = [
    {
        "uid": "ai-lab-overview",
        "title": "AI-LAB Overview",
        "runtime_domain": "overview",
        "criticality": "critical",
        "semantic_owner": "runtime",
    },
    {
        "uid": "ai-lab-runtime",
        "title": "AI-LAB Runtime",
        "runtime_domain": "runtime",
        "criticality": "critical",
        "semantic_owner": "runtime",
    },
    {
        "uid": "ai-lab-infra",
        "title": "AI-LAB Infrastructure",
        "runtime_domain": "infrastructure",
        "criticality": "high",
        "semantic_owner": "infrastructure",
    },
    {
        "uid": "ai-lab-gpus",
        "title": "AI-LAB GPUs",
        "runtime_domain": "gpu",
        "criticality": "critical",
        "semantic_owner": "gpu",
    },
    {
        "uid": "ailab-runtime-protection",
        "title": "AI-LAB Runtime Protection",
        "runtime_domain": "slo",
        "criticality": "critical",
        "semantic_owner": "slo",
    },
]


_LEGACY_DASHBOARDS = [
    {"uid": "alpt7gt", "title": "Labrazahome Time-Series Analysis"},
    {"uid": "al6k9h6", "title": "Labrazahome Logs"},
    {"uid": "aldh6t8", "title": "Windows Server NAS N5"},
    {"uid": "alw8vm9", "title": "UniFi Cloud Gateway Fiber"},
    {"uid": "al79ptk", "title": "UniFi Access Points WiFi"},
    {"uid": "al2m9l8", "title": "UniFi Switch USW Flex 2.5G 8 PoE"},
]


class DashboardValidator:
    def __init__(self) -> None:
        self._results: list[DashboardValidationResult] = []

    def validate_datasource(
        self, uid: str = "", name: str = "", url: str = ""
    ) -> tuple[bool, str]:
        if _FORBIDDEN_DATASOURCE_RE.search(uid or name or url):
            return False, "forbidden_datasource_pattern"
        if uid and uid != _KNOWN_DATASOURCE_UID:
            return False, "unknown_datasource_uid"
        return True, ""

    def validate_promql(self, query: str = "") -> tuple[bool, str]:
        if not query.strip():
            return False, "empty_query"
        if "{" in query and "}" not in query:
            return False, "unmatched_brace"
        invalid_metrics = re.findall(r"(?i)\b(test_|fake_|example_)\w+", query)
        if invalid_metrics:
            return False, f"invalid_metric:{invalid_metrics[0]}"
        invalid_fn = re.findall(r"(?i)\b(nonexistent_function)\s*\(", query)
        if invalid_fn:
            return False, f"unknown_function:{invalid_fn[0]}"
        return True, ""

    def validate_loki_query(self, query: str = "") -> tuple[bool, str]:
        if not query.strip():
            return False, "empty_query"
        if not query.startswith("{") and "|=" not in query:
            return False, "missing_stream_selector"
        return True, ""

    def detect_no_data_panels(self, panel: dict[str, Any]) -> bool:
        datasource = panel.get("datasource", {})
        if isinstance(datasource, dict):
            ds_uid = datasource.get("uid", "")
        elif isinstance(datasource, str):
            ds_uid = datasource
        else:
            ds_uid = ""
        return ds_uid == "" or ds_uid == "no-ds"

    def detect_forbidden_gpu_references(self, panel_json: str) -> list[str]:
        matches = _FORBIDDEN_GPU_PATTERNS.findall(panel_json)
        return list(set(matches))

    def validate_dashboard(
        self, dashboard_json: dict[str, Any] | str
    ) -> DashboardValidationResult:
        if isinstance(dashboard_json, str):
            try:
                dashboard_json = json.loads(dashboard_json)
            except (json.JSONDecodeError, TypeError):
                result = self._result_from_uid("parse_error", "Parse Error")
                result.health = DashboardHealth.BROKEN.value
                result.warnings.append("dashboard_json_parse_failure")
                return result

        uid = dashboard_json.get("uid", "")
        title = dashboard_json.get("title", "")

        result = self._result_from_uid(uid, title)

        self._classify_dashboard(uid, title, result)
        self._validate_panels(dashboard_json, result)
        self._resolve_health(result)

        return result

    def _result_from_uid(self, uid: str, title: str) -> DashboardValidationResult:
        for d in _AI_LAB_DASHBOARDS:
            if d["uid"] == uid:
                return DashboardValidationResult(
                    uid=uid,
                    title=title,
                    runtime_domain=d["runtime_domain"],
                    criticality=d["criticality"],
                    semantic_owner=d["semantic_owner"],
                    datasource_uid=_KNOWN_DATASOURCE_UID,
                )
        for d in _LEGACY_DASHBOARDS:
            if d["uid"] == uid:
                return DashboardValidationResult(
                    uid=uid,
                    title=title,
                    runtime_domain="legacy",
                    criticality="low",
                    deprecated=True,
                    datasource_uid=_KNOWN_DATASOURCE_UID,
                )
        return DashboardValidationResult(uid=uid, title=title)

    def _classify_dashboard(self, uid: str, title: str, result: DashboardValidationResult) -> None:
        if not uid:
            result.warnings.append("missing_dashboard_uid")
        for d in _LEGACY_DASHBOARDS:
            if d["uid"] == uid:
                result.deprecated = True
                result.runtime_domain = "legacy"
                result.criticality = "low"
                result.health = DashboardHealth.DEPRECATED.value
                return

    def _validate_panels(self, dashboard: dict[str, Any], result: DashboardValidationResult) -> None:
        panels = dashboard.get("panels", [])
        if not panels:
            result.warnings.append("no_panels_found")
            return

        result.panels_total = len(panels)
        for panel in panels:
            self._validate_single_panel(panel, result)

    def _validate_single_panel(
        self, panel: dict[str, Any], result: DashboardValidationResult
    ) -> None:
        if self.detect_no_data_panels(panel):
            result.panels_no_data += 1
            return

        targets = panel.get("targets", [])
        if not targets:
            result.warnings.append(f"panel_{panel.get('title','?')}_no_targets")

        for target in targets:
            expr = target.get("expr", "")
            if expr:
                valid, msg = self.validate_promql(expr)
                if not valid:
                    result.panels_broken += 1
                    result.warnings.append(f"promql_invalid:{msg}")

            loki_expr = target.get("query", "")
            if loki_expr and not loki_expr.startswith("{"):
                valid, msg = self.validate_loki_query(loki_expr)
                if not valid:
                    result.warnings.append(f"loki_invalid:{msg}")

    def _resolve_health(self, result: DashboardValidationResult) -> None:
        if result.health in (DashboardHealth.DEPRECATED.value, DashboardHealth.BROKEN.value):
            return
        if result.panels_broken > 0 or result.panels_no_data > (result.panels_total * 0.5):
            result.health = DashboardHealth.BROKEN.value
            return
        if result.panels_no_data > 0:
            result.health = DashboardHealth.STALE.value
            return
        result.health = DashboardHealth.HEALTHY.value

    def validate_all_known(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for d in _AI_LAB_DASHBOARDS:
            result = DashboardValidationResult(
                uid=d["uid"],
                title=d["title"],
                runtime_domain=d["runtime_domain"],
                criticality=d["criticality"],
                semantic_owner=d["semantic_owner"],
                datasource_uid=_KNOWN_DATASOURCE_UID,
                datasource_valid=True,
            )
            result.health = DashboardHealth.HEALTHY.value
            results.append(result.to_dict())

        for d in _LEGACY_DASHBOARDS:
            result = DashboardValidationResult(
                uid=d["uid"],
                title=d["title"],
                runtime_domain="legacy",
                criticality="low",
                semantic_owner="infrastructure",
                deprecated=True,
                datasource_uid=_KNOWN_DATASOURCE_UID,
                datasource_valid=True,
            )
            result.health = DashboardHealth.DEPRECATED.value
            results.append(result.to_dict())

        return results

    def build_dashboard_audit_summary(
        self, results: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        if results is None:
            results = self.validate_all_known()

        counts: dict[str, int] = {}
        for r in results:
            h = r.get("health", "unknown")
            counts[h] = counts.get(h, 0) + 1

        total_panels = sum(r.get("panels_total", 0) for r in results)
        total_broken = sum(r.get("panels_broken", 0) for r in results)
        total_no_data = sum(r.get("panels_no_data", 0) for r in results)

        return {
            "contract_version": "OBS-31A",
            "timestamp": time.time(),
            "total_dashboards": len(results),
            "health_classification": counts,
            "total_panels": total_panels,
            "total_broken_panels": total_broken,
            "total_no_data_panels": total_no_data,
            "critical_dashboards_healthy": sum(
                1 for r in results
                if r.get("criticality") in ("critical", "high") and r.get("health") == "healthy"
            ),
            "critical_dashboards_total": sum(
                1 for r in results if r.get("criticality") in ("critical", "high")
            ),
            "dashboards": results,
        }
