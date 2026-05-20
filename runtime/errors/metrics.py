from __future__ import annotations

import json
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from runtime.errors.runtime_errors import RuntimeErrorEvent
from runtime.errors.taxonomy import RuntimeErrorCategory
from runtime.errors.severity import ErrorSeverity

_LOG_DIR = Path("/opt/ai-lab/logs")
_LOG_PATH = _LOG_DIR / "runtime_errors.jsonl"
_MAX_LOG_BYTES = 100 * 1024 * 1024
_BACKUP_COUNT = 7

_logger: logging.Logger | None = None

_AI_LAB_ERROR_ATTRIBUTION_ENABLED = os.environ.get(
    "AI_LAB_ERROR_ATTRIBUTION_ENABLED", "true"
).lower() == "true"
_AI_LAB_ERROR_STRUCTURED_LOGS = os.environ.get(
    "AI_LAB_ERROR_STRUCTURED_LOGS", "true"
).lower() == "true"
_AI_LAB_ERROR_PROMETHEUS_ENABLED = os.environ.get(
    "AI_LAB_ERROR_PROMETHEUS_ENABLED", "true"
).lower() == "true"


def _get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger
    _logger = logging.getLogger("runtime_errors")
    _logger.setLevel(logging.INFO)
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        str(_LOG_PATH),
        maxBytes=_MAX_LOG_BYTES,
        backupCount=_BACKUP_COUNT,
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(handler)
    _logger.propagate = False
    return _logger


COUNTERS: dict[str, Any] = {}
_COUNTERS_INITIALIZED = False


def _init_counters() -> None:
    global COUNTERS, _COUNTERS_INITIALIZED
    if _COUNTERS_INITIALIZED:
        return
    try:
        from prometheus_client import Counter
        COUNTERS["errors_total"] = Counter(
            "ailab_runtime_errors_total",
            "Runtime errors by category, severity and component",
            ["category", "severity", "component"],
        )
        COUNTERS["error_recoverability"] = Counter(
            "ailab_runtime_error_recoverability_total",
            "Runtime errors by recoverability",
            ["recoverability"],
        )
        COUNTERS["timeout_total"] = Counter(
            "ailab_runtime_timeout_total",
            "Timeout errors by stage (connect/read/stream_idle)",
            ["stage"],
        )
        COUNTERS["stream_interruptions"] = Counter(
            "ailab_runtime_stream_interruptions_total",
            "Stream interruptions by reason",
            ["reason"],
        )
        COUNTERS["upstream_failures"] = Counter(
            "ailab_runtime_upstream_failures_total",
            "Upstream failures by reason",
            ["reason"],
        )
        COUNTERS["gateway_internal"] = Counter(
            "ailab_runtime_gateway_internal_total",
            "Gateway internal exceptions by exception type",
            ["exception"],
        )
        COUNTERS["client_disconnect"] = Counter(
            "ailab_runtime_client_disconnect_total",
            "Client disconnect events",
        )
        COUNTERS["error_slo_impact"] = Counter(
            "ailab_runtime_error_slo_impact_total",
            "Errors impacting SLO by slo type",
            ["slo"],
        )
        COUNTERS["error_retryable"] = Counter(
            "ailab_runtime_error_retryable_total",
            "Retryable errors",
        )
        COUNTERS["error_nonrecoverable"] = Counter(
            "ailab_runtime_error_nonrecoverable_total",
            "Non-recoverable errors",
        )
        _COUNTERS_INITIALIZED = True
    except ImportError:
        COUNTERS["_prometheus_unavailable"] = True


def _counter(name: str) -> Any:
    c = COUNTERS.get(name)
    if c is None:
        return None
    return c


def emit_structured_log(event: RuntimeErrorEvent) -> None:
    if not _AI_LAB_ERROR_STRUCTURED_LOGS:
        return
    d = event.to_dict()
    for skip in ("first_seen", "last_seen", "occurrence_count"):
        if d.get(skip) is None:
            d.pop(skip, None)
    _get_logger().info(json.dumps(d, ensure_ascii=False, default=str))


def emit_prometheus(event: RuntimeErrorEvent) -> None:
    if not _AI_LAB_ERROR_PROMETHEUS_ENABLED:
        return
    if not _COUNTERS_INITIALIZED:
        _init_counters()
    labels = event.to_prometheus_labels()
    c = _counter("errors_total")
    if c is not None:
        c.labels(**labels).inc()
    rc = _counter("error_recoverability")
    if rc is not None:
        rc.labels(recoverability=event.recoverability.value).inc()
    if event.slo_impact:
        sc = _counter("error_slo_impact")
        if sc is not None:
            sc.labels(slo="degradation").inc()
    if event.retryable:
        retry = _counter("error_retryable")
        if retry is not None:
            retry.inc()
    else:
        nonrec = _counter("error_nonrecoverable")
        if nonrec is not None:
            nonrec.inc()
    cat = event.category
    if cat in (
        RuntimeErrorCategory.UPSTREAM_TIMEOUT,
        RuntimeErrorCategory.LMSTUDIO_TIMEOUT,
        RuntimeErrorCategory.LMSTUDIO_STREAM_STALL,
    ):
        stage = "unknown"
        if "timeout" in event.origin_stage:
            stage = event.origin_stage
        elif cat == RuntimeErrorCategory.LMSTUDIO_STREAM_STALL:
            stage = "stream_idle"
        elif cat == RuntimeErrorCategory.UPSTREAM_TIMEOUT:
            stage = "connect"
        elif cat == RuntimeErrorCategory.LMSTUDIO_TIMEOUT:
            stage = "read"
        tc = _counter("timeout_total")
        if tc is not None:
            tc.labels(stage=stage).inc()
    if cat in (
        RuntimeErrorCategory.STREAM_INTERRUPTED,
        RuntimeErrorCategory.LMSTUDIO_STREAM_STALL,
        RuntimeErrorCategory.STREAM_BACKPRESSURE,
        RuntimeErrorCategory.CLIENT_DISCONNECT,
    ):
        reason = cat.value.lower()
        si = _counter("stream_interruptions")
        if si is not None:
            si.labels(reason=reason).inc()
    if cat in (
        RuntimeErrorCategory.UPSTREAM_TIMEOUT,
        RuntimeErrorCategory.UPSTREAM_CONNECTION,
        RuntimeErrorCategory.UPSTREAM_INVALID_RESPONSE,
    ):
        uf = _counter("upstream_failures")
        if uf is not None:
            uf.labels(reason=cat.value.lower()).inc()
    if cat == RuntimeErrorCategory.GATEWAY_INTERNAL:
        gi = _counter("gateway_internal")
        if gi is not None:
            gi.labels(exception=event.exception_class or "unknown").inc()
    if cat == RuntimeErrorCategory.CLIENT_DISCONNECT:
        cd = _counter("client_disconnect")
        if cd is not None:
            cd.inc()


def emit_error(event: RuntimeErrorEvent) -> None:
    if not _AI_LAB_ERROR_ATTRIBUTION_ENABLED:
        return
    emit_structured_log(event)
    emit_prometheus(event)
