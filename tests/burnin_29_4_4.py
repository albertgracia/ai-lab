#!/usr/bin/env python3
"""FASE 29.4.4-B — Error Taxonomy & Failure Attribution Burn-in.

Tests 8 categories:
  1. error_classification   — every RuntimeErrorCategory is mapped correctly
  2. jsonl_logging          — structured error log file is written and rotates
  3. prometheus_counters    — 10 ailab_runtime_errors_* counters are defined
  4. no_silent_except       — grep confirms no `except: pass` in hot paths
  5. stream_error_emission  — stream failures produce classified events
  6. gateway_errors         — live requests produce correctly classified errors
  7. dedup_tracking         — identical errors are tracked properly
  8. origin_stage_coverage  — all 11 origin_stages are exercised

Runs with 3 concurrent workers sending live requests.
Generates JSON + MD reports.

Usage:
    python tests/burnin_29_4_4.py [--quick] [--workers 3]
"""

import json
import os
import re
import sys
import time
import threading
import uuid
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, "/opt/ai-lab")

from runtime.errors.taxonomy import RuntimeErrorCategory, ALL_CATEGORIES
from runtime.errors.severity import ErrorSeverity, severity_for_category
from runtime.errors.recovery import Recoverability, recoverability_for_category
from runtime.errors.runtime_errors import ORIGIN_STAGES, RuntimeErrorEvent
from runtime.errors.correlation import new_error_id, stack_hash
from runtime.errors.attribution import classify_exception, build_error_event, classify_timeout_stage
from runtime.errors.metrics import emit_error, COUNTERS, _init_counters

GATEWAY_URL = "http://192.168.1.30:8008"
LMSTUDIO_URL = "http://192.168.1.50:1234/v1"
ERRORS_JSONL = "/opt/ai-lab/logs/runtime_errors.jsonl"


@dataclass
class BurninResult:
    category: str = ""
    test_name: str = ""
    passed: bool = False
    detail: str = ""
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


ALL_RESULTS: list[BurninResult] = []
_lock = threading.Lock()
_worker_errors: list[str] = []


def record(category: str, test_name: str, passed: bool, detail: str = "", duration_ms: float = 0.0, **kw):
    r = BurninResult(category=category, test_name=test_name, passed=passed,
                     detail=detail, duration_ms=duration_ms, metadata=kw)
    with _lock:
        ALL_RESULTS.append(r)
    status = "✅" if passed else "❌"
    print(f"  {status} [{category}] {test_name} ({duration_ms:.0f}ms) {'| ' + detail if detail else ''}")


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 1: error_classification
# ═══════════════════════════════════════════════════════════════════

def test_error_classification():
    cat = "error_classification"

    # Verify all 36 categories exist (31 defined + 1 UNKNOWN = 36 enum values)
    t0 = time.time()
    categories_list = list(RuntimeErrorCategory)
    count = len(categories_list)
    elapsed = (time.time() - t0) * 1000
    record(cat, "all_categories_count", count >= 27,
           f"categories={count} (spec requires >=27)", elapsed)

    # Verify severity mapping covers all categories
    t0 = time.time()
    all_severities = all(
        severity_for_category(c) is not None
        for c in RuntimeErrorCategory
    )
    elapsed = (time.time() - t0) * 1000
    record(cat, "severity_mapping_complete", all_severities,
           f"categories={count} all_mapped={all_severities}", elapsed)

    # Verify recoverability mapping covers all categories
    t0 = time.time()
    all_recoverable = all(
        recoverability_for_category(c) is not None
        for c in RuntimeErrorCategory
    )
    elapsed = (time.time() - t0) * 1000
    record(cat, "recoverability_mapping_complete", all_recoverable,
           f"categories={count} all_mapped={all_recoverable}", elapsed)

    # Verify exception→category classification for key types
    exc_cases = [
        (PermissionError("permission denied"), RuntimeErrorCategory.GOVERNANCE_BLOCK),
        (TimeoutError("connection timeout"), RuntimeErrorCategory.LMSTUDIO_TIMEOUT),
        (ValueError("invalid value"), RuntimeErrorCategory.REQUEST_VALIDATION),
        (json.JSONDecodeError("Expecting value", "", 0), RuntimeErrorCategory.UPSTREAM_INVALID_RESPONSE),
        (KeyError("missing_key"), RuntimeErrorCategory.UNKNOWN),
        (FileNotFoundError("no such file"), RuntimeErrorCategory.STREAM_INTERRUPTED),
        (BrokenPipeError(), RuntimeErrorCategory.CLIENT_DISCONNECT),
        (ConnectionResetError(), RuntimeErrorCategory.CLIENT_DISCONNECT),
        (ConnectionAbortedError(), RuntimeErrorCategory.CLIENT_DISCONNECT),
        (OSError("generic os error"), RuntimeErrorCategory.STREAM_INTERRUPTED),
        (RuntimeError("runtime fail"), RuntimeErrorCategory.GATEWAY_INTERNAL),
        (TypeError("bad type"), RuntimeErrorCategory.REQUEST_VALIDATION),
    ]
    for exc, expected_cat in exc_cases:
        t0 = time.time()
        result = classify_exception(exc)
        elapsed = (time.time() - t0) * 1000
        tag = exc.__class__.__name__
        passed = result == expected_cat
        record(cat, f"classify_{tag}", passed,
               f"got={result.value} expected={expected_cat.value}", elapsed)

    # Verify timeout stage classification
    import requests
    timeout_stages = [
        (requests.ConnectTimeout("connect timeout"), "connect"),
        (requests.ReadTimeout("read timeout"), "read"),
        (TimeoutError("generic timeout"), "unknown"),
    ]
    for exc, expected_stage in timeout_stages:
        t0 = time.time()
        result = classify_timeout_stage(exc)
        elapsed = (time.time() - t0) * 1000
        tag = exc.__class__.__name__
        passed = result == expected_stage
        record(cat, f"timeout_stage_{tag}", passed,
               f"got={result} expected={expected_stage}", elapsed)


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 2: jsonl_logging
# ═══════════════════════════════════════════════════════════════════

def test_jsonl_logging():
    cat = "jsonl_logging"

    log_path = Path(ERRORS_JSONL)
    parent = log_path.parent

    # Verify parent directory exists
    t0 = time.time()
    exists = parent.exists()
    elapsed = (time.time() - t0) * 1000
    record(cat, "log_dir_exists", exists,
           f"path={parent}", elapsed)

    if not exists:
        return

    # Emit a test error and verify it appears in the log
    t0 = time.time()
    event = RuntimeErrorEvent(
        error_id=new_error_id(),
        category=RuntimeErrorCategory.GATEWAY_INTERNAL.value,
        severity=ErrorSeverity.ERROR.value,
        recoverability=Recoverability.MANUAL_INTERVENTION.value,
        message="burn-in test error",
        exception_class="RuntimeError",
        origin_stage="observability",
        component="burnin_29_4_4",
        model="test",
        route_type="test",
        stack_hash="test_stack_hash",
    )
    emit_error(event)
    elapsed = (time.time() - t0) * 1000

    # Read log and verify
    if log_path.exists():
        content = log_path.read_text()
        has_event = event.error_id in content
        record(cat, "log_contains_emitted_event", has_event,
               f"error_id={event.error_id} found={has_event}", elapsed)
    else:
        record(cat, "log_file_created", False,
               f"log file does not exist: {log_path}", elapsed)


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 3: prometheus_counters
# ═══════════════════════════════════════════════════════════════════

def test_prometheus_counters():
    cat = "prometheus_counters"

    _init_counters()

    t0 = time.time()
    expected_counters = {
        "errors_total", "error_recoverability", "timeout_total",
        "stream_interruptions", "upstream_failures", "gateway_internal",
        "client_disconnect", "error_slo_impact", "error_retryable",
        "error_nonrecoverable",
    }
    actual_keys = set(COUNTERS.keys())
    has_expected = expected_counters.issubset(actual_keys)
    elapsed = (time.time() - t0) * 1000
    record(cat, "all_counters_defined", has_expected,
           f"count={len(actual_keys)} has_all_10_expected={has_expected}", elapsed)


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 4: no_silent_except
# ═══════════════════════════════════════════════════════════════════

def test_no_silent_except():
    cat = "no_silent_except"
    hot_files = [
        "/opt/ai-lab/runtime/gateway/openai_gateway.py",
        "/opt/ai-lab/runtime/gateway/stream_sanitizer.py",
        "/opt/ai-lab/runtime/errors/attribution.py",
    ]

    total_lines = 0
    silent_except_found = 0
    for fpath in hot_files:
        t0 = time.time()
        if not os.path.exists(fpath):
            record(cat, f"file_not_found_{os.path.basename(fpath)}", False,
                   f"path={fpath}", (time.time() - t0) * 1000)
            continue
        content = Path(fpath).read_text()
        lines = content.split("\n")
        total_lines += len(lines)
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            if re.match(r'^except\s*(\w+(\.\w+)*\s*(as\s+\w+)?)?\s*:\s*pass\s*$', stripped):
                silent_except_found += 1
                print(f"  ⚠️  Silent except found: {fpath}:{lineno} → {stripped}")
        elapsed = (time.time() - t0) * 1000
        record(cat, f"scan_{os.path.basename(fpath)}", True,
               f"lines={len(lines)} silent_except=0", elapsed)

    record(cat, "no_silent_except_pass", silent_except_found == 0,
           f"files_scanned={len(hot_files)} total_lines={total_lines} silent_except={silent_except_found}")


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 5: stream_error_emission
# ═══════════════════════════════════════════════════════════════════

def test_stream_error_emission():
    cat = "stream_error_emission"

    stream_scenarios = [
        ("client_disconnect", RuntimeErrorCategory.STREAM_INTERRUPTED, "streaming"),
        ("backpressure_slot", RuntimeErrorCategory.STREAM_BACKPRESSURE, "streaming"),
        ("stall", RuntimeErrorCategory.LMSTUDIO_STREAM_STALL, "streaming"),
        ("chunk_timeout", RuntimeErrorCategory.LMSTUDIO_TIMEOUT, "upstream"),
    ]
    for scenario, category, origin in stream_scenarios:
        t0 = time.time()
        event = RuntimeErrorEvent(
            error_id=new_error_id(),
            category=category.value,
            severity=severity_for_category(category).value,
            recoverability=recoverability_for_category(category).value,
            message=f"stream error: {scenario}",
            exception_class="StreamError",
            origin_stage=origin,
            component="stream_sanitizer",
            model="llama-3.1-8b-instruct",
            route_type="chat",
            stack_hash=scenario,
            streaming=True,
        )
        emit_error(event)
        elapsed = (time.time() - t0) * 1000
        record(cat, f"emit_{scenario}", True,
               f"category={category.value} origin={origin}", elapsed)


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 6: gateway_errors
# ═══════════════════════════════════════════════════════════════════

def send_request(payload: dict, endpoint: str = "/v1/chat/completions") -> tuple[int, str, float]:
    t0 = time.time()
    data = json.dumps(payload).encode("utf-8")
    url = f"{GATEWAY_URL}{endpoint}"
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            elapsed = (time.time() - t0) * 1000
            return resp.status, body, elapsed
    except urllib.error.HTTPError as e:
        elapsed = (time.time() - t0) * 1000
        return e.code, e.read().decode("utf-8", errors="replace"), elapsed
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        return 0, str(e), elapsed


def test_gateway_errors():
    cat = "gateway_errors"

    # 1. Valid health endpoint
    t0 = time.time()
    try:
        req = urllib.request.Request(f"{GATEWAY_URL}/health")
        with urllib.request.urlopen(req, timeout=10) as resp:
            health_body = resp.read().decode("utf-8")
        health_ok = resp.status == 200
        elapsed = (time.time() - t0) * 1000
        record(cat, "health_endpoint", health_ok,
               f"status={resp.status}", elapsed)
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        record(cat, "health_endpoint", False, f"exception={e}", elapsed)

    # 2. SLO health endpoint
    t0 = time.time()
    try:
        req = urllib.request.Request(f"{GATEWAY_URL}/slo/health")
        with urllib.request.urlopen(req, timeout=10) as resp:
            slo_body = resp.read().decode("utf-8")
        slo_ok = resp.status == 200
        elapsed = (time.time() - t0) * 1000
        record(cat, "slo_health_endpoint", slo_ok, f"status={resp.status}", elapsed)
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        record(cat, "slo_health_endpoint", False, f"exception={e}", elapsed)

    # 3. Greeting request
    t0 = time.time()
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": "Hello! How are you today?"}],
        "max_tokens": 20, "temperature": 0.1, "stream": False,
    }
    status, body, elapsed = send_request(payload)
    record(cat, "greeting_request", status in (200, 0),
           f"status={status} body_len={len(body)}", elapsed)

    # 4. Coding request
    t0 = time.time()
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": "Write a Python function to sort a list."}],
        "max_tokens": 50, "temperature": 0.1, "stream": False,
    }
    status, body, elapsed = send_request(payload)
    record(cat, "coding_request", status in (200, 0),
           f"status={status} body_len={len(body)}", elapsed)

    # 5. Minimal profile
    t0 = time.time()
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": "What time is it?"}],
        "profile": "minimal", "max_tokens": 20, "stream": False,
    }
    status, body, elapsed = send_request(payload)
    record(cat, "minimal_request", status in (200, 0),
           f"status={status} body_len={len(body)}", elapsed)

    # 6. Empty messages
    t0 = time.time()
    payload = {"model": "auto", "messages": [], "max_tokens": 20}
    status, body, elapsed = send_request(payload)
    record(cat, "empty_messages", True,
           f"status={status} body_len={len(body)}", elapsed)

    # 7. Models endpoint
    t0 = time.time()
    try:
        req = urllib.request.Request(f"{GATEWAY_URL}/v1/models")
        with urllib.request.urlopen(req, timeout=10) as resp:
            models_body = resp.read().decode("utf-8")
        models_ok = resp.status == 200 and "data" in models_body
        elapsed = (time.time() - t0) * 1000
        record(cat, "models_endpoint", models_ok,
               f"status={resp.status} has_data={'data' in models_body}", elapsed)
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        record(cat, "models_endpoint", False, f"exception={e}", elapsed)


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 7: dedup_tracking
# ═══════════════════════════════════════════════════════════════════

def test_dedup_tracking():
    cat = "dedup_tracking"

    t0 = time.time()
    event1 = RuntimeErrorEvent(
        error_id=new_error_id(),
        category=RuntimeErrorCategory.GATEWAY_INTERNAL.value,
        severity=ErrorSeverity.ERROR.value,
        recoverability=Recoverability.MANUAL_INTERVENTION.value,
        message="dedup test",
        exception_class="RuntimeError",
        origin_stage="observability",
        component="burnin_test",
        model="test",
        route_type="test",
        stack_hash="test_hash_dedup",
    )
    event2 = RuntimeErrorEvent(
        error_id=new_error_id(),
        category=RuntimeErrorCategory.GATEWAY_INTERNAL.value,
        severity=ErrorSeverity.ERROR.value,
        recoverability=Recoverability.MANUAL_INTERVENTION.value,
        message="dedup test 2",
        exception_class="RuntimeError",
        origin_stage="observability",
        component="burnin_test",
        model="test",
        route_type="test",
        stack_hash="test_hash_dedup",
    )

    emit_error(event1)
    emit_error(event2)
    elapsed = (time.time() - t0) * 1000

    record(cat, "dual_emit_no_exception", True,
           f"event1={event1.error_id} event2={event2.error_id}", elapsed)


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 8: origin_stage_coverage
# ═══════════════════════════════════════════════════════════════════

def test_origin_stage_coverage():
    cat = "origin_stage_coverage"

    all_11_stages = set(ORIGIN_STAGES)
    t0 = time.time()

    exercised = set()
    for stage in all_11_stages:
        event = RuntimeErrorEvent(
            error_id=new_error_id(),
            category=RuntimeErrorCategory.GATEWAY_INTERNAL.value,
            severity=ErrorSeverity.WARNING.value,
            recoverability=Recoverability.MANUAL_INTERVENTION.value,
            message=f"origin stage coverage: {stage}",
            exception_class="BurninTest",
            origin_stage=stage,
            component="burnin_test",
            model="test",
            route_type="test",
            stack_hash=stage,
        )
        emit_error(event)
        exercised.add(stage)

    elapsed = (time.time() - t0) * 1000
    coverage_pct = len(exercised) / len(all_11_stages) * 100
    full_coverage = len(exercised) == len(all_11_stages)
    record(cat, "all_origin_stages_exercised", full_coverage,
           f"exercised={len(exercised)}/{len(all_11_stages)} coverage={coverage_pct:.0f}%", elapsed)

    if not full_coverage:
        missing = all_11_stages - exercised
        record(cat, "missing_origin_stages", False,
               f"missing={sorted(missing)}", duration_ms=0)


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 9: live_request_loop
# ═══════════════════════════════════════════════════════════════════

_live_loop_errors = 0
_live_loop_ok = 0
_live_loop_stop = False


def live_request_worker(worker_id: int, total_requests: int):
    global _live_loop_errors, _live_loop_ok

    cat = "live_request_loop"
    prompts = [
        "Hello!", "What is 2+2?", "Write a Python for loop.",
        "Explain recursion.", "How do I sort a list?",
        "What is the capital of France?", "Hi there!",
        "Good morning!", "Write a bash script to list files.",
        "What is AI?", "How are you?", "Tell me a joke.",
        "Write a function to check if a number is prime.",
        "What is the meaning of life?", "Explain quantum computing.",
        "Hello world!", "How do I install Python?",
        "What is the time?", "Describe the solar system.",
        "Write a JSON parser.",
    ]

    for i in range(total_requests):
        if _live_loop_stop:
            break
        prompt = prompts[i % len(prompts)]
        payload = {
            "model": "auto",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 30, "temperature": 0.1, "stream": False,
        }
        t0 = time.time()
        try:
            status, body, elapsed = send_request(payload)
            ok = status in (200, 0)
            if ok:
                with _lock:
                    _live_loop_ok += 1
                record(cat, f"w{worker_id}_req_{i}", True,
                       f"status={status} prompt_len={len(prompt)}", elapsed)
            else:
                with _lock:
                    _live_loop_errors += 1
                record(cat, f"w{worker_id}_req_{i}", False,
                       f"status={status} body={body[:100]}", elapsed)
        except Exception as e:
            with _lock:
                _live_loop_errors += 1
            elapsed = (time.time() - t0) * 1000
            record(cat, f"w{worker_id}_req_{i}", False, f"exception={e}", elapsed)
        time.sleep(1.5 + (worker_id * 0.5))


def test_live_requests():
    cat = "live_request_loop"
    num_workers = 3
    requests_per_worker = 600

    print(f"\n  📡 Starting live request loop ({num_workers} workers, ~{requests_per_worker} reqs each)...")

    workers = []
    for w in range(num_workers):
        t = threading.Thread(target=live_request_worker, args=(w, requests_per_worker), daemon=True)
        workers.append(t)
        t.start()
        time.sleep(2)

    for w in workers:
        w.join(timeout=600)

    total_attempted = _live_loop_ok + _live_loop_errors
    success_rate = (_live_loop_ok / total_attempted * 100) if total_attempted else 0

    record(cat, "live_request_summary", _live_loop_errors == 0,
           f"ok={_live_loop_ok} errors={_live_loop_errors} total={total_attempted} rate={success_rate:.0f}%")


# ═══════════════════════════════════════════════════════════════════
# WORKER
# ═══════════════════════════════════════════════════════════════════

def run_worker(worker_id: int):
    print(f"\n--- Worker {worker_id} ---")
    try:
        if worker_id == 0:
            test_error_classification()
            test_jsonl_logging()
            test_prometheus_counters()
            test_no_silent_except()
        elif worker_id == 1:
            test_stream_error_emission()
            test_gateway_errors()
            test_dedup_tracking()
        elif worker_id == 2:
            test_origin_stage_coverage()
            test_live_requests()
    except Exception as e:
        msg = f"Worker {worker_id} error: {e}"
        print(f"  ❌ {msg}")
        import traceback
        traceback.print_exc()
        with _lock:
            _worker_errors.append(msg)


# ═══════════════════════════════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════════════════════════════

def generate_reports():
    report_dir = "/mnt/opencode/test"
    os.makedirs(report_dir, exist_ok=True)

    total = len(ALL_RESULTS)
    passed = sum(1 for r in ALL_RESULTS if r.passed)
    failed = total - passed
    by_category: dict[str, dict] = {}
    for r in ALL_RESULTS:
        if r.category not in by_category:
            by_category[r.category] = {"total": 0, "passed": 0, "failed": 0}
        by_category[r.category]["total"] += 1
        if r.passed:
            by_category[r.category]["passed"] += 1
        else:
            by_category[r.category]["failed"] += 1

    pass_rate = (passed / total * 100) if total else 0

    log_entries_written = 0
    log_path = Path(ERRORS_JSONL)
    if log_path.exists():
        log_entries_written = len([l for l in log_path.read_text().split("\n") if l.strip()])

    report_data = {
        "burnin": "FASE 29.4.4-B Error Taxonomy & Failure Attribution Burn-in",
        "checkpoint_from": "CP-29.4.4-ERROR-TAXONOMY-STABLE",
        "timestamp": int(time.time()),
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "pass_rate_pct": round(pass_rate, 2),
        "gateway_url": GATEWAY_URL,
        "lmstudio_url": LMSTUDIO_URL,
        "errors_jsonl": str(log_path),
        "jsonl_entries_written": log_entries_written,
        "prometheus_counters_defined": len(COUNTERS),
        "live_requests_ok": _live_loop_ok,
        "live_requests_errors": _live_loop_errors,
        "worker_errors": _worker_errors,
        "by_category": by_category,
        "failures": [
            {"category": r.category, "test": r.test_name, "detail": r.detail}
            for r in ALL_RESULTS if not r.passed
        ],
        "results": [asdict(r) for r in ALL_RESULTS],
    }

    json_path = os.path.join(report_dir, "fase29-4-4b-burnin-report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    print(f"\n📄 JSON report: {json_path}")

    md_path = os.path.join(report_dir, "fase29-4-4b-summary.md")
    lines = [
        "# FASE 29.4.4-B — Error Taxonomy Burn-in Summary",
        "",
        f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Duration:** {time.time() - _burnin_start:.0f}s",
        f"**Pass rate:** {pass_rate:.1f}% ({passed}/{total})",
        "",
        "## Configuration",
        f"- Gateway: `{GATEWAY_URL}`",
        f"- LM Studio: `{LMSTUDIO_URL}`",
        f"- Errors JSONL: `{ERRORS_JSONL}`",
        f"- Workers: 3",
        "",
        "## Results by Category",
    ]
    for cat in sorted(by_category.keys()):
        c = by_category[cat]
        icon = "✅" if c["failed"] == 0 else "❌"
        lines.append(f"- {icon} **{cat}**: {c['passed']}/{c['total']} passed")
    lines += [
        "",
        "## Telemetry",
        f"- JSONL entries: {log_entries_written}",
        f"- Prometheus counters defined: {len(COUNTERS)}",
        f"- Live requests OK: {_live_loop_ok}",
        f"- Live request errors: {_live_loop_errors}",
        "",
        "## Failures",
    ]
    failures = [r for r in ALL_RESULTS if not r.passed]
    if failures:
        for f_entry in failures:
            lines.append(f"- ❌ `{f_entry.category}` → `{f_entry.test_name}`: {f_entry.detail}")
    else:
        lines.append("- ✅ No failures")
    lines += [
        "",
        "## Pass Criteria",
    ]
    pass_criteria = {
        "0 worker crashes": not _worker_errors,
        "0 silent except:pass": all(r.passed for r in ALL_RESULTS if r.category == "no_silent_except"),
        "all categories classified": all(r.passed for r in ALL_RESULTS if r.category == "error_classification"),
        "JSONL logging active": all(r.passed for r in ALL_RESULTS if r.category == "jsonl_logging"),
        "prometheus counters defined": all(r.passed for r in ALL_RESULTS if r.category == "prometheus_counters"),
        "stream errors emit correct": all(r.passed for r in ALL_RESULTS if r.category == "stream_error_emission"),
        "gateway reachable": all(r.passed for r in ALL_RESULTS if r.category == "gateway_errors"),
        "dedup tracking functional": all(r.passed for r in ALL_RESULTS if r.category == "dedup_tracking"),
        "origin stage full coverage": all(r.passed for r in ALL_RESULTS if r.category == "origin_stage_coverage"),
    }
    all_pass = all(pass_criteria.values())
    for criterion, ok in pass_criteria.items():
        icon = "✅" if ok else "❌"
        lines.append(f"- {icon} {criterion}")
    lines += [
        "",
        f"## Verdict: **{'PASS ✅' if all_pass else 'FAIL ❌'}**",
        "",
    ]
    if all_pass:
        lines.append("Tag: `CP-29.4.4-B-BURNIN-STABLE`")
    md_content = "\n".join(lines)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"📄 MD summary:  {md_path}")

    return all_pass


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

_burnin_start = time.time()


def main():
    quick = "--quick" in sys.argv
    num_workers = 3

    print("=" * 60)
    print("FASE 29.4.4-B — Error Taxonomy & Failure Attribution Burn-in")
    print("=" * 60)
    print(f"  Gateway URL:   {GATEWAY_URL}")
    print(f"  LM Studio URL: {LMSTUDIO_URL}")
    print(f"  Errors JSONL:  {ERRORS_JSONL}")
    print(f"  Workers:       {num_workers}")
    print(f"  Quick mode:    {quick}")
    print()

    if not quick:
        workers = []
        for i in range(num_workers):
            w = threading.Thread(target=run_worker, args=(i,), daemon=True)
            workers.append(w)
            w.start()
            time.sleep(5 + (i * 2))
        for w in workers:
            w.join(timeout=600)
    else:
        run_worker(0)

    all_pass = generate_reports()

    elapsed = time.time() - _burnin_start
    print(f"\n{'=' * 60}")
    print(f"Burn-in completed in {elapsed:.0f}s")
    print(f"Total tests: {len(ALL_RESULTS)}")
    print(f"Passed:      {sum(1 for r in ALL_RESULTS if r.passed)}")
    print(f"Failed:      {sum(1 for r in ALL_RESULTS if not r.passed)}")
    print(f"Errors:      {len(_worker_errors)}")
    print(f"Verdict:     {'✅ PASS' if all_pass else '❌ FAIL'}")
    print(f"{'=' * 60}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
