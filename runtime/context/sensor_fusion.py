import json
import time
import requests
from enum import Enum
from dataclasses import dataclass, field
from typing import Any

from runtime.context.prometheus_client import PrometheusQueryClient

SENSOR_FUSION_MAX_CHARS = 16_000

LMSTUDIO_URL = "http://192.168.1.50:1234/v1"


class SensorPriority(Enum):
    CRITICAL = 3
    IMPORTANT = 2
    AUXILIARY = 1


DOMAIN_PRIORITY: dict[str, SensorPriority] = {
    "gateway": SensorPriority.CRITICAL,
    "router": SensorPriority.CRITICAL,
    "gpu_nodes": SensorPriority.CRITICAL,
    "control_plane": SensorPriority.IMPORTANT,
    "live_api": SensorPriority.IMPORTANT,
    "containers": SensorPriority.IMPORTANT,
    "docker": SensorPriority.IMPORTANT,
    "system_node": SensorPriority.IMPORTANT,
    "smartctl": SensorPriority.IMPORTANT,
    "lmstudio_models": SensorPriority.IMPORTANT,
    "windows_exporters": SensorPriority.AUXILIARY,
    "unifi": SensorPriority.AUXILIARY,
    "cloudflare_tunnel": SensorPriority.AUXILIARY,
}


@dataclass
class RuntimeTopologyState:
    mode: str = "degraded_single_gpu"
    active_gpus: list[dict] = field(default_factory=list)
    inventory_gpus: list[dict] = field(default_factory=list)
    unexpected_down: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "active_gpus": self.active_gpus,
            "inventory_gpus": self.inventory_gpus,
            "unexpected_down": self.unexpected_down,
        }


@dataclass
class RuntimeSensorFusionSnapshot:
    timestamp: float = 0.0
    topology: RuntimeTopologyState = field(default_factory=RuntimeTopologyState)
    observed_data: dict[str, Any] = field(default_factory=dict)
    derived_state: dict[str, Any] = field(default_factory=dict)
    domain_confidence: dict[str, str] = field(default_factory=dict)
    observed_sources: list[str] = field(default_factory=list)
    missing_sources: list[str] = field(default_factory=list)
    expected_offline_targets: list[dict] = field(default_factory=list)
    unexpected_down_targets: list[dict] = field(default_factory=list)
    last_scrape_seconds_ago: dict[str, float] = field(default_factory=dict)
    context_size_bytes: int = 0

    def to_dict(self, max_chars: int = SENSOR_FUSION_MAX_CHARS) -> dict[str, Any]:
        base = {
            "timestamp": self.timestamp,
            "topology": self.topology.to_dict(),
            "domain_confidence": self.domain_confidence,
            "observed_sources_count": len(self.observed_sources),
            "missing_sources_count": len(self.missing_sources),
            "expected_offline": [t.get("name", t.get("job", "?")) for t in self.expected_offline_targets],
            "unexpected_down": [t.get("name", t.get("job", "?")) for t in self.unexpected_down_targets],
            "freshness": {k: f"{v:.1f}s ago" for k, v in self.last_scrape_seconds_ago.items()},
        }
        derived = {}
        for domain, state in self.derived_state.items():
            if domain in ("gpu_nodes", "gateway", "system_node", "control_plane"):
                derived[domain] = state
        base["derived_state"] = derived

        observed = {}
        for domain, data in self.observed_data.items():
            if domain in ("gpu_nodes", "gateway", "system_node", "lmstudio_models"):
                if isinstance(data, dict):
                    truncated = {k: v for k, v in data.items() if not isinstance(v, (list, dict)) or len(str(v)) < 200}
                    observed[domain] = truncated
        base["observed_data"] = observed

        serialized = json.dumps(base, ensure_ascii=False, default=str)
        if len(serialized) > max_chars:
            priority_order = ["derived_state", "observed_data", "freshness", "domain_confidence"]
            for key in priority_order:
                if len(serialized) <= max_chars:
                    break
                if key in base:
                    del base[key]
                    serialized = json.dumps(base, ensure_ascii=False, default=str)
            if len(serialized) > max_chars:
                base["_truncated"] = True
                serialized = json.dumps(base, ensure_ascii=False, default=str)[:max_chars]
                serialized = serialized.rstrip(",") + ',"_truncated":true}'
        base["_runtime_generation"] = "30I"
        base["context_size_bytes"] = len(serialized)
        return base


class SensorFusionEngine:
    def __init__(self, prometheus: PrometheusQueryClient | None = None):
        self.prometheus = prometheus or PrometheusQueryClient()
        self._gpu_metrics_cache: dict[str, Any] | None = None
        self._gpu_metrics_ts: float = 0

    def collect(self) -> RuntimeSensorFusionSnapshot:
        snapshot = RuntimeSensorFusionSnapshot(timestamp=time.time())
        self._collect_gpu_nodes(snapshot)
        self._collect_gateway(snapshot)
        self._collect_router(snapshot)
        self._collect_live_api(snapshot)
        self._collect_control_plane(snapshot)
        self._collect_containers(snapshot)
        self._collect_docker(snapshot)
        self._collect_system_node(snapshot)
        self._collect_smartctl(snapshot)
        self._collect_lmstudio_models(snapshot)
        self._collect_windows_exporters(snapshot)
        self._collect_unifi(snapshot)
        self._collect_cloudflare_tunnel(snapshot)
        self._compute_topology(snapshot)
        self._compute_domain_confidence(snapshot)
        return snapshot

    def _store_observed(self, snapshot: RuntimeSensorFusionSnapshot, domain: str, data: dict | None, priority: SensorPriority) -> None:
        if data is not None:
            snapshot.observed_data[domain] = data
            snapshot.observed_sources.append(domain)
        else:
            snapshot.missing_sources.append(domain)

    def _check_up(self, snapshot: RuntimeSensorFusionSnapshot, domain: str, job: str, priority: SensorPriority) -> dict | None:
        result = self.prometheus.get_target_up(job)
        if result is not None:
            self._store_observed(snapshot, domain, result, priority)
            if result["value"] == 0:
                is_inventory = "rx7900xt" in job.lower() or "60:" in result.get("instance", "")
                entry = {"job": job, "instance": result.get("instance", "?"), "expected": is_inventory}
                if is_inventory:
                    snapshot.expected_offline_targets.append(entry)
                else:
                    snapshot.unexpected_down_targets.append(entry)
                    snapshot.derived_state[domain] = {"health": "down", "expected": False}
            else:
                snapshot.derived_state[domain] = {"health": "ok", "expected": True}
            return result
        snapshot.missing_sources.append(domain)
        return None

    def _collect_gateway(self, snapshot: RuntimeSensorFusionSnapshot) -> None:
        data: dict[str, Any] = {"source_of_truth": "prometheus"}
        up = self._check_up(snapshot, "gateway", "ai-lab-gateway", SensorPriority.CRITICAL)
        if up:
            data["up"] = up["value"]
            snapshot.derived_state["gateway"] = {"health": "ok" if up["value"] == 1 else "down"}

        for q, label in [
            ("ailab_route_family_total", "route_families"),
            ("ailab_first_token_latency_ms", "ttfb_ms"),
        ]:
            r = self.prometheus.query(q)
            if r:
                data[label] = r
        for q, label in [
            ("ailab_runtime_slo_state", "slo_state"),
            ("ailab_runtime_degradation_level", "degradation_level"),
        ]:
            v = self.prometheus.query_instant(q)
            if v is not None:
                data[label] = v
        r = self.prometheus.query('ailab_runtime_model_state')
        if r:
            data["model_states"] = [{"model": m.get("metric", {}).get("model"), "status": m.get("metric", {}).get("status"), "value": m.get("value",["0","0"])[1]} for m in r]
        eg = self.prometheus.query('ailab_report_evidence_guard_scoped_total')
        if eg:
            data["evidence_guard"] = [{"action": m.get("metric", {}).get("action"), "model": m.get("metric", {}).get("model"), "value": m.get("value",["0","0"])[1]} for m in eg]
        self._store_observed(snapshot, "gateway", data, SensorPriority.CRITICAL)

    def _collect_router(self, snapshot: RuntimeSensorFusionSnapshot) -> None:
        self._check_up(snapshot, "router", "ai-lab-router", SensorPriority.CRITICAL)

    def _collect_live_api(self, snapshot: RuntimeSensorFusionSnapshot) -> None:
        self._check_up(snapshot, "live_api", "ai-lab-live-api", SensorPriority.IMPORTANT)

    def _collect_control_plane(self, snapshot: RuntimeSensorFusionSnapshot) -> None:
        self._check_up(snapshot, "control_plane", "ai-lab-cadvisor", SensorPriority.IMPORTANT)

    def _collect_containers(self, snapshot: RuntimeSensorFusionSnapshot) -> None:
        self._check_up(snapshot, "containers", "ai-lab-cadvisor", SensorPriority.IMPORTANT)

    def _collect_docker(self, snapshot: RuntimeSensorFusionSnapshot) -> None:
        result = self.prometheus.get_target_up("docker")
        if result is not None:
            self._store_observed(snapshot, "docker", result, SensorPriority.IMPORTANT)
            snapshot.derived_state["docker"] = {"health": "ok" if result["value"] == 1 else "down"}
        else:
            snapshot.missing_sources.append("docker")

    def _collect_system_node(self, snapshot: RuntimeSensorFusionSnapshot) -> None:
        data: dict[str, Any] = {"source_of_truth": "prometheus"}
        up = self._check_up(snapshot, "system_node", "ai-lab-node", SensorPriority.IMPORTANT)
        if up:
            data["up"] = up["value"]
        for q, label in [
            ("node_cpu_seconds_total", "cpu_seconds_total"),
            ("node_memory_MemAvailable_bytes", "mem_available_bytes"),
            ("node_memory_MemTotal_bytes", "mem_total_bytes"),
            ("node_filesystem_avail_bytes", "fs_avail_bytes"),
            ("node_filesystem_size_bytes", "fs_size_bytes"),
        ]:
            v = self.prometheus.query_instant(q)
            if v is not None:
                data[label] = v
        if data.get("mem_available_bytes") and data.get("mem_total_bytes"):
            data["mem_usage_pct"] = round(100 * (1 - data["mem_available_bytes"] / data["mem_total_bytes"]), 1)
        if data.get("fs_avail_bytes") and data.get("fs_size_bytes"):
            data["fs_usage_pct"] = round(100 * (1 - data["fs_avail_bytes"] / data["fs_size_bytes"]), 1)
        self._store_observed(snapshot, "system_node", data if len(data) > 1 else None, SensorPriority.IMPORTANT)

    def _collect_gpu_nodes(self, snapshot: RuntimeSensorFusionSnapshot) -> None:
        data: dict[str, Any] = {"source_of_truth": "prometheus"}
        rx9070_up = self.prometheus.get_target_up("ai-lab-gpu-rx9070")
        rx7900xt_up = self.prometheus.get_target_up("ai-lab-gpu-rx7900xt")
        gpu_metrics = self.prometheus.query_gpu_metrics()

        if rx9070_up:
            data["rx9070"] = {"status": "up" if rx9070_up["value"] == 1 else "down", "instance": rx9070_up.get("instance", "?")}
        if rx7900xt_up:
            data["rx7900xt"] = {"status": "down", "instance": rx7900xt_up.get("instance", "?"), "expected_offline": True}
        if gpu_metrics:
            data["gpu_metrics"] = gpu_metrics
            snapshot._gpu_metrics_cache = gpu_metrics

        if rx9070_up and rx9070_up["value"] == 1:
            snapshot.derived_state["gpu_nodes"] = {"health": "ok", "active": "RX9070", "vram_gb": 16}
        elif rx9070_up and rx9070_up["value"] == 0:
            snapshot.derived_state["gpu_nodes"] = {"health": "degraded", "active": "none", "reason": "RX9070 down"}
        else:
            snapshot.derived_state["gpu_nodes"] = {"health": "unknown", "active": "unknown"}
        self._store_observed(snapshot, "gpu_nodes", data, SensorPriority.CRITICAL)

    def _collect_smartctl(self, snapshot: RuntimeSensorFusionSnapshot) -> None:
        self._check_up(snapshot, "smartctl", "smartctl-exporter", SensorPriority.IMPORTANT)

    def _collect_lmstudio_models(self, snapshot: RuntimeSensorFusionSnapshot) -> None:
        data: dict[str, Any] = {"source_of_truth": "lmstudio_api"}
        try:
            resp = requests.get(f"{LMSTUDIO_URL}/models", timeout=5.0)
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                data["models"] = [m.get("id") for m in models if isinstance(m, dict)]
                data["model_count"] = len(data["models"])
                self._store_observed(snapshot, "lmstudio_models", data, SensorPriority.IMPORTANT)
                snapshot.derived_state["lmstudio_models"] = {"health": "ok", "model_count": data["model_count"]}
            else:
                snapshot.missing_sources.append("lmstudio_models")
        except (requests.ConnectionError, requests.Timeout, json.JSONDecodeError):
            snapshot.missing_sources.append("lmstudio_models")
            snapshot.derived_state["lmstudio_models"] = {"health": "unreachable"}

    def _collect_windows_exporters(self, snapshot: RuntimeSensorFusionSnapshot) -> None:
        data: dict[str, Any] = {"source_of_truth": "prometheus"}
        for job in ["serv2025-hyperv2", "serv2025-market", "windows11-nas"]:
            r = self.prometheus.get_target_up(job)
            if r:
                data[job] = {"status": "up" if r["value"] == 1 else "down", "instance": r.get("instance", "?")}
        if data and any(k != "source_of_truth" for k in data):
            self._store_observed(snapshot, "windows_exporters", data, SensorPriority.AUXILIARY)
        else:
            snapshot.missing_sources.append("windows_exporters")

    def _collect_unifi(self, snapshot: RuntimeSensorFusionSnapshot) -> None:
        self._check_up(snapshot, "unifi", "unpoller", SensorPriority.AUXILIARY)

    def _collect_cloudflare_tunnel(self, snapshot: RuntimeSensorFusionSnapshot) -> None:
        self._check_up(snapshot, "cloudflare_tunnel", "cloudflare-tunnel", SensorPriority.AUXILIARY)

    def _compute_topology(self, snapshot: RuntimeSensorFusionSnapshot) -> None:
        gpu_data = snapshot.observed_data.get("gpu_nodes", {})
        rx9070_status = "unknown"
        rx7900xt_expected_offline = False
        if isinstance(gpu_data, dict):
            rx9070_info = gpu_data.get("rx9070", {})
            if isinstance(rx9070_info, dict):
                rx9070_status = rx9070_info.get("status", "unknown")
            rx7900_info = gpu_data.get("rx7900xt", {})
            if isinstance(rx7900_info, dict):
                rx7900xt_expected_offline = rx7900_info.get("expected_offline", False)

        active_gpus = []
        inventory_gpus = []
        unexpected_down = []

        if rx9070_status == "up":
            gpu_metrics = snapshot._gpu_metrics_cache or {}
            active_gpus.append({
                "name": "RX9070",
                "host": "192.168.1.50",
                "vram_gb": 16,
                "status": "online",
                "expected_offline": False,
                "gpu_temp_c": gpu_metrics.get("temp_gpu_core_c"),
                "gpu_load_pct": gpu_metrics.get("load_gpu_core"),
                "gpu_power_w": gpu_metrics.get("power_gpu_package_w"),
                "gpu_fan_rpm": gpu_metrics.get("fan_gpu_fan_rpm"),
            })
        else:
            unexpected_down.append({"name": "RX9070", "host": "192.168.1.50", "expected": False})

        inventory_gpus.append({
            "name": "RX7900XT",
            "host": "192.168.1.60",
            "vram_gb": 20,
            "status": "offline",
            "expected_offline": True,
        })
        if rx7900xt_expected_offline:
            snapshot.expected_offline_targets.append({"name": "RX7900XT", "job": "ai-lab-gpu-rx7900xt", "expected": True})

        if len(active_gpus) >= 2:
            mode = "multi_gpu"
        elif len(active_gpus) == 1 and len(inventory_gpus) > 0:
            mode = "degraded_single_gpu"
        elif len(active_gpus) == 1:
            mode = "single_gpu"
        else:
            mode = "inventory_only"

        snapshot.topology = RuntimeTopologyState(
            mode=mode,
            active_gpus=active_gpus,
            inventory_gpus=inventory_gpus,
            unexpected_down=unexpected_down,
        )

    def _compute_domain_confidence(self, snapshot: RuntimeSensorFusionSnapshot) -> None:
        total_weight = 0
        observed_weight = 0
        domain_confs: dict[str, str] = {}

        for domain, priority in DOMAIN_PRIORITY.items():
            w = priority.value
            total_weight += w
            if domain in snapshot.observed_sources:
                observed_weight += w
                domain_confs[domain] = "high"
            elif domain in snapshot.expected_offline_targets:
                observed_weight += w
                domain_confs[domain] = "medium"
            else:
                conf = "low"
                for t in snapshot.unexpected_down_targets:
                    if t.get("job", "").startswith(domain):
                        conf = "low"
                        break
                domain_confs[domain] = conf

        snapshot.domain_confidence = domain_confs

        ratio = observed_weight / total_weight if total_weight > 0 else 0
        critical_missing = any(
            DOMAIN_PRIORITY.get(d) == SensorPriority.CRITICAL and d in snapshot.missing_sources
            for d in DOMAIN_PRIORITY
        )
        has_unexpected_down = len(snapshot.unexpected_down_targets) > 0

        if ratio >= 0.8 and not critical_missing and not has_unexpected_down:
            confidence = "high"
        elif ratio >= 0.5 and not critical_missing:
            confidence = "medium"
        else:
            confidence = "low"
        snapshot._global_confidence = confidence
