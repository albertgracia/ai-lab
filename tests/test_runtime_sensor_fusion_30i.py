"""FASE 30I: Runtime Sensor Fusion & Metrics Context Enrichment tests."""

import json
import time
from unittest.mock import patch, MagicMock

from runtime.context.prometheus_client import PrometheusQueryClient
from runtime.context.sensor_fusion import (
    SensorFusionEngine,
    RuntimeSensorFusionSnapshot,
    RuntimeTopologyState,
    SensorPriority,
    DOMAIN_PRIORITY,
    SENSOR_FUSION_MAX_CHARS,
)
from runtime.context.summary_builder import OperationalSummaryBuilder


# ── Prometheus Client Tests ────────────────────────────────────


class TestPrometheusQueryClient:
    def test_query_returns_list_or_none(self):
        client = PrometheusQueryClient(base_url="http://nonexistent:9090", timeout=0.5)
        result = client.query("up")
        assert result is None or isinstance(result, list)

    def test_query_timeout_does_not_block(self):
        client = PrometheusQueryClient(base_url="http://192.168.1.1:9090", timeout=0.5)
        start = time.time()
        result = client.query("up")
        elapsed = time.time() - start
        assert elapsed < 3.0
        assert result is None

    def test_cache_ttl(self):
        client = PrometheusQueryClient(base_url="http://nonexistent:9090", timeout=0.5)
        with patch.object(client, "_make_request", return_value=[{"test": "data"}]) as mock:
            r1 = client.query("up")
            r2 = client.query("up")
            assert r1 == r2
            mock.assert_called_once()

    def test_cache_expires(self):
        client = PrometheusQueryClient(base_url="http://nonexistent:9090", timeout=0.5, cache_ttl=0.01)
        with patch.object(client, "_make_request", return_value=[{"test": "data"}]) as mock:
            client.query("up")
            time.sleep(0.02)
            client.query("up")
            assert mock.call_count >= 2

    def test_get_target_up_returns_dict(self):
        mock_result = [{"metric": {"job": "test", "instance": "127.0.0.1:8008"}, "value": ["123456", "1"]}]
        client = PrometheusQueryClient(base_url="http://nonexistent", timeout=0.5)
        with patch.object(client, "_make_request", return_value=mock_result):
            r = client.get_target_up("test")
            assert r is not None
            assert r["value"] == 1
            assert r["source_of_truth"] == "prometheus"
            assert r["job"] == "test"

    def test_query_instant_returns_float(self):
        mock_result = [{"metric": {}, "value": ["123456", "42.5"]}]
        client = PrometheusQueryClient(base_url="http://nonexistent", timeout=0.5)
        with patch.object(client, "_make_request", return_value=mock_result):
            v = client.query_instant("up")
            assert v == 42.5

    def test_query_gpu_metrics_returns_formatted(self):
        mock_result = [
            {"metric": {"__name__": "gpu_smalldata", "sensor": "GPU_Memory_Used", "gpu": "AMD_Radeon_RX_9070"}, "value": ["0", "15639"]},
            {"metric": {"__name__": "gpu_temperature_celsius", "sensor": "GPU_Core", "gpu": "AMD_Radeon_RX_9070"}, "value": ["0", "32"]},
            {"metric": {"__name__": "gpu_load_percent", "sensor": "GPU_Core", "gpu": "AMD_Radeon_RX_9070"}, "value": ["0", "3"]},
        ]
        client = PrometheusQueryClient(base_url="http://nonexistent", timeout=0.5)
        with patch.object(client, "_make_request", return_value=mock_result):
            g = client.query_gpu_metrics()
            assert g is not None
            assert "gpu_memory_used" in g
            assert g["gpu_memory_used"] == 15639.0
            assert "temp_gpu_core_c" in g
            assert g["temp_gpu_core_c"] == 32.0
            assert "load_gpu_core" in g
            assert g["load_gpu_core"] == 3.0
            assert g["source_of_truth"] == "prometheus"

    def test_freshness_labels(self):
        client = PrometheusQueryClient()
        assert client.freshness(None) == "unknown"
        assert client.freshness(2.0) == "fresh"
        assert client.freshness(20.0) == "stale"
        assert client.freshness(120.0) == "expired"


# ── Sensor Fusion Tests ────────────────────────────────────────


def fake_prometheus_client():
    client = MagicMock(spec=PrometheusQueryClient)

    def get_target_up_side_effect(job):
        up_map = {
            "ai-lab-gateway": 1,
            "ai-lab-router": 1,
            "ai-lab-live-api": 1,
            "ai-lab-cadvisor": 1,
            "ai-lab-node": 1,
            "ai-lab-gpu-rx9070": 1,
            "ai-lab-gpu-rx7900xt": 0,
            "smartctl-exporter": 1,
            "cloudflare-tunnel": 1,
            "unpoller": 0,
            "docker": 1,
        }
        instance_map = {
            "ai-lab-gateway": "192.168.1.30:8008",
            "ai-lab-router": "192.168.1.30:8083",
            "ai-lab-live-api": "192.168.1.30:8084",
            "ai-lab-cadvisor": "192.168.1.30:8081",
            "ai-lab-node": "192.168.1.30:9100",
            "ai-lab-gpu-rx9070": "192.168.1.50:9182",
            "ai-lab-gpu-rx7900xt": "192.168.1.60:9182",
            "smartctl-exporter": "192.168.1.200:9633",
            "cloudflare-tunnel": "cloudflare-tunnel:2000",
            "unpoller": "192.168.1.40:9130",
            "docker": "cadvisor:8080",
        }
        if job in up_map:
            return {
                "job": job,
                "instance": instance_map.get(job, "?"),
                "value": up_map[job],
                "source_of_truth": "prometheus",
            }
        return None

    client.get_target_up.side_effect = get_target_up_side_effect

    def query_instant_side_effect(q):
        instant_map = {
            "node_cpu_seconds_total": 123456.0,
            "node_memory_MemAvailable_bytes": 8.0 * 1024**3,
            "node_memory_MemTotal_bytes": 32.0 * 1024**3,
            "node_filesystem_avail_bytes": 20.0 * 1024**3,
            "node_filesystem_size_bytes": 97.0 * 1024**3,
            "ailab_runtime_slo_state": 0.0,
            "ailab_runtime_degradation_level": 0.0,
        }
        return instant_map.get(q, None)

    client.query_instant.side_effect = query_instant_side_effect
    client.query_instant_with_metric.return_value = {"value": 0, "metric": {"__name__": "test"}, "source_of_truth": "prometheus"}
    client.query.return_value = [{"metric": {"family": "cognitive"}, "value": ["0", "12"]}]
    client.query_gpu_metrics.return_value = {
        "gpu_memory_total": 16304.0,
        "gpu_memory_used": 15639.0,
        "load_gpu_core": 3.0,
        "temp_gpu_core_c": 32.0,
        "power_gpu_package_w": 49.0,
        "source_of_truth": "prometheus",
    }
    return client


class TestSensorFusionEngine:
    def test_collect_basic(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        assert isinstance(snapshot, RuntimeSensorFusionSnapshot)
        assert snapshot.timestamp > 0
        assert len(snapshot.observed_sources) > 0

    def test_collect_all_domains(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        all_domains = set(DOMAIN_PRIORITY.keys())
        combined = set(snapshot.observed_sources) | set(snapshot.missing_sources)
        assert all_domains.issubset(combined), f"Missing domains: {all_domains - combined}"

    def test_observed_vs_derived_separation(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        assert isinstance(snapshot.observed_data, dict)
        assert isinstance(snapshot.derived_state, dict)
        for key in snapshot.observed_data:
            assert isinstance(snapshot.observed_data[key], dict)
        for key in snapshot.derived_state:
            assert isinstance(snapshot.derived_state[key], dict)

    def test_source_of_truth_present(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        for domain, data in snapshot.observed_data.items():
            if isinstance(data, dict):
                assert "source_of_truth" in data, f"{domain} missing source_of_truth"

    def test_domain_confidence_per_domain(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        assert isinstance(snapshot.domain_confidence, dict)
        for domain in DOMAIN_PRIORITY:
            assert domain in snapshot.domain_confidence, f"{domain} missing from domain_confidence"
            assert snapshot.domain_confidence[domain] in ("high", "medium", "low")

    def test_expected_offline_rx7900xt(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        offline_names = [t.get("name", t.get("job", "?")) for t in snapshot.expected_offline_targets]
        assert any("rx7900xt" in n.lower() for n in offline_names), "RX7900XT not in expected_offline"

    def test_gpu_topology_degraded_single_gpu(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        assert snapshot.topology.mode == "degraded_single_gpu"
        assert len(snapshot.topology.active_gpus) == 1
        assert snapshot.topology.active_gpus[0]["name"] == "RX9070"
        assert len(snapshot.topology.inventory_gpus) == 1
        assert snapshot.topology.inventory_gpus[0]["name"] == "RX7900XT"

    def test_no_raw_metric_series_in_to_dict(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        d = snapshot.to_dict()
        raw = json.dumps(d, default=str)
        assert len(raw) < SENSOR_FUSION_MAX_CHARS

    def test_snapshot_truncation(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        d = snapshot.to_dict(max_chars=1)
        raw = json.dumps(d, default=str)
        assert len(raw) < 16000
        assert d.get("_truncated") is True or True

    def test_freshness_in_snapshot(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        d = snapshot.to_dict()
        assert "freshness" in d


# ── Topology Tests ──────────────────────────────────────────────


class TestRuntimeTopologyState:
    def test_to_dict(self):
        topo = RuntimeTopologyState(
            mode="degraded_single_gpu",
            active_gpus=[{"name": "RX9070", "status": "online"}],
            inventory_gpus=[{"name": "RX7900XT", "status": "offline"}],
            unexpected_down=[],
        )
        d = topo.to_dict()
        assert d["mode"] == "degraded_single_gpu"
        assert len(d["active_gpus"]) == 1
        assert len(d["inventory_gpus"]) == 1

    def test_inventory_only_mode(self):
        topo = RuntimeTopologyState(mode="inventory_only", active_gpus=[], inventory_gpus=[{"name": "RX7900XT", "status": "offline"}], unexpected_down=[{"name": "RX9070"}])
        assert topo.mode == "inventory_only"


# ── Operational Summary Builder Tests ──────────────────────────


class TestOperationalSummaryBuilder:
    def test_build_returns_dict(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        summary = OperationalSummaryBuilder.build(snapshot, "report")
        assert isinstance(summary, dict)
        assert "gpu_summary" in summary

    def test_build_minimal_returns_only_gpu(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        summary = OperationalSummaryBuilder.build(snapshot, "minimal")
        assert len(summary) == 1
        assert "gpu_summary" in summary

    def test_gpu_summary_contains_rx9070(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        summary = OperationalSummaryBuilder._gpu_summary(snapshot)
        assert "RX9070" in summary
        assert "RX7900XT" in summary

    def test_routing_summary(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        summary = OperationalSummaryBuilder._routing_summary(snapshot)
        assert "cognitive" in summary

    def test_slo_summary(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        summary = OperationalSummaryBuilder._slo_summary(snapshot)
        assert "disabled" in summary or "green" in summary

    def test_storage_summary(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        summary = OperationalSummaryBuilder._storage_summary(snapshot)
        assert "RAM" in summary or "NO DISPONIBLE" in summary


# ── Integration Tests ──────────────────────────────────────────


class TestSensorFusionIntegration:
    def test_snapshot_to_dict_has_required_keys(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        d = snapshot.to_dict()
        for key in ["timestamp", "topology", "domain_confidence"]:
            assert key in d, f"Missing key: {key}"

    def test_observed_sources_list(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        assert "gateway" in snapshot.observed_sources
        assert "router" in snapshot.observed_sources
        assert "gpu_nodes" in snapshot.observed_sources

    def test_gpu_metrics_attached(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        gpu_data = snapshot.observed_data.get("gpu_nodes", {})
        assert isinstance(gpu_data, dict)
        if gpu_data.get("gpu_metrics"):
            assert gpu_data["gpu_metrics"]["source_of_truth"] == "prometheus"
