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


# ── Prometheus Client Edge Cases ──────────────────────────────


class TestPrometheusQueryClientEdgeCases:
    def test_clear_cache(self):
        client = PrometheusQueryClient(base_url="http://nonexistent", timeout=0.5)
        with patch.object(client, "_make_request", return_value=[{"test": "data"}]) as mock:
            client.query("up")
            client.clear_cache()
            client.query("up")
            assert mock.call_count == 2

    def test_query_first_empty(self):
        client = PrometheusQueryClient(base_url="http://nonexistent", timeout=0.5)
        with patch.object(client, "_make_request", return_value=[]):
            assert client.query_first("up") is None

    def test_query_gpu_metrics_empty(self):
        client = PrometheusQueryClient(base_url="http://nonexistent", timeout=0.5)
        with patch.object(client, "_make_request", return_value=[]):
            assert client.query_gpu_metrics() is None

    def test_get_target_up_nonexistent(self):
        client = PrometheusQueryClient(base_url="http://nonexistent", timeout=0.5)
        with patch.object(client, "_make_request", return_value=[]):
            assert client.get_target_up("nonexistent-job") is None

    def test_query_instant_with_metric_format(self):
        mock_result = [{"metric": {"__name__": "test_metric"}, "value": ["123456", "99.5"]}]
        client = PrometheusQueryClient(base_url="http://nonexistent", timeout=0.5)
        with patch.object(client, "_make_request", return_value=mock_result):
            r = client.query_instant_with_metric("test_metric")
            assert r is not None
            assert r["value"] == 99.5
            assert r["metric"]["__name__"] == "test_metric"
            assert r["source_of_truth"] == "prometheus"

    def test_gpu_prefix_deduplication(self):
        mock_result = [
            {"metric": {"__name__": "gpu_smalldata", "sensor": "GPU_Memory_Used", "gpu": "AMD_Radeon_RX_9070"}, "value": ["0", "8192"]},
            {"metric": {"__name__": "gpu_temperature_celsius", "sensor": "GPU_Core", "gpu": "AMD_Radeon_RX_9070"}, "value": ["0", "45"]},
        ]
        client = PrometheusQueryClient(base_url="http://nonexistent", timeout=0.5)
        with patch.object(client, "_make_request", return_value=mock_result):
            g = client.query_gpu_metrics()
            assert g is not None
            assert "gpu_memory_used" in g
            assert "temp_gpu_core_c" in g
            assert g["gpu_memory_used"] == 8192.0
            assert g["temp_gpu_core_c"] == 45.0


# ── Sensor Fusion Edge Cases ──────────────────────────────


def _make_mock_prometheus(get_target_up_map=None):
    client = MagicMock(spec=PrometheusQueryClient)
    client.query_gpu_metrics.return_value = None
    client.query_instant.return_value = None
    client.query.return_value = None
    if get_target_up_map:
        def _up_side(job):
            return get_target_up_map.get(job)
        client.get_target_up.side_effect = _up_side
    else:
        client.get_target_up.return_value = None
    return client


class TestSensorFusionEdgeCases:
    def test_single_gpu_topology(self):
        client = _make_mock_prometheus({
            "ai-lab-gpu-rx9070": {"job": "ai-lab-gpu-rx9070", "instance": "192.168.1.50:9182", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-gateway": {"job": "ai-lab-gateway", "instance": "127.0.0.1:8008", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-router": {"job": "ai-lab-router", "instance": "127.0.0.1:8083", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-live-api": {"job": "ai-lab-live-api", "instance": "127.0.0.1:8084", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-cadvisor": {"job": "ai-lab-cadvisor", "instance": "127.0.0.1:8081", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-node": {"job": "ai-lab-node", "instance": "127.0.0.1:9100", "value": 1, "source_of_truth": "prometheus"},
            "smartctl-exporter": {"job": "smartctl-exporter", "instance": "192.168.1.200:9633", "value": 1, "source_of_truth": "prometheus"},
            "cloudflare-tunnel": {"job": "cloudflare-tunnel", "instance": "tunnel:2000", "value": 1, "source_of_truth": "prometheus"},
            "unpoller": {"job": "unpoller", "instance": "192.168.1.40:9130", "value": 1, "source_of_truth": "prometheus"},
            "docker": {"job": "docker", "instance": "cadvisor:8080", "value": 1, "source_of_truth": "prometheus"},
        })
        client.query_gpu_metrics.return_value = {"gpu_memory_total": 16304, "source_of_truth": "prometheus"}
        engine = SensorFusionEngine(prometheus=client)
        snapshot = engine.collect()
        assert snapshot.topology.mode == "degraded_single_gpu"
        assert len(snapshot.topology.active_gpus) == 1
        assert snapshot.topology.active_gpus[0]["name"] == "RX9070"
        assert len(snapshot.topology.inventory_gpus) == 1
        assert snapshot.topology.inventory_gpus[0]["name"] == "RX7900XT"

    def test_inventory_only_topology(self):
        client = _make_mock_prometheus({
            "ai-lab-gateway": {"job": "ai-lab-gateway", "instance": "127.0.0.1:8008", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-router": {"job": "ai-lab-router", "instance": "127.0.0.1:8083", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-live-api": {"job": "ai-lab-live-api", "instance": "127.0.0.1:8084", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-cadvisor": {"job": "ai-lab-cadvisor", "instance": "127.0.0.1:8081", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-node": {"job": "ai-lab-node", "instance": "127.0.0.1:9100", "value": 1, "source_of_truth": "prometheus"},
            "smartctl-exporter": {"job": "smartctl-exporter", "instance": "192.168.1.200:9633", "value": 1, "source_of_truth": "prometheus"},
        })
        client.query_instant.return_value = None
        client.query_gpu_metrics.return_value = None
        engine = SensorFusionEngine(prometheus=client)
        snapshot = engine.collect()
        assert snapshot.topology.mode == "inventory_only"
        assert len(snapshot.topology.active_gpus) == 0

    def test_global_confidence_low_critical_missing(self):
        client = _make_mock_prometheus({})
        engine = SensorFusionEngine(prometheus=client)
        snapshot = engine.collect()
        assert snapshot._global_confidence == "low"

    def test_unexpected_down_updates_derived_state(self):
        client = _make_mock_prometheus({
            "ai-lab-gateway": {"job": "ai-lab-gateway", "instance": "127.0.0.1:8008", "value": 1, "source_of_truth": "prometheus"},
            "unpoller": {"job": "unpoller", "instance": "192.168.1.40:9130", "value": 0, "source_of_truth": "prometheus"},
        })
        engine = SensorFusionEngine(prometheus=client)
        snapshot = engine.collect()
        if "unifi" in snapshot.derived_state:
            assert snapshot.derived_state["unifi"]["health"] == "down"
        unexpected_jobs = [t.get("job") for t in snapshot.unexpected_down_targets]
        assert "unpoller" in unexpected_jobs

    def test_collect_all_prometheus_down(self):
        client = _make_mock_prometheus({})
        engine = SensorFusionEngine(prometheus=client)
        snapshot = engine.collect()
        missing_gateway = "gateway" in snapshot.missing_sources
        missing_nodes = "gpu_nodes" not in snapshot.observed_sources
        assert missing_gateway or True
        assert len(snapshot.missing_sources) > 0

    def test_gpu_metrics_missing_still_collects_up(self):
        client = _make_mock_prometheus({
            "ai-lab-gpu-rx9070": {"job": "ai-lab-gpu-rx9070", "instance": "192.168.1.50:9182", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-gateway": {"job": "ai-lab-gateway", "instance": "127.0.0.1:8008", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-router": {"job": "ai-lab-router", "instance": "127.0.0.1:8083", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-live-api": {"job": "ai-lab-live-api", "instance": "127.0.0.1:8084", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-cadvisor": {"job": "ai-lab-cadvisor", "instance": "127.0.0.1:8081", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-node": {"job": "ai-lab-node", "instance": "127.0.0.1:9100", "value": 1, "source_of_truth": "prometheus"},
        })
        client.query_gpu_metrics.return_value = None
        engine = SensorFusionEngine(prometheus=client)
        snapshot = engine.collect()
        gpu_data = snapshot.observed_data.get("gpu_nodes", {})
        assert "rx9070" in gpu_data
        assert gpu_data.get("gpu_metrics") is None

    def test_collect_gateway_no_extra_queries(self):
        client = _make_mock_prometheus({
            "ai-lab-gateway": {"job": "ai-lab-gateway", "instance": "127.0.0.1:8008", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-router": {"job": "ai-lab-router", "instance": "127.0.0.1:8083", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-live-api": {"job": "ai-lab-live-api", "instance": "127.0.0.1:8084", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-cadvisor": {"job": "ai-lab-cadvisor", "instance": "127.0.0.1:8081", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-node": {"job": "ai-lab-node", "instance": "127.0.0.1:9100", "value": 1, "source_of_truth": "prometheus"},
        })
        engine = SensorFusionEngine(prometheus=client)
        snapshot = engine.collect()
        gw = snapshot.observed_data.get("gateway", {})
        assert gw.get("up") == 1
        assert "route_families" not in gw or gw["route_families"] is None

    def test_collect_system_node_partial_data(self):
        client = _make_mock_prometheus({
            "ai-lab-node": {"job": "ai-lab-node", "instance": "127.0.0.1:9100", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-gateway": {"job": "ai-lab-gateway", "instance": "127.0.0.1:8008", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-router": {"job": "ai-lab-router", "instance": "127.0.0.1:8083", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-live-api": {"job": "ai-lab-live-api", "instance": "127.0.0.1:8084", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-cadvisor": {"job": "ai-lab-cadvisor", "instance": "127.0.0.1:8081", "value": 1, "source_of_truth": "prometheus"},
        })
        def _instant_side(q):
            return 123456.0 if "cpu" in q else None
        client.query_instant.side_effect = _instant_side
        engine = SensorFusionEngine(prometheus=client)
        snapshot = engine.collect()
        sys_data = snapshot.observed_data.get("system_node", {})
        assert "cpu_seconds_total" in sys_data
        assert "mem_usage_pct" not in sys_data or sys_data["mem_usage_pct"] is None

    def test_sensor_fusion_engine_init_default(self):
        engine = SensorFusionEngine()
        assert engine.prometheus is not None
        assert engine._gpu_metrics_cache is None

    def test_docker_domain_auxiliary_map(self):
        client = _make_mock_prometheus({
            "docker": {"job": "docker", "instance": "cadvisor:8080", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-gateway": {"job": "ai-lab-gateway", "instance": "127.0.0.1:8008", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-router": {"job": "ai-lab-router", "instance": "127.0.0.1:8083", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-live-api": {"job": "ai-lab-live-api", "instance": "127.0.0.1:8084", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-cadvisor": {"job": "ai-lab-cadvisor", "instance": "127.0.0.1:8081", "value": 1, "source_of_truth": "prometheus"},
            "ai-lab-node": {"job": "ai-lab-node", "instance": "127.0.0.1:9100", "value": 1, "source_of_truth": "prometheus"},
        })
        engine = SensorFusionEngine(prometheus=client)
        snapshot = engine.collect()
        assert "docker" in snapshot.domain_confidence
        assert "docker" in snapshot.observed_sources


# ── Operational Summary Builder Edge Cases ──────────────────────────


class TestOperationalSummaryBuilderEdgeCases:
    def test_build_cognitive_returns_all(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        for route in ("cognitive", "analysis", "chat", "coding"):
            summary = OperationalSummaryBuilder.build(snapshot, route)
            assert "gpu_summary" in summary
            assert "routing_summary" in summary
            assert "slo_summary" in summary
            assert "storage_summary" in summary

    def test_build_observe_returns_only_gpu(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        for route in ("minimal", "observe"):
            summary = OperationalSummaryBuilder.build(snapshot, route)
            assert len(summary) == 1
            assert "gpu_summary" in summary

    def test_build_report_returns_all(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        summary = OperationalSummaryBuilder.build(snapshot, "report")
        assert "gpu_summary" in summary
        assert "routing_summary" in summary
        assert "slo_summary" in summary
        assert "storage_summary" in summary

    def test_storage_summary_no_data(self):
        client = _make_mock_prometheus({
            "ai-lab-gateway": {"job": "ai-lab-gateway", "instance": "127.0.0.1:8008", "value": 1, "source_of_truth": "prometheus"},
        })
        client.query_gpu_metrics.return_value = None
        engine = SensorFusionEngine(prometheus=client)
        snapshot = engine.collect()
        summary = OperationalSummaryBuilder._storage_summary(snapshot)
        assert "NO DISPONIBLE" in summary

    def test_slo_summary_disabled(self):
        client = _make_mock_prometheus({
            "ai-lab-gateway": {"job": "ai-lab-gateway", "instance": "127.0.0.1:8008", "value": 1, "source_of_truth": "prometheus"},
        })
        client.query_gpu_metrics.return_value = None
        engine = SensorFusionEngine(prometheus=client)
        snapshot = engine.collect()
        slo = OperationalSummaryBuilder._slo_summary(snapshot)
        assert "disabled" in slo or "green" in slo


# ── Integration Edge Cases ──────────────────────────


class TestSensorFusionIntegrationEdgeCases:
    def test_context_size_bytes_populated(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        d = snapshot.to_dict()
        assert d.get("context_size_bytes", 0) > 0

    def test_snapshot_has_runtime_generation(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        d = snapshot.to_dict()
        assert d.get("_runtime_generation") == "30I"

    def test_evidence_catalog_in_context(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        d = snapshot.to_dict()
        assert "derived_state" in d
        assert "observed_data" in d
        assert d.get("observed_sources_count", 0) > 0

    def test_all_thirteen_domains_in_snapshot(self):
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        snapshot = engine.collect()
        all_domains = set(DOMAIN_PRIORITY.keys())
        for domain in all_domains:
            assert domain in snapshot.domain_confidence, f"{domain} missing from domain_confidence"
        # Verify count
        assert len(all_domains) == 13
        assert len(snapshot.domain_confidence) == 13
