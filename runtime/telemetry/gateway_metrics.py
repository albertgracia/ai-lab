from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime
from threading import Lock
from typing import Any

METRICS = {
    "requests_total": 0,
    "streams_total": 0,
    "errors_total": 0,
    "last_model": None,
    "last_path": None,
    "last_latency_ms": None,
    "last_error": None,
    "updated_at": None,
}


# Bounded in-memory latency store (FASE 37A)
# - Keeps a small rolling window per (kind, route_family, model)
# - Deterministic percentile computation (no external deps)
_LAT_LOCK = Lock()
_LAT_MAX_SAMPLES = 256
_LAT_STORE: dict[tuple[str, str, str], deque[float]] = defaultdict(lambda: deque(maxlen=_LAT_MAX_SAMPLES))


def _pct(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if q <= 0:
        return float(min(values))
    if q >= 1:
        return float(max(values))
    s = sorted(values)
    # Deterministic index, avoids interpolation complexity.
    idx = int(round((len(s) - 1) * q))
    idx = max(0, min(len(s) - 1, idx))
    return float(s[idx])


def record_latency_sample(
    ms: float,
    *,
    kind: str = "request_total",
    route_family: str | None = None,
    model: str | None = None,
) -> None:
    try:
        v = float(ms)
    except Exception:
        return
    if v < 0:
        return
    rf = (route_family or "unknown")[:64]
    m = (model or "unknown")[:96]
    k = (kind or "request_total")[:32]
    with _LAT_LOCK:
        _LAT_STORE[(k, rf, m)].append(v)


def get_latency_stats(
    *,
    kind: str = "request_total",
    route_family: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    rf = (route_family or "*")[:64]
    m = (model or "*")[:96]
    k = (kind or "request_total")[:32]

    with _LAT_LOCK:
        # Exact key
        if rf != "*" and m != "*":
            vals = list(_LAT_STORE.get((k, rf, m), ()))
            return _stats_from(vals)

        # Wildcards: aggregate across matching keys (bounded by store size)
        vals: list[float] = []
        for (kk, rr, mm), dq in _LAT_STORE.items():
            if kk != k:
                continue
            if rf != "*" and rr != rf:
                continue
            if m != "*" and mm != m:
                continue
            vals.extend(list(dq))
        return _stats_from(vals)


def _stats_from(vals: list[float]) -> dict[str, Any]:
    if not vals:
        return {"count": 0, "p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0, "last_ms": 0.0}
    last = float(vals[-1])
    return {
        "count": int(len(vals)),
        "p50_ms": round(_pct(vals, 0.50), 1),
        "p95_ms": round(_pct(vals, 0.95), 1),
        "max_ms": round(max(vals), 1),
        "last_ms": round(last, 1),
    }


def register_request(path, model=None):
    METRICS["requests_total"] += 1
    METRICS["last_model"] = model
    METRICS["last_path"] = path
    METRICS["updated_at"] = datetime.utcnow().isoformat()


def register_stream():
    METRICS["streams_total"] += 1


def register_error(error):
    METRICS["errors_total"] += 1
    METRICS["last_error"] = str(error)
    METRICS["updated_at"] = datetime.utcnow().isoformat()


def register_latency(ms, model: str | None = None, route_family: str | None = None, kind: str = "request_total"):
    METRICS["last_latency_ms"] = ms
    # Best-effort: bounded rolling stats store.
    try:
        record_latency_sample(ms, kind=kind, route_family=route_family, model=model)
    except Exception:
        pass


def get_metrics():
    return METRICS
