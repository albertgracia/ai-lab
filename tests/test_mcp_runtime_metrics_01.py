from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "mcp" / "runtime-mcp" / "metrics.py"


def load_metrics_module():
    spec = importlib.util.spec_from_file_location("ailab_mcp_metrics_snapshot", METRICS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_render_prometheus_metrics_contains_expected_metric_names() -> None:
    metrics = load_metrics_module()
    metrics.bootstrap_process_metrics("8091", "local", "semantic", auth_mode="none")
    metrics.bootstrap_process_metrics("8092", "lan", "lan", auth_mode="token")
    rendered = metrics.render_prometheus_metrics()

    expected = {
        "ailab_mcp_up",
        "ailab_mcp_requests_total",
        "ailab_mcp_auth_failures_total",
        "ailab_mcp_auth_success_total",
        "ailab_mcp_tool_calls_total",
        "ailab_mcp_tool_errors_total",
        "ailab_mcp_initialize_total",
        "ailab_mcp_endpoint_info",
        "ailab_mcp_build_info",
        "ailab_mcp_request_duration_seconds",
        "ailab_mcp_tool_duration_seconds",
    }
    missing = sorted(name for name in expected if name not in rendered)
    assert not missing, f"Missing metrics: {missing}"
    assert rendered.startswith("# HELP ailab_mcp_up")


def test_metrics_render_allowed_labels_and_safe_normalization() -> None:
    metrics = load_metrics_module()
    metrics.bootstrap_process_metrics("8091", "local", "semantic", auth_mode="none")
    metrics.record_request("8091", "semantic", "success", 0.12, method="initialize", bind="local")
    metrics.record_auth_success("8092", "lan", bind="lan")
    metrics.record_auth_failure("8092", "lan", bind="lan")
    metrics.record_tool_call("8091", "semantic", "ailab_status", "success", 0.05, bind="local")
    metrics.record_tool_call("8091", "semantic", "not_a_real_tool", "error", 0.25, bind="local")
    rendered = metrics.render_prometheus_metrics()

    assert 'endpoint="8091"' in rendered
    assert 'bind="local"' in rendered
    assert 'service="semantic"' in rendered
    assert 'tool="ailab_status"' in rendered
    assert 'tool="unknown"' in rendered
    assert 'status="success"' in rendered
    assert 'status="error"' in rendered
    assert 'method="initialize"' in rendered


def test_unknown_endpoint_is_normalized_without_full_ip_labels() -> None:
    metrics = load_metrics_module()
    metrics.record_request("192.168.1.88", "semantic", "success", 0.2, method="tools/list", bind="local")
    rendered = metrics.render_prometheus_metrics()

    assert 'endpoint="unknown"' in rendered
    assert "192.168.1.88" not in rendered


def test_forbidden_secret_like_strings_do_not_appear_in_rendered_metrics() -> None:
    metrics = load_metrics_module()
    metrics.bootstrap_process_metrics("8092", "lan", "lan", auth_mode="token")
    rendered = metrics.render_prometheus_metrics()

    forbidden = {
        "Authorization",
        "Bearer",
        "AILAB_MCP_TOKEN",
        "token=",
        "prompt=",
        "query=",
        "payload=",
    }
    for marker in forbidden:
        assert marker not in rendered


def test_histograms_render_in_basic_prometheus_text_format() -> None:
    metrics = load_metrics_module()
    metrics.bootstrap_process_metrics("8091", "local", "semantic", auth_mode="none")
    metrics.record_request("8091", "semantic", "success", 0.4, method="tools/call", bind="local")
    metrics.record_tool_call("8091", "semantic", "ailab_status", "success", 0.2, bind="local")
    rendered = metrics.render_prometheus_metrics()

    assert "ailab_mcp_request_duration_seconds_bucket" in rendered
    assert "ailab_mcp_request_duration_seconds_sum" in rendered
    assert "ailab_mcp_request_duration_seconds_count" in rendered
    assert "ailab_mcp_tool_duration_seconds_bucket" in rendered
    assert "ailab_mcp_tool_duration_seconds_sum" in rendered
    assert "ailab_mcp_tool_duration_seconds_count" in rendered
