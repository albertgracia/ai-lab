from runtime.formatters.gpu_operational_formatter import (
    format_gpu_operational_summary,
    format_gpu_inventory_state,
)
from runtime.formatters.runtime_operational_formatter import (
    compact_runtime_response,
    format_runtime_cluster_state,
)
from runtime.gateway.tool_request_classifier import select_operational_response_profile


GPU_ACTIVE = {
    "gpu_id": "RX9070",
    "host": "192.168.1.50",
    "inventory_state": "known",
    "observed_state": "online",
    "operational_state": "active",
    "topology_role": "active_inference_backend",
    "observed_metrics": {
        "temperature_c": 36.0,
        "gpu_load_percent": 0,
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

GPU_INV = {
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
}

CTX = {
    "gpu_operational_summaries": [GPU_ACTIVE, GPU_INV],
    "topology_mode": "degraded_single_gpu",
    "domain_confidence": {"gpu_nodes": "high", "gateway": "high"},
    "source_quality": {
        "gpu_nodes": {
            "source_of_truth": ["gpu_exporter", "prometheus"],
            "freshness": {"status": "fresh"},
            "confidence": "high",
        },
        "gateway": {
            "source_of_truth": ["prometheus"],
            "freshness": {"status": "fresh"},
            "confidence": "high",
        },
    },
}


def test_gpu_response_compact_format():
    text = format_gpu_operational_summary(GPU_ACTIVE)
    assert text.splitlines()[0] == "RX9070"
    assert "status=active" in text


def test_rx9070_contains_freshness():
    text = format_gpu_operational_summary(GPU_ACTIVE)
    assert "freshness=fresh(6s)" in text


def test_rx9070_contains_confidence():
    text = format_gpu_operational_summary(GPU_ACTIVE)
    assert "confidence=high" in text


def test_rx9070_contains_source():
    text = format_gpu_operational_summary(GPU_ACTIVE)
    assert "source=gpu_exporter+prometheus+lmstudio_api" in text


def test_rx7900xt_expected_offline_format():
    text = format_gpu_inventory_state(GPU_INV)
    assert "observed_state=expected_offline" in text
    assert "status=inactive" in text


def test_no_raw_metric_flood():
    text = format_gpu_operational_summary(GPU_ACTIVE)
    assert "temperature_c" not in text
    assert "gpu_load_percent" not in text


def test_runtime_cluster_compact_summary():
    text = format_runtime_cluster_state(CTX)
    assert "AI-LAB Runtime" in text
    assert "topology=degraded_single_gpu" in text


def test_missing_metrics_degrades_cleanly():
    degraded = dict(GPU_ACTIVE)
    degraded["observed_metrics"] = {}
    text = format_gpu_operational_summary(degraded)
    assert "gpu_load=NO DISPONIBLE" in text
    assert "vram=NO DISPONIBLE" in text


def test_operational_formatter_json_safe():
    text = compact_runtime_response("estado GPU RX9070", CTX)
    assert isinstance(text, str)


def test_compact_responses_shorter_than_legacy():
    text = format_gpu_operational_summary(GPU_ACTIVE)
    legacy = (
        "La GPU RX9070 está online y funcionando correctamente. "
        "Actualmente presenta una temperatura estable, una carga baja, potencia dentro de rango, "
        "memoria VRAM disponible y ventiladores operando de forma normal según la telemetría observada del runtime."
    )
    assert len(text) < len(legacy)


def test_operational_prompt_uses_compact_mode():
    assert select_operational_response_profile("estado GPU RX9070") == "operational_compact"


def test_verbose_mode_still_available():
    assert select_operational_response_profile("estado GPU RX9070 detallado") == "operational_verbose"
