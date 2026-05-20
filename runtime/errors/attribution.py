from __future__ import annotations

import json
import traceback
from typing import Any

import requests

from runtime.errors.taxonomy import RuntimeErrorCategory
from runtime.errors.runtime_errors import RuntimeErrorEvent


def classify_exception(exc: BaseException) -> RuntimeErrorCategory:
    if isinstance(exc, requests.ConnectTimeout):
        return RuntimeErrorCategory.UPSTREAM_TIMEOUT
    if isinstance(exc, requests.ReadTimeout):
        return RuntimeErrorCategory.LMSTUDIO_TIMEOUT
    if isinstance(exc, requests.ConnectionError):
        return RuntimeErrorCategory.UPSTREAM_CONNECTION
    if isinstance(exc, requests.exceptions.RequestException):
        exc_str = str(exc).lower()
        if "timeout" in exc_str:
            return RuntimeErrorCategory.UPSTREAM_TIMEOUT
        if "connection" in exc_str or "refused" in exc_str or "reset" in exc_str:
            return RuntimeErrorCategory.UPSTREAM_CONNECTION
        return RuntimeErrorCategory.LMSTUDIO_TIMEOUT
    if isinstance(exc, BrokenPipeError):
        return RuntimeErrorCategory.CLIENT_DISCONNECT
    if isinstance(exc, ConnectionResetError):
        return RuntimeErrorCategory.CLIENT_DISCONNECT
    if isinstance(exc, ConnectionAbortedError):
        return RuntimeErrorCategory.CLIENT_DISCONNECT
    if isinstance(exc, json.JSONDecodeError):
        return RuntimeErrorCategory.UPSTREAM_INVALID_RESPONSE
    if isinstance(exc, PermissionError):
        return RuntimeErrorCategory.GOVERNANCE_BLOCK
    if isinstance(exc, TimeoutError):
        return RuntimeErrorCategory.LMSTUDIO_TIMEOUT
    if isinstance(exc, (OSError, ConnectionError)):
        return RuntimeErrorCategory.STREAM_INTERRUPTED
    if isinstance(exc, (ValueError, TypeError)):
        return RuntimeErrorCategory.REQUEST_VALIDATION
    if isinstance(exc, (RuntimeError, SystemError)):
        return RuntimeErrorCategory.GATEWAY_INTERNAL
    return RuntimeErrorCategory.UNKNOWN


def classify_http_status(status: int, body: str = "") -> RuntimeErrorCategory:
    if status == 429:
        return RuntimeErrorCategory.CONCURRENCY_THROTTLE
    if status == 503:
        return RuntimeErrorCategory.LMSTUDIO_MODEL_UNAVAILABLE
    if status >= 400:
        if "unloaded" in body.lower():
            return RuntimeErrorCategory.LMSTUDIO_MODEL_UNAVAILABLE
        return RuntimeErrorCategory.UPSTREAM_INVALID_RESPONSE
    return RuntimeErrorCategory.UNKNOWN


def classify_stream_failure(reason: str) -> RuntimeErrorCategory:
    r_lower = reason.lower()
    if "idle" in r_lower or "stall" in r_lower:
        return RuntimeErrorCategory.LMSTUDIO_STREAM_STALL
    if "duration" in r_lower or "timeout" in r_lower:
        return RuntimeErrorCategory.STREAM_INTERRUPTED
    if "client" in r_lower or "disconnect" in r_lower:
        return RuntimeErrorCategory.CLIENT_DISCONNECT
    if "backpressure" in r_lower or "slot" in r_lower:
        return RuntimeErrorCategory.STREAM_BACKPRESSURE
    if "orphan" in r_lower:
        return RuntimeErrorCategory.STREAM_INTERRUPTED
    return RuntimeErrorCategory.STREAM_INTERRUPTED


def classify_timeout(stage: str) -> RuntimeErrorCategory:
    s_lower = stage.lower()
    if s_lower in ("connect", "connection"):
        return RuntimeErrorCategory.UPSTREAM_TIMEOUT
    if s_lower in ("read", "response"):
        return RuntimeErrorCategory.LMSTUDIO_TIMEOUT
    if s_lower in ("stream_idle", "stream"):
        return RuntimeErrorCategory.LMSTUDIO_STREAM_STALL
    if s_lower in ("first_chunk", "ttfb"):
        return RuntimeErrorCategory.LMSTUDIO_TIMEOUT
    return RuntimeErrorCategory.UPSTREAM_TIMEOUT


def infer_root_cause(exc: BaseException, category: RuntimeErrorCategory) -> str:
    cause = str(exc)[:500]
    if not cause:
        cause = category.value
    tb = traceback.format_exc()
    lines = [l.strip() for l in tb.splitlines() if l.strip()]
    for line in reversed(lines):
        if line.startswith("requests.exceptions") or line.startswith("urllib3"):
            cause = line[:200]
            break
    return cause


def build_error_event(
    exc: BaseException | None,
    *,
    category: RuntimeErrorCategory | None = None,
    origin_stage: str = "gateway",
    component: str = "gateway",
    source_file: str = "",
    workflow_id: str | None = None,
    request_id: str | None = None,
    model: str | None = None,
    route_type: str | None = None,
    streaming: bool = False,
    slo_impact: bool = False,
    latency_ms: float | None = None,
    message: str = "",
    **kw: Any,
) -> RuntimeErrorEvent:
    if exc is not None and category is None:
        category = classify_exception(exc)
    elif category is None:
        category = RuntimeErrorCategory.UNKNOWN
    return RuntimeErrorEvent.from_exception(
        exc or RuntimeError(category.value),
        category=category,
        origin_stage=origin_stage,
        component=component,
        source_file=source_file,
        workflow_id=workflow_id,
        request_id=request_id,
        model=model,
        route_type=route_type,
        streaming=streaming,
        slo_impact=slo_impact,
        latency_ms=latency_ms,
        message=message,
        **kw,
    )


def classify_timeout_stage(exc: BaseException) -> str:
    exc_str = str(exc).lower()
    if isinstance(exc, requests.ConnectTimeout):
        return "connect"
    if isinstance(exc, requests.ReadTimeout):
        return "read"
    if "connect" in exc_str:
        return "connect"
    if "read" in exc_str:
        return "read"
    if "stream" in exc_str:
        return "stream"
    return "unknown"
