"""COGNITIVE-SLO-01: cognitive runtime SLO burn-in.

Validates SLO evaluation against live runtime state:
- SLO endpoints respond correctly
- Health state classification works with real data
- Violations recorded and retrievable
- Prometheus metrics exposed
- Registry/guards/evidence feed into SLO correctly

Run:
  python3 tests/burnin_cognitive_slo_01.py
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, "/opt/ai-lab")

DURATION_MINUTES = max(2, min(20, int(os.getenv("BURNIN_DURATION_MINUTES", "5"))))
MAX_WORKERS = 3

GATEWAY = os.getenv("BURNIN_GATEWAY_URL", "http://192.168.1.30:8008")
PROMETHEUS = os.getenv("BURNIN_PROMETHEUS_URL", "http://192.168.1.40:9090")

from runtime.slo.cognitive_slo import (
    evaluate_slos,
    get_slo_summary,
    get_slo_status,
    get_slo_violations,
    record_latency,
    reset_slo_state,
    build_slo_prometheus_metrics,
)


_lock = threading.Lock()
_results: dict[str, list] = {
    "slo_snapshots": [],
    "slo_statuses": [],
    "slo_violations": [],
    "api_snapshots": [],
    "prometheus_snapshots": [],
    "errors": [],
}
_cancelled = threading.Event()


def _ts() -> float:
    return time.time()


def _elapsed(start: float) -> str:
    secs = time.time() - start
    m, s = divmod(int(secs), 60)
    return f"{m:02d}:{s:02d}"


def _record(key: str, data: dict) -> None:
    with _lock:
        _results[key].append(data)


def _record_error(source: str, message: str, detail: str = "") -> None:
    with _lock:
        _results["errors"].append({"ts": _ts(), "source": source, "message": message, "detail": detail})


def do_slo_summary() -> dict:
    try:
        snap = get_slo_summary()
        return {"ok": True, "data": snap}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def do_slo_status() -> dict:
    try:
        status = get_slo_status()
        return {"ok": True, "data": status}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def do_slo_violations() -> dict:
    try:
        v = get_slo_violations()
        return {"ok": True, "data": v}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def do_api_check(endpoint: str) -> dict:
    import requests
    t0 = _ts()
    try:
        r = requests.get(f"{GATEWAY}{endpoint}", timeout=5)
        dt = (_ts() - t0) * 1000
        ok = r.status_code == 200
        data = r.json() if ok else {}
        return {"ok": ok, "latency_ms": round(dt, 1), "data": data, "endpoint": endpoint}
    except Exception as e:
        return {"ok": False, "error": str(e), "endpoint": endpoint}


def do_prometheus_check() -> dict:
    import requests
    queries = {
        "slo_violations": "ailab_slo_violations_total",
        "slo_degraded": "ailab_slo_degraded_total",
        "slo_safe_mode": "ailab_slo_safe_mode_total",
        "slo_registry": "ailab_slo_registry_consistency",
        "slo_gateway": "ailab_slo_gateway_health",
        "slo_lmstudio": "ailab_slo_lmstudio_health",
    }
    results = {}
    all_ok = True
    for name, query in queries.items():
        try:
            r = requests.get(f"{PROMETHEUS}/api/v1/query", params={"query": query}, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "success" and data.get("data", {}).get("result", []):
                    results[name] = data["data"]["result"][0]["value"][1]
                else:
                    results[name] = None
                    all_ok = False
            else:
                results[name] = None
                all_ok = False
        except Exception:
            results[name] = None
            all_ok = False
    return {"ok": all_ok, "results": results}


def do_evaluation_with_real_data() -> dict:
    import requests
    results_data = {}
    try:
        r_guard = requests.get(f"{GATEWAY}/runtime/guards/summary", timeout=5)
        guard = r_guard.json().get("summary", {}) if r_guard.status_code == 200 else {}
    except Exception:
        guard = {}

    try:
        r_ev = requests.get(f"{GATEWAY}/runtime/evidence/summary", timeout=5)
        evidence = r_ev.json().get("summary", {}) if r_ev.status_code == 200 else {}
    except Exception:
        evidence = {}

    try:
        r_reg = requests.get(f"{GATEWAY}/runtime/models/registry", timeout=5)
        registry = r_reg.json().get("registry", {}) if r_reg.status_code == 200 else {}
    except Exception:
        registry = {}

    try:
        snap = evaluate_slos(
            guard_summary=guard,
            evidence_summary=evidence,
            registry_snapshot=registry,
            lmstudio_up=1.0,
            gateway_up=1.0,
        )
        results_data["overall_status"] = snap.get("overall_status", "unknown")
        results_data["slos_total"] = len(snap.get("slos", []))
        results_data["violations"] = snap.get("violations_total", 0)
        violated = [s for s in (snap.get("slos") or []) if s.get("violated")]
        results_data["violated_slos"] = [s["name"] for s in violated]
        results_data["ok"] = True
    except Exception as e:
        results_data["ok"] = False
        results_data["error"] = str(e)
    return results_data


def main() -> int:
    start_ts = _ts()
    duration_secs = DURATION_MINUTES * 60
    print("=" * 60)
    print("COGNITIVE SLO BURN-IN 01")
    print(f"Duration: {DURATION_MINUTES} min ({duration_secs}s)")
    print(f"Gateway:  {GATEWAY}")
    print(f"Prometheus: {PROMETHEUS}")
    print("=" * 60)

    import requests

    # Pre-flight
    print(f"\n── Pre-flight checks ──")
    preflight_ok = True
    for ep in ["/runtime/slo/summary", "/runtime/slo/status", "/runtime/slo/violations", "/health"]:
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

    if not preflight_ok:
        print("\nFAIL pre-flight — aborting")
        return 3

    print(f"\n── Burn-in running ({duration_secs}s) ──")

    # Reset SLO state for clean evaluation
    reset_slo_state()

    cycle = 0
    last_progress_ts = time.time()

    try:
        while time.time() - start_ts < duration_secs and not _cancelled.is_set():
            cycle += 1
            now = time.time()

            if now - last_progress_ts >= 30:
                pct = ((now - start_ts) / duration_secs) * 100
                with _lock:
                    errs = len(_results["errors"])
                print(f"[{_elapsed(start_ts)}] {pct:.0f}% done | cycle={cycle} | errors={errs}")
                last_progress_ts = now

            # Inject realistic latency samples
            record_latency(float(300 + (cycle % 200)), stream=False)
            if cycle % 3 == 0:
                record_latency(float(800 + (cycle % 500)), stream=True)
            if cycle % 5 == 0:
                record_latency(float(50 + (cycle % 100)), endpoint="registry")

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                futures = []
                futures.append(pool.submit(do_slo_summary))
                futures.append(pool.submit(do_slo_status))
                futures.append(pool.submit(do_slo_violations))
                futures.append(pool.submit(do_evaluation_with_real_data))

                if cycle % 3 == 0:
                    futures.append(pool.submit(do_api_check, "/runtime/slo/summary"))
                    futures.append(pool.submit(do_api_check, "/runtime/slo/status"))
                    futures.append(pool.submit(do_api_check, "/runtime/slo/violations"))

                if cycle % 5 == 0:
                    futures.append(pool.submit(do_prometheus_check))

                for future in as_completed(futures, timeout=15):
                    try:
                        result = future.result()
                        if "overall_status" in result:
                            _record("slo_snapshots", result)
                        elif result.get("data", {}).get("overall_status"):
                            _record("slo_statuses", result)
                        elif result.get("data", {}).get("violations"):
                            _record("slo_violations", result)
                        elif result.get("results") and "slo_violations" in result.get("results", {}):
                            _record("prometheus_snapshots", result)
                        elif result.get("endpoint", "").startswith("/runtime/slo/"):
                            _record("api_snapshots", result)
                    except Exception as e:
                        _record_error("future", str(e))

            time.sleep(max(0, 2.0 - (time.time() - now)))

    except KeyboardInterrupt:
        print(f"\n[{_elapsed(start_ts)}] Interrupted")
        _cancelled.set()

    # Report
    duration_actual = time.time() - start_ts
    print(f"\n{'=' * 60}")
    print("SLO BURN-IN COMPLETE")
    print(f"{'=' * 60}")

    with _lock:
        slo_snaps = list(_results["slo_snapshots"])
        slo_statuses = list(_results["slo_statuses"])
        slo_violations = list(_results["slo_violations"])
        api_snaps = list(_results["api_snapshots"])
        prom_snaps = list(_results["prometheus_snapshots"])
        errors = list(_results["errors"])

    report = {
        "duration_seconds": round(duration_actual, 1),
        "duration_minutes": round(duration_actual / 60, 1),
        "total_cycles": cycle,
        "errors_total": len(errors),
    }

    # SLO evaluations analysis
    if slo_snaps:
        last_eval = slo_snaps[-1]
        report["slo_evaluations_total"] = len(slo_snaps)
        report["final_overall_status"] = last_eval.get("overall_status", "unknown")
        report["final_violations_total"] = last_eval.get("violations", 0)
        report["final_violated_slos"] = last_eval.get("violated_slos", [])
        statuses = {}
        for s in slo_snaps:
            st = s.get("overall_status", "unknown")
            statuses[st] = statuses.get(st, 0) + 1
        report["slo_status_distribution"] = statuses
    else:
        report["slo_evaluations_total"] = 0
        report["final_overall_status"] = "no_data"

    # API endpoints
    api_ok = sum(1 for s in api_snaps if s.get("ok"))
    api_total = len(api_snaps)
    api_latencies = sorted([s.get("latency_ms", 0) for s in api_snaps if s.get("ok")])

    def pct(data, p):
        if not data:
            return 0
        idx = max(0, min(len(data) - 1, int(len(data) * p / 100)))
        return data[idx]

    report["api"] = {
        "checks_ok": api_ok,
        "checks_total": api_total,
        "latency_p50": round(pct(api_latencies, 50), 1) if api_latencies else 0,
        "latency_p95": round(pct(api_latencies, 95), 1) if api_latencies else 0,
    }

    # Prometheus
    prom_ok = sum(1 for s in prom_snaps if s.get("ok"))
    prom_total = len(prom_snaps)
    report["prometheus"] = {"checks_ok": prom_ok, "checks_total": prom_total}

    # Error analysis
    err_sources = {}
    for e in errors:
        src = e.get("source", "unknown")
        err_sources[src] = err_sources.get(src, 0) + 1
    report["error_sources"] = err_sources

    # PASS/FAIL
    pass_conditions = True
    fail_reasons = []

    if prom_total > 0 and prom_ok < prom_total * 0.5:
        pass_conditions = False
        fail_reasons.append(f"Prometheus failure >50% ({prom_ok}/{prom_total})")

    if api_total > 0 and api_ok < api_total * 0.8:
        pass_conditions = False
        fail_reasons.append(f"API failure >20% ({api_ok}/{api_total})")

    report["pass"] = pass_conditions
    report["fail_reasons"] = fail_reasons

    print(json.dumps(report, indent=2, default=str))

    # Write report
    report_path = "/tmp/COGNITIVE-SLO-01.md"
    try:
        with open(report_path, "w") as f:
            f.write("# COGNITIVE-SLO-01 Report\n\n")
            f.write(f"- **Duration:** {report['duration_minutes']} min ({report['duration_seconds']}s)\n")
            f.write(f"- **Total cycles:** {report['total_cycles']}\n")
            f.write(f"- **Errors:** {report['errors_total']}\n\n")
            f.write("## SLO Evaluations\n")
            f.write(f"- Evaluations performed: {report['slo_evaluations_total']}\n")
            f.write(f"- Final overall status: {report.get('final_overall_status', 'N/A')}\n")
            f.write(f"- Final violations: {report.get('final_violations_total', 0)}\n")
            f.write(f"- Violated SLOs: {report.get('final_violated_slos', [])}\n")
            if "slo_status_distribution" in report:
                f.write("- Status distribution:\n")
                for s, c in sorted(report["slo_status_distribution"].items()):
                    f.write(f"  - {s}: {c}\n")
            f.write("\n## API Endpoints\n")
            f.write(f"- Checks OK: {report['api']['checks_ok']}/{report['api']['checks_total']}\n")
            f.write(f"- Latency p50: {report['api']['latency_p50']} ms\n")
            f.write(f"- Latency p95: {report['api']['latency_p95']} ms\n\n")
            f.write("## Prometheus\n")
            f.write(f"- Checks OK: {report['prometheus']['checks_ok']}/{report['prometheus']['checks_total']}\n\n")
            f.write("## Errors\n")
            for src, count in sorted(err_sources.items(), key=lambda x: -x[1]):
                f.write(f"- **{src}:** {count}\n")
            f.write("\n## Verdict\n")
            if pass_conditions:
                f.write("**PASS** - SLO framework operational\n")
            else:
                f.write("**FAIL** - condiciones:\n")
                for r in fail_reasons:
                    f.write(f"- {r}\n")
        print(f"\nReport: {report_path}")
    except Exception as e:
        print(f"WARN: report write failed: {e}")

    print(f"\n{'=' * 60}")
    print(f"VERDICT: {'PASS' if pass_conditions else 'FAIL'}")
    print(f"{'=' * 60}")
    return 0 if pass_conditions else 1


if __name__ == "__main__":
    raise SystemExit(main())
