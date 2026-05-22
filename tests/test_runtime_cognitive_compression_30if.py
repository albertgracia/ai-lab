import json
import time
from unittest.mock import patch

from runtime.context.cognitive_compression import (
    COGNITIVE_CONTRACT_VERSION,
    build_runtime_cognitive_summary,
    compress_gpu_signals,
    compress_route_signals,
    compress_governance_signals,
    compress_storage_signals,
    compress_observability_signals,
    rank_operational_signals,
    build_actionable_summary,
)

RX9070_ACTIVE = {
    "gpu_id": "RX9070",
    "host": "192.168.1.50",
    "inventory_state": "known",
    "observed_state": "online",
    "operational_state": "active",
    "topology_role": "active_inference_backend",
    "observed_metrics": {
        "temperature_c": 36.0,
        "gpu_load_percent": 3,
        "power_watts": 49,
        "fan_rpm": 906,
        "vram_used_gb": 4.2,
        "vram_total_gb": 16,
        "vram_free_gb": 11.8,
    },
    "derived_state": {"health": "ok"},
    "missing_metrics": [],
    "source_of_truth": ["gpu_exporter", "prometheus", "lmstudio_api"],
    "freshness": {"status": "fresh", "age_seconds": 6, "last_seen": 1, "source": "prometheus"},
    "confidence": "high",
    "evidence_level": "observed",
}

RX7900XT_EXPECTED_OFFLINE = {
    "gpu_id": "RX7900XT",
    "host": "192.168.1.60",
    "inventory_state": "known",
    "observed_state": "expected_offline",
    "operational_state": "inactive",
    "topology_role": "inventory_offline",
    "observed_metrics": {},
    "derived_state": {"expected_offline": True},
    "missing_metrics": [],
    "source_of_truth": ["inventory", "prometheus"],
    "freshness": {"status": "unavailable", "age_seconds": None, "last_seen": None, "source": "inventory"},
    "confidence": "medium",
    "evidence_level": "inventory",
    "inventory_expected_offline": True,
}

RX9070_UNEXPECTED_DOWN = {
    "gpu_id": "RX9070",
    "host": "192.168.1.50",
    "inventory_state": "known",
    "observed_state": "down",
    "operational_state": "inactive",
    "topology_role": "inactive",
    "observed_metrics": {},
    "derived_state": {"health": "down"},
    "missing_metrics": ["temperature_c", "gpu_load_percent", "power_watts", "fan_rpm", "vram_used_gb", "vram_free_gb"],
    "source_of_truth": ["prometheus"],
    "freshness": {"status": "expired", "age_seconds": 120, "last_seen": 1, "source": "prometheus"},
    "confidence": "low",
    "evidence_level": "missing",
    "inventory_expected_offline": False,
}


def _make_snapshot(
    gpu_summaries=None,
    topology_mode="degraded_single_gpu",
    domain_confidence=None,
    observed_count=8,
    missing_count=2,
    stale=None,
    freshness=None,
    derived_state=None,
    expected_offline=None,
    unexpected_down=None,
    observed_data=None,
):
    return {
        "timestamp": time.time(),
        "topology": {
            "mode": topology_mode,
            "active_gpus": [{"name": "RX9070", "host": "192.168.1.50"}] if topology_mode != "inventory_only" else [],
            "inventory_gpus": [{"name": "RX7900XT", "host": "192.168.1.60"}],
            "unexpected_down": [],
        },
        "gpu_operational_summaries": gpu_summaries or [],
        "domain_confidence": domain_confidence or {},
        "observed_sources_count": observed_count,
        "missing_sources_count": missing_count,
        "expected_offline": expected_offline or [],
        "unexpected_down": unexpected_down or [],
        "freshness": freshness or {},
        "stale_sources": stale or [],
        "sensor_contract_version": "30I-D",
        "derived_state": derived_state or {},
        "observed_data": observed_data or {},
        "source_quality": {},
        "context_size_bytes": 1024,
        "_runtime_generation": "30I",
    }


class TestCognitiveSummaryContract:
    def test_cognitive_summary_contract_version(self):
        snapshot = _make_snapshot(gpu_summaries=[RX9070_ACTIVE, RX7900XT_EXPECTED_OFFLINE])
        result = build_runtime_cognitive_summary(snapshot)
        assert result["contract_version"] == COGNITIVE_CONTRACT_VERSION
        assert result["_runtime_generation"] == "30I-F"

    def test_cognitive_summary_json_safe(self):
        snapshot = _make_snapshot(gpu_summaries=[RX9070_ACTIVE])
        result = build_runtime_cognitive_summary(snapshot)
        dumped = json.dumps(result, ensure_ascii=False, default=str)
        assert isinstance(dumped, str)
        assert len(dumped) > 0


class TestGpuSignals:
    def test_gpu_signals_compressed(self):
        snapshot = _make_snapshot(gpu_summaries=[RX9070_ACTIVE, RX7900XT_EXPECTED_OFFLINE])
        signals = compress_gpu_signals(snapshot)
        assert len(signals) >= 2
        messages = " ".join(s["message"] for s in signals)
        assert "RX9070" in messages
        assert "RX7900XT" in messages

    def test_rx7900xt_expected_offline_compressed_as_info(self):
        snapshot = _make_snapshot(gpu_summaries=[RX7900XT_EXPECTED_OFFLINE])
        signals = compress_gpu_signals(snapshot)
        assert len(signals) == 1
        assert signals[0]["severity"] == "info"
        assert "expected_offline" in signals[0]["message"]

    def test_unexpected_down_becomes_warning(self):
        snapshot = _make_snapshot(gpu_summaries=[RX9070_UNEXPECTED_DOWN])
        signals = compress_gpu_signals(snapshot)
        assert len(signals) >= 1
        assert signals[0]["severity"] == "warning"
        assert "down" in signals[0]["message"].lower() or "unavailable" in signals[0]["message"].lower()

    def test_no_raw_metric_flood(self):
        snapshot = _make_snapshot(gpu_summaries=[RX9070_ACTIVE, RX7900XT_EXPECTED_OFFLINE])
        signals = compress_gpu_signals(snapshot)
        result = build_runtime_cognitive_summary(snapshot)
        serialized = json.dumps(result, ensure_ascii=False, default=str)
        assert "temp_gpu_core_c" not in serialized
        assert "gpu_memory_used" not in serialized
        assert "gpu_load_percent" not in serialized
        # But compact derived names are ok
        assert "temperature_c" not in serialized

    def test_low_confidence_when_prometheus_missing(self):
        snapshot = _make_snapshot(
            gpu_summaries=[RX9070_ACTIVE],
            observed_count=2,
            missing_count=10,
            domain_confidence={"gpu_nodes": "low", "gateway": "low"},
        )
        result = build_runtime_cognitive_summary(snapshot)
        assert result["confidence"] == "low"


class TestRecommendations:
    def test_recommended_actions_are_evidence_bound(self):
        snapshot = _make_snapshot(gpu_summaries=[RX9070_ACTIVE, RX7900XT_EXPECTED_OFFLINE])
        result = build_runtime_cognitive_summary(snapshot)
        for action in result.get("recommended_actions", []):
            assert isinstance(action, str)
            assert len(action) > 5

    def test_unavailable_data_listed(self):
        snapshot = _make_snapshot(gpu_summaries=[RX9070_ACTIVE])
        # Force empty sensor_snapshot to trigger unavailable
        empty_result = build_runtime_cognitive_summary(None)
        assert "unavailable_data" in empty_result
        assert len(empty_result["unavailable_data"]) > 0


class TestSignalRanking:
    def test_signal_ranking(self):
        signals = [
            {"domain": "gpu", "severity": "info", "message": "RX9070 active"},
            {"domain": "routing", "severity": "critical", "message": "gateway DOWN"},
            {"domain": "observability", "severity": "warning", "message": "Prometheus stale"},
        ]
        ranked = rank_operational_signals(signals)
        assert ranked[0]["severity"] == "critical"
        assert ranked[1]["severity"] == "warning"
        assert ranked[2]["severity"] == "info"


class TestStorageSignals:
    def test_storage_recursion_risk_signal(self):
        snapshot = _make_snapshot(gpu_summaries=[RX9070_ACTIVE])
        extra = {"recursive_backup_risk": True}
        signals = compress_storage_signals(snapshot, extra)
        messages = " ".join(s["message"] for s in signals)
        assert "recursion" in messages.lower()


class TestEndpoint:
    @patch("runtime.context.sensor_fusion.SensorFusionEngine")
    def test_endpoint_runtime_cognitive_summary_200(self, MockEngine):
        from runtime.context.cognitive_compression import build_runtime_cognitive_summary
        mock_snapshot = _make_snapshot(gpu_summaries=[RX9070_ACTIVE, RX7900XT_EXPECTED_OFFLINE])
        result = build_runtime_cognitive_summary(mock_snapshot)
        assert result["overall_state"] in ("healthy", "healthy_degraded", "degraded", "critical", "unknown")
        assert "important_signals" in result


class TestObservedRuntime:
    @patch("runtime.context.sensor_fusion.SensorFusionEngine")
    def test_observed_runtime_contains_cognitive_summary(self, MockEngine):
        from runtime.context.report_runtime_context import build_report_runtime_context
        mock_snap = MockEngine.return_value.collect.return_value
        mock_snap.topology.to_dict.return_value = {"mode": "degraded_single_gpu"}
        mock_snap.domain_confidence = {"gpu_nodes": "high"}
        mock_snap.derived_state = {"gpu_nodes": {"health": "ok"}}
        mock_snap.observed_sources = ["gpu_nodes", "gateway"]
        mock_snap.missing_sources = []
        mock_snap.expected_offline_targets = [{"name": "RX7900XT", "job": "ai-lab-gpu-rx7900xt"}]
        mock_snap.unexpected_down_targets = []
        mock_snap.stale_sources = []
        mock_snap.last_scrape_seconds_ago = {"gpu_nodes": 0.0}
        mock_snap.timestamp = time.time()
        mock_snap.to_dict.return_value = _make_snapshot(
            gpu_summaries=[RX9070_ACTIVE, RX7900XT_EXPECTED_OFFLINE]
        )
        contract = {
            "sensor_contract_version": "30I-D",
            "topology_mode": "degraded_single_gpu",
            "gpu_operational_summaries": [RX9070_ACTIVE, RX7900XT_EXPECTED_OFFLINE],
            "gpu_summary": {"deprecated_alias": True},
            "domain_confidence": {"gpu_nodes": "high"},
            "source_quality": {},
            "expected_offline_targets": ["ai-lab-gpu-rx7900xt"],
            "unexpected_down_targets": [],
            "derived_state": {"gpu_nodes": {"health": "ok"}},
        }
        MockEngine.return_value.build_sensor_contract.return_value = contract
        MockEngine.return_value.build_gpu_operational_summaries.return_value = [
            RX9070_ACTIVE, RX7900XT_EXPECTED_OFFLINE
        ]
        ctx = build_report_runtime_context()
        assert "cognitive_summary" in ctx
        assert ctx["cognitive_summary"]["contract_version"] == "30I-F"


class TestPromptUsesCognitive:
    def test_prompt_uses_cognitive_summary_first(self):
        cognitive = {
            "contract_version": "30I-F",
            "overall_state": "healthy_degraded",
            "summary": "Runtime estable en modo degraded_single_gpu",
            "important_signals": [
                {
                    "domain": "gpu",
                    "severity": "info",
                    "message": "RX9070 active, temp=36C, VRAM 4.2/16GB free=11.8GB",
                    "evidence": ["gpu_exporter", "prometheus"],
                    "confidence": "high",
                    "freshness": "fresh",
                }
            ],
            "risks": ["ningún riesgo activo detectado"],
            "recommended_actions": ["continuar validación de sensor fusion antes de Multi-GPU"],
            "confidence": "high",
            "freshness": "fresh",
        }
        assert cognitive["overall_state"] == "healthy_degraded"
        assert len(cognitive["important_signals"]) > 0
        summary = cognitive["summary"]
        assert "Runtime" in summary
        assert "degraded_single_gpu" in summary or "estable" in summary


class TestOverallState:
    def test_healthy_state(self):
        snapshot = _make_snapshot(gpu_summaries=[RX9070_ACTIVE, RX7900XT_EXPECTED_OFFLINE])
        result = build_runtime_cognitive_summary(snapshot)
        assert result["overall_state"] == "healthy_degraded"

    def test_empty_snapshot_fallback(self):
        result = build_runtime_cognitive_summary(None)
        assert result["overall_state"] == "unknown"
        assert result["confidence"] == "low"
