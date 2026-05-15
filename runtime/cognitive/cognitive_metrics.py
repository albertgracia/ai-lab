"""Cognitive Metrics — in-memory runtime observable.

Thread‑safe aggregator of cognitive telemetry: context shaping,
working memory, adaptive routing.  Exposed via Live API /api/cognitive.

Design principle: keep it simple — a flat dict with atomic increments.
No external dependencies, no persistence (that's cognitive_history.py).
"""

import copy
from threading import Lock

_lock = Lock()
_COGNITIVE = {
    "context_shaping_total": 0,
    "context_shaping_errors": 0,
    "avg_shaping_latency_ms": 0,      # most recent shaping call
    "avg_context_size": 0,
    "avg_context_budget_used": 0.0,
    "last_files_used": 0,
    "last_files_names": [],
    "working_memory_sessions": 0,
    "avg_turns_per_session": 0,
    "avg_digest_size": 0,
    "adaptive_routing_total": 0,
    "adaptive_routing_fallbacks": 0,
    "routing_failovers": 0,
    "avg_routing_latency_ms": 0,
}

# ── last context debug snapshot ────────────────────────────────────────
_last_context = {}


def increment(key: str, value: int = 1):
    with _lock:
        if key in _COGNITIVE:
            _COGNITIVE[key] += value


def set_metric(key: str, value):
    with _lock:
        if key in _COGNITIVE:
            _COGNITIVE[key] = value


def store_context_debug(data: dict):
    """Store last context shaping debug info."""
    global _last_context
    with _lock:
        _last_context = copy.deepcopy(data)


def get_context_debug() -> dict:
    with _lock:
        return copy.deepcopy(_last_context)


def snapshot() -> dict:
    with _lock:
        return copy.deepcopy(_COGNITIVE)


def reset():
    global _COGNITIVE
    with _lock:
        for key in _COGNITIVE:
            _COGNITIVE[key] = 0 if isinstance(_COGNITIVE[key], (int, float)) else []
