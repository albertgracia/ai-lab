"""RUNTIME-RESILIENCE-BURNIN-01: comprehensive cognitive runtime burn-in.

Validates stability, bounded cognition, and resilience across:
  - gateway, federation guards, evidence lineage, model registry
  - LM Studio completions (stream + non-stream)
  - Prometheus metrics, Grafana (reachability), GitNexus
  - memory / resource tracking

Duration: configurable via env BURNIN_DURATION_MINUTES (default 15, max 60).

Run:
  python3 tests/burnin_runtime_resilience_01.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, "/opt/ai-lab")

# ── config ────────────────────────────────────────────────────────────────────
DURATION_MINUTES = max(1, min(60, int(os.getenv("BURNIN_DURATION_MINUTES", "15"))))
MAX_WORKERS = 3
SNAPSHOT_INTERVAL = 30  # seconds between resource snapshots
STALL_WARNING_SECONDS = 120  # warn if no progress for this long

GATEWAY = os.getenv("BURNIN_GATEWAY_URL", "http://192.168.1.30:8008")
PROMETHEUS = os.getenv("BURNIN_PROMETHEUS_URL", "http://192.168.1.40:9090")
LMSTUDIO = os.getenv("BURNIN_LMSTUDIO_URL", "http://192.168.1.50:1234/v1").rstrip("/")
GRAFANA = os.getenv("BURNIN_GRAFANA_URL", "http://192.168.1.40:3000")
GITNEXUS = os.getenv("BURNIN_GITNEXUS_URL", "http://gitnexus.ai-lab.local:4747")

CHAT_URL = f"{LMSTUDIO}/chat/completions"
MODELS_URL = f"{LMSTUDIO}/models"

from runtime.models.model_registry import (
    DEPRECATED_QWEN_14B_ALIAS as MODEL_DEPRECATED,
    MODEL_LLAMA_8B as MODEL_LLAMA,
    MODEL_QWEN_14B as MODEL_QWEN,
)

_MODEL_CANONICAL = MODEL_QWEN
_MODEL_FASTPATH = MODEL_LLAMA

# ── shared state ──────────────────────────────────────────────────────────────
_lock = threading.Lock()
_results: dict[str, list] = {
    "completions": [],
    "guard_snapshots": [],
    "evidence_snapshots": [],
    "registry_snapshots": [],
    "prometheus_snapshots": [],
    "lmstudio_snapshots": [],
    "resource_snapshots": [],
    "gitnexus_snapshots": [],
    "errors": [],
}
_cancelled = threading.Event()

# ── helpers ───────────────────────────────────────────────────────────────────

def _req():
    import requests
    return requests


def _ts() -> float:
    return time.time()


def _elapsed(start: float) -> str:
    secs = time.time() - start
    m, s = divmod(int(secs), 60)
    return f"{m:02d}:{s:02d}"


def _chat_payload(model: str, *, stream: bool) -> dict:
    return {
        "model": model,
        "stream": stream,
        "messages": [
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": "Reply with a single short word."},
        ],
        "max_tokens": 8,
        "temperature": 0.0,
    }


def _record(key: str, data: dict) -> None:
    with _lock:
        _results[key].append(data)


def _record_error(source: str, message: str, detail: str = "") -> None:
    with _lock:
        _results["errors"].append({"ts": _ts(), "source": source, "message": message, "detail": detail})


# ── workers ───────────────────────────────────────────────────────────────────

def do_completion(cycle: int, model: str, stream: bool) -> dict:
    """Send one completion and return timing + result."""
    requests = _req()
    t0 = _ts()
    try:
        timeout = 25 if stream else 15
        if stream:
            chunks = 0
            with requests.post(CHAT_URL, json=_chat_payload(model, stream=True), stream=True, timeout=timeout) as r:
                r.raise_for_status()
                for raw in r.iter_lines(decode_unicode=True):
                    if not raw:
                        continue
                    line = raw.strip()
                    if line.startswith("data:"):
                        chunks += 1
            latency = (_ts() - t0) * 1000
            return {"ts": t0, "cycle": cycle, "model": model, "stream": True, "latency_ms": round(latency, 1), "chunks": chunks, "ok": True}
        else:
            r = requests.post(CHAT_URL, json=_chat_payload(model, stream=False), timeout=timeout)
            r.raise_for_status()
            out = r.json() or {}
            latency = (_ts() - t0) * 1000
            model_out = out.get("model", "")
            return {"ts": t0, "cycle": cycle, "model": model, "stream": False, "latency_ms": round(latency, 1), "model_out": model_out, "ok": True}
    except Exception as e:
        latency = (_ts() - t0) * 1000
        return {"ts": t0, "cycle": cycle, "model": model, "stream": stream, "latency_ms": round(latency, 1), "ok": False, "error": str(e)}


def do_guards_check() -> dict:
    requests = _req()
    try:
        r = requests.get(f"{GATEWAY}/runtime/guards/summary", timeout=5)
        if r.status_code != 200:
            return {"ok": False, "error": f"status={r.status_code}"}
        return {"ok": True, "data": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def do_evidence_check() -> dict:
    requests = _req()
    try:
        r = requests.get(f"{GATEWAY}/runtime/evidence/summary", timeout=5)
        if r.status_code != 200:
            return {"ok": False, "error": f"status={r.status_code}"}
        return {"ok": True, "data": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def do_registry_check() -> dict:
    requests = _req()
    try:
        r = requests.get(f"{GATEWAY}/runtime/models/registry", timeout=5)
        if r.status_code != 200:
            return {"ok": False, "error": f"status={r.status_code}"}
        return {"ok": True, "data": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def do_prometheus_check() -> dict:
    requests = _req()
    queries = {
        "gateway_up": "up{job='ai-lab-gateway'}",
        "registry_models": "ailab_registry_models_total",
        "guard_state": "ailab_federation_guard_state",
        "lmstudio_up": "ailab_lmstudio_up",
        "evidence_props": "ailab_evidence_propagations_total",
    }
    results = {}
    all_ok = True
    for name, query in queries.items():
        try:
            r = requests.get(f"{PROMETHEUS}/api/v1/query", params={"query": query}, timeout=5)
            if r.status_code != 200:
                results[name] = None
                all_ok = False
            else:
                data = r.json()
                if data.get("status") == "success":
                    result = data.get("data", {}).get("result", [])
                    results[name] = result[0]["value"][1] if result else None
                else:
                    results[name] = None
                    all_ok = False
        except Exception:
            results[name] = None
            all_ok = False
    return {"ok": all_ok, "results": results}


def do_lmstudio_models_check() -> dict:
    requests = _req()
    try:
        t0 = _ts()
        r = requests.get(MODELS_URL, timeout=5)
        dt = (_ts() - t0) * 1000
        if r.status_code != 200:
            return {"ok": False, "latency_ms": round(dt, 1), "error": f"status={r.status_code}"}
        data = r.json() or {}
        ids = [d.get("id") for d in (data.get("data") or []) if isinstance(d, dict)]
        return {
            "ok": True,
            "latency_ms": round(dt, 1),
            "models": ids,
            "has_canonical": MODEL_QWEN in ids,
            "has_fastpath": MODEL_LLAMA in ids,
            "has_deprecated": MODEL_DEPRECATED in ids,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def do_resource_snapshot(pid: int) -> dict:
    try:
        with open(f"/proc/{pid}/status") as f:
            raw = f.read()
        vm_rss_kb = 0
        for line in raw.splitlines():
            if line.startswith("VmRSS:"):
                vm_rss_kb = int(line.split()[1])
                break
        return {"ts": _ts(), "rss_kb": vm_rss_kb}
    except Exception:
        return {"ts": _ts(), "rss_kb": 0}


def do_gitnexus_check() -> dict:
    requests = _req()
    try:
        t0 = _ts()
        r = requests.get(f"{GITNEXUS}/api/health", timeout=5)
        dt = (_ts() - t0) * 1000
        return {"ok": r.status_code == 200, "latency_ms": round(dt, 1)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def do_grafana_check() -> dict:
    requests = _req()
    try:
        t0 = _ts()
        r = requests.get(f"{GRAFANA}/api/health", timeout=5)
        dt = (_ts() - t0) * 1000
        return {"ok": r.status_code == 200, "latency_ms": round(dt, 1)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── fail conditions ───────────────────────────────────────────────────────────

_FAIL_CONDITIONS: list[str] = []


def check_fail_conditions() -> list[str]:
    """Return list of FAIL reasons; empty = PASS."""
    fails: list[str] = []

    with _lock:
        errors = list(_results["errors"])
        lmstudio_snaps = list(_results["lmstudio_snapshots"])
        guard_snaps = list(_results["guard_snapshots"])

    if len(errors) > 0:
        latest_errors = errors[-10:]
        for e in latest_errors:
            if "repeated" in e.get("message", "").lower():
                fails.append(f"REPEATED_DEADLOCK: {e['source']}: {e['message']}")

    for snap in lmstudio_snaps:
        if snap.get("has_deprecated"):
            fails.append(f"DEPRECATED_ALIAS_RESURRECTION at ts={snap.get('ts', 0)}")
            break

    for snap in guard_snaps:
        data = snap.get("data", {})
        summary = data if isinstance(data, dict) else {}
        state_obj = summary.get("state") if isinstance(summary, dict) else {}
        state = state_obj.get("state") if isinstance(state_obj, dict) else ""
        counters = summary.get("counters") if isinstance(summary, dict) else {}
        state_transitions = counters.get("state_transitions_total", 0) if isinstance(counters, dict) else 0
        if state == "SAFE_MODE" and state_transitions and isinstance(state_transitions, (int, float)) and state_transitions > 5:
            fails.append(f"SAFE_MODE_LOOP: {state_transitions} transitions")
            break

    with _lock:
        evidence_snaps = list(_results["evidence_snapshots"])
    for snap in evidence_snaps[-5:]:
        data = snap.get("data", {})
        summary = data if isinstance(data, dict) else {}
        depth = summary.get("lineage_depth_max", 0) if isinstance(summary, dict) else 0
        stored = summary.get("stored_evidences", 0) if isinstance(summary, dict) else 0
        if isinstance(depth, (int, float)) and depth > 50:
            fails.append(f"UNBOUNDED_LINEAGE_DEPTH: max_depth={depth}")
        if isinstance(stored, (int, float)) and stored > 2000:
            fails.append(f"UNBOUNDED_EVIDENCE_STORE: stored={stored}")

    return fails


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    global _cancelled
    start_ts = _ts()
    duration_secs = DURATION_MINUTES * 60
    print(f"=" * 60)
    print(f"RUNTIME RESILIENCE BURN-IN 01")
    print(f"Duration: {DURATION_MINUTES} min ({duration_secs}s)")
    print(f"Gateway:  {GATEWAY}")
    print(f"LMStudio: {LMSTUDIO}")
    print(f"Prometheus: {PROMETHEUS}")
    print(f"Grafana: {GRAFANA}")
    print(f"GitNexus: {GITNEXUS}")
    print(f"Models:   canonical={_MODEL_CANONICAL}, fastpath={_MODEL_FASTPATH}")
    print(f"=" * 60)

    requests = _req()

    # 0. Gateway PID for resource tracking
    gateway_pid = 0
    try:
        r = requests.get(f"{GATEWAY}/health", timeout=5)
        if r.status_code == 200:
            print(f"[{_elapsed(start_ts)}] Gateway health OK")
    except Exception as e:
        print(f"[{_elapsed(start_ts)}] FAIL gateway unreachable: {e}")
        return 2

    # Find gateway PID via /proc (we're on same host)
    for pid_str in os.listdir("/proc"):
        if not pid_str.isdigit():
            continue
        try:
            with open(f"/proc/{pid_str}/cmdline") as f:
                cmd = f.read()
            if "openai_gateway.py" in cmd:
                gateway_pid = int(pid_str)
                break
        except Exception:
            continue
    if gateway_pid:
        print(f"[{_elapsed(start_ts)}] Gateway PID: {gateway_pid}")
    else:
        print(f"[{_elapsed(start_ts)}] WARNING: could not find gateway PID")

    # 1. Pre-flight checks
    print(f"\n── Pre-flight checks ──")
    preflight_ok = True

    # Gateway
    for ep in ["/health", "/runtime/models/registry", "/runtime/guards/summary", "/runtime/evidence/summary"]:
        try:
            r = requests.get(f"{GATEWAY}{ep}", timeout=5)
            if r.status_code == 200:
                print(f"  OK {ep}")
            else:
                print(f"  FAIL {ep} status={r.status_code}")
                preflight_ok = False
        except Exception as e:
            print(f"  FAIL {ep}: {e}")
            preflight_ok = False

    # LM Studio
    try:
        r = requests.get(MODELS_URL, timeout=5)
        if r.status_code == 200:
            data = r.json() or {}
            ids = [d.get("id") for d in (data.get("data") or []) if isinstance(d, dict)]
            print(f"  OK /v1/models ({len(ids)} models)")
            if MODEL_DEPRECATED in ids:
                print(f"  FAIL deprecated alias present: {MODEL_DEPRECATED}")
                preflight_ok = False
        else:
            print(f"  FAIL /v1/models status={r.status_code}")
            preflight_ok = False
    except Exception as e:
        print(f"  FAIL /v1/models: {e}")
        preflight_ok = False

    # Prometheus
    try:
        r = requests.get(f"{PROMETHEUS}/api/v1/query", params={"query": "up{job='ai-lab-gateway'}"}, timeout=5)
        if r.status_code == 200 and r.json().get("status") == "success":
            print("  OK Prometheus /api/v1/query")
        else:
            print(f"  FAIL Prometheus query status={r.status_code}")
            preflight_ok = False
    except Exception as e:
        print(f"  FAIL Prometheus: {e}")
        preflight_ok = False

    # Grafana
    try:
        r = requests.get(f"{GRAFANA}/api/health", timeout=5)
        if r.status_code == 200:
            print(f"  OK Grafana /api/health")
        else:
            print(f"  FAIL Grafana health status={r.status_code}")
    except Exception as e:
        print(f"  WARN Grafana unreachable: {e}")

    # GitNexus
    try:
        r = requests.get(f"{GITNEXUS}/api/health", timeout=5)
        if r.status_code == 200:
            print(f"  OK GitNexus /api/health")
        else:
            print(f"  WARN GitNexus health={r.status_code}")
    except Exception as e:
        print(f"  WARN GitNexus unreachable: {e}")

    if not preflight_ok:
        print("\nFAIL pre-flight checks — aborting burn-in")
        return 3

    print(f"\n── Burn-in running ({duration_secs}s) ──")

    # 2. Burn-in loop
    cycle = 0
    last_check_ts = time.time()
    last_progress_ts = time.time()
    model_rotation = 0  # 0=canonical, 1=fastpath

    try:
        while time.time() - start_ts < duration_secs and not _cancelled.is_set():
            cycle += 1
            now = time.time()
            remaining = duration_secs - (now - start_ts)

            # Print progress every 60s
            if now - last_progress_ts >= 60:
                elapsed_str = _elapsed(start_ts)
                rem_m, rem_s = divmod(int(remaining), 60)
                with _lock:
                    comp_ok = sum(1 for c in _results["completions"] if c.get("ok"))
                    comp_total = len(_results["completions"])
                    errs = len(_results["errors"])
                pct = ((now - start_ts) / duration_secs) * 100
                print(f"[{elapsed_str}] {pct:.0f}% done | completions: {comp_ok}/{comp_total} OK | errors: {errs}")
                last_progress_ts = now

            # Detect stall
            if now - last_progress_ts > STALL_WARNING_SECONDS:
                print(f"[{_elapsed(start_ts)}] WARNING: possible stall — no progress for {STALL_WARNING_SECONDS}s")

            # Execute work in thread pool
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                futures = []

                # Completion (alternate model + stream mode)
                model = _MODEL_CANONICAL if model_rotation % 2 == 0 else _MODEL_FASTPATH
                stream = model_rotation % 4 >= 2
                futures.append(pool.submit(do_completion, cycle, model, stream))
                model_rotation += 1

                # If cycle % 3 == 0, add a second concurrent completion
                if cycle % 3 == 0:
                    alt_model = _MODEL_FASTPATH if model == _MODEL_CANONICAL else _MODEL_CANONICAL
                    futures.append(pool.submit(do_completion, cycle, alt_model, False))

                # Periodic health checks
                if cycle % 2 == 0:
                    futures.append(pool.submit(do_guards_check))
                    futures.append(pool.submit(do_evidence_check))
                    futures.append(pool.submit(do_registry_check))

                if cycle % 3 == 0:
                    futures.append(pool.submit(do_lmstudio_models_check))
                    futures.append(pool.submit(do_prometheus_check))

                if cycle % 5 == 0:
                    futures.append(pool.submit(do_gitnexus_check))

                # Collect results
                for future in as_completed(futures, timeout=30):
                    try:
                        result = future.result()
                        if "cycle" in result:
                            _record("completions", result)
                        elif "models" in result:
                            _record("lmstudio_snapshots", result)
                        elif "results" in result and "gateway_up" in result.get("results", {}):
                            _record("prometheus_snapshots", result)
                        elif result.get("data", {}).get("endpoint") == "runtime/guards/summary":
                            _record("guard_snapshots", result)
                        elif result.get("data", {}).get("endpoint") == "runtime/evidence/summary":
                            _record("evidence_snapshots", result)
                        elif result.get("data", {}).get("endpoint") == "runtime/models/registry":
                            _record("registry_snapshots", result)
                        elif result.get("latency_ms") is not None and "models" not in result and "results" not in result and "data" not in result:
                            _record("gitnexus_snapshots", result)
                    except Exception as e:
                        _record_error("future", str(e))

            # Resource snapshot
            if gateway_pid > 0 and cycle % 3 == 0:
                snap = do_resource_snapshot(gateway_pid)
                _record("resource_snapshots", snap)

            # Fail condition check
            fails = check_fail_conditions()
            if fails:
                print(f"[{_elapsed(start_ts)}] FAIL conditions detected:")
                for f in fails:
                    print(f"  - {f}")
                return 4

            # Throttle: ensure ~1 cycle per 3-5 seconds
            elapsed_cycle = time.time() - now
            sleep_time = max(0, 3.0 - elapsed_cycle)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print(f"\n[{_elapsed(start_ts)}] Burn-in interrupted by user")
        _cancelled.set()

    # 3. Final report
    duration_actual = time.time() - start_ts
    print(f"\n{'=' * 60}")
    print(f"BURN-IN COMPLETE")
    print(f"{'=' * 60}")

    with _lock:
        completions = list(_results["completions"])
        guard_snaps = list(_results["guard_snapshots"])
        evidence_snaps = list(_results["evidence_snapshots"])
        lmstudio_snaps = list(_results["lmstudio_snapshots"])
        prometheus_snaps = list(_results["prometheus_snapshots"])
        resource_snaps = list(_results["resource_snapshots"])
        errors = list(_results["errors"])
        gitnexus_snaps = list(_results["gitnexus_snapshots"])

    # Compute stats
    comp_ok = [c for c in completions if c.get("ok")]
    comp_fail = [c for c in completions if not c.get("ok")]
    comp_stream = [c for c in comp_ok if c.get("stream")]
    comp_nonstream = [c for c in comp_ok if not c.get("stream")]
    latencies = sorted([c["latency_ms"] for c in comp_ok])

    def percentile(data, p):
        if not data:
            return 0
        idx = max(0, min(len(data) - 1, int(len(data) * p / 100)))
        return data[idx]

    report = {
        "duration_seconds": round(duration_actual, 1),
        "duration_minutes": round(duration_actual / 60, 1),
        "total_completions": len(completions),
        "successful_completions": len(comp_ok),
        "failed_completions": len(comp_fail),
        "stream_count": len(comp_stream),
        "non_stream_count": len(comp_nonstream),
        "latency_ms_p50": round(percentile(latencies, 50), 1),
        "latency_ms_p95": round(percentile(latencies, 95), 1),
        "max_latency_ms": round(max(latencies), 1) if latencies else 0,
        "min_latency_ms": round(min(latencies), 1) if latencies else 0,
        "errors_total": len(errors),
        "guard_snapshots_count": len(guard_snaps),
        "evidence_snapshots_count": len(evidence_snaps),
        "lmstudio_checks_count": len(lmstudio_snaps),
        "prometheus_checks_count": len(prometheus_snaps),
        "resource_snapshots_count": len(resource_snaps),
        "gitnexus_checks_count": len(gitnexus_snaps),
    }

    # Guard state analysis
    guard_states = {}
    for snap in guard_snaps:
        data = snap.get("data", {})
        payload = data if isinstance(data, dict) else {}
        summary = payload.get("summary") if isinstance(payload, dict) else {}
        state_obj = summary.get("state") if isinstance(summary, dict) else {}
        s = state_obj.get("state", "unknown") if isinstance(state_obj, dict) else "unknown"
        guard_states[s] = guard_states.get(s, 0) + 1

    report["guard_states"] = guard_states

    # Evidence analysis
    max_depth = 0
    max_stored = 0
    total_props = 0
    total_stale = 0
    total_replay_risk = 0
    for snap in evidence_snaps:
        data = snap.get("data", {})
        summary = data if isinstance(data, dict) else {}
        if not isinstance(summary, dict):
            continue
        max_depth = max(max_depth, summary.get("lineage_depth_max", 0) or 0)
        max_stored = max(max_stored, summary.get("stored_evidences", 0) or 0)
        total_props = max(total_props, summary.get("evidence_propagations_total", 0) or 0)
        total_stale = max(total_stale, summary.get("stale_evidence_total", 0) or 0)
        total_replay_risk = max(total_replay_risk, summary.get("replay_risk_total", 0) or 0)

    report["evidence"] = {
        "max_lineage_depth": max_depth,
        "max_stored": max_stored,
        "total_propagations": total_props,
        "total_stale": total_stale,
        "total_replay_risk": total_replay_risk,
    }

    # LM Studio health
    lmstudio_ok = sum(1 for s in lmstudio_snaps if s.get("ok"))
    lmstudio_fail = sum(1 for s in lmstudio_snaps if not s.get("ok"))
    lmstudio_deprecated = any(s.get("has_deprecated") for s in lmstudio_snaps)
    lmstudio_latencies = sorted([s.get("latency_ms", 0) for s in lmstudio_snaps if s.get("ok")])

    report["lmstudio"] = {
        "checks_ok": lmstudio_ok,
        "checks_failed": lmstudio_fail,
        "deprecated_alias_detected": lmstudio_deprecated,
        "latency_ms_p50": round(percentile(lmstudio_latencies, 50), 1) if lmstudio_latencies else 0,
        "latency_ms_p95": round(percentile(lmstudio_latencies, 95), 1) if lmstudio_latencies else 0,
        "model_inventory": {},
    }

    # Last LM Studio state
    if lmstudio_snaps:
        last_lm = lmstudio_snaps[-1]
        if last_lm.get("models"):
            report["lmstudio"]["last_models"] = last_lm["models"]

    # Resource analysis
    rss_values = sorted([s["rss_kb"] for s in resource_snaps if s.get("rss_kb", 0) > 0])
    report["resources"] = {
        "rss_kb_min": min(rss_values) if rss_values else 0,
        "rss_kb_max": max(rss_values) if rss_values else 0,
        "rss_kb_avg": round(sum(rss_values) / len(rss_values), 1) if rss_values else 0,
        "rss_mb_max": round(max(rss_values) / 1024, 1) if rss_values else 0,
        "rss_mb_avg": round(sum(rss_values) / len(rss_values) / 1024, 1) if rss_values else 0,
    }

    # Prometheus health
    prom_ok = sum(1 for s in prometheus_snaps if s.get("ok"))
    prom_total = len(prometheus_snaps)
    report["prometheus"] = {"checks_ok": prom_ok, "checks_total": prom_total}

    # GitNexus health
    gitnexus_ok = sum(1 for s in gitnexus_snaps if s.get("ok"))
    gitnexus_total = len(gitnexus_snaps)
    report["gitnexus"] = {"checks_ok": gitnexus_ok, "checks_total": gitnexus_total}

    # Error analysis
    error_sources = {}
    for e in errors:
        src = e.get("source", "unknown")
        error_sources[src] = error_sources.get(src, 0) + 1
    report["error_sources"] = error_sources

    # PASS / FAIL determination
    pass_conditions = True
    fail_reasons = []

    if comp_fail and len(comp_fail) > len(completions) * 0.2:
        pass_conditions = False
        fail_reasons.append(f"completion failure rate >20% ({len(comp_fail)}/{len(completions)})")
    if report.get("lmstudio", {}).get("deprecated_alias_detected"):
        pass_conditions = False
        fail_reasons.append("deprecated alias resurrected in LM Studio")
    if report.get("evidence", {}).get("max_lineage_depth", 0) > 50:
        pass_conditions = False
        fail_reasons.append(f"unbounded lineage depth: {report['evidence']['max_lineage_depth']}")
    if prom_total > 0 and prom_ok < prom_total * 0.5:
        pass_conditions = False
        fail_reasons.append(f"Prometheus scrape failure rate >50% ({prom_ok}/{prom_total})")
    if report.get("resources", {}).get("rss_mb_max", 0) > 1024:
        pass_conditions = False
        fail_reasons.append(f"gateway RSS >1024MB ({report['resources']['rss_mb_max']} MB)")
    if lmstudio_fail > lmstudio_ok:
        pass_conditions = False
        fail_reasons.append(f"LM Studio failure rate >50% ({lmstudio_fail}/{lmstudio_ok + lmstudio_fail})")
    if "SAFE_MODE" in guard_states and guard_states.get("SAFE_MODE", 0) > 5:
        pass_conditions = False
        fail_reasons.append(f"SAFE_MODE observed {guard_states.get('SAFE_MODE', 0)} times")

    report["pass"] = pass_conditions
    report["fail_reasons"] = fail_reasons

    # Print report
    print(json.dumps(report, indent=2, default=str))

    # Write report file
    report_path = "/tmp/RUNTIME-RESILIENCE-BURNIN-01.md"
    try:
        with open(report_path, "w") as f:
            f.write(f"# RUNTIME-RESILIENCE-BURNIN-01 Report\n\n")
            f.write(f"- **Duration:** {report['duration_minutes']} min ({report['duration_seconds']}s)\n")
            f.write(f"- **Total requests:** {report['total_completions']}\n")
            f.write(f"- **Successful completions:** {report['successful_completions']}\n")
            f.write(f"- **Failed completions:** {report['failed_completions']}\n")
            f.write(f"- **Stream tests:** {report['stream_count']}\n")
            f.write(f"- **Non-stream tests:** {report['non_stream_count']}\n")
            f.write(f"- **Errors:** {report['errors_total']}\n")
            f.write(f"- **Latency p50:** {report['latency_ms_p50']} ms\n")
            f.write(f"- **Latency p95:** {report['latency_ms_p95']} ms\n")
            f.write(f"- **Max latency:** {report['max_latency_ms']} ms\n\n")
            f.write(f"## Guard States\n")
            for s, count in guard_states.items():
                f.write(f"- **{s}:** {count}\n")
            f.write(f"\n## Evidence\n")
            f.write(f"- Max lineage depth: {report['evidence']['max_lineage_depth']}\n")
            f.write(f"- Max stored: {report['evidence']['max_stored']}\n")
            f.write(f"- Total propagations: {report['evidence']['total_propagations']}\n")
            f.write(f"- Total stale: {report['evidence']['total_stale']}\n")
            f.write(f"- Total replay risk: {report['evidence']['total_replay_risk']}\n\n")
            f.write(f"## LM Studio\n")
            f.write(f"- Checks OK: {report['lmstudio']['checks_ok']}\n")
            f.write(f"- Checks failed: {report['lmstudio']['checks_failed']}\n")
            f.write(f"- Deprecated alias detected: {report['lmstudio']['deprecated_alias_detected']}\n")
            f.write(f"- /models latency p50: {report['lmstudio']['latency_ms_p50']} ms\n")
            f.write(f"- /models latency p95: {report['lmstudio']['latency_ms_p95']} ms\n\n")
            f.write(f"## Resources\n")
            f.write(f"- RSS min: {report['resources']['rss_kb_min']} KB ({round(report['resources']['rss_kb_min']/1024, 1)} MB)\n")
            f.write(f"- RSS max: {report['resources']['rss_kb_max']} KB ({report['resources']['rss_mb_max']} MB)\n")
            f.write(f"- RSS avg: {report['resources']['rss_kb_avg']} KB ({report['resources']['rss_mb_avg']} MB)\n\n")
            f.write(f"## Prometheus\n")
            f.write(f"- Checks OK: {report['prometheus']['checks_ok']}/{report['prometheus']['checks_total']}\n\n")
            f.write(f"## GitNexus\n")
            f.write(f"- Checks OK: {report['gitnexus']['checks_ok']}/{report['gitnexus']['checks_total']}\n\n")
            f.write(f"## Error Sources\n")
            for src, count in sorted(error_sources.items(), key=lambda x: -x[1]):
                f.write(f"- **{src}:** {count}\n")
            f.write(f"\n## Verdict\n")
            if pass_conditions:
                f.write(f"**PASS** — runtime cognitivo bounded y estable\n")
            else:
                f.write(f"**FAIL** — condiciones de fallo detectadas:\n")
                for r in fail_reasons:
                    f.write(f"- {r}\n")
        print(f"\nReport written to {report_path}")
    except Exception as e:
        print(f"WARN: could not write report: {e}")

    if pass_conditions:
        print(f"\n{'=' * 60}")
        print(f"VERDICT: PASS — runtime remains stable and bounded")
        print(f"{'=' * 60}")
        return 0
    else:
        print(f"\n{'=' * 60}")
        print(f"VERDICT: FAIL")
        for r in fail_reasons:
            print(f"  - {r}")
        print(f"{'=' * 60}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
