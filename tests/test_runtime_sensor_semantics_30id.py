from unittest.mock import MagicMock, patch

from runtime.context.evidence_guard import build_evidence_catalog
from runtime.context.report_runtime_context import build_report_runtime_context
from runtime.context.sensor_fusion import SENSOR_CONTRACT_VERSION, SensorFusionEngine


def fake_prometheus_client():
    client = MagicMock()

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
            "unpoller": 1,
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
                "instance": instance_map[job],
                "value": up_map[job],
                "source_of_truth": "prometheus",
            }
        return None

    client.get_target_up.side_effect = get_target_up_side_effect
    client.query_instant.side_effect = lambda q: {
        "node_cpu_seconds_total": 123456.0,
        "node_memory_MemAvailable_bytes": 8.0 * 1024**3,
        "node_memory_MemTotal_bytes": 32.0 * 1024**3,
        "node_filesystem_avail_bytes": 20.0 * 1024**3,
        "node_filesystem_size_bytes": 97.0 * 1024**3,
        "ailab_runtime_slo_state": 0.0,
        "ailab_runtime_degradation_level": 0.0,
    }.get(q)
    client.query_instant_with_metric.return_value = {"value": 0.0, "metric": {"__name__": "test"}, "source_of_truth": "prometheus"}
    client.query.return_value = [{"metric": {"family": "cognitive"}, "value": ["0", "12"]}]
    client.query_gpu_metrics.return_value = {
        "gpu_memory_total": 16700.0,
        "gpu_memory_used": 15639.0,
        "load_gpu_core": 3.0,
        "temp_gpu_core_c": 36.0,
        "power_gpu_package_w": 48.0,
        "fan_gpu_fan_rpm": 1082.0,
        "source_of_truth": "prometheus",
    }
    return client


def build_contract():
    engine = SensorFusionEngine(prometheus=fake_prometheus_client())
    snapshot = engine.collect()
    return engine, snapshot, engine.build_sensor_contract(snapshot)


def test_gpu_summary_has_source_of_truth():
    _, _, contract = build_contract()
    assert contract["gpu_operational_summaries"][0]["source_of_truth"]


def test_gpu_summary_has_freshness():
    _, _, contract = build_contract()
    freshness = contract["gpu_operational_summaries"][0]["freshness"]
    assert freshness["status"] in ("fresh", "stale", "expired", "unavailable")


def test_gpu_summary_has_confidence():
    _, _, contract = build_contract()
    assert contract["gpu_operational_summaries"][0]["confidence"] in ("high", "medium", "low")


def test_rx9070_observed_state_online():
    _, _, contract = build_contract()
    assert contract["gpu_operational_summaries"][0]["observed_state"] == "online"


def test_rx7900xt_expected_offline_not_critical():
    _, _, contract = build_contract()
    rx7900 = next(item for item in contract["gpu_operational_summaries"] if item["gpu_id"] == "RX7900XT")
    assert rx7900["observed_state"] == "expected_offline"
    assert rx7900["confidence"] != "high"
    assert contract["domain_confidence"]["gpu_nodes"] == "high"


def test_inventory_state_not_equal_observed_state():
    _, _, contract = build_contract()
    rx7900 = next(item for item in contract["gpu_operational_summaries"] if item["gpu_id"] == "RX7900XT")
    assert rx7900["inventory_state"] == "known"
    assert rx7900["observed_state"] != rx7900["inventory_state"]


def test_observed_metrics_separated_from_derived_state():
    _, _, contract = build_contract()
    rx9070 = contract["gpu_operational_summaries"][0]
    assert "temperature_c" in rx9070["observed_metrics"]
    assert "temperature_c" not in rx9070["derived_state"]


def test_gpu_summary_no_raw_metric_flood():
    _, _, contract = build_contract()
    payload = str(contract["gpu_operational_summaries"][0])
    assert "temp_gpu_core_c" not in payload
    assert "load_gpu_core" not in payload


def test_runtime_sensors_contract_version_30id():
    _, _, contract = build_contract()
    assert contract["sensor_contract_version"] == SENSOR_CONTRACT_VERSION


@patch("runtime.context.sensor_fusion.requests.get")
def test_observed_runtime_contains_gpu_operational_summaries(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "data": [
            {"id": "llama-3.1-8b-instruct"},
            {"id": "qwen2.5-coder-14b-instruct"},
        ]
    }
    with patch("runtime.context.sensor_fusion.SensorFusionEngine") as mock_engine_cls:
        engine, snapshot, contract = build_contract()
        mock_engine = MagicMock()
        mock_engine.collect.return_value = snapshot
        mock_engine.build_sensor_contract.return_value = contract
        mock_engine_cls.return_value = mock_engine
        ctx = build_report_runtime_context()
    assert ctx["sensor_contract_version"] == SENSOR_CONTRACT_VERSION
    assert isinstance(ctx["gpu_operational_summaries"], list)
    assert ctx["sensor_snapshot"]["sensor_contract_version"] == SENSOR_CONTRACT_VERSION


def test_freshness_stale_does_not_invent_values():
    engine = SensorFusionEngine(prometheus=fake_prometheus_client())
    snapshot = engine.collect()
    snapshot.last_scrape_seconds_ago["gpu_nodes"] = 120.0
    contract = engine.build_sensor_contract(snapshot)
    rx9070 = contract["gpu_operational_summaries"][0]
    assert rx9070["freshness"]["status"] == "expired"
    assert rx9070["observed_metrics"]["temperature_c"] == 36.0


def test_confidence_per_domain():
    _, snapshot, contract = build_contract()
    assert contract["domain_confidence"]["gpu_nodes"] == snapshot.domain_confidence["gpu_nodes"]
    assert "gpu_nodes" in contract["source_quality"]


def test_evidence_catalog_uses_sensor_summaries():
    _, _, contract = build_contract()
    ctx = {
        "gpu_operational_summaries": contract["gpu_operational_summaries"],
        "inference_nodes": {"active": [], "inventory": []},
        "models": {"active": [], "disabled": [], "discovered": []},
        "services": {},
    }
    catalog = build_evidence_catalog(ctx)
    assert "rx9070" in catalog["nodes"]
    assert "192.168.1.50" in catalog["hosts"]


def test_gpu_summary_alias_backward_compatible():
    _, _, contract = build_contract()
    assert contract["gpu_summary"]["deprecated_alias"] is True
    assert contract["gpu_summary"]["alias_for"] == "gpu_operational_summaries"
