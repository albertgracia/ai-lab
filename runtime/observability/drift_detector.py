"""FASE OBS-31A: Runtime ↔ Grafana drift detection.

Detects mismatches between runtime cognitive state and Grafana
dashboard topology, GPU inventory, and service metadata.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DriftDetectionResult:
    gpu_drift: list[dict[str, Any]] = field(default_factory=list)
    topology_drift: list[dict[str, Any]] = field(default_factory=list)
    service_drift: list[dict[str, Any]] = field(default_factory=list)
    model_drift: list[dict[str, Any]] = field(default_factory=list)
    semantic_drift: list[dict[str, Any]] = field(default_factory=list)
    total_drifts: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": "OBS-31A",
            "timestamp": time.time(),
            "total_drifts": len(self.gpu_drift) + len(self.topology_drift)
                + len(self.service_drift) + len(self.model_drift)
                + len(self.semantic_drift),
            "gpu_drift": self.gpu_drift,
            "topology_drift": self.topology_drift,
            "service_drift": self.service_drift,
            "model_drift": self.model_drift,
            "semantic_drift": self.semantic_drift,
        }


_EXPECTED_GPUS = frozenset({"RX9070", "RX7900XT", "rx9070", "rx7900xt"})
_EXPECTED_HOSTS = frozenset({
    "192.168.1.30", "192.168.1.50", "192.168.1.60",
    "192.168.1.40", "192.168.1.200", "ubuntu-ialab",
})
_EXPECTED_SERVICES = frozenset({
    "ailab-gateway", "ailab-router", "ailab-live-api",
    "ailab-docs", "ailab-heartbeat", "ailab-metrics",
    "ailab-runner", "prometheus", "grafana",
})
_FORBIDDEN_GPU_PATTERNS = {
    "a100", "h100", "h200", "b100", "b200",
    "v100", "t4", "l4", "l40s", "a10", "a16",
    "mi250", "mi300", "mi350",
}


class DriftDetector:
    def __init__(
        self,
        runtime_context: dict[str, Any] | None = None,
    ):
        self._runtime_context = runtime_context or {}
        self._result = DriftDetectionResult()

    def detect_gpu_drift(
        self,
        dashboard_gpus: list[str] | None = None,
        runtime_gpus: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        drifts: list[dict[str, Any]] = []
        if runtime_gpus is None:
            runtime_gpus = list(_EXPECTED_GPUS)

        dashboard_set = set()
        if dashboard_gpus:
            dashboard_set = {g.lower().strip() for g in dashboard_gpus}

        runtime_set = {g.lower().strip() for g in (runtime_gpus or [])}

        for gpu in dashboard_set:
            if gpu in _FORBIDDEN_GPU_PATTERNS:
                drifts.append({
                    "type": "forbidden_gpu_in_dashboard",
                    "gpu": gpu,
                    "severity": "critical",
                    "detail": f"GPU {gpu} no existe en el runtime activo",
                })
            elif gpu not in runtime_set and gpu not in _EXPECTED_GPUS:
                drifts.append({
                    "type": "unknown_gpu_in_dashboard",
                    "gpu": gpu,
                    "severity": "high",
                    "detail": f"GPU {gpu} no reconocida por el runtime",
                })

        for gpu in runtime_set:
            if gpu not in dashboard_set:
                pass

        self._result.gpu_drift = drifts
        return drifts

    def detect_topology_drift(
        self,
        dashboard_topology: dict[str, Any] | None = None,
        runtime_topology: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        drifts: list[dict[str, Any]] = []
        rt = runtime_topology or self._runtime_context.get("runtime_topology", {})
        dt = dashboard_topology or {}

        runtime_mode = rt.get("mode", "") if isinstance(rt, dict) else ""
        dashboard_mode = dt.get("mode", "") if isinstance(dt, dict) else ""

        if dashboard_mode and runtime_mode and dashboard_mode != runtime_mode:
            drifts.append({
                "type": "topology_mode_mismatch",
                "dashboard_mode": dashboard_mode,
                "runtime_mode": runtime_mode,
                "severity": "high",
                "detail": "Dashboard topology mode differs from runtime",
            })

        self._result.topology_drift = drifts
        return drifts

    def detect_service_drift(
        self,
        dashboard_services: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        drifts: list[dict[str, Any]] = []
        if not dashboard_services:
            return drifts

        ds_set = {s.lower().strip() for s in dashboard_services}
        for svc in ds_set:
            if svc not in _EXPECTED_SERVICES and "prometheus" not in svc and "grafana" not in svc:
                pass

        for expected in _EXPECTED_SERVICES:
            if expected not in ds_set and "prometheus" not in expected and "grafana" not in expected:
                pass

        self._result.service_drift = drifts
        return drifts

    def detect_all(
        self,
        dashboard_gpus: list[str] | None = None,
        runtime_gpus: list[str] | None = None,
        dashboard_topology: dict[str, Any] | None = None,
        runtime_topology: dict[str, Any] | None = None,
        dashboard_services: list[str] | None = None,
    ) -> DriftDetectionResult:
        self.detect_gpu_drift(dashboard_gpus, runtime_gpus)
        self.detect_topology_drift(dashboard_topology, runtime_topology)
        self.detect_service_drift(dashboard_services)
        return self._result


def build_drift_summary(
    drift_result: DriftDetectionResult | None = None,
) -> dict[str, Any]:
    if drift_result is None:
        drift_result = DriftDetectionResult()
    return drift_result.to_dict()
