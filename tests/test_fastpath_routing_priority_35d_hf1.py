"""HOTFIX 35D-HF1: FastPath Routing Priority tests.

Verifies that operational queries use tool_fastpath
while deep/coding queries still use report/cognitive/deep paths.
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/opt/ai-lab")

from runtime.gateway.tool_request_classifier import (
    classify_chat_route,
    is_report_request,
    should_prioritize_operational_fastpath,
    detect_operational_fastpath_intent,
    RuntimeRoute,
)


# ── should_prioritize_operational_fastpath unit tests ─────────────


def test_fastpath_runtime_status():
    assert should_prioritize_operational_fastpath(
        "estado runtime", tool_fastpath=True, intent_mode=""
    ) is True


def test_fastpath_gpu_status():
    assert should_prioritize_operational_fastpath(
        "estado GPU RX9070", tool_fastpath=True, intent_mode=""
    ) is True


def test_fastpath_observability_status():
    assert should_prioritize_operational_fastpath(
        "estado observabilidad", tool_fastpath=True, intent_mode=""
    ) is True


def test_fastpath_governance_status():
    assert should_prioritize_operational_fastpath(
        "estado governance", tool_fastpath=True, intent_mode=""
    ) is True


def test_fastpath_validation_status():
    assert should_prioritize_operational_fastpath(
        "estado validation", tool_fastpath=True, intent_mode=""
    ) is True


def test_fastpath_exporters_down():
    assert should_prioritize_operational_fastpath(
        "qué exporters están down", tool_fastpath=True, intent_mode=""
    ) is True


def test_fastpath_prometheus_targets():
    assert should_prioritize_operational_fastpath(
        "lista targets Prometheus", tool_fastpath=True, intent_mode=""
    ) is True


# ── Deep-path exclusion tests ────────────────────────────────────


def test_deep_report_not_fastpath():
    assert should_prioritize_operational_fastpath(
        "informe exhaustivo del estado del runtime", tool_fastpath=True, intent_mode=""
    ) is False


def test_forensic_analysis_not_fastpath():
    assert should_prioritize_operational_fastpath(
        "análisis forense del incidente de governance", tool_fastpath=True, intent_mode=""
    ) is False


def test_remediation_plan_not_fastpath():
    assert should_prioritize_operational_fastpath(
        "remediation plan para el módulo gateway", tool_fastpath=True, intent_mode=""
    ) is False


def test_coding_request_not_fastpath():
    assert should_prioritize_operational_fastpath(
        "implementa un script de validación", tool_fastpath=True, intent_mode=""
    ) is False


def test_detailed_architecture_not_fastpath():
    assert should_prioritize_operational_fastpath(
        "arquitectura detallada del router cognitivo", tool_fastpath=True, intent_mode=""
    ) is False


# ── Edge cases ───────────────────────────────────────────────────


def test_no_tool_fastpath_flag():
    assert should_prioritize_operational_fastpath(
        "estado runtime", tool_fastpath=False, intent_mode=""
    ) is False


def test_empty_text():
    assert should_prioritize_operational_fastpath(
        "", tool_fastpath=True, intent_mode=""
    ) is False


def test_no_operational_intent():
    assert should_prioritize_operational_fastpath(
        "cuéntame un chiste", tool_fastpath=True, intent_mode=""
    ) is False


# ── classify_chat_route integration tests ────────────────────────


def _make_payload(user_text: str, *, tools: bool = True) -> dict:
    p: dict = {
        "model": "default",
        "messages": [{"role": "user", "content": user_text}],
    }
    if tools:
        p["tools"] = [{"function": {"name": "test_tool", "description": "test"}}]
    return p


def _classify(text: str, *, tools: bool = True, intent_mode: str = "") -> RuntimeRoute:
    payload = _make_payload(text, tools=tools)
    return classify_chat_route(
        payload,
        mode_name="default",
        user_text=text,
        request_text=text,
        is_report_request=is_report_request(text),
        greeting_fastpath=False,
        tool_fastpath=tools,
        intent_mode=intent_mode,
    )


def test_classify_runtime_status_is_fastpath():
    route = _classify("estado runtime")
    assert route.family == "tool_fastpath", f"Expected tool_fastpath, got {route}"
    assert route.variant == "operational"


def test_classify_gpu_status_is_fastpath():
    route = _classify("estado GPU RX9070")
    assert route.family == "tool_fastpath", f"Expected tool_fastpath, got {route}"
    assert route.variant == "operational"


def test_classify_observability_is_fastpath():
    route = _classify("estado observabilidad")
    assert route.family == "tool_fastpath", f"Expected tool_fastpath, got {route}"
    assert route.variant == "operational"


def test_classify_governance_is_fastpath():
    route = _classify("estado governance")
    assert route.family == "tool_fastpath", f"Expected tool_fastpath, got {route}"
    assert route.variant == "operational"


def test_classify_validation_is_fastpath():
    route = _classify("estado validation")
    assert route.family == "tool_fastpath", f"Expected tool_fastpath, got {route}"
    assert route.variant == "operational"


def test_classify_exporters_down_is_fastpath():
    route = _classify("qué exporters están down")
    assert route.family == "tool_fastpath", f"Expected tool_fastpath, got {route}"
    assert route.variant == "operational"


def test_classify_prometheus_targets_is_fastpath():
    route = _classify("lista targets Prometheus")
    assert route.family == "tool_fastpath", f"Expected tool_fastpath, got {route}"
    assert route.variant == "operational"


# ── classify deep routes stay deep ───────────────────────────────


def test_classify_deep_report_not_fastpath():
    route = _classify("informe exhaustivo del estado del runtime")
    assert route.family != "tool_fastpath", f"Expected non-fastpath, got {route}"


def test_classify_forensic_not_fastpath():
    route = _classify("análisis forense del incidente de governance")
    assert route.family != "tool_fastpath", f"Expected non-fastpath, got {route}"


def test_classify_remediation_not_fastpath():
    route = _classify("remediation plan para el módulo gateway")
    assert route.family != "tool_fastpath", f"Expected non-fastpath, got {route}"


def test_classify_coding_not_fastpath():
    route = _classify("implementa un script de validación")
    assert route.family != "tool_fastpath", f"Expected non-fastpath, got {route}"


def test_classify_detailed_architecture_not_fastpath():
    route = _classify("arquitectura detallada del router cognitivo")
    assert route.family != "tool_fastpath", f"Expected non-fastpath, got {route}"


def test_classify_no_tools_defaults_cognitive():
    payload = _make_payload("estado runtime", tools=False)
    route = classify_chat_route(
        payload,
        mode_name="default",
        user_text="estado runtime",
        request_text="estado runtime",
        is_report_request=False,
        greeting_fastpath=False,
        tool_fastpath=False,
        intent_mode="",
    )
    assert route.family == "cognitive", f"Expected cognitive without tools, got {route}"
