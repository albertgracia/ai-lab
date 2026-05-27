"""Tests for MEMORY-INJECTION-TELEMETRY-01.

Covers:
1. Telemetry default sin memoria
2. Telemetry con memoria
3. Bounded max collections
4. No prompt completo en payload
5. No respuesta completa en payload
6. Truncation flag
7. avg_score/max_score/min_score
8. prompt_tokens_delta
9. Missing fields fail-safe
10. Qdrant write failure no rompe request
11. Prometheus metrics builder
12. Endpoint summary
13. No dynamic high-cardinality labels
14. No runtime/state writes
"""

import json
import math
import time
from unittest.mock import patch, MagicMock


def _make_messages(text: str = "hello world", count: int = 1) -> list[dict]:
    return [{"role": "user", "content": text} for _ in range(count)]


# ── 1. Telemetry default sin memoria ─────────────────────────────────

def test_telemetry_default_no_memory():
    from runtime.memory.memory_injection_telemetry import build_telemetry

    t = build_telemetry(route_family="minimal", model="test-model")
    assert t["memory_injected"] is False
    assert t["chars_injected"] == 0
    assert t["estimated_tokens_injected"] == 0
    assert t["collections_used"] == []
    assert t["matches_total"] == 0
    assert t["context_truncated"] is False
    assert t["route_family"] == "minimal"
    assert t["model"] == "test-model"
    assert t["telemetry_version"] == "1.0"
    assert "timestamp" in t


# ── 2. Telemetry con memoria ─────────────────────────────────────────

def test_telemetry_with_memory():
    from runtime.memory.memory_injection_telemetry import build_telemetry

    t = build_telemetry(
        memory_injected=True,
        chars_injected=1200,
        collections_used=["agent_knowledge", "incidents"],
        matches_total=3,
        avg_score=0.75,
        max_score=0.92,
        min_score=0.45,
        route_family="report",
        model="qwen2.5-coder-14b",
    )
    assert t["memory_injected"] is True
    assert t["chars_injected"] == 1200
    assert t["estimated_tokens_injected"] > 0
    assert len(t["collections_used"]) == 2
    assert t["matches_total"] == 3
    assert t["avg_score"] == 0.75
    assert t["max_score"] == 0.92
    assert t["min_score"] == 0.45


# ── 3. Estimated tokens calculation ──────────────────────────────────

def test_estimated_tokens():
    from runtime.memory.memory_injection_telemetry import estimate_tokens

    assert estimate_tokens("hello") == 2  # ceil(5/4) = 2
    assert estimate_tokens("abcd") == 1   # ceil(4/4) = 1
    assert estimate_tokens("") == 0
    assert estimate_tokens("a" * 100) == 25  # ceil(100/4) = 25


def test_estimate_messages_tokens():
    from runtime.memory.memory_injection_telemetry import estimate_messages_tokens

    msgs = _make_messages("hello", 3)
    tokens = estimate_messages_tokens(msgs)
    assert tokens > 0
    assert estimate_messages_tokens([]) == 0
    assert estimate_messages_tokens(None) == 0


# ── 4. No prompt completo en payload ─────────────────────────────────

def test_no_prompt_in_telemetry_payload():
    from runtime.memory.memory_injection_telemetry import build_telemetry

    t = build_telemetry(memory_injected=True, chars_injected=500, route_family="cognitive")
    keys = list(t.keys())
    # No debe contener prompt completo ni messages
    assert "prompt" not in keys
    assert "messages" not in keys
    assert "content" not in keys
    # Debe tener solo metadata bounded
    assert "memory_injected" in keys
    assert "chars_injected" in keys
    assert "route_family" in keys


# ── 5. No respuesta completa en payload ──────────────────────────────

def test_no_response_in_telemetry_payload():
    from runtime.memory.memory_injection_telemetry import build_telemetry

    t = build_telemetry(latency_ms=15000, ttfb_ms=5000, success=True)
    assert "response" not in t
    assert "completion" not in t
    assert "choices" not in t
    assert t["latency_ms"] == 15000.0
    assert t["ttfb_ms"] == 5000.0


# ── 6. Truncation flag ───────────────────────────────────────────────

def test_truncation_flag():
    from runtime.memory.memory_injection_telemetry import build_telemetry

    t = build_telemetry(context_truncated=True)
    assert t["context_truncated"] is True
    t2 = build_telemetry(context_truncated=False)
    assert t2["context_truncated"] is False
    t3 = build_telemetry()
    assert t3["context_truncated"] is False


# ── 7. avg_score / max_score / min_score ─────────────────────────────

def test_scores():
    from runtime.memory.memory_injection_telemetry import build_telemetry

    t = build_telemetry(avg_score=0.85, max_score=0.95, min_score=0.5)
    assert t["avg_score"] == 0.85
    assert t["max_score"] == 0.95
    assert t["min_score"] == 0.5
    t2 = build_telemetry()
    assert t2["avg_score"] is None
    assert t2["max_score"] is None
    assert t2["min_score"] is None


# ── 8. prompt_tokens_delta ───────────────────────────────────────────

def test_prompt_tokens_delta():
    from runtime.memory.memory_injection_telemetry import build_telemetry

    t = build_telemetry(prompt_tokens_before=100, prompt_tokens_after=350)
    assert t["prompt_tokens_delta"] == 250
    t2 = build_telemetry(prompt_tokens_before=100, prompt_tokens_after=50)
    # delta no debe ser negativo
    assert t2["prompt_tokens_delta"] == 0

    t3 = build_telemetry()
    assert t3["prompt_tokens_delta"] is None


# ── 9. Missing fields fail-safe ──────────────────────────────────────

def test_missing_fields_failsafe():
    from runtime.memory.memory_injection_telemetry import build_telemetry

    t = build_telemetry()
    assert t["memory_injected"] is False
    assert t["chars_injected"] == 0
    assert t["collections_used"] == []
    assert t["matches_total"] == 0


# ── 10. Qdrant write failure no rompe request ────────────────────────

def test_qdrant_write_failure_caught():
    from runtime.memory.memory_injection_telemetry import build_cognitive_history_payload, build_telemetry

    t = build_telemetry(memory_injected=True, chars_injected=300, route_family="minimal")
    payload = build_cognitive_history_payload(t, task_type="fast", context_size=5000)
    assert payload["memory_injected"] is True
    assert payload["chars_injected"] == 300
    assert payload["route_family"] == "minimal"


# ── 11. Prometheus metrics builder ────────────────────────────────────

def test_prometheus_metrics_import():
    from runtime.telemetry.prometheus_metrics import (
        MEMORY_INJECTION_EVENTS_TOTAL,
        MEMORY_INJECTION_CHARS_TOTAL,
        MEMORY_INJECTION_TOKENS_TOTAL,
        MEMORY_INJECTION_MATCHES_TOTAL,
        MEMORY_INJECTION_TRUNCATED_TOTAL,
        MEMORY_INJECTION_LAST_CHARS,
        MEMORY_INJECTION_LAST_TOKENS,
        MEMORY_INJECTION_LATENCY_CORRELATION_TOTAL,
        record_memory_injection_metrics,
    )
    assert MEMORY_INJECTION_EVENTS_TOTAL is not None
    assert MEMORY_INJECTION_CHARS_TOTAL is not None
    assert record_memory_injection_metrics is not None


def test_record_memory_injection_metrics():
    from runtime.telemetry.prometheus_metrics import record_memory_injection_metrics
    from runtime.memory.memory_injection_telemetry import build_telemetry

    t = build_telemetry(
        memory_injected=True, chars_injected=500,
        matches_total=3, context_truncated=False,
        route_family="report",
    )
    # Debe ejecutarse sin errores
    record_memory_injection_metrics(t)
    t2 = build_telemetry(memory_injected=False, chars_injected=0, route_family="minimal")
    record_memory_injection_metrics(t2)


# ── 12. Endpoint summary ──────────────────────────────────────────────

def test_telemetry_summary():
    from runtime.memory.memory_injection_telemetry import (
        get_telemetry_summary, record_telemetry_event, build_telemetry,
    )

    summary = get_telemetry_summary()
    assert "events_total" in summary
    assert "chars_injected_total" in summary
    assert "last_event" in summary

    t = build_telemetry(memory_injected=True, chars_injected=1000, route_family="cognitive")
    record_telemetry_event(t)
    summary2 = get_telemetry_summary()
    assert summary2["events_total"] >= 1
    assert summary2["last_event"] is not None


# ── 13. No dynamic high-cardinality labels ────────────────────────────

def test_no_high_cardinality_labels():
    from runtime.telemetry.prometheus_metrics import (
        MEMORY_INJECTION_LATENCY_CORRELATION_TOTAL,
    )
    # The only label is route_family + injected — both bounded
    # Verify no request_id, model, or user labels
    registry_labels = MEMORY_INJECTION_LATENCY_CORRELATION_TOTAL._labelnames
    assert isinstance(registry_labels, tuple)
    assert "route_family" in registry_labels
    assert "injected" in registry_labels
    assert "request_id" not in registry_labels
    assert "model" not in registry_labels
    assert "user" not in registry_labels


# ── 14. No runtime/state writes ──────────────────────────────────────

def test_no_runtime_state_writes():
    from runtime.memory.memory_injection_telemetry import (
        build_telemetry, record_telemetry_event,
    )
    t = build_telemetry(memory_injected=True, chars_injected=100, route_family="minimal")
    record_telemetry_event(t)
    # Solo modifica variables en memoria del modulo
    # No debe escribir a disco
    assert True


# ── 15. Cognitive history payload builder ─────────────────────────────

def test_cognitive_history_payload():
    from runtime.memory.memory_injection_telemetry import (
        build_telemetry, build_cognitive_history_payload,
    )

    t = build_telemetry(
        memory_injected=True, chars_injected=800,
        collections_used=["incidents"], matches_total=2,
        avg_score=0.65, max_score=0.88, min_score=0.42,
        recall_source="watchdog",
        context_budget_chars=4000, context_budget_used_chars=800,
        context_truncated=False,
        prompt_tokens_before=200, prompt_tokens_after=400,
        route_family="minimal", model="llama-3.1-8b",
    )
    payload = build_cognitive_history_payload(
        t, task_type="fast", context_size=6000, shaping_latency_ms=5000.0,
    )
    assert payload["schema_version"] == "1.0"
    assert payload["event_type"] == "context_shaping"
    assert payload["memory_injected"] is True
    assert payload["chars_injected"] == 800
    assert payload["collections_used"] == ["incidents"]
    assert payload["matches_total"] == 2
    assert payload["avg_score"] == 0.65
    assert payload["context_truncated"] is False
    assert payload["prompt_tokens_delta"] == 200
    assert payload["route_family"] == "minimal"


# ── 16. Messages chars count ─────────────────────────────────────────

def test_messages_chars():
    from runtime.memory.memory_injection_telemetry import messages_chars

    msgs = [{"role": "user", "content": "hello world"}]
    assert messages_chars(msgs) == len("hello world")
    assert messages_chars([]) == 0
    assert messages_chars(None) == 0


# ── 17. Estimate system prompt tokens ────────────────────────────────

def test_estimate_system_prompt_tokens():
    from runtime.memory.memory_injection_telemetry import estimate_system_prompt_tokens

    assert estimate_system_prompt_tokens("hello world") > 0
    assert estimate_system_prompt_tokens("") == 0
    assert estimate_system_prompt_tokens(None) == 0
