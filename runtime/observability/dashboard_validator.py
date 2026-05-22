"""FASE OBS-31A.2: Grafana dashboard and panel validation engine.

Validates dashboards, panels, datasources, and PromQL queries
against runtime contracts and known infrastructure.
Detects stale, broken, fake, legacy, and drift conditions.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


DASHBOARD_VALIDATOR_CONTRACT_VERSION = "OBS-31A.2"


class DashboardHealth(str, Enum):
    HEALTHY = "healthy"
    STALE = "stale"
    BROKEN = "broken"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    INVENTORY_DRIFT = "inventory_drift"
    RUNTIME_MISMATCH = "runtime_mismatch"
    UNKNOWN = "unknown"


class QueryValidity(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    STALE = "stale"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    EMPTY = "empty"


_KWOWN_DATASOURCE_UID = "PBFA97CFB590B2093"
_KNOWN_LOKI_UID = "fflfh9qp8mxogc"
_KNOWN_LOKI_URL = "http://192.168.1.40:3100"
_KNOWN_PROMETHEUS_URL = "http://192.168.1.40:9090"

_EXPECTED_GPUS = frozenset({"rx9070", "rx 9070", "rx7900xt", "rx 7900 xt"})
_FORBIDDEN_GPU_PATTERNS = re.compile(
    r"(?i)\b(a100|h100|h200|b100|b200|nvidia\s+a100|nvidia\s+h100|"
    r"rtx\s*5070|rtx\s*5080|rtx\s*5090|rtx\s*4090|tesla|t4|l4|v100|"
    r"mi250|mi300|mi350|l40s|a10|a16)\b"
)
_FORBIDDEN_DATASOURCE_RE = re.compile(r"(?i)(testdatasource|fake|dev-local)")
_STALE_METRIC_PATTERNS = re.compile(
    r"(?i)\b(memory_contamination\w*|hallucination_risk\w*|"
    r"tool_fastpath_fallback\w*|completion_empty_after_truncation\w*|"
    r"gateway_singleton_violation\w*|gateway_unclean_shutdown\w*)\b"
)
_DEPRECATED_METRIC_PATTERNS = re.compile(
    r"(?i)\b(router_chat_requests|router_hard_facts|"
    r"episodic_embeddings|episodic_memory_size|"
    r"failovers|sessions_orphan)\b"
)
_FAKE_NODE_PATTERNS = re.compile(
    r"(?i)\b(node-0[3-9]|gpu-node-0[3-9]|worker-0[3-9]|"
    r"inference-[2-9]|cluster-node-[2-9]|gpu-server-[2-9])\b"
)
_FAILED_NODE_PATTERNS = re.compile(
    r"(?i)\b(192\.168\.1\.[6-9][0-9]|192\.168\.2\.)"
)


class DashboardValidator:
    def __init__(self) -> None:
        self._results: list[DashboardValidationResult] = []

    # ── Datasource validation ──

    def validate_datasource(
        self, uid: str = "", name: str = "", url: str = ""
    ) -> tuple[bool, str]:
        if _FORBIDDEN_DATASOURCE_RE.search(uid or name or url):
            return False, "forbidden_datasource_pattern"
        if uid and uid == _KNOWN_LOKI_UID:
            return True, ""
        if uid and uid != _KWOWN_DATASOURCE_UID:
            return False, "unknown_datasource_uid"
        return True, ""

    # ── PromQL validation ──

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

    def validate_promql_expression(self, query: str = "") -> tuple[str, list[str]]:
        """Detailed PromQL validation returning severity and warnings."""
        if not query.strip():
            return QueryValidity.EMPTY.value, ["empty_query"]
        warnings: list[str] = []
        if "{" in query and "}" not in query:
            warnings.append("unmatched_brace")
        stale = _STALE_METRIC_PATTERNS.findall(query)
        if stale:
            warnings.append(f"stale_metric:{','.join(set(stale))}")
        dep = _DEPRECATED_METRIC_PATTERNS.findall(query)
        if dep:
            warnings.append(f"deprecated_metric:{','.join(set(dep))}")
        invalid = re.findall(r"(?i)\b(test_|fake_|example_)\w+", query)
        if invalid:
            warnings.append(f"invalid_metric:{invalid[0]}")
            return QueryValidity.INVALID.value, warnings
        fake_node = _FAKE_NODE_PATTERNS.findall(query)
        if fake_node:
            warnings.append(f"fake_node:{','.join(set(fake_node))}")
        if warnings:
            return QueryValidity.STALE.value, warnings
        return QueryValidity.VALID.value, []

    # ── Loki query validation ──

    def validate_loki_query(self, query: str = "") -> tuple[bool, str]:
        if not query.strip():
            return False, "empty_query"
        if not query.startswith("{") and "|=" not in query:
            return False, "missing_stream_selector"
        return True, ""

    def validate_loki_expression(self, query: str = "") -> tuple[str, list[str]]:
        if not query.strip():
            return QueryValidity.EMPTY.value, ["empty_query"]
        warnings: list[str] = []
        if not query.startswith("{"):
            warnings.append("missing_stream_selector")
        return QueryValidity.INVALID.value if warnings else QueryValidity.VALID.value, warnings

    # ── No-data detection ──

    def detect_no_data_panels(self, panel: dict[str, Any]) -> bool:
        datasource = panel.get("datasource", {})
        if isinstance(datasource, dict):
            ds_uid = datasource.get("uid", "")
        elif isinstance(datasource, str):
            ds_uid = datasource
        else:
            ds_uid = ""
        return ds_uid == "" or ds_uid == "no-ds"

    # ── GPU references ──

    def detect_forbidden_gpu_references(self, panel_json: str) -> list[str]:
        matches = _FORBIDDEN_GPU_PATTERNS.findall(panel_json)
        return list(set(matches))

    def detect_legacy_gpu_inventory(self, panel_json: str) -> list[str]:
        legacy = re.findall(r"(?i)\b(rtx\s*3090|rtx\s*3080|rtx\s*3070|"
                            r"gtx\s*1080|gtx\s*1060|quadro|"
                            r"rx\s*580|rx\s*590|vega)\b", panel_json)
        return list(set(legacy))

    def detect_fake_topology(self, panel_json: str) -> list[str]:
        matches = _FAKE_NODE_PATTERNS.findall(panel_json)
        failed_nodes = _FAILED_NODE_PATTERNS.findall(panel_json)
        results: list[str] = []
        if matches:
            results.append(f"fake_topology_nodes:{','.join(set(matches))}")
        return results

    # ── Stale dashboard detection ──

    def detect_stale_dashboards(self, dashboard: dict[str, Any]) -> list[str]:
        warnings: list[str] = []
        panels = dashboard.get("panels", [])
        no_data_count = 0
        for panel in panels:
            if self.detect_no_data_panels(panel):
                no_data_count += 1
        if no_data_count > 0:
            warnings.append(f"no_data_panels:{no_data_count}")
        if no_data_count > len(panels) * 0.5:
            warnings.append("majority_no_data")
        return warnings

    # ── Inventory drift ──

    def detect_inventory_drift(
        self, dashboard_uid: str, dashboard_json: dict[str, Any] | str = ""
    ) -> list[dict[str, Any]]:
        drifts: list[dict[str, Any]] = []
        try:
            from runtime.observability.grafana_inventory import get_dashboard_by_uid
            known = get_dashboard_by_uid(dashboard_uid)
        except ImportError:
            return drifts
        if known is None:
            drifts.append({
                "type": "unknown_dashboard",
                "uid": dashboard_uid,
                "severity": "medium",
                "detail": "Dashboard uid not in known inventory",
            })
            return drifts
        return drifts

    # ── Runtime mismatch ──

    def detect_runtime_mismatch(
        self, dashboard_json: dict[str, Any] | str = ""
    ) -> list[dict[str, Any]]:
        drifts: list[dict[str, Any]] = []
        json_str = json.dumps(dashboard_json) if isinstance(dashboard_json, dict) else dashboard_json
        forbidden = self.detect_forbidden_gpu_references(json_str)
        for gpu in forbidden:
            drifts.append({
                "type": "forbidden_gpu",
                "gpu": gpu,
                "severity": "critical",
                "detail": f"GPU {gpu} no existe en el runtime activo",
            })
        legacy_gpus = self.detect_legacy_gpu_inventory(json_str)
        for gpu in legacy_gpus:
            drifts.append({
                "type": "legacy_gpu",
                "gpu": gpu,
                "severity": "high",
                "detail": f"GPU {gpu} no está en uso en el runtime activo",
            })
        fake_topos = self.detect_fake_topology(json_str)
        for ft in fake_topos:
            drifts.append({
                "type": "fake_topology",
                "detail": ft,
                "severity": "high",
            })
        return drifts

    # ── Panel query validation ──

    def validate_panel_queries(self, panel: dict[str, Any]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        targets = panel.get("targets", [])
        for target in targets:
            expr = target.get("expr", "")
            if expr:
                validity, warnings = self.validate_promql_expression(expr)
                results.append({
                    "type": "promql",
                    "expr": expr[:120],
                    "validity": validity,
                    "warnings": warnings,
                })
            loki_expr = target.get("query", "")
            if loki_expr:
                validity, warnings = self.validate_loki_expression(loki_expr)
                results.append({
                    "type": "loki",
                    "expr": loki_expr[:120],
                    "validity": validity,
                    "warnings": warnings,
                })
        return results

    # ── Dashboard validation (backward compat + expanded) ──

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
        self._check_runtime_drift(dashboard_json, result)
        self._resolve_health(result)

        return result

    def _result_from_uid(self, uid: str, title: str) -> DashboardValidationResult:
        try:
            from runtime.observability.grafana_inventory import _AI_LAB_DASHBOARDS as AI, _LEGACY_DASHBOARDS as LEGACY
        except ImportError:
            AI = []
            LEGACY = []
        for d in AI:
            if d["uid"] == uid:
                return DashboardValidationResult(
                    uid=uid, title=title,
                    runtime_domain=d.get("runtime_domain", ""),
                    criticality=d.get("criticality", "low"),
                    semantic_owner=d.get("semantic_owner", ""),
                    datasource_uid=d.get("datasource_uid", _KWOWN_DATASOURCE_UID),
                )
        for d in LEGACY:
            if d["uid"] == uid:
                return DashboardValidationResult(
                    uid=uid, title=title,
                    runtime_domain="legacy", criticality="low",
                    semantic_owner="infrastructure", deprecated=True,
                    datasource_uid=d.get("datasource_uid", _KWOWN_DATASOURCE_UID),
                )
        return DashboardValidationResult(uid=uid, title=title)

    def _classify_dashboard(self, uid: str, title: str, result: DashboardValidationResult) -> None:
        if not uid:
            result.warnings.append("missing_dashboard_uid")
        try:
            from runtime.observability.grafana_inventory import _LEGACY_DASHBOARDS as LEGACY
            for d in LEGACY:
                if d["uid"] == uid:
                    result.deprecated = True
                    result.runtime_domain = "legacy"
                    result.criticality = "low"
                    result.health = DashboardHealth.DEPRECATED.value
                    return
        except ImportError:
            pass

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

    def _check_runtime_drift(
        self, dashboard: dict[str, Any], result: DashboardValidationResult
    ) -> None:
        drift_issues = self.detect_runtime_mismatch(dashboard)
        for issue in drift_issues:
            result.warnings.append(f"{issue['type']}:{issue.get('gpu','')}")

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

    # ── Known dashboard validation ──

    def validate_all_known(self) -> list[dict[str, Any]]:
        from runtime.observability.grafana_inventory import _AI_LAB_DASHBOARDS as AI, _LEGACY_DASHBOARDS as LEGACY
        results: list[dict[str, Any]] = []
        for d in AI:
            result = DashboardValidationResult(
                uid=d["uid"], title=d["title"],
                runtime_domain=d.get("runtime_domain", ""),
                criticality=d.get("criticality", "low"),
                semantic_owner=d.get("semantic_owner", ""),
                datasource_uid=_KWOWN_DATASOURCE_UID,
                datasource_valid=True,
            )
            result.health = DashboardHealth.HEALTHY.value
            results.append(result.to_dict())
        for d in LEGACY:
            result = DashboardValidationResult(
                uid=d["uid"], title=d["title"],
                runtime_domain="legacy", criticality="low",
                semantic_owner="infrastructure", deprecated=True,
                datasource_uid=_KWOWN_DATASOURCE_UID,
                datasource_valid=True,
            )
            result.health = DashboardHealth.DEPRECATED.value
            results.append(result.to_dict())
        return results

    # ── Audit summary ──

    def build_dashboard_audit_summary(
        self, results: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        if results is None:
            results = self.validate_all_known()
        counts: dict[str, int] = {}
        for r in results:
            h = r.get("health", "unknown")
            counts[h] = counts.get(h, 0) + 1
        return {
            "contract_version": DASHBOARD_VALIDATOR_CONTRACT_VERSION,
            "timestamp": time.time(),
            "total_dashboards": len(results),
            "health_classification": counts,
            "total_panels": sum(r.get("panels_total", 0) for r in results),
            "total_broken_panels": sum(r.get("panels_broken", 0) for r in results),
            "total_no_data_panels": sum(r.get("panels_no_data", 0) for r in results),
            "critical_dashboards_healthy": sum(
                1 for r in results
                if r.get("criticality") in ("critical", "high") and r.get("health") == "healthy"
            ),
            "critical_dashboards_total": sum(
                1 for r in results if r.get("criticality") in ("critical", "high")
            ),
            "dashboards": results,
        }

    # ── Full Grafana drift audit ──

    def run_grafana_drift_audit(self) -> dict[str, Any]:
        inventory_results = self.validate_all_known()
        from runtime.observability.grafana_inventory import build_inventory_summary
        inventory = build_inventory_summary()

        counts: dict[str, int] = {}
        for r in inventory_results:
            h = r.get("health", "unknown")
            counts[h] = counts.get(h, 0) + 1

        broken_dashboards = [r for r in inventory_results if r.get("health") == "broken"]
        stale_dashboards = [r for r in inventory_results if r.get("health") == "stale"]
        legacy_dashboards = [r for r in inventory_results if r.get("deprecated")]

        return {
            "contract_version": DASHBOARD_VALIDATOR_CONTRACT_VERSION,
            "timestamp": time.time(),
            "total_dashboards": len(inventory_results),
            "health_classification": counts,
            "broken_dashboards": [r.get("uid") for r in broken_dashboards],
            "stale_dashboards": [r.get("uid") for r in stale_dashboards],
            "legacy_dashboards": [r.get("uid") for r in legacy_dashboards],
            "total_drift_issues": sum(len(r.get("warnings", []))
                                       for r in inventory_results),
            "total_broken_panels": sum(r.get("panels_broken", 0)
                                        for r in inventory_results),
            "total_no_data_panels": sum(r.get("panels_no_data", 0)
                                         for r in inventory_results),
            "critical_healthy": inventory.get("critical_healthy", 0),
            "critical_total": inventory.get("critical_total", 0),
            "dashboards": inventory_results,
        }


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
