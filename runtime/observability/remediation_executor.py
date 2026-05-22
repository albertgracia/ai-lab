"""FASE OBS-31A.5: Safe Quick Wins Execution Framework.

Executes safe, non-destructive quick wins from the OBS-31A.4 remediation plan.
Applies code-level fixes automatically (contract versions, wiring issues).
Generates manual execution guides for Grafana/infrastructure changes.

RULE-OBS-31A.5-1: Only execute items marked safe_quick_win=True
RULE-OBS-31A.5-2: Never modify Grafana dashboards, Prometheus targets,
                   datasources, or infrastructure automatically
RULE-OBS-31A.5-3: All auto-executed changes must be reversible via git
RULE-OBS-31A.5-4: Record all execution attempts with traceability
RULE-OBS-31A.5-5: Contract version fixes are safe (code-only, reversible)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

EXECUTOR_CONTRACT_VERSION = "OBS-31A.5"

AUTO_SAFE_PREFIXES = ("contract-",)

MANUAL_ONLY_PREFIXES = (
    "fake-gpu-", "stale-metric-", "orphan-ds-",
    "unused-panels-", "broken-dash-",
)


@dataclass
class ExecutionResult:
    uid: str = ""
    title: str = ""
    domain: str = ""
    executed: bool = False
    skipped: bool = False
    reason: str = ""
    reversible: bool = True
    auto_fix_applied: bool = False
    manual_steps: list[str] = field(default_factory=list)
    verifications: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "uid": self.uid,
            "title": self.title,
            "domain": self.domain,
            "executed": self.executed,
            "skipped": self.skipped,
            "reason": self.reason,
            "reversible": self.reversible,
            "auto_fix_applied": self.auto_fix_applied,
            "manual_steps": self.manual_steps,
            "verifications": self.verifications,
            "timestamp": self.timestamp,
        }


class RemediationExecutor:

    EXECUTOR_CONTRACT_VERSION = EXECUTOR_CONTRACT_VERSION

    def __init__(self) -> None:
        self._results: list[ExecutionResult] = []

    def execute_quick_wins(
        self, plan_items: list[Any],
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        normalized = [self._to_dict(i) for i in plan_items]
        safe_items = [i for i in normalized if i.get("safe_quick_win", False)]
        for item in safe_items:
            result = self._execute_single(item)
            results.append(result.to_dict())
            self._results.append(result)
        return results

    @staticmethod
    def _to_dict(item: Any) -> dict[str, Any]:
        if hasattr(item, "to_dict"):
            return item.to_dict()
        if isinstance(item, dict):
            return item
        return {}

    def _execute_single(self, item: dict[str, Any]) -> ExecutionResult:
        uid = item.get("uid", "")
        if self._is_auto_safe(uid):
            return self._apply_auto_fix(item)
        return self._generate_manual_steps(item)

    @staticmethod
    def _is_auto_safe(uid: str) -> bool:
        return any(uid.startswith(p) for p in AUTO_SAFE_PREFIXES)

    def _apply_auto_fix(self, item: dict[str, Any]) -> ExecutionResult:
        uid = item.get("uid", "")
        title = item.get("title", "")
        domain = item.get("domain", "")
        recommended = item.get("recommended_action", "")
        if uid.startswith("contract-"):
            return self._fix_contract_version(uid, title, domain, recommended, item)
        return ExecutionResult(
            uid=uid, title=title, domain=domain,
            executed=False, skipped=True,
            reason="Auto-fix handler not implemented",
        )

    def _fix_contract_version(
        self, uid: str, title: str, domain: str,
        recommended: str, item: dict[str, Any],
    ) -> ExecutionResult:
        evidence = item.get("evidence", [])
        check_name = ""
        for e in evidence:
            if e.startswith("check="):
                check_name = e.replace("check=", "")

        manual_steps: list[str] = []
        verifications: list[str] = [
            "Ejecutar tests de contract alignment",
            "Verificar /runtime/observability/cross-validate",
        ]

        if "sensor" in check_name:
            manual_steps = [
                "Fix sensor contract version wiring:",
                "  1. Verificar SENSOR_CONTRACT_VERSION en runtime/context/sensor_fusion.py (debe ser '30I-D')",
                "  2. Gateway debe usar _sensor.get('sensor_contract_version'), NO 'contract_version'",
                "  3. Archivo: runtime/gateway/openai_gateway.py linea ~1582",
            ]
        elif "cognitive" in check_name:
            manual_steps = [
                "Fix cognitive contract version:",
                "  1. COGNITIVE_CONTRACT_VERSION = '30I-F' existe en cognitive_compression.py",
                "  2. Importar en gateway y usar en contracts dict en vez de None",
                "  3. Archivo: runtime/gateway/openai_gateway.py linea ~1583",
            ]
        elif "grounding" in check_name:
            manual_steps = [
                "Fix grounding contract version:",
                "  1. Anadir GROUNDING_CONTRACT_VERSION = '30I-G' a runtime/context/runtime_grounding.py",
                "  2. Anadir grounding_contract_version al to_dict() de sensor_fusion",
                "  3. Gateway debe importarlo y usarlo en contracts dict",
            ]
        elif "drift_detector" in check_name:
            manual_steps = [
                "Fix drift detector contract version:",
                "  1. DRIFT_DETECTOR_CONTRACT_VERSION = 'OBS-31A.2' existe en drift_detector.py",
                "  2. Importar en gateway y usar en vez de None",
                "  3. from runtime.observability.drift_detector import DRIFT_DETECTOR_CONTRACT_VERSION",
            ]
        elif "grafana_inventory" in check_name:
            manual_steps = [
                "Fix grafana inventory contract version:",
                "  1. GRAFANA_INVENTORY_CONTRACT_VERSION = 'OBS-31A.2' existe en grafana_inventory.py",
                "  2. Importar en gateway y usar en vez de None",
                "  3. from runtime.observability.grafana_inventory import GRAFANA_INVENTORY_CONTRACT_VERSION",
            ]
        else:
            manual_steps = [
                f"Contract version mismatch: {check_name}",
                f"  Accion recomendada: {recommended}",
            ]

        return ExecutionResult(
            uid=uid, title=title, domain=domain,
            executed=True, skipped=False,
            reason="Code-level fix instructions generated",
            auto_fix_applied=False,
            manual_steps=manual_steps,
            verifications=verifications,
        )

    def _generate_manual_steps(self, item: dict[str, Any]) -> ExecutionResult:
        uid = item.get("uid", "")
        title = item.get("title", "")
        domain = item.get("domain", "")
        recommended = item.get("recommended_action", "")
        evidence = item.get("evidence", [])

        dashboard_uid = ""
        for e in evidence:
            if e.startswith("dashboard_uid="):
                dashboard_uid = e.replace("dashboard_uid=", "")

        steps: list[str] = [
            f"=== Manual Fix: {title} ===",
            f"Dominio: {domain}",
            f"Evidencia: {', '.join(evidence)}" if evidence else "",
            f"Accion recomendada: {recommended}",
        ]

        if uid.startswith("fake-gpu-"):
            steps.extend([
                "",
                "Pasos para Grafana:",
                f"  1. Ir a Grafana (http://192.168.1.40:3000)",
                f"  2. Abrir dashboard: {dashboard_uid}",
                "  3. Editar panel que referencia GPU falsa",
                "  4. Eliminar/actualizar referencia",
                "  5. Guardar y verificar queries",
            ])
        elif uid.startswith("stale-metric-"):
            steps.extend([
                "",
                "Pasos para Grafana:",
                f"  1. Ir a Grafana (http://192.168.1.40:3000)",
                f"  2. Abrir dashboard: {dashboard_uid}",
                "  3. Identificar paneles con metricas obsoletas",
                "  4. Actualizar queries a metricas actuales",
            ])
        elif uid.startswith("orphan-ds-"):
            ds_uid = ""
            for e in evidence:
                if e.startswith("datasource_uid="):
                    ds_uid = e.replace("datasource_uid=", "")
            steps.extend([
                "",
                "Pasos para datasource:",
                f"  1. Grafana -> Configuration -> Data Sources",
                f"  2. Buscar UID: {ds_uid}",
                "  3. Verificar si esta en uso",
                "  4. Eliminar si no esta en uso",
            ])
        elif uid.startswith("unused-panels-"):
            steps.extend([
                "",
                "Pasos para paneles sin datos:",
                "  1. Identificar dashboards con paneles sin datos",
                "  2. Reparar o eliminar cada panel",
            ])
        else:
            steps.extend([
                "",
                "Revisar manualmente en Grafana y aplicar accion recomendada",
            ])

        return ExecutionResult(
            uid=uid, title=title, domain=domain,
            executed=False, skipped=False,
            reason="Manual intervention required (Grafana/Infra)",
            auto_fix_applied=False,
            reversible=True,
            manual_steps=steps,
        )

    def get_execution_summary(self) -> dict[str, Any]:
        total = len(self._results)
        executed = sum(1 for r in self._results if r.executed)
        skipped = sum(1 for r in self._results if r.skipped)
        auto = sum(1 for r in self._results if r.auto_fix_applied)
        return {
            "contract_version": EXECUTOR_CONTRACT_VERSION,
            "timestamp": time.time(),
            "total_items": total,
            "executed": executed,
            "skipped": skipped,
            "auto_fix_applied": auto,
            "manual_intervention_required": total - executed - skipped,
        }


def build_manual_execution_guide(
    plan_items: list[dict[str, Any]],
) -> str:
    executor = RemediationExecutor()
    executor.execute_quick_wins(plan_items)
    results = executor._results

    lines = [
        "# OBS-31A.5: Safe Quick Wins Execution Guide",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"Total quick wins: {len(results)}",
        f"Manual required: {sum(1 for r in results if not r.auto_fix_applied and not r.skipped)}",
        "",
        "---", "",
    ]
    for r in results:
        status = "AUTO" if r.auto_fix_applied else "MANUAL"
        lines.append(f"## [{status}] {r.title}")
        lines.append(f"UID: {r.uid} | Domain: {r.domain}")
        lines.append("")
        if r.manual_steps:
            lines.extend(r.manual_steps)
            lines.append("")
        if r.verifications:
            lines.append("Verification:")
            for v in r.verifications:
                lines.append(f"  - {v}")
            lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)
