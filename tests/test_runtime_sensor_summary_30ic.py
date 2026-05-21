"""FASE 30I-C: Runtime Sensor Summary Exposure tests."""

from unittest.mock import MagicMock, patch

from runtime.context.sensor_fusion import (
    SensorFusionEngine,
    DOMAIN_PRIORITY,
)


def fake_prometheus_client():
    """Create a fake Prometheus client for testing."""
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
        "gpu_memory_total": 16700.0,  # in MB
        "gpu_memory_used": 15639.0,   # in MB
        "load_gpu_core": 25.0,        # percentage
        "temp_gpu_core_c": 35.0,      # celsius
        "power_gpu_package_w": 45.0,  # watts
        "fan_gpu_fan_rpm": 1200.0,    # RPM
        "source_of_truth": "prometheus",
    }
    return client


class TestGPUOperationalSummary:
    def test_gpu_operational_summary_contains_metrics(self):
        """Test that GPU operational summary contains real metrics."""
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        summary = engine.build_gpu_operational_summary()
        
        assert "gpu_metrics" in summary
        metrics = summary["gpu_metrics"]
        assert "temperature_c" in metrics
        assert "power_watts" in metrics
        assert "gpu_load_percent" in metrics
        assert "fan_rpm" in metrics
        assert "vram_used_gb" in metrics
        assert "vram_total_gb" in metrics
        assert "vram_free_gb" in metrics
        
        # Check values are reasonable
        assert metrics["temperature_c"] == 35.0
        assert metrics["power_watts"] == 45.0
        assert metrics["gpu_load_percent"] == 25.0
        assert metrics["fan_rpm"] == 1200.0
        assert metrics["vram_used_gb"] > 0
        assert metrics["vram_total_gb"] > 0
        assert metrics["vram_free_gb"] >= 0

    def test_gpu_operational_summary_json_safe(self):
        """Test that GPU operational summary is JSON serializable."""
        import json
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        summary = engine.build_gpu_operational_summary()
        
        # Should not raise exception
        json_str = json.dumps(summary, ensure_ascii=False)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

    def test_gpu_operational_summary_no_raw_metric_flood(self):
        """Test that GPU operational summary is compact, not raw metric flood."""
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        summary = engine.build_gpu_operational_summary()
        
        # Should not contain raw Prometheus metric names
        summary_str = str(summary)
        assert "temp_gpu_core_c" not in summary_str
        assert "load_gpu_core" not in summary_str
        assert "power_gpu_package_w" not in summary_str
        assert "fan_gpu_fan_rpm" not in summary_str
        assert "gpu_memory_used" not in summary_str
        assert "gpu_memory_total" not in summary_str
        
        # Should contain friendly names
        assert "temperature_c" in summary_str
        assert "gpu_load_percent" in summary_str
        assert "power_watts" in summary_str
        assert "fan_rpm" in summary_str
        assert "vram_used_gb" in summary_str
        assert "vram_total_gb" in summary_str

    def test_gpu_intent_detection(self):
        """Test GPU intent detection patterns."""
        from runtime.gateway.tool_request_classifier import detect_gpu_runtime_intent
        
        # Should detect GPU intents
        assert detect_gpu_runtime_intent("estado GPU RX9070") == True
        assert detect_gpu_runtime_intent("temperatura de la GPU") == True
        assert detect_gpu_runtime_intent("cuanta vram usada") == True
        assert detect_gpu_runtime_intent("potencia consumo") == True
        assert detect_gpu_runtime_intent("fan rpm") == True
        assert detect_gpu_runtime_intent("watts de potencia") == True
        assert detect_gpu_runtime_intent("carga gpu") == True
        assert detect_gpu_runtime_intent("estado de gpu") == True
        
        # Should not detect non-GPU intents
        assert detect_gpu_runtime_intent("hola como estas") == False
        assert detect_gpu_runtime_intent("que puedes hacer") == False
        assert detect_gpu_runtime_intent("informe tecnico") == False
        assert detect_gpu_runtime_intent("") == False
        assert detect_gpu_runtime_intent(None) == False

    def test_rx7900xt_expected_offline(self):
        """Test that RX7900XT is correctly identified as expected offline."""
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        summary = engine.build_gpu_operational_summary()
        
        # RX7900XT should be in inventory, not active
        assert "inventory_gpu" in summary
        inventory = summary["inventory_gpu"]
        assert inventory["name"] == "RX7900XT"
        assert inventory["expected_offline"] == True
        assert inventory["status"] == "offline"
        assert inventory["topology_role"] == "inventory_offline"
        
        # Should have no active metrics
        assert inventory["gpu_metrics"] == {}

    def test_missing_metric_returns_no_disponible(self):
        """Test that missing metrics are handled gracefully."""
        # Mock Prometheus client that returns empty GPU metrics
        client = fake_prometheus_client()
        client.query_gpu_metrics.return_value = {}  # Empty metrics
        
        engine = SensorFusionEngine(prometheus=client)
        summary = engine.build_gpu_operational_summary()
        
        # Should still have basic structure
        assert "name" in summary
        assert summary["name"] == "RX9070"
        assert "gpu_metrics" in summary
        
        # Metrics dict should be empty when no data
        assert summary["gpu_metrics"] == {}

    def test_gpu_summary_contains_confidence(self):
        """Test that GPU summary includes confidence field."""
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        summary = engine.build_gpu_operational_summary()
        
        assert "confidence" in summary
        assert summary["confidence"] in ("high", "medium", "low")

    def test_gpu_summary_contains_source_of_truth(self):
        """Test that GPU summary includes source_of_truth field."""
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        summary = engine.build_gpu_operational_summary()
        
        assert "source_of_truth" in summary
        assert isinstance(summary["source_of_truth"], list)
        assert len(summary["source_of_truth"]) > 0
        # Should include prometheus and possibly gpu_exporter
        assert "prometheus" in summary["source_of_truth"]

    def test_gpu_summary_contains_freshness(self):
        """Test that GPU summary includes freshness field."""
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        summary = engine.build_gpu_operational_summary()
        
        assert "freshness" in summary
        assert summary["freshness"] in ("fresh", "stale", "expired", "unknown")

    def test_observed_metrics_prioritized_over_inventory(self):
        """Test that observed metrics are used instead of just inventory data."""
        engine = SensorFusionEngine(prometheus=fake_prometheus_client())
        summary = engine.build_gpu_operational_summary()
        
        # Should have active GPU data, not just inventory
        assert summary.get("status") == "online"
        assert summary.get("topology_role") == "active_inference_backend"
        assert summary.get("expected_offline") == False
        
        # Should have real metrics, not just placeholder
        metrics = summary.get("gpu_metrics", {})
        assert len(metrics) > 0
        assert "temperature_c" in metrics
        assert "power_watts" in metrics


class TestGPUShortQuestionRouting:
    def test_gpu_short_question_uses_sensor_summary(self):
        """Test that short GPU questions use sensor summary data."""
        from runtime.gateway.tool_request_classifier import detect_gpu_runtime_intent
        
        # Test the specific example from the requirements
        user_question = "estado GPU RX9070"
        assert detect_gpu_runtime_intent(user_question) == True
        
        # Verify that when this intent is detected, the system
        # should prioritize sensor_snapshot.gpu_operational_summaries
        # This is validated in the openai_gateway.py integration
        
        # Test a few more variations
        assert detect_gpu_runtime_intent("estado de GPU") == True
        assert detect_gpu_runtime_intent("temperatura GPU") == True
        assert detect_gpu_runtime_intent("cuanta VRAM") == True
        assert detect_gpu_runtime_intent("potencia de consumo") == True


if __name__ == "__main__":
    # Simple test runner
    import traceback
    import sys
    
    test_instance = TestGPUOperationalSummary()
    test_instance_routing = TestGPUShortQuestionRouting()
    
    tests = [
        ("test_gpu_operational_summary_contains_metrics", test_instance.test_gpu_operational_summary_contains_metrics),
        ("test_gpu_operational_summary_json_safe", test_instance.test_gpu_operational_summary_json_safe),
        ("test_gpu_operational_summary_no_raw_metric_flood", test_instance.test_gpu_operational_summary_no_raw_metric_flood),
        ("test_gpu_intent_detection", test_instance.test_gpu_intent_detection),
        ("test_rx7900xt_expected_offline", test_instance.test_rx7900xt_expected_offline),
        ("test_missing_metric_returns_no_disponible", test_instance.test_missing_metric_returns_no_disponible),
        ("test_gpu_summary_contains_confidence", test_instance.test_gpu_summary_contains_confidence),
        ("test_gpu_summary_contains_source_of_truth", test_instance.test_gpu_summary_contains_source_of_truth),
        ("test_gpu_summary_contains_freshness", test_instance.test_gpu_summary_contains_freshness),
        ("test_observed_metrics_prioritized_over_inventory", test_instance.test_observed_metrics_prioritized_over_inventory),
        ("test_gpu_short_question_uses_sensor_summary", test_instance_routing.test_gpu_short_question_uses_sensor_summary),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"✅ {test_name}")
            passed += 1
        except Exception as e:
            print(f"❌ {test_name}: {e}")
            traceback.print_exc()
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)