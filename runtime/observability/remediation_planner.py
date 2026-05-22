"""FASE OBS-31A.4: Observability Remediation Planner.

Generates evidence-bound remediation plans from OBS-31A audit data.
Classifies findings, detects quick wins, high-risk changes, and
groups remediation into operational phases.

RULE-OBS-31A.4-1: No todo drift requiere corrección inmediata.
RULE-OBS-31A.4-2: expected_offline ≠ remediation urgente.
RULE-OBS-31A.4-3: Dashboards legacy deben clasificarse antes de eliminarse.
RULE-OBS-31A.4-4: Runtime operational continuity tiene prioridad.
RULE-OBS-31A.4-6: No ejecutar cambios automáticos destructivos.
"""

from __future__ import annotations

import re
import time
import uuid
from typing import Any

from runtime.observability.remediation_contracts import (
    REMEDIATION_CONTRACT_VERSION,
    RemediationItem,
    RemediationPlan,
    RemediationRisk,
    RemediationSummary,
    build_remediation_item,
)

REMEDIATION_PLANNER_CONTRACT_VERSION = REMEDIATION_CONTRACT_VERSION

_FORBIDDEN_GPU_PATTERNS = re.compile(
    r"(?i)\b(a100\w*|h100\w*|h200\w*|b100\w*|b200\w*|nvidia\s+a100\w*|nvidia\s+h100\w*|"
    r"rtx\s*5070\w*|rtx\s*5080\w*|rtx\s*5090\w*|rtx\s*4090\w*|tesla\w*|t4\w*|l4\w*|v100\w*|"
    r"mi250\w*|mi300\w*|mi350\w*|l40s\w*|a10\w*|a16\w*)\b"
)
_FAKE_NODE_PATTERNS = re.compile(
    r"(?i)\b(node-0[3-9]|gpu-node-0[3-9]|worker-0[3-9]|"
    r"inference-[2-9]|cluster-node-[2-9]|gpu-server-[2-9])\b"
)
_STALE_METRIC_MARKERS = (
    "memory_contamination", "hallucination_risk",
    "tool_fastpath_fallback", "completion_empty_after_truncation",
    "gateway_singleton_violation",
)
_KNOWN_ACTIVE_GPUS = frozenset({"rx9070", "rx 9070"})
_KNOWN_OFFLINE_GPUS = frozenset({"rx7900xt", "rx 7900 xt"})
_CRITICAL_DASHBOARD_UIDS = frozenset({
    "ai-lab-overview", "ai-lab-runtime", "ai-lab-gpus",
    "ailab-runtime-protection",
})
_CRITICAL_SERVICES = frozenset({
    "prometheus", "ailab-gateway", "grafana",
})
_EXPECTED_DATASOURCE_UIDS = frozenset({
    "PBFA97CFB590B2093", "fflfh9qp8mxogc",
})


class RemediationPlanner:

    REMEDIATION_PLANNER_CONTRACT_VERSION = REMEDIATION_PLANNER_CONTRACT_VERSION

    def __init__(self) -> None:
        self._plan = RemediationPlan()
        self._summary = RemediationSummary()

    # ── Entry point ──

    def build_remediation_plan(
        self,
        drift_result: dict[str, Any] | None = None,
        dashboard_inventory: list[dict[str, Any]] | None = None,
        dashboard_audit: dict[str, Any] | None = None,
        prometheus_targets: dict[str, Any] | None = None,
        runtime_alignment: dict[str, Any] | None = None,
        grafana_dashboards: list[dict[str, Any]] | None = None,
    ) -> RemediationPlan:
        self._plan = RemediationPlan()
        items: list[RemediationItem] = []

        items.extend(self._detect_fake_gpu_remediation(grafana_dashboards))
        items.extend(self._detect_legacy_topology(grafana_dashboards))
        items.extend(self._detect_stale_metrics(dashboard_audit))
        items.extend(self._detect_broken_dashboards(dashboard_audit))
        items.extend(self._detect_orphan_datasources(dashboard_inventory))
        items.extend(self._detect_dashboard_drift(drift_result))
        items.extend(self._detect_runtime_alignment_issues(runtime_alignment))
        items.extend(self._detect_expected_offline_not_critical(prometheus_targets))
        items.extend(self._detect_prometheus_target_issues(prometheus_targets))
        items.extend(self._detect_duplicate_dashboards(dashboard_inventory))
        items.extend(self._detect_unused_panels(dashboard_audit))
        items.extend(self._detect_inconsistent_contracts(runtime_alignment))

        self._plan.items = items
        self._plan.total_items = len(items)
        self._classify_counts(items)
        self._plan.quick_wins = self.detect_quick_wins(items)
        self._plan.high_risk_changes = self.detect_high_risk_changes(items)
        self._plan.phases = self.group_remediation_by_phase(items)
        self._summary = self._build_summary()

        return self._plan

    def _classify_counts(self, items: list[RemediationItem]) -> None:
        sev = {"critical": 0, "high": 0, "medium": 0, "low": 0, "informational": 0}
        for i in items:
            s = i.severity.lower()
            if s in sev:
                sev[s] += 1
        self._plan.critical_count = sev["critical"]
        self._plan.high_count = sev["high"]
        self._plan.medium_count = sev["medium"]
        self._plan.low_count = sev["low"]
        self._plan.informational_count = sev["informational"]

    # ── Detectors ──

    def _detect_fake_gpu_remediation(
        self, dashboards: list[dict[str, Any]] | None,
    ) -> list[RemediationItem]:
        items: list[RemediationItem] = []
        if not dashboards:
            return items
        for d in dashboards:
            uid = d.get("uid", "") if isinstance(d, dict) else ""
            panel_text = str(d)
            forbidden = _FORBIDDEN_GPU_PATTERNS.findall(panel_text)
            for gpu in set(forbidden):
                items.append(build_remediation_item(
                    uid=f"fake-gpu-{gpu}-{uuid.uuid4().hex[:6]}",
                    title=f"GPU falsa en dashboard: {gpu}",
                    description=f"GPU '{gpu}' no existe en runtime activo",
                    domain="gpu", problem_class="cosmetic",
                    severity="high", source="grafana_dashboard",
                    evidence=[f"dashboard_uid={uid}", f"gpu={gpu}"],
                    safe_quick_win=True,
                    phase="phase_1_safe_quick_wins",
                    owner="observability",
                    recommended_action=f"Eliminar referencia a {gpu} del dashboard {uid}",
                ))
        return items

    def _detect_legacy_topology(
        self, dashboards: list[dict[str, Any]] | None,
    ) -> list[RemediationItem]:
        items: list[RemediationItem] = []
        if not dashboards:
            return items
        all_text = " ".join(str(d) for d in dashboards)
        fake_nodes = _FAKE_NODE_PATTERNS.findall(all_text)
        for node in set(fake_nodes):
            items.append(build_remediation_item(
                uid=f"fake-topo-{node}",
                title=f"Topología legacy: {node}",
                description=f"Nodo '{node}' en dashboards no existe en runtime",
                domain="topology", problem_class="legacy",
                severity="medium", source="grafana_dashboard",
                evidence=[f"node={node}"],
                safe_quick_win=True,
                phase="phase_3_dashboard_modernization",
                owner="infrastructure",
                recommended_action=f"Reemplazar nodo {node} por topología real",
            ))
        return items

    def _detect_stale_metrics(
        self, audit: dict[str, Any] | None,
    ) -> list[RemediationItem]:
        items: list[RemediationItem] = []
        if not audit:
            return items
        dashboards = audit.get("dashboards", [])
        uid_set: set[str] = set()
        for d in dashboards:
            warnings = d.get("warnings", [])
            uid = d.get("uid", "")
            for w in warnings:
                if any(marker in w for marker in _STALE_METRIC_MARKERS):
                    if uid not in uid_set:
                        uid_set.add(uid)
                        items.append(build_remediation_item(
                            uid=f"stale-metric-{uid}",
                            title=f"Métricas stale en dashboard {uid}",
                            description=f"Dashboard {uid} usa métricas obsoletas",
                            domain="observability", problem_class="technical_debt",
                            severity="medium", source="dashboard_audit",
                            evidence=[f"dashboard_uid={uid}", f"warning={w}"],
                            safe_quick_win=True,
                            phase="phase_3_dashboard_modernization",
                            owner="runtime",
                            recommended_action=f"Actualizar queries en dashboard {uid} a métricas actuales",
                        ))
        return items

    def _detect_broken_dashboards(
        self, audit: dict[str, Any] | None,
    ) -> list[RemediationItem]:
        items: list[RemediationItem] = []
        if not audit:
            return items
        broken = audit.get("broken_dashboards", [])
        for uid in broken:
            critical = uid in _CRITICAL_DASHBOARD_UIDS
            items.append(build_remediation_item(
                uid=f"broken-dash-{uid}",
                title=f"Dashboard roto: {uid}",
                description=f"Dashboard {uid} tiene paneles rotos o sin datos",
                domain="observability", problem_class="observability_blocking",
                severity="critical" if critical else "high",
                source="dashboard_audit",
                evidence=[f"dashboard_uid={uid}", "health=broken"],
                safe_quick_win=not critical,
                high_risk_change=critical,
                phase="phase_3_dashboard_modernization",
                owner="observability",
                recommended_action=f"Reparar paneles rotos en dashboard {uid}",
                runtime_dependency="grafana",
            ))
        return items

    def _detect_orphan_datasources(
        self, inventory: list[dict[str, Any]] | None,
    ) -> list[RemediationItem]:
        items: list[RemediationItem] = []
        if not inventory:
            return items
        found_uids: set[str] = set()
        for d in inventory:
            uid = d.get("datasource_uid", "")
            if uid:
                found_uids.add(uid)
        orphan = found_uids - _EXPECTED_DATASOURCE_UIDS - {""}
        for ouid in orphan:
            items.append(build_remediation_item(
                uid=f"orphan-ds-{ouid[:8]}",
                title=f"Datasource huérfano: {ouid}",
                description=f"Datasource UID {ouid} no está en la lista de datasources conocidos",
                domain="observability", problem_class="technical_debt",
                severity="low", source="dashboard_inventory",
                evidence=[f"datasource_uid={ouid}"],
                safe_quick_win=True,
                phase="phase_4_legacy_cleanup",
                owner="infrastructure",
                recommended_action=f"Verificar y eliminar datasource {ouid} si no está en uso",
            ))
        return items

    def _detect_dashboard_drift(
        self, drift: dict[str, Any] | None,
    ) -> list[RemediationItem]:
        items: list[RemediationItem] = []
        if not drift:
            return items
        for dtype in ("gpu_drift", "topology_drift", "inventory_drift", "semantic_drift", "runtime_mismatch"):
            drifts = drift.get(dtype, [])
            for d in drifts:
                items.append(build_remediation_item(
                    uid=f"drift-{dtype}-{uuid.uuid4().hex[:6]}",
                    title=f"Drift detectado: {d.get('type', dtype)}",
                    description=d.get("detail", f"Drift en {dtype}"),
                    domain="observability", problem_class="technical_debt",
                    severity=d.get("severity", "medium"),
                    source="drift_detection",
                    evidence=[f"drift_type={dtype}", f"detail={d.get('detail','')}"],
                    safe_quick_win=d.get("severity") in ("low", "medium"),
                    phase="phase_2_runtime_alignment",
                    owner="runtime",
                    recommended_action=f"Corregir drift: {d.get('type', dtype)} en {d.get('detail','')}",
                    runtime_dependency="drift_detector",
                ))
        return items

    def _detect_runtime_alignment_issues(
        self, alignment: dict[str, Any] | None,
    ) -> list[RemediationItem]:
        items: list[RemediationItem] = []
        if not alignment:
            return items
        score = alignment.get("alignment_score", 100)
        level = alignment.get("alignment_level", "healthy")
        if level in ("unhealthy", "critical") or score < 50:
            items.append(build_remediation_item(
                uid="runtime-alignment-critical",
                title=f"Alineación runtime-observabilidad crítica ({score}/100)",
                description=f"Score {score} ({level}) requiere atención inmediata",
                domain="observability", problem_class="runtime_blocking",
                severity="critical", source="runtime_alignment",
                evidence=[f"score={score}", f"level={level}"],
                safe_quick_win=False,
                high_risk_change=True,
                phase="phase_2_runtime_alignment",
                owner="runtime",
                recommended_action="Investigar causas de baja alineación runtime-observabilidad",
                runtime_dependency="runtime_alignment_validator",
            ))
        return items

    def _detect_expected_offline_not_critical(
        self, targets: dict[str, Any] | None,
    ) -> list[RemediationItem]:
        items: list[RemediationItem] = []
        if not targets:
            return items
        expected = targets.get("expected_offline", []) or []
        for item in expected:
            items.append(build_remediation_item(
                uid=f"expected-offline-{item[:20]}",
                title=f"Target expected_offline: {item}",
                description=f"Target '{item}' correctamente clasificado como expected_offline. Sin acción urgente.",
                domain="observability", problem_class="expected_offline",
                severity="informational", source="prometheus_audit",
                evidence=[f"target={item}", "classification=expected_offline"],
                safe_quick_win=False,
                phase="phase_4_legacy_cleanup",
                owner="infrastructure",
                recommended_action=f"Monitorear si {item} vuelve a estar online",
            ))
        return items

    def _detect_prometheus_target_issues(
        self, targets: dict[str, Any] | None,
    ) -> list[RemediationItem]:
        items: list[RemediationItem] = []
        if not targets:
            return items
        unexpected = targets.get("unexpected_down", targets.get("degraded", []))
        if isinstance(unexpected, list):
            for t in unexpected:
                job = t.get("job", str(t)[:30]) if isinstance(t, dict) else str(t)[:30]
                critical_job = any(c in job for c in _CRITICAL_SERVICES)
                items.append(build_remediation_item(
                    uid=f"unexpected-down-{job[:20]}",
                    title=f"Target caído inesperadamente: {job}",
                    description=f"Target {job} está down pero no es expected_offline",
                    domain="observability", problem_class="runtime_blocking",
                    severity="critical" if critical_job else "high",
                    source="prometheus_audit",
                    evidence=[f"target={job}", "status=unexpected_down"],
                    safe_quick_win=False,
                    high_risk_change=critical_job,
                    phase="phase_2_runtime_alignment",
                    owner="infrastructure" if not critical_job else "runtime",
                    recommended_action=f"Investigar caída de {job}",
                    runtime_dependency="prometheus",
                ))
        return items

    def _detect_duplicate_dashboards(
        self, inventory: list[dict[str, Any]] | None,
    ) -> list[RemediationItem]:
        items: list[RemediationItem] = []
        if not inventory:
            return items
        titles: dict[str, list[str]] = {}
        for d in inventory:
            title = d.get("title", "").lower().strip()
            uid = d.get("uid", "")
            if title:
                titles.setdefault(title, []).append(uid)
        for title, uids in titles.items():
            if len(uids) > 1:
                items.append(build_remediation_item(
                    uid=f"dup-dash-{uids[0][:8]}",
                    title=f"Dashboard duplicado: {title[:40]}",
                    description=f"Título '{title}' aparece en {len(uids)} dashboards: {uids}",
                    domain="observability", problem_class="technical_debt",
                    severity="low", source="dashboard_inventory",
                    evidence=[f"uids={uids}", f"title={title}"],
                    safe_quick_win=True,
                    phase="phase_4_legacy_cleanup",
                    owner="observability",
                    recommended_action=f"Consolidar dashboards duplicados con título '{title}'",
                ))
        return items

    def _detect_unused_panels(
        self, audit: dict[str, Any] | None,
    ) -> list[RemediationItem]:
        items: list[RemediationItem] = []
        if not audit:
            return items
        no_data = audit.get("total_no_data_panels", 0)
        if no_data > 0:
            items.append(build_remediation_item(
                uid="unused-panels-bulk",
                title=f"Paneles sin datos: {no_data}",
                description=f"Se detectaron {no_data} paneles sin datasource en dashboards",
                domain="observability", problem_class="cosmetic",
                severity="low", source="dashboard_audit",
                evidence=[f"no_data_panels={no_data}"],
                safe_quick_win=True,
                phase="phase_3_dashboard_modernization",
                owner="observability",
                recommended_action=f"Revisar {no_data} paneles sin datasource y eliminar o reparar",
            ))
        return items

    def _detect_inconsistent_contracts(
        self, alignment: dict[str, Any] | None,
    ) -> list[RemediationItem]:
        items: list[RemediationItem] = []
        if not alignment:
            return items

        contract_alignment = alignment.get("contract_alignment", {})
        checks = contract_alignment.get("checks", [])
        for c in checks:
            if not c.get("passed", True):
                items.append(build_remediation_item(
                    uid=f"contract-{c.get('check', 'unknown')}",
                    title=f"Contract version inconsistente: {c.get('check', '')}",
                    description=c.get("detail", "Contract version mismatch"),
                    domain="observability", problem_class="technical_debt",
                    severity=c.get("severity", "high"),
                    source="runtime_alignment",
                    evidence=[f"check={c.get('check','')}", f"actual={c.get('actual','')}"],
                    safe_quick_win=True,
                    phase="phase_5_governance_hardening",
                    owner="runtime",
                    recommended_action=f"Actualizar contract version: {c.get('check','')}",
                    runtime_dependency="contracts",
                ))
        return items

    # ── Quick wins ──

    def detect_quick_wins(
        self, items: list[RemediationItem] | None = None,
    ) -> list[RemediationItem]:
        if items is None:
            items = self._plan.items
        return [i for i in items if i.safe_quick_win]

    def detect_high_risk_changes(
        self, items: list[RemediationItem] | None = None,
    ) -> list[RemediationItem]:
        if items is None:
            items = self._plan.items
        return [i for i in items if i.high_risk_change]

    def group_remediation_by_phase(
        self, items: list[RemediationItem] | None = None,
    ) -> dict[str, list[RemediationItem]]:
        if items is None:
            items = self._plan.items
        phases: dict[str, list[RemediationItem]] = {
            "phase_1_safe_quick_wins": [],
            "phase_2_runtime_alignment": [],
            "phase_3_dashboard_modernization": [],
            "phase_4_legacy_cleanup": [],
            "phase_5_governance_hardening": [],
        }
        for i in items:
            p = i.phase if i.phase in phases else "phase_4_legacy_cleanup"
            phases[p].append(i)
        return phases

    # ── Risk calculation ──

    def calculate_remediation_risk(
        self, item: RemediationItem,
    ) -> RemediationRisk:
        if item.severity == "critical":
            return RemediationRisk(
                severity="critical", runtime_impact="high",
                operational_risk="high", change_risk="high",
                reversible=False, requires_restart=True,
            )
        if item.severity == "high":
            return RemediationRisk(
                severity="high", runtime_impact="medium",
                operational_risk="medium", change_risk="medium",
                reversible=True, requires_restart=False,
            )
        if item.severity == "medium":
            return RemediationRisk(
                severity="medium", runtime_impact="low",
                operational_risk="low", change_risk="low",
                reversible=True, requires_restart=False,
            )
        return RemediationRisk(
            severity=item.severity, runtime_impact="none",
            operational_risk="none", change_risk="none",
            reversible=True, requires_restart=False,
        )

    # ── Summary ──

    def _build_summary(self) -> RemediationSummary:
        items = self._plan.items
        legacy_count = sum(1 for i in items if i.problem_class == "legacy")
        stale_count = sum(1 for i in items if "stale" in i.uid)
        orphan_count = sum(1 for i in items if "orphan" in i.uid)
        drift_count = sum(1 for i in items if "drift" in i.uid)
        quick_count = len(self._plan.quick_wins)
        high_risk_count = len(self._plan.high_risk_changes)

        total = len(items)
        critical = self._plan.critical_count
        score = self._calc_remediation_score(critical, total)

        complexity = "low"
        if total > 30:
            complexity = "high"
        elif total > 15:
            complexity = "medium"

        return RemediationSummary(
            total_findings=total,
            critical_findings=critical,
            legacy_dashboards=legacy_count,
            stale_panels=stale_count,
            orphan_datasources=orphan_count,
            runtime_drift_count=drift_count,
            estimated_complexity=complexity,
            quick_win_count=quick_count,
            high_risk_count=high_risk_count,
            remediation_score=score,
            phases_summary={k: len(v) for k, v in self._plan.phases.items()},
        )

    def _calc_remediation_score(
        self, critical: int, total: int,
    ) -> float:
        if total == 0:
            return 100.0
        critical_penalty = critical * 15
        raw = max(0, 100 - critical_penalty - max(0, total - 20) * 2)
        return float(raw)

    # ── Public API ──

    def generate_remediation_summary(
        self, plan: RemediationPlan | None = None,
    ) -> RemediationSummary:
        if plan is not None:
            self._plan = plan
            self._summary = self._build_summary()
        return self._summary

    def get_technical_debt_report(
        self, plan: RemediationPlan | None = None,
    ) -> dict[str, Any]:
        if plan is not None:
            self._plan = plan
        summary = self.generate_remediation_summary()
        debt_items = [i for i in self._plan.items
                       if i.problem_class in ("technical_debt", "legacy", "cosmetic")]
        return {
            "contract_version": REMEDIATION_CONTRACT_VERSION,
            "timestamp": time.time(),
            "summary": summary.to_dict(),
            "technical_debt_items": len(debt_items),
            "by_domain": self._count_by_domain(debt_items),
            "estimated_effort": self._estimate_effort(debt_items),
        }

    def _count_by_domain(
        self, items: list[RemediationItem],
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for i in items:
            d = i.domain or "unknown"
            counts[d] = counts.get(d, 0) + 1
        return counts

    def _estimate_effort(
        self, items: list[RemediationItem],
    ) -> str:
        total = len(items)
        if total == 0:
            return "none"
        if total <= 5:
            return "hours"
        if total <= 20:
            return "days"
        return "weeks"


def build_remediation_plan(
    drift_result: dict[str, Any] | None = None,
    dashboard_inventory: list[dict[str, Any]] | None = None,
    dashboard_audit: dict[str, Any] | None = None,
    prometheus_targets: dict[str, Any] | None = None,
    runtime_alignment: dict[str, Any] | None = None,
    grafana_dashboards: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    planner = RemediationPlanner()
    plan = planner.build_remediation_plan(
        drift_result=drift_result,
        dashboard_inventory=dashboard_inventory,
        dashboard_audit=dashboard_audit,
        prometheus_targets=prometheus_targets,
        runtime_alignment=runtime_alignment,
        grafana_dashboards=grafana_dashboards,
    )
    return plan.to_dict()


def classify_remediation_priority(item: RemediationItem) -> str:
    if item.severity == "critical":
        return "P0"
    if item.severity == "high":
        return "P1" if item.high_risk_change else "P2"
    if item.severity == "medium":
        return "P3"
    if item.severity == "low":
        return "P4"
    return "P5"
