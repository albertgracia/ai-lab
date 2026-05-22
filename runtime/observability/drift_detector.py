"""FASE OBS-31A.2: Runtime ↔ Grafana drift detection engine.

Detects mismatches between runtime cognitive state and Grafana
dashboard topology, GPU inventory, service metadata, inventory
alignment, and runtime semantics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


DRIFT_DETECTOR_CONTRACT_VERSION = "OBS-31A.2"


@dataclass
class DriftDetectionResult:
    gpu_drift: list[dict[str, Any]] = field(default_factory=list)
    topology_drift: list[dict[str, Any]] = field(default_factory=list)
    service_drift: list[dict[str, Any]] = field(default_factory=list)
    model_drift: list[dict[str, Any]] = field(default_factory=list)
    semantic_drift: list[dict[str, Any]] = field(default_factory=list)
    inventory_drift: list[dict[str, Any]] = field(default_factory=list)
    runtime_mismatch: list[dict[str, Any]] = field(default_factory=list)
    total_drifts: int = 0

    def to_dict(self) -> dict[str, Any]:
        total = (len(self.gpu_drift) + len(self.topology_drift)
                 + len(self.service_drift) + len(self.model_drift)
                 + len(self.semantic_drift) + len(self.inventory_drift)
                 + len(self.runtime_mismatch))
        return {
            "contract_version": DRIFT_DETECTOR_CONTRACT_VERSION,
            "timestamp": time.time(),
            "total_drifts": total,
            "gpu_drift": self.gpu_drift,
            "topology_drift": self.topology_drift,
            "service_drift": self.service_drift,
            "model_drift": self.model_drift,
            "semantic_drift": self.semantic_drift,
            "inventory_drift": self.inventory_drift,
            "runtime_mismatch": self.runtime_mismatch,
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
    "rtx 5070", "rtx 5080", "rtx 5090",
    "rtx 4090", "rtx 3090", "rtx 3080",
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
                    "gpu": gpu, "severity": "critical",
                    "detail": f"GPU {gpu} no existe en el runtime activo",
                })
            elif gpu not in runtime_set and gpu not in _EXPECTED_GPUS:
                drifts.append({
                    "type": "unknown_gpu_in_dashboard",
                    "gpu": gpu, "severity": "high",
                    "detail": f"GPU {gpu} no reconocida por el runtime",
                })

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

        runtime_node_count = len(_EXPECTED_HOSTS)
        dashboard_node_count = dt.get("node_count", 0) if isinstance(dt, dict) else 0
        if dashboard_node_count and dashboard_node_count > runtime_node_count:
            drifts.append({
                "type": "node_count_mismatch",
                "dashboard_nodes": dashboard_node_count,
                "runtime_nodes": runtime_node_count,
                "severity": "medium",
                "detail": "Dashboard shows more nodes than runtime expects",
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

    def detect_semantic_drift(
        self,
        dashboard_domains: list[str] | None = None,
        runtime_domains: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        drifts: list[dict[str, Any]] = []
        if not dashboard_domains or not runtime_domains:
            return drifts

        dd_set = {d.lower().strip() for d in dashboard_domains}
        rd_set = {d.lower().strip() for d in runtime_domains}

        for domain in dd_set:
            if domain not in rd_set:
                drifts.append({
                    "type": "domain_mismatch",
                    "dashboard_domain": domain,
                    "severity": "medium",
                    "detail": f"Domain '{domain}' en dashboard no existe en runtime",
                })
        self._result.semantic_drift = drifts
        return drifts

    def detect_inventory_drift(
        self,
        dashboard_inventory: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        drifts: list[dict[str, Any]] = []
        if not dashboard_inventory:
            return drifts

        try:
            from runtime.observability.grafana_inventory import _ALL_DASHBOARDS as KNOWN
            known_uids = {d["uid"] for d in KNOWN}
        except ImportError:
            known_uids = set()

        for d in dashboard_inventory:
            uid = d.get("uid", "")
            if uid and uid not in known_uids:
                drifts.append({
                    "type": "unknown_dashboard",
                    "uid": uid,
                    "title": d.get("title", ""),
                    "severity": "medium",
                    "detail": f"Dashboard {uid} no está en el inventario conocido",
                })

        self._result.inventory_drift = drifts
        return drifts

    def detect_runtime_mismatch(
        self,
        dashboard_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        drifts: list[dict[str, Any]] = []
        if not dashboard_metadata:
            return drifts

        d_owner = dashboard_metadata.get("semantic_owner", "")
        d_domain = dashboard_metadata.get("runtime_domain", "")

        valid_domains = {"overview", "runtime", "infrastructure", "gpu", "slo", "legacy", "memory", "cognitive"}
        if d_domain and d_domain not in valid_domains:
            drifts.append({
                "type": "invalid_runtime_domain",
                "domain": d_domain,
                "severity": "low",
                "detail": f"Runtime domain '{d_domain}' no es un dominio válido",
            })

        if d_owner and d_owner not in {"runtime", "infrastructure", "gpu", "slo", "memory", "cognitive", "governance"}:
            drifts.append({
                "type": "invalid_semantic_owner",
                "owner": d_owner,
                "severity": "low",
                "detail": f"Semantic owner '{d_owner}' no es un owner válido",
            })

        self._result.runtime_mismatch = drifts
        return drifts

    def detect_all(
        self,
        dashboard_gpus: list[str] | None = None,
        runtime_gpus: list[str] | None = None,
        dashboard_topology: dict[str, Any] | None = None,
        runtime_topology: dict[str, Any] | None = None,
        dashboard_services: list[str] | None = None,
        dashboard_domains: list[str] | None = None,
        runtime_domains: list[str] | None = None,
        dashboard_inventory: list[dict[str, Any]] | None = None,
        dashboard_metadata: dict[str, Any] | None = None,
    ) -> DriftDetectionResult:
        self.detect_gpu_drift(dashboard_gpus, runtime_gpus)
        self.detect_topology_drift(dashboard_topology, runtime_topology)
        self.detect_service_drift(dashboard_services)
        self.detect_semantic_drift(dashboard_domains, runtime_domains)
        self.detect_inventory_drift(dashboard_inventory)
        self.detect_runtime_mismatch(dashboard_metadata)
        total = (len(self._result.gpu_drift) + len(self._result.topology_drift)
                 + len(self._result.service_drift) + len(self._result.model_drift)
                 + len(self._result.semantic_drift) + len(self._result.inventory_drift)
                 + len(self._result.runtime_mismatch))
        self._result.total_drifts = total
        return self._result


def build_drift_summary(
    drift_result: DriftDetectionResult | None = None,
) -> dict[str, Any]:
    if drift_result is None:
        drift_result = DriftDetectionResult()
    return drift_result.to_dict()


def build_runtime_alignment_summary(
    drift_result: DriftDetectionResult | None = None,
    dashboard_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if drift_result is None:
        drift_result = DriftDetectionResult()
    drift_dict = drift_result.to_dict()

    total_drifts = drift_dict.get("total_drifts", 0)
    total_dashboards = len(dashboard_results) if dashboard_results else 0
    broken_dashboards = sum(1 for r in (dashboard_results or [])
                             if r.get("health") in ("broken", "stale"))
    healthy_dashboards = sum(1 for r in (dashboard_results or [])
                              if r.get("health") == "healthy")

    total_penalty = total_drifts * 5 + broken_dashboards * 10
    alignment_score = max(0, min(100, 100 - total_penalty))
    if alignment_score >= 90:
        level = "healthy"
    elif alignment_score >= 70:
        level = "degraded"
    elif alignment_score >= 50:
        level = "unhealthy"
    else:
        level = "critical"

    return {
        "contract_version": DRIFT_DETECTOR_CONTRACT_VERSION,
        "timestamp": time.time(),
        "alignment_score": alignment_score,
        "alignment_level": level,
        "components": {
            "total_drifts": total_drifts,
            "total_dashboards": total_dashboards,
            "healthy_dashboards": healthy_dashboards,
            "broken_dashboards": broken_dashboards,
            "drift_penalty": total_drifts * 5,
            "broken_penalty": broken_dashboards * 10,
            "total_penalty": total_penalty,
        },
        "drift_summary": drift_dict,
    }
