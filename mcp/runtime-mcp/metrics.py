from __future__ import annotations

import json
import os
import platform
import threading
import time
from collections import defaultdict
from importlib import metadata
from typing import Iterable

REQUEST_BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
TOOL_BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

ALLOWED_ENDPOINTS = {
    "8091": {"bind": "local", "service": "semantic", "auth": "none"},
    "8092": {"bind": "lan", "service": "lan", "auth": "token"},
}
ALLOWED_TOOLS = {
    "ailab_status",
    "ailab_runtime_health",
    "ailab_route_preview",
    "ailab_operator_summary",
    "ailab_incidents_active",
    "ailab_slo_status",
    "ailab_health_latency",
    "ailab_memory_search",
    "unknown",
}
ALLOWED_METHODS = {
    "initialize",
    "tools/list",
    "tools/call",
    "prompts/list",
    "resources/list",
    "ping",
    "metrics",
    "sse",
    "unknown",
}
ALLOWED_STATUSES = {"success", "error", "auth_failed", "unknown"}
ALLOWED_LABEL_KEYS = {
    "endpoint",
    "bind",
    "service",
    "method",
    "tool",
    "status",
    "client_type",
    "mode",
    "auth",
    "version",
    "python_version",
    "mcp_version",
    "commit",
}
FORBIDDEN_LABEL_KEYS = {
    "token",
    "authorization",
    "prompt",
    "query",
    "payload",
    "user_text",
    "stacktrace",
    "memory_result",
    "arguments",
    "result",
    "peer_ip",
    "client_info",
}


class _CounterMetric:
    def __init__(self) -> None:
        self.samples: defaultdict[tuple[tuple[str, str], ...], float] = defaultdict(float)

    def inc(self, labels: dict[str, str], value: float = 1.0) -> None:
        self.samples[_label_key(labels)] += value


class _GaugeMetric:
    def __init__(self) -> None:
        self.samples: dict[tuple[tuple[str, str], ...], float] = {}

    def set(self, labels: dict[str, str], value: float) -> None:
        self.samples[_label_key(labels)] = value


class _HistogramMetric:
    def __init__(self, buckets: Iterable[float]) -> None:
        self.buckets = tuple(float(bucket) for bucket in buckets)
        self.bucket_counts: defaultdict[tuple[tuple[str, str], ...], list[int]] = defaultdict(
            lambda: [0 for _ in self.buckets]
        )
        self.counts: defaultdict[tuple[tuple[str, str], ...], int] = defaultdict(int)
        self.sums: defaultdict[tuple[tuple[str, str], ...], float] = defaultdict(float)

    def observe(self, labels: dict[str, str], value: float) -> None:
        key = _label_key(labels)
        safe_value = max(float(value), 0.0)
        for index, bucket in enumerate(self.buckets):
            if safe_value <= bucket:
                self.bucket_counts[key][index] += 1
        self.counts[key] += 1
        self.sums[key] += safe_value


_METRICS = {
    "up": _GaugeMetric(),
    "requests_total": _CounterMetric(),
    "request_duration_seconds": _HistogramMetric(REQUEST_BUCKETS),
    "auth_failures_total": _CounterMetric(),
    "auth_success_total": _CounterMetric(),
    "tool_calls_total": _CounterMetric(),
    "tool_errors_total": _CounterMetric(),
    "tool_duration_seconds": _HistogramMetric(TOOL_BUCKETS),
    "initialize_total": _CounterMetric(),
    "clients_active": _GaugeMetric(),
    "endpoint_info": _GaugeMetric(),
    "build_info": _GaugeMetric(),
}
_LOCK = threading.Lock()


def _label_key(labels: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((key, str(value)) for key, value in labels.items()))


def _labels_from_key(key: tuple[tuple[str, str], ...]) -> dict[str, str]:
    return dict(key)


def _format_labels(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    pairs = [f'{key}="{str(value).replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}"' for key, value in sorted(labels.items())]
    return "{" + ",".join(pairs) + "}"


def _normalize_label_key(key: str) -> str:
    normalized = str(key or "").strip().lower()
    if normalized in FORBIDDEN_LABEL_KEYS:
        raise ValueError(f"forbidden label key: {key}")
    if normalized not in ALLOWED_LABEL_KEYS:
        raise ValueError(f"unsupported label key: {key}")
    return normalized


def _sanitize_labels(labels: dict[str, str]) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for key, value in labels.items():
        normalized_key = _normalize_label_key(key)
        sanitized[normalized_key] = str(value).strip() or "unknown"
    return sanitized


def _normalize_endpoint_context(endpoint: str, bind: str | None = None, service: str | None = None) -> dict[str, str]:
    endpoint_value = str(endpoint or "").strip()
    endpoint_config = ALLOWED_ENDPOINTS.get(endpoint_value)
    if not endpoint_config:
        return {"endpoint": "unknown", "bind": "unknown", "service": "unknown"}
    bind_value = endpoint_config["bind"] if bind is None else str(bind).strip()
    service_value = endpoint_config["service"] if service is None else str(service).strip()
    if bind_value != endpoint_config["bind"] or service_value != endpoint_config["service"]:
        return {"endpoint": "unknown", "bind": "unknown", "service": "unknown"}
    return {"endpoint": endpoint_value, "bind": bind_value, "service": service_value}


def _normalize_tool(tool: str) -> str:
    tool_value = str(tool or "unknown").strip()
    return tool_value if tool_value in ALLOWED_TOOLS else "unknown"


def _normalize_method(method: str | None) -> str:
    method_value = str(method or "unknown").strip().lower()
    return method_value if method_value in ALLOWED_METHODS else "unknown"


def _normalize_status(status: str | None) -> str:
    status_value = str(status or "unknown").strip().lower()
    return status_value if status_value in ALLOWED_STATUSES else "unknown"


def _build_info_labels() -> dict[str, str]:
    try:
        mcp_version = metadata.version("mcp")
    except metadata.PackageNotFoundError:
        mcp_version = "unknown"
    return {
        "python_version": platform.python_version(),
        "mcp_version": mcp_version,
        "commit": os.environ.get("AILAB_MCP_BUILD_COMMIT", "snapshot"),
    }


def bootstrap_process_metrics(
    endpoint: str,
    bind: str,
    service: str,
    *,
    auth_mode: str,
    version: str | None = None,
) -> None:
    context = _normalize_endpoint_context(endpoint, bind=bind, service=service)
    resolved_auth = "token" if auth_mode == "token" else "none"
    resolved_version = version or os.environ.get("AILAB_MCP_VERSION", "snapshot")
    with _LOCK:
        _METRICS["up"].set(context, 1.0)
        _METRICS["clients_active"].set(context, 0.0)
        _METRICS["endpoint_info"].set(
            _sanitize_labels(
                {
                    **context,
                    "mode": "read-only",
                    "auth": resolved_auth,
                    "version": resolved_version,
                }
            ),
            1.0,
        )
        _METRICS["build_info"].set(_sanitize_labels(_build_info_labels()), 1.0)


def set_mcp_up(endpoint: str, service: str, value: float, bind: str | None = None) -> None:
    context = _normalize_endpoint_context(endpoint, bind=bind, service=service)
    with _LOCK:
        _METRICS["up"].set(context, 1.0 if value else 0.0)


def set_clients_active(endpoint: str, service: str, value: float, bind: str | None = None) -> None:
    context = _normalize_endpoint_context(endpoint, bind=bind, service=service)
    with _LOCK:
        _METRICS["clients_active"].set(context, max(float(value), 0.0))


def record_request(
    endpoint: str,
    service: str,
    status: str,
    duration_seconds: float,
    *,
    method: str | None = None,
    bind: str | None = None,
) -> None:
    context = _normalize_endpoint_context(endpoint, bind=bind, service=service)
    labels = _sanitize_labels({**context, "method": _normalize_method(method)})
    _normalize_status(status)
    with _LOCK:
        _METRICS["requests_total"].inc(labels)
        _METRICS["request_duration_seconds"].observe(labels, duration_seconds)


def record_auth_success(endpoint: str, service: str, bind: str | None = None) -> None:
    context = _normalize_endpoint_context(endpoint, bind=bind, service=service)
    with _LOCK:
        _METRICS["auth_success_total"].inc(context)


def record_auth_failure(endpoint: str, service: str, bind: str | None = None) -> None:
    context = _normalize_endpoint_context(endpoint, bind=bind, service=service)
    with _LOCK:
        _METRICS["auth_failures_total"].inc(context)


def record_initialize(endpoint: str, service: str, status: str, bind: str | None = None) -> None:
    context = _normalize_endpoint_context(endpoint, bind=bind, service=service)
    labels = _sanitize_labels({**context, "status": _normalize_status(status)})
    with _LOCK:
        _METRICS["initialize_total"].inc(labels)


def record_tool_call(
    endpoint: str,
    service: str,
    tool: str,
    status: str,
    duration_seconds: float,
    *,
    bind: str | None = None,
) -> None:
    context = _normalize_endpoint_context(endpoint, bind=bind, service=service)
    normalized_status = _normalize_status(status)
    labels = _sanitize_labels(
        {
            **context,
            "tool": _normalize_tool(tool),
            "status": normalized_status,
        }
    )
    histogram_labels = _sanitize_labels({**context, "tool": labels["tool"]})
    with _LOCK:
        _METRICS["tool_calls_total"].inc(labels)
        _METRICS["tool_duration_seconds"].observe(histogram_labels, duration_seconds)
        if normalized_status == "error":
            _METRICS["tool_errors_total"].inc(histogram_labels)


def extract_mcp_method(scope: dict, body: bytes) -> str:
    path = str(scope.get("path") or "")
    http_method = str(scope.get("method") or "").upper()
    if path == "/metrics":
        return "metrics"
    if path != "/mcp":
        return "unknown"
    if http_method == "GET":
        return "sse"
    if not body:
        return "unknown"
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "unknown"
    if isinstance(payload, list):
        payload = payload[0] if payload and isinstance(payload[0], dict) else {}
    if not isinstance(payload, dict):
        return "unknown"
    return _normalize_method(payload.get("method"))


class MCPMetricsMiddleware:
    def __init__(self, app, *, endpoint: str, bind: str, service: str) -> None:
        self.app = app
        self.endpoint = endpoint
        self.bind = bind
        self.service = service

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        messages: list[dict] = []
        body_parts: list[bytes] = []
        more_body = True
        while more_body:
            message = await receive()
            messages.append(message)
            if message.get("type") != "http.request":
                break
            body_parts.append(message.get("body", b""))
            more_body = message.get("more_body", False)

        body = b"".join(body_parts)
        method = extract_mcp_method(scope, body)
        status_code = 500
        started = time.perf_counter()

        async def replay_receive():
            if messages:
                return messages.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send_wrapper(message):
            nonlocal status_code
            if message.get("type") == "http.response.start":
                status_code = int(message.get("status", 500))
            await send(message)

        try:
            await self.app(scope, replay_receive, send_wrapper)
        except Exception:
            duration = time.perf_counter() - started
            record_request(
                self.endpoint,
                self.service,
                "error",
                duration,
                method=method,
                bind=self.bind,
            )
            if method == "initialize":
                record_initialize(self.endpoint, self.service, "error", bind=self.bind)
            raise

        duration = time.perf_counter() - started
        request_status = "success" if status_code < 500 else "error"
        record_request(
            self.endpoint,
            self.service,
            request_status,
            duration,
            method=method,
            bind=self.bind,
        )
        if method == "initialize":
            record_initialize(self.endpoint, self.service, request_status, bind=self.bind)


def render_prometheus_metrics() -> str:
    lines = [
        "# HELP ailab_mcp_up MCP endpoint up state.",
        "# TYPE ailab_mcp_up gauge",
    ]
    lines.extend(_render_gauge_series("ailab_mcp_up", _METRICS["up"]))
    lines.extend(
        [
            "# HELP ailab_mcp_requests_total Total MCP requests received.",
            "# TYPE ailab_mcp_requests_total counter",
        ]
    )
    lines.extend(_render_counter_series("ailab_mcp_requests_total", _METRICS["requests_total"]))
    lines.extend(
        [
            "# HELP ailab_mcp_request_duration_seconds MCP request duration in seconds.",
            "# TYPE ailab_mcp_request_duration_seconds histogram",
        ]
    )
    lines.extend(_render_histogram_series("ailab_mcp_request_duration_seconds", _METRICS["request_duration_seconds"]))
    lines.extend(
        [
            "# HELP ailab_mcp_auth_failures_total MCP auth failures.",
            "# TYPE ailab_mcp_auth_failures_total counter",
        ]
    )
    lines.extend(_render_counter_series("ailab_mcp_auth_failures_total", _METRICS["auth_failures_total"]))
    lines.extend(
        [
            "# HELP ailab_mcp_auth_success_total MCP auth successes.",
            "# TYPE ailab_mcp_auth_success_total counter",
        ]
    )
    lines.extend(_render_counter_series("ailab_mcp_auth_success_total", _METRICS["auth_success_total"]))
    lines.extend(
        [
            "# HELP ailab_mcp_tool_calls_total MCP tool calls.",
            "# TYPE ailab_mcp_tool_calls_total counter",
        ]
    )
    lines.extend(_render_counter_series("ailab_mcp_tool_calls_total", _METRICS["tool_calls_total"]))
    lines.extend(
        [
            "# HELP ailab_mcp_tool_errors_total MCP tool execution errors.",
            "# TYPE ailab_mcp_tool_errors_total counter",
        ]
    )
    lines.extend(_render_counter_series("ailab_mcp_tool_errors_total", _METRICS["tool_errors_total"]))
    lines.extend(
        [
            "# HELP ailab_mcp_tool_duration_seconds MCP tool duration in seconds.",
            "# TYPE ailab_mcp_tool_duration_seconds histogram",
        ]
    )
    lines.extend(_render_histogram_series("ailab_mcp_tool_duration_seconds", _METRICS["tool_duration_seconds"]))
    lines.extend(
        [
            "# HELP ailab_mcp_initialize_total MCP initialize calls.",
            "# TYPE ailab_mcp_initialize_total counter",
        ]
    )
    lines.extend(_render_counter_series("ailab_mcp_initialize_total", _METRICS["initialize_total"]))
    lines.extend(
        [
            "# HELP ailab_mcp_clients_active Active MCP client sessions gauge placeholder.",
            "# TYPE ailab_mcp_clients_active gauge",
        ]
    )
    lines.extend(_render_gauge_series("ailab_mcp_clients_active", _METRICS["clients_active"]))
    lines.extend(
        [
            "# HELP ailab_mcp_endpoint_info MCP endpoint metadata.",
            "# TYPE ailab_mcp_endpoint_info gauge",
        ]
    )
    lines.extend(_render_gauge_series("ailab_mcp_endpoint_info", _METRICS["endpoint_info"]))
    lines.extend(
        [
            "# HELP ailab_mcp_build_info MCP build metadata.",
            "# TYPE ailab_mcp_build_info gauge",
        ]
    )
    lines.extend(_render_gauge_series("ailab_mcp_build_info", _METRICS["build_info"]))
    return "\n".join(lines) + "\n"


def _render_counter_series(name: str, metric: _CounterMetric) -> list[str]:
    lines: list[str] = []
    for key in sorted(metric.samples):
        lines.append(f"{name}{_format_labels(_labels_from_key(key))} {metric.samples[key]:.6f}")
    return lines


def _render_gauge_series(name: str, metric: _GaugeMetric) -> list[str]:
    lines: list[str] = []
    for key in sorted(metric.samples):
        lines.append(f"{name}{_format_labels(_labels_from_key(key))} {metric.samples[key]:.6f}")
    return lines


def _render_histogram_series(name: str, metric: _HistogramMetric) -> list[str]:
    lines: list[str] = []
    for key in sorted(metric.counts):
        labels = _labels_from_key(key)
        bucket_counts = metric.bucket_counts[key]
        for index, bucket in enumerate(metric.buckets):
            bucket_labels = dict(labels)
            bucket_labels["le"] = f"{bucket:.2f}".rstrip("0").rstrip(".")
            lines.append(f"{name}_bucket{_format_labels(bucket_labels)} {bucket_counts[index]}")
        inf_labels = dict(labels)
        inf_labels["le"] = "+Inf"
        lines.append(f"{name}_bucket{_format_labels(inf_labels)} {metric.counts[key]}")
        lines.append(f"{name}_sum{_format_labels(labels)} {metric.sums[key]:.6f}")
        lines.append(f"{name}_count{_format_labels(labels)} {metric.counts[key]}")
    return lines


def metrics_http_body() -> str:
    return render_prometheus_metrics()
