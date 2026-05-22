"""FASE OBS-31A.3: Runtime ↔ Observability Alignment.

Cross-validates 6 runtime endpoints against Prometheus targets,
Grafana dashboards, model inventory, GPU states, storage/archive
state, topology_mode, and contract versions.

Key criteria:
  - RX9070 = active en runtime, Prometheus y Grafana
  - RX7900XT = expected_offline en runtime, Prometheus y Grafana
  - No A100/RTX5070/topología legacy en capa activa
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

RUNTIME_ALIGNMENT_CONTRACT_VERSION = "OBS-31A.3"

EXPECTED_ACTIVE_GPUS = frozenset({"rx9070", "rx 9070"})
EXPECTED_OFFLINE_GPUS = frozenset({"rx7900xt", "rx 7900 xt"})
EXPECTED_GPU_HOSTS = {
    "rx9070": "192.168.1.50",
    "rx7900xt": "192.168.1.60",
}
_FORBIDDEN_GPU_PATTERNS = re.compile(
    r"(?i)\b(a100|h100|h200|b100|b200|nvidia\s+a100|nvidia\s+h100|"
    r"rtx\s*5070|rtx\s*5080|rtx\s*5090|rtx\s*4090|tesla|t4|l4|v100|"
    r"mi250|mi300|mi350|l40s|a10|a16)\b"
)
_FAKE_NODE_PATTERNS = re.compile(
    r"(?i)\b(node-0[3-9]|gpu-node-0[3-9]|worker-0[3-9]|"
    r"inference-[2-9]|cluster-node-[2-9]|gpu-server-[2-9])\b"
)
VALID_TOPOLOGY_MODES = frozenset({
    "single_node", "degraded_single_gpu", "single_gpu",
    "multi_gpu", "inventory_only",
})
VALID_CONTRACT_PREFIXES = ("OBS-31A", "30I-", "OBS-31A.", "30I")
KNOWN_STORAGE_PATHS = frozenset({"/", "/mnt/opencode"})


@dataclass
class AlignmentCheck:
    domain: str = ""
    check: str = ""
    passed: bool = False
    severity: str = "info"
    detail: str = ""
    expected: Any = None
    actual: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "check": self.check,
            "passed": self.passed,
            "severity": self.severity,
            "detail": self.detail,
            "expected": self.expected,
            "actual": self.actual,
        }


@dataclass
class RuntimeAlignmentValidationResult:
    gpu_checks: list[AlignmentCheck] = field(default_factory=list)
    topology_checks: list[AlignmentCheck] = field(default_factory=list)
    model_checks: list[AlignmentCheck] = field(default_factory=list)
    contract_checks: list[AlignmentCheck] = field(default_factory=list)
    storage_checks: list[AlignmentCheck] = field(default_factory=list)
    service_checks: list[AlignmentCheck] = field(default_factory=list)
    alignment_score: float = 0.0
    alignment_level: str = "unknown"
    gpu_passed: int = 0
    gpu_total: int = 0
    topology_passed: int = 0
    topology_total: int = 0
    model_passed: int = 0
    model_total: int = 0
    contract_passed: int = 0
    contract_total: int = 0
    storage_passed: int = 0
    storage_total: int = 0
    service_passed: int = 0
    service_total: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": RUNTIME_ALIGNMENT_CONTRACT_VERSION,
            "timestamp": time.time(),
            "alignment_score": round(self.alignment_score, 2),
            "alignment_level": self.alignment_level,
            "gpu_alignment": {
                "passed": self.gpu_passed,
                "total": self.gpu_total,
                "checks": [c.to_dict() for c in self.gpu_checks],
            },
            "topology_alignment": {
                "passed": self.topology_passed,
                "total": self.topology_total,
                "checks": [c.to_dict() for c in self.topology_checks],
            },
            "model_alignment": {
                "passed": self.model_passed,
                "total": self.model_total,
                "checks": [c.to_dict() for c in self.model_checks],
            },
            "contract_alignment": {
                "passed": self.contract_passed,
                "total": self.contract_total,
                "checks": [c.to_dict() for c in self.contract_checks],
            },
            "storage_alignment": {
                "passed": self.storage_passed,
                "total": self.storage_total,
                "checks": [c.to_dict() for c in self.storage_checks],
            },
            "service_alignment": {
                "passed": self.service_passed,
                "total": self.service_total,
                "checks": [c.to_dict() for c in self.service_checks],
            },
        }


class RuntimeAlignmentValidator:

    RUNTIME_ALIGNMENT_CONTRACT_VERSION = RUNTIME_ALIGNMENT_CONTRACT_VERSION

    def __init__(self) -> None:
        self._result = RuntimeAlignmentValidationResult()

    # ── GPU State Alignment ──

    def validate_gpu_state(
        self,
        sensor_snapshot: dict[str, Any] | None = None,
        prometheus_targets: dict[str, Any] | None = None,
        grafana_dashboards: list[dict[str, Any]] | None = None,
    ) -> list[AlignmentCheck]:
        checks: list[AlignmentCheck] = []
        sensor = sensor_snapshot or {}
        targets = prometheus_targets or {}
        dashboards = grafana_dashboards or []

        gpu_summaries = sensor.get("gpu_operational_summaries", [])
        observed_gpu_names = {
            g.get("gpu_id", "").lower().strip()
            for g in gpu_summaries if g.get("gpu_id")
        }

        # RX9070 debe estar activo en runtime
        rx9070_in_runtime = any(
            "rx9070" in name for name in observed_gpu_names
        )
        checks.append(AlignmentCheck(
            domain="gpu", check="rx9070_active_in_runtime",
            passed=rx9070_in_runtime,
            severity="critical",
            detail=f"RX9070 {'detectado' if rx9070_in_runtime else 'NO detectado'} en runtime",
            expected=True, actual=rx9070_in_runtime,
        ))

        # RX7900XT debe estar como expected_offline o inventory en runtime
        rx7900xt_in_inventory = sensor.get("topology", {}).get("inventory_gpus", [])
        rx7900xt_found = any(
            "rx7900xt" in str(g).lower() for g in rx7900xt_in_inventory
        )
        checks.append(AlignmentCheck(
            domain="gpu", check="rx7900xt_expected_offline_in_runtime",
            passed=rx7900xt_found,
            severity="high",
            detail=f"RX7900XT {'en inventario' if rx7900xt_found else 'NO encontrado'} en runtime",
            expected=True, actual=rx7900xt_found,
        ))

        # RX7900XT en Prometheus: must be expected_offline
        target_list = targets.get("targets", []) or targets.get("results", [])
        rx7900xt_prom = any(
            "rx7900xt" in str(t.get("job", "")).lower()
            or "7900xt" in str(t.get("job", "")).lower()
            for t in target_list
        )
        expected_offline_list = targets.get("expected_offline", []) or []
        rx7900xt_expected_off = any(
            "7900xt" in str(e).lower() for e in expected_offline_list
        )
        # If RX7900XT exists in Prometheus targets, check it's classified as expected_offline
        if rx7900xt_prom:
            checks.append(AlignmentCheck(
                domain="gpu", check="rx7900xt_expected_offline_prometheus",
                passed=bool(rx7900xt_expected_off),
                severity="high",
                detail=f"RX7900XT en Prometheus {'correctamente clasificado como expected_offline'
                        if rx7900xt_expected_off else 'NO clasificado como expected_offline'}",
                expected=True, actual=rx7900xt_expected_off,
            ))

        # No forbidden GPUs in dashboards
        for d in dashboards:
            if not isinstance(d, dict):
                continue
            title = d.get("title", "")
            uid = d.get("uid", "")
            panel_json = str(d)
            forbidden = _FORBIDDEN_GPU_PATTERNS.findall(panel_json)
            if forbidden:
                checks.append(AlignmentCheck(
                    domain="gpu", check="no_forbidden_gpu_in_dashboards",
                    passed=False, severity="critical",
                    detail=f"GPU prohibida {', '.join(set(forbidden))} en dashboard {uid} ({title})",
                    expected="no forbidden GPUs", actual=set(forbidden),
                ))

        if not any(c.check == "no_forbidden_gpu_in_dashboards" for c in checks):
            checks.append(AlignmentCheck(
                domain="gpu", check="no_forbidden_gpu_in_dashboards",
                passed=True, severity="info",
                detail="No se detectaron GPUs prohibidas en dashboards",
                expected=True, actual=True,
            ))

        # No forbidden GPUs in runtime active layer
        for g in gpu_summaries:
            gpu_id = g.get("gpu_id", "")
            if _FORBIDDEN_GPU_PATTERNS.search(gpu_id):
                checks.append(AlignmentCheck(
                    domain="gpu", check="no_forbidden_gpu_in_runtime",
                    passed=False, severity="critical",
                    detail=f"GPU prohibida {gpu_id} en capa activa del runtime",
                    expected="no forbidden GPUs", actual=gpu_id,
                ))

        self._result.gpu_checks = checks
        self._result.gpu_passed = sum(1 for c in checks if c.passed)
        self._result.gpu_total = len(checks)
        return checks

    # ── Topology Alignment ──

    def validate_topology(
        self,
        runtime_summary: dict[str, Any] | None = None,
        sensor_snapshot: dict[str, Any] | None = None,
        grafana_dashboards: list[dict[str, Any]] | None = None,
    ) -> list[AlignmentCheck]:
        checks: list[AlignmentCheck] = []
        summary = runtime_summary or {}
        sensor = sensor_snapshot or {}
        dashboards = grafana_dashboards or []

        topology_mode_runtime = sensor.get("topology", {}).get("mode", "")
        topology_mode_summary = summary.get("topology_mode", "")

        # Topology modes should match
        if topology_mode_runtime and topology_mode_summary:
            match = topology_mode_runtime == topology_mode_summary
            checks.append(AlignmentCheck(
                domain="topology", check="topology_mode_consistent",
                passed=match, severity="high",
                detail=("topology_mode coincide" if match
                        else f"sensor={topology_mode_runtime} != summary={topology_mode_summary}"),
                expected=topology_mode_runtime, actual=topology_mode_summary,
            ))

        # Topology mode should be a known valid mode
        if topology_mode_runtime:
            known = topology_mode_runtime in VALID_TOPOLOGY_MODES
            checks.append(AlignmentCheck(
                domain="topology", check="topology_mode_valid",
                passed=known, severity="critical",
                detail=f"Modo '{topology_mode_runtime}' {'válido' if known else 'NO válido'}",
                expected="known mode", actual=topology_mode_runtime,
            ))

        # No fake nodes in dashboards
        panel_text = " ".join(str(d) for d in dashboards)
        fake_nodes = _FAKE_NODE_PATTERNS.findall(panel_text)
        checks.append(AlignmentCheck(
            domain="topology", check="no_fake_topology_in_dashboards",
            passed=len(fake_nodes) == 0,
            severity="high",
            detail=f"Nodos falsos detectados: {set(fake_nodes)}" if fake_nodes
                   else "No se detectaron nodos falsos en dashboards",
            expected="no fake nodes", actual=fake_nodes if fake_nodes else "none",
        ))

        self._result.topology_checks = checks
        self._result.topology_passed = sum(1 for c in checks if c.passed)
        self._result.topology_total = len(checks)
        return checks

    # ── Model Inventory Alignment ──

    def validate_model_inventory(
        self,
        lmstudio_state: dict[str, Any] | None = None,
        runtime_models: dict[str, Any] | None = None,
    ) -> list[AlignmentCheck]:
        checks: list[AlignmentCheck] = []
        lmstudio = lmstudio_state or {}
        rt_models = runtime_models or {}

        # Extract active models from runtime
        active_frontier = set()
        for model_id, data in rt_models.items():
            if isinstance(data, dict) and data.get("status") in ("active", "loaded"):
                active_frontier.add(model_id)

        # Extract models from LM Studio state (supports dict and list formats)
        lmstudio_models: set[str] = set()
        lmstudio_statuses = lmstudio.get("statuses") or lmstudio.get("models") or {}
        if isinstance(lmstudio_statuses, dict):
            for model_id, data in lmstudio_statuses.items():
                if isinstance(data, dict):
                    lmstudio_models.add(data.get("id", model_id))
                elif isinstance(data, str):
                    lmstudio_models.add(data)
        elif isinstance(lmstudio_statuses, list):
            for item in lmstudio_statuses:
                if isinstance(item, dict):
                    lmstudio_models.add(item.get("id", ""))
                elif isinstance(item, str):
                    lmstudio_models.add(item)

        expected_active = {"qwen2.5-coder-14b-instruct", "llama-3.1-8b-instruct", "nomic-embed-text-v1.5"}
        for model in expected_active:
            present_in_runtime = any(model in m for m in active_frontier)
            present_in_lmstudio = any(model in m for m in lmstudio_models)
            checks.append(AlignmentCheck(
                domain="model", check=f"model_{model}_active",
                passed=present_in_runtime and present_in_lmstudio,
                severity="critical" if model in ("qwen2.5-coder-14b-instruct",) else "high",
                detail=(f"Modelo {model}: runtime={'✓' if present_in_runtime else '✗'}, "
                        f"lmstudio={'✓' if present_in_lmstudio else '✗'}"),
                expected="active in both", actual=f"runtime={present_in_runtime}, lmstudio={present_in_lmstudio}",
            ))

        self._result.model_checks = checks
        self._result.model_passed = sum(1 for c in checks if c.passed)
        self._result.model_total = len(checks)
        return checks

    # ── Contract Version Alignment ──

    def validate_contract_versions(
        self,
        contracts: dict[str, str | None] | None = None,
    ) -> list[AlignmentCheck]:
        checks: list[AlignmentCheck] = []
        all_contracts = contracts or {}

        expected_versions = {
            "sensor": ("30I-D", "30I-"),
            "cognitive": ("30I-F", "30I-"),
            "grounding": ("30I-G", "30I-"),
            "observability": ("OBS-31A", "OBS-31A."),
            "prometheus_audit": ("OBS-31A.1", "OBS-31A."),
            "drift_detector": ("OBS-31A.2", "OBS-31A."),
            "grafana_inventory": ("OBS-31A.2", "OBS-31A."),
            "runtime_alignment": ("OBS-31A.3", "OBS-31A."),
        }

        for contract_key, (exact, prefix) in expected_versions.items():
            actual = all_contracts.get(contract_key)
            if actual is None:
                severity = "critical" if contract_key in ("observability", "runtime_alignment") else "high"
                checks.append(AlignmentCheck(
                    domain="contract", check=f"{contract_key}_version",
                    passed=False, severity=severity,
                    detail=f"Contract version para '{contract_key}' NO disponible",
                    expected=f"{exact} or {prefix}*", actual=None,
                ))
                continue
            prefix_match = actual.startswith(prefix) if prefix else actual == exact
            checks.append(AlignmentCheck(
                domain="contract", check=f"{contract_key}_version",
                passed=prefix_match or actual == exact,
                severity="critical" if contract_key in ("observability", "runtime_alignment") else "high",
                detail=f"{contract_key}: actual={actual}, expected={exact} or {prefix}*",
                expected=f"{exact} or {prefix}*", actual=actual,
            ))

        self._result.contract_checks = checks
        self._result.contract_passed = sum(1 for c in checks if c.passed)
        self._result.contract_total = len(checks)
        return checks

    # ── Storage Alignment ──

    def validate_storage(
        self,
        sensor_snapshot: dict[str, Any] | None = None,
    ) -> list[AlignmentCheck]:
        checks: list[AlignmentCheck] = []
        sensor = sensor_snapshot or {}

        observed_data = sensor.get("observed_data", {})
        system_data = observed_data.get("system_node", {})

        disk_data = {}
        if isinstance(system_data, dict):
            disk_data = system_data.get("disk", {}) or system_data

        disk_total = disk_data.get("total_gb", 0) or disk_data.get("total", 0)
        disk_used = disk_data.get("used_gb", 0) or disk_data.get("used", 0)
        disk_avail = disk_data.get("available_gb", 0) or disk_data.get("available", 0)

        has_disk_info = bool(disk_total and disk_used)
        checks.append(AlignmentCheck(
            domain="storage", check="disk_usage_available",
            passed=has_disk_info,
            severity="medium",
            detail=f"Datos de disco: {'disponibles' if has_disk_info else 'NO disponibles'}",
            expected="disk data present", actual=has_disk_info,
        ))

        # NAS archive check
        runtime_state = sensor.get("derived_state", {})
        archive_ok = runtime_state.get("storage", {}).get("archive_healthy", True)
        checks.append(AlignmentCheck(
            domain="storage", check="archive_state_healthy",
            passed=bool(archive_ok),
            severity="medium",
            detail=f"Archivo NAS: {'saludable' if archive_ok else 'problema detectado'}",
            expected=True, actual=archive_ok,
        ))

        self._result.storage_checks = checks
        self._result.storage_passed = sum(1 for c in checks if c.passed)
        self._result.storage_total = len(checks)
        return checks

    # ── Service Alignment ──

    def validate_services(
        self,
        prometheus_targets: dict[str, Any] | None = None,
    ) -> list[AlignmentCheck]:
        checks: list[AlignmentCheck] = []
        targets = prometheus_targets or {}

        target_list = targets.get("targets", []) or targets.get("results", [])

        expected_services = {
            "ailab-gateway", "ailab-router", "ailab-live-api",
            "prometheus", "grafana",
        }

        # Build map of job -> status from target list
        job_status: dict[str, str] = {}
        for t in target_list:
            job = t.get("job", "")
            if isinstance(t, dict):
                t_info = t.get("target", t)
                if isinstance(t_info, dict):
                    job = t_info.get("labels", {}).get("job", "") or t.get("job", "")
            status = t.get("status", t.get("health", "unknown"))
            job_status[job] = status

        for svc in expected_services:
            status = job_status.get(svc, "unknown")
            passed = status in ("healthy", "up", "active")
            checks.append(AlignmentCheck(
                domain="service", check=f"service_{svc}_up",
                passed=passed, severity="critical",
                detail=f"Servicio {svc}: {status}",
                expected="healthy/up", actual=status,
            ))

        self._result.service_checks = checks
        self._result.service_passed = sum(1 for c in checks if c.passed)
        self._result.service_total = len(checks)
        return checks

    # ── Cross-validation runner ──

    def validate_all(
        self,
        sensor_snapshot: dict[str, Any] | None = None,
        runtime_summary: dict[str, Any] | None = None,
        prometheus_targets: dict[str, Any] | None = None,
        grafana_dashboards: list[dict[str, Any]] | None = None,
        lmstudio_state: dict[str, Any] | None = None,
        runtime_models: dict[str, Any] | None = None,
        contracts: dict[str, str | None] | None = None,
    ) -> RuntimeAlignmentValidationResult:
        self.validate_gpu_state(sensor_snapshot, prometheus_targets, grafana_dashboards)
        self.validate_topology(runtime_summary, sensor_snapshot, grafana_dashboards)
        self.validate_model_inventory(lmstudio_state, runtime_models)
        self.validate_contract_versions(contracts)
        self.validate_storage(sensor_snapshot)
        self.validate_services(prometheus_targets)

        self._compute_score()
        return self._result

    def _compute_score(self) -> None:
        total_checks = (
            self._result.gpu_total + self._result.topology_total
            + self._result.model_total + self._result.contract_total
            + self._result.storage_total + self._result.service_total
        )
        total_passed = (
            self._result.gpu_passed + self._result.topology_passed
            + self._result.model_passed + self._result.contract_passed
            + self._result.storage_passed + self._result.service_passed
        )
        if total_checks == 0:
            self._result.alignment_score = 0.0
            self._result.alignment_level = "unknown"
            return

        score = round((total_passed / total_checks) * 100.0, 2)
        self._result.alignment_score = score

        if score >= 90:
            self._result.alignment_level = "healthy"
        elif score >= 70:
            self._result.alignment_level = "degraded"
        elif score >= 50:
            self._result.alignment_level = "unhealthy"
        else:
            self._result.alignment_level = "critical"


def build_runtime_alignment_result(
    validator: RuntimeAlignmentValidator | None = None,
) -> dict[str, Any]:
    if validator is None:
        return RuntimeAlignmentValidationResult().to_dict()
    return validator._result.to_dict()
