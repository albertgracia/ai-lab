"""FASE 37C: Critical Path Analysis burn-in.

Validates live HTTP endpoints + /metrics exposure.
Writes report to /tmp/CRITICAL-PATH-ANALYSIS-01.md

Run:
  python3 tests/burnin_critical_path_analysis_37c.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


GATEWAY = os.getenv("BURNIN_GATEWAY_URL", "http://127.0.0.1:8008")
DURATION_MINUTES = max(2, min(10, int(os.getenv("BURNIN_DURATION_MINUTES", "5"))))
REPORT_PATH = "/tmp/CRITICAL-PATH-ANALYSIS-01.md"


def _ts() -> float:
    return time.time()


def _get_json(path: str) -> dict:
    t0 = _ts()
    r = requests.get(f"{GATEWAY}{path}", timeout=8)
    dt = (_ts() - t0) * 1000
    ok = r.status_code == 200
    data = r.json() if ok else {}
    return {"ok": ok, "status_code": r.status_code, "path": path, "latency_ms": round(dt, 1), "data": data}


def _get_metrics_presence() -> dict:
    r = requests.get(f"{GATEWAY}/metrics", timeout=8)
    ok = r.status_code == 200
    txt = r.text if ok else ""
    wanted = [
        "ailab_critical_path_score",
        "ailab_critical_path_top_modules_total",
        "ailab_critical_path_high_total",
        "ailab_critical_path_critical_total",
        "ailab_critical_path_unknowns_total",
        "ailab_critical_path_routes_critical_total",
        "ailab_critical_path_recommendations_total",
    ]
    present = {k: (k in txt) for k in wanted}
    return {"ok": ok, "status_code": r.status_code, "present": present}


def _write_report(*, verdict: str, results: list[dict], errors: list[dict], metrics: dict) -> None:
    last = next((r for r in reversed(results) if r.get("path") == "/runtime/critical-path" and r.get("ok")), None)
    score = None
    severity = None
    if last:
        d = last.get("data") or {}
        score = d.get("score")
        severity = d.get("severity")

    lines = []
    lines.append(f"# CRITICAL-PATH-ANALYSIS-01 burn-in\n\n")
    lines.append(f"- gateway: `{GATEWAY}`\n")
    lines.append(f"- duration_minutes: {DURATION_MINUTES}\n")
    lines.append(f"- verdict: **{verdict}**\n")
    lines.append(f"- last_score: `{score}`\n")
    lines.append(f"- last_severity: `{severity}`\n\n")
    lines.append("## Metrics Presence\n\n")
    for k, v in (metrics.get("present") or {}).items():
        lines.append(f"- {k}: {v}\n")
    lines.append("\n## Endpoint Results (sample)\n\n")
    for r in results[-12:]:
        lines.append(f"- {r.get('path')} {r.get('status_code')} ok={r.get('ok')} latency_ms={r.get('latency_ms')}\n")
    if errors:
        lines.append("\n## Errors\n\n")
        for e in errors[-10:]:
            lines.append(f"- {e.get('endpoint')}: {e.get('error')}\n")

    Path(REPORT_PATH).write_text("".join(lines), encoding="utf-8")


def main() -> int:
    started = _ts()
    duration_s = DURATION_MINUTES * 60

    endpoints = [
        "/runtime/critical-path",
        "/runtime/critical-path/summary",
        "/runtime/critical-path/modules?top_n=10",
        "/runtime/critical-path/routes",
        "/runtime/critical-path/chokepoints",
        "/runtime/critical-path/blast-radius",
        "/runtime/critical-path/dependencies?file=runtime/gateway/openai_gateway.py",
        "/runtime/critical-path/recommendations",
        "/runtime/health/summary",
        "/runtime/correlation/summary",
        "/runtime/graph/summary",
    ]

    results: list[dict] = []
    errors: list[dict] = []

    while _ts() - started < duration_s:
        for ep in endpoints:
            try:
                results.append(_get_json(ep))
            except Exception as e:
                errors.append({"ts": _ts(), "endpoint": ep, "error": str(e)})
        time.sleep(3)

    metrics = _get_metrics_presence()

    expected_contract = "37C-CRITICAL-PATH-ANALYSIS-01"
    payload_ok = True
    for r in results:
        if r.get("path", "").startswith("/runtime/critical-path"):
            d = r.get("data") if isinstance(r.get("data"), dict) else {}
            if d.get("contract_version") != expected_contract:
                payload_ok = False
                break
            # Fail if handler fell back to the unknown endpoint guard.
            if d.get("error") == "unknown_critical_path_endpoint":
                payload_ok = False
                break

    verdict = "PASS"
    if any(not r.get("ok") for r in results):
        verdict = "FAIL"
    if not payload_ok:
        verdict = "FAIL"
    if errors:
        verdict = "FAIL"
    if not metrics.get("ok") or not all(metrics.get("present", {}).values()):
        verdict = "FAIL"

    _write_report(verdict=verdict, results=results, errors=errors, metrics=metrics)
    return 0 if verdict == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
