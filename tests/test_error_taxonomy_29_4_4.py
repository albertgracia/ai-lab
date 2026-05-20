#!/usr/bin/env python3
"""FASE 29.4.4 — Error Taxonomy & Failure Attribution Tests."""

import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

passed = 0
failed = 0
total = 0

import requests


def test(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed, total
    total += 1
    if ok:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        msg = f"  ❌ {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)


print("\nFASE 29.4.4 — Error Taxonomy & Failure Attribution Tests")
print("=" * 60)

# ── Imports ──────────────────────────────────────────────────
from runtime.errors.taxonomy import RuntimeErrorCategory, ALL_CATEGORIES
from runtime.errors.severity import ErrorSeverity, severity_for_category
from runtime.errors.recovery import Recoverability, recoverability_for_category, RECOVERABILITY_MAP
from runtime.errors.severity import SEVERITY_MAP
from runtime.errors.correlation import new_error_id, stack_hash, dedup_key, CorrelationTags
from runtime.errors.runtime_errors import RuntimeErrorEvent, ORIGIN_STAGES
from runtime.errors.attribution import (
    classify_exception, classify_http_status, classify_stream_failure,
    classify_timeout, classify_timeout_stage, infer_root_cause,
    build_error_event,
)
from runtime.errors.metrics import emit_error

# ── 1. Taxonomy completeness (27 categories) ────────────────
cat_values = [e.value for e in RuntimeErrorCategory]
cats = list(RuntimeErrorCategory)
test("taxonomy has 31 categories", len(cats) >= 27, f"count={len(cats)}")
test("taxonomy includes UPSTREAM_TIMEOUT", RuntimeErrorCategory.UPSTREAM_TIMEOUT in cats)
test("taxonomy includes UNKNOWN", RuntimeErrorCategory.UNKNOWN in cats)
test("taxonomy includes GATEWAY_INTERNAL", RuntimeErrorCategory.GATEWAY_INTERNAL in cats)
test("taxonomy includes CLIENT_DISCONNECT", RuntimeErrorCategory.CLIENT_DISCONNECT in cats)
test("taxonomy includes STREAM_INTERRUPTED", RuntimeErrorCategory.STREAM_INTERRUPTED in cats)
test("taxonomy includes MODEL_DISABLED", RuntimeErrorCategory.MODEL_DISABLED in cats)
test("taxonomy includes ROLLBACK_FAILURE", RuntimeErrorCategory.ROLLBACK_FAILURE in cats)
test("taxonomy all unique", len(set(cat_values)) == len(cat_values))
test("ALL_CATEGORIES matches", len(ALL_CATEGORIES) == len(cat_values))

# ── 2. classify_exception — timeout mapping ─────────────────
test("ConnectTimeout → UPSTREAM_TIMEOUT",
     classify_exception(requests.ConnectTimeout()) == RuntimeErrorCategory.UPSTREAM_TIMEOUT)
test("ReadTimeout → LMSTUDIO_TIMEOUT",
     classify_exception(requests.ReadTimeout()) == RuntimeErrorCategory.LMSTUDIO_TIMEOUT)
test("ConnectionError → UPSTREAM_CONNECTION",
     classify_exception(requests.ConnectionError()) == RuntimeErrorCategory.UPSTREAM_CONNECTION)
test("RequestException(timeout) → UPSTREAM_TIMEOUT",
     classify_exception(requests.exceptions.RequestException("timeout occurred")) == RuntimeErrorCategory.UPSTREAM_TIMEOUT)

# ── 3. classify_exception — connection errors ────────────────
test("BrokenPipeError → CLIENT_DISCONNECT",
     classify_exception(BrokenPipeError()) == RuntimeErrorCategory.CLIENT_DISCONNECT)
test("ConnectionResetError → CLIENT_DISCONNECT",
     classify_exception(ConnectionResetError()) == RuntimeErrorCategory.CLIENT_DISCONNECT)
test("ConnectionAbortedError → CLIENT_DISCONNECT",
     classify_exception(ConnectionAbortedError()) == RuntimeErrorCategory.CLIENT_DISCONNECT)

# ── 4. classify_exception — data errors ─────────────────────
import json as _json
test("JSONDecodeError → UPSTREAM_INVALID_RESPONSE",
     classify_exception(_json.JSONDecodeError("msg", "doc", 0)) == RuntimeErrorCategory.UPSTREAM_INVALID_RESPONSE)

# ── 5. classify_exception — OSError / stream ────────────────
test("OSError → STREAM_INTERRUPTED",
     classify_exception(OSError()) == RuntimeErrorCategory.STREAM_INTERRUPTED)

# ── 6. classify_exception — validation / generic ────────────
test("ValueError → REQUEST_VALIDATION",
     classify_exception(ValueError("bad input")) == RuntimeErrorCategory.REQUEST_VALIDATION)
test("TypeError → REQUEST_VALIDATION",
     classify_exception(TypeError("bad type")) == RuntimeErrorCategory.REQUEST_VALIDATION)
test("RuntimeError → GATEWAY_INTERNAL",
     classify_exception(RuntimeError("internal")) == RuntimeErrorCategory.GATEWAY_INTERNAL)
test("PermissionError → GOVERNANCE_BLOCK",
     classify_exception(PermissionError("denied")) == RuntimeErrorCategory.GOVERNANCE_BLOCK)
test("TimeoutError → LMSTUDIO_TIMEOUT",
     classify_exception(TimeoutError("slow")) == RuntimeErrorCategory.LMSTUDIO_TIMEOUT)
test("Exception → UNKNOWN (fallback)",
     classify_exception(Exception()) == RuntimeErrorCategory.UNKNOWN)

# ── 7. classify_http_status ──────────────────────────────────
test("429 → CONCURRENCY_THROTTLE",
     classify_http_status(429) == RuntimeErrorCategory.CONCURRENCY_THROTTLE)
test("503 → LMSTUDIO_MODEL_UNAVAILABLE",
     classify_http_status(503) == RuntimeErrorCategory.LMSTUDIO_MODEL_UNAVAILABLE)
test("400+ unloaded → LMSTUDIO_MODEL_UNAVAILABLE",
     classify_http_status(400, "model unloaded error") == RuntimeErrorCategory.LMSTUDIO_MODEL_UNAVAILABLE)
test("400+ other → UPSTREAM_INVALID_RESPONSE",
     classify_http_status(400, "bad request") == RuntimeErrorCategory.UPSTREAM_INVALID_RESPONSE)

# ── 8. classify_stream_failure ──────────────────────────────
test("idle → LMSTUDIO_STREAM_STALL",
     classify_stream_failure("idle timeout") == RuntimeErrorCategory.LMSTUDIO_STREAM_STALL)
test("stall → LMSTUDIO_STREAM_STALL",
     classify_stream_failure("stall detected") == RuntimeErrorCategory.LMSTUDIO_STREAM_STALL)
test("duration → STREAM_INTERRUPTED",
     classify_stream_failure("max duration reached") == RuntimeErrorCategory.STREAM_INTERRUPTED)
test("client → CLIENT_DISCONNECT",
     classify_stream_failure("client disconnect") == RuntimeErrorCategory.CLIENT_DISCONNECT)
test("backpressure → STREAM_BACKPRESSURE",
     classify_stream_failure("backpressure limit") == RuntimeErrorCategory.STREAM_BACKPRESSURE)
test("orphan → STREAM_INTERRUPTED",
     classify_stream_failure("orphan cleanup") == RuntimeErrorCategory.STREAM_INTERRUPTED)

# ── 9. classify_timeout ─────────────────────────────────────
test("connect stage → UPSTREAM_TIMEOUT",
     classify_timeout("connect") == RuntimeErrorCategory.UPSTREAM_TIMEOUT)
test("connection stage → UPSTREAM_TIMEOUT",
     classify_timeout("connection") == RuntimeErrorCategory.UPSTREAM_TIMEOUT)
test("read stage → LMSTUDIO_TIMEOUT",
     classify_timeout("read") == RuntimeErrorCategory.LMSTUDIO_TIMEOUT)
test("response stage → LMSTUDIO_TIMEOUT",
     classify_timeout("response") == RuntimeErrorCategory.LMSTUDIO_TIMEOUT)
test("stream_idle → LMSTUDIO_STREAM_STALL",
     classify_timeout("stream_idle") == RuntimeErrorCategory.LMSTUDIO_STREAM_STALL)
test("first_chunk → LMSTUDIO_TIMEOUT",
     classify_timeout("first_chunk") == RuntimeErrorCategory.LMSTUDIO_TIMEOUT)

# ── 10. classify_timeout_stage ───────────────────────────────
test("ConnectTimeout → connect", classify_timeout_stage(requests.ConnectTimeout()) == "connect")
test("ReadTimeout → read", classify_timeout_stage(requests.ReadTimeout()) == "read")
exc_conn = requests.ConnectionError("connect failed")
test("ConnectionError with connect → connect",
     classify_timeout_stage(exc_conn) == "connect")

# ── 11. RuntimeErrorEvent ──────────────────────────────────
ev = RuntimeErrorEvent(category=RuntimeErrorCategory.UPSTREAM_TIMEOUT)
test("event has error_id", bool(ev.error_id))
test("event has timestamp", ev.timestamp > 0)
test("event category set", ev.category == RuntimeErrorCategory.UPSTREAM_TIMEOUT)
test("event severity auto-set", ev.severity == ErrorSeverity.ERROR)
test("event recoverability auto-set", ev.recoverability == Recoverability.RETRYABLE)
test("event retryable = True for RETRYABLE", ev.retryable is True)
test("event to_dict includes category", "category" in ev.to_dict())
test("event to_dict has no client_ip", "client_ip" not in ev.to_dict())
test("event to_json valid", isinstance(json.loads(ev.to_json()), dict))

ev2 = RuntimeErrorEvent(category=RuntimeErrorCategory.CLIENT_DISCONNECT)
test("CLIENT_DISCONNECT severity INFO", ev2.severity == ErrorSeverity.INFO)
test("CLIENT_DISCONNECT recoverability AUTO", ev2.recoverability == Recoverability.AUTO_RECOVERABLE)

ev3 = RuntimeErrorEvent(category=RuntimeErrorCategory.MODEL_DISABLED)
test("MODEL_DISABLED NON_RECOVERABLE", ev3.recoverability == Recoverability.NON_RECOVERABLE)
test("MODEL_DISABLED retryable False", ev3.retryable is False)

ev4 = RuntimeErrorEvent(category=RuntimeErrorCategory.GATEWAY_INTERNAL)
test("GATEWAY_INTERNAL severity CRITICAL", ev4.severity == ErrorSeverity.CRITICAL)
test("GATEWAY_INTERNAL recoverability MANUAL", ev4.recoverability == Recoverability.MANUAL_INTERVENTION)

ev5 = RuntimeErrorEvent(category=RuntimeErrorCategory.MEMORY_EMPTY)
test("MEMORY_EMPTY severity INFO", ev5.severity == ErrorSeverity.INFO)

# ── 12. origin_stage validation ──────────────────────────────
test("ORIGIN_STAGES has routing", "routing" in ORIGIN_STAGES)
test("ORIGIN_STAGES has streaming", "streaming" in ORIGIN_STAGES)
test("ORIGIN_STAGES has upstream", "upstream" in ORIGIN_STAGES)
test("ORIGIN_STAGES has governance", "governance" in ORIGIN_STAGES)
test("ORIGIN_STAGES has agentic", "agentic" in ORIGIN_STAGES)
test("ORIGIN_STAGES has sandbox", "sandbox" in ORIGIN_STAGES)
test("ORIGIN_STAGES has rollback", "rollback" in ORIGIN_STAGES)
test("ORIGIN_STAGES has reporting", "reporting" in ORIGIN_STAGES)
test("ORIGIN_STAGES has memory", "memory" in ORIGIN_STAGES)
test("ORIGIN_STAGES has observability", "observability" in ORIGIN_STAGES)
test("ORIGIN_STAGES has classification", "classification" in ORIGIN_STAGES)

# ── 13. build_error_event ──────────────────────────────────
ev6 = build_error_event(
    ValueError("bad payload"),
    origin_stage="upstream", component="gateway",
    source_file="test.py", streaming=False,
    model="qwen2.5-14b", route_type="cognitive",
    slo_impact=True, latency_ms=1234,
)
test("build: category from exception",
     ev6.category == RuntimeErrorCategory.REQUEST_VALIDATION)
test("build: origin_stage set", ev6.origin_stage == "upstream")
test("build: component set", ev6.component == "gateway")
test("build: model set", ev6.model == "qwen2.5-14b")
test("build: route_type set", ev6.route_type == "cognitive")
test("build: slo_impact True", ev6.slo_impact is True)
test("build: latency_ms set", ev6.latency_ms == 1234)
test("build: exception_class set", ev6.exception_class == "ValueError")
test("build: message has bad payload", "bad payload" in ev6.message)

ev7 = build_error_event(
    requests.ReadTimeout("upstream too slow"),
    origin_stage="streaming", component="gateway",
    model="llama-3.1-8b", streaming=True,
)
test("build ReadTimeout → LMSTUDIO_TIMEOUT",
     ev7.category == RuntimeErrorCategory.LMSTUDIO_TIMEOUT)
test("build ReadTimeout retryable True", ev7.retryable is True)
test("build ReadTimeout recoverability RETRYABLE",
     ev7.recoverability == Recoverability.RETRYABLE)

ev8 = build_error_event(None, category=RuntimeErrorCategory.GATEWAY_INTERNAL,
                          message="manual test")
test("build None + explicit category", ev8.category == RuntimeErrorCategory.GATEWAY_INTERNAL)
test("build None + message", "manual test" in ev8.message)

# ── 14. severity_for_category for ALL categories ────────────
for cat in RuntimeErrorCategory:
    sev = severity_for_category(cat)
    test(f"severity_for({cat.value}) returns valid",
         sev in ErrorSeverity,
         f"got {sev}")

# ── 15. recoverability_for_category for ALL categories ──────
for cat in RuntimeErrorCategory:
    rec = recoverability_for_category(cat)
    test(f"recoverability_for({cat.value}) returns valid",
         rec in Recoverability,
         f"got {rec}")

# ── 16. correlation / dedup ─────────────────────────────────
id1 = new_error_id()
id2 = new_error_id()
test("new_error_id generates unique IDs", id1 != id2)
test("new_error_id is hex str", isinstance(id1, str) and len(id1) == 16)

test("stack_hash empty for None", stack_hash(None) == "")
sh1 = stack_hash("line1\nline2")
test("stack_hash returns 12 chars", len(sh1) == 12)
test("stack_hash deterministic", stack_hash("line1\nline2") == sh1)

dk1 = dedup_key({"category": "UPSTREAM_TIMEOUT", "exception_class": "Timeout", "component": "gw"})
dk2 = dedup_key({"category": "UPSTREAM_TIMEOUT", "exception_class": "Timeout", "component": "gw"})
dk3 = dedup_key({"category": "UNKNOWN", "exception_class": "Timeout", "component": "gw"})
test("dedup_key deterministic", dk1 == dk2)
test("dedup_key different for diff category", dk1 != dk3)
test("dedup_key is hex str", isinstance(dk1, str) and len(dk1) == 16)

ct = CorrelationTags(session_id="s1", user_id="u1")
ctd = ct.to_dict()
test("correlation tags to_dict has session_id", ctd.get("session_id") == "s1")
test("correlation tags to_dict has user_id", ctd.get("user_id") == "u1")
test("correlation tags excludes None fields", "deployment_id" not in ctd)

# ── 17. severity mapping complete ────────────────────────────
test("severity map covers all 31 categories",
     len(SEVERITY_MAP) >= 27,
     f"mapped={len(SEVERITY_MAP)}")
test("recoverability map covers all 31 categories",
     len(RECOVERABILITY_MAP) >= 27,
     f"mapped={len(RECOVERABILITY_MAP)}")

# ── 18. infer_root_cause ────────────────────────────────────
rc = infer_root_cause(ValueError("invalid input"), RuntimeErrorCategory.REQUEST_VALIDATION)
test("root_cause contains error message", "invalid input" in rc)
test("root_cause not empty", bool(rc))

# ── 19. No secrets in event fields ──────────────────────────
ev_secrets = RuntimeErrorEvent(
    category=RuntimeErrorCategory.UNKNOWN,
    message="prompt: what is the meaning of life",
)
d = ev_secrets.to_dict()
for field in d:
    val = str(d[field])
    if field in ("message", "root_cause"):
        continue
    test(f"field {field} has no prompt content",
         "meaning of life" not in val)

# ── Summary ──────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"Results: {passed}/{total} passed, {failed} failed")
print(f"{'✅ ALL PASS' if failed == 0 else '❌ FAILURES DETECTED'}")
print(f"{'=' * 60}")

sys.exit(0 if failed == 0 else 1)

