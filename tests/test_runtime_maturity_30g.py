"""FASE 30G: Operational Reporting Discipline"""

import json
import pytest

from runtime.gateway.tool_request_classifier import (
    FORBIDDEN_TOOL_RECOMMENDATIONS,
    sanitize_report_output,
)
from runtime.maturity.descriptor import RuntimePhase
from runtime.maturity.builder import _resolve_generation_phase
from runtime.telemetry.prometheus_metrics import (
    record_report_request,
    record_report_model_classification,
    record_report_node_classification,
    record_report_data_quality,
    record_report_forbidden_recommendation,
    REPORT_REQUESTS_BY_MODEL,
    REPORT_FORBIDDEN_RECOMMENDATION_BLOCKED,
)


# ── FORBIDDEN_TOOL_RECOMMENDATIONS ────────────────────────────────

def test_forbidden_tools_is_set():
    assert isinstance(FORBIDDEN_TOOL_RECOMMENDATIONS, set)
    assert len(FORBIDDEN_TOOL_RECOMMENDATIONS) > 0


def test_forbidden_tools_contains_expected():
    assert "datadog" in FORBIDDEN_TOOL_RECOMMENDATIONS
    assert "new relic" in FORBIDDEN_TOOL_RECOMMENDATIONS
    assert "sentry" in FORBIDDEN_TOOL_RECOMMENDATIONS
    assert "splunk" in FORBIDDEN_TOOL_RECOMMENDATIONS


def test_forbidden_tools_excludes_native_stack():
    assert "prometheus" not in FORBIDDEN_TOOL_RECOMMENDATIONS
    assert "grafana" not in FORBIDDEN_TOOL_RECOMMENDATIONS


def test_forbidden_tools_all_lowercase():
    for tool in FORBIDDEN_TOOL_RECOMMENDATIONS:
        assert tool == tool.lower(), f"{tool} is not lowercase"


# ── sanitize_report_output ────────────────────────────────────────

def test_sanitize_clean_content():
    content = "AI-LAB runtime esta operativo con 3 modelos activos."
    result, found = sanitize_report_output(content)
    assert result == content
    assert found == []


def test_sanitize_none_content():
    result, found = sanitize_report_output(None)
    assert result == ""
    assert found == []


def test_sanitize_empty_content():
    result, found = sanitize_report_output("")
    assert result == ""
    assert found == []


def test_sanitize_detects_forbidden_tool():
    content = (
        "Se recomienda implementar Datadog para monitorizar "
        "la infraestructura del runtime."
    )
    result, found = sanitize_report_output(content)
    assert "datadog" in found
    assert "DISCIPLINA OPERACIONAL" in result


def test_sanitize_multiple_forbidden_tools():
    content = (
        "Para observabilidad se podria usar Datadog o New Relic. "
        "Alternativamente Sentry para errores."
    )
    result, found = sanitize_report_output(content)
    assert "datadog" in found
    assert "new relic" in found
    assert "sentry" in found
    assert "DISCIPLINA OPERACIONAL" in result


def test_sanitize_appends_note_not_inline():
    content = (
        "El runtime funciona correctamente. "
        "Se recomienda Datadog para tracing."
    )
    result, found = sanitize_report_output(content)
    assert found == ["datadog"]
    assert result.startswith("El runtime funciona")
    assert "[DISCIPLINA OPERACIONAL]" in result
    assert result.index("[DISCIPLINA OPERACIONAL]") > result.index("Datadog")


def test_sanitize_preserves_non_forbidden_content():
    content = (
        "Metricas disponibles via Prometheus en :9090 "
        "y dashboards en Grafana :3000."
    )
    result, found = sanitize_report_output(content)
    assert found == []
    assert result == content


# ── RuntimePhase ─────────────────────────────────────────────────

def test_runtime_phase_has_30G():
    assert RuntimePhase.PHASE_30G.value == "30G"


def test_resolve_generation_phase_returns_30g():
    phase = _resolve_generation_phase()
    assert phase == "30G"


# ── Metric recorders ─────────────────────────────────────────────

def test_record_report_request_called():
    record_report_request("qwen2.5-coder-14b", "heavy")
    val = REPORT_REQUESTS_BY_MODEL.labels(model="qwen2.5-coder-14b", type="heavy")._value.get()
    assert val >= 1


def test_record_report_model_classification_called():
    record_report_model_classification("active")
    record_report_model_classification("disabled")


def test_record_report_node_classification_called():
    record_report_node_classification("active")
    record_report_node_classification("inventory")


def test_record_report_data_quality_called():
    record_report_data_quality("complete")
    record_report_data_quality("partial")
    record_report_data_quality("minimal")


def test_record_report_forbidden_recommendation_called():
    record_report_forbidden_recommendation("datadog")
    val = REPORT_FORBIDDEN_RECOMMENDATION_BLOCKED.labels(tool="datadog")._value.get()
    assert val >= 1


# ── manifest_profiles.json (no duplicate report key) ────────────

def test_manifest_no_duplicate_report_key():
    import json as _json
    from pathlib import Path
    manifest = _json.loads(Path("/opt/ai-lab/runtime/profiles/manifest_profiles.json").read_text())
    routes = manifest.get("routes", {})
    assert "report" in routes
    assert routes["report"] == "chat_profile.json"
