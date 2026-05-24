"""FASE 37B: Graph-Runtime Correlation burn-in.

Validates live HTTP endpoints + /metrics exposure.
Writes report to /tmp/GRAPH-RUNTIME-CORRELATION-01.md

Run:
  python3 tests/burnin_graph_runtime_correlation_37b.py
"""

from __future__ import annotations

import json
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
REPORT_PATH = "/tmp/GRAPH-RUNTIME-CORRELATION-01.md"


def _ts() -> float:
    return time.time()


def _get_json(path: str) -> dict:
    t0 = _ts()
    r = requests.get(f"{GATEWAY}{path}", timeout=5)
    dt = (_ts() - t0) * 1000
    ok = r.status_code == 200
    data = r.json() if ok else {}
    return {"ok": ok, "status_code": r.status_code, "path": path, "latency_ms": round(dt, 1), "data": data}


def _get_metrics_presence() -> dict:
    r = requests.get(f"{GATEWAY}/metrics", timeout=5)
    ok = r.status_code == 200
    txt = r.text if ok else ""
    wanted = [
        "ailab_correlation_score",
        "ailab_correlation_hotspots_total",
        "ailab_correlation_high_risk_total",
        "ailab_correlation_critical_total",
        "ailab_correlation_unknowns_total",
        "ailab_correlation_recommendations_total",
    ]
    present = {k: (k in txt) for k in wanted}
    return {"ok": ok, "status_code": r.status_code, "present": present}


def main() -> int:
    started = _ts()
    duration_s = DURATION_MINUTES * 60

    endpoints = [
        "/runtime/correlation",
        "/runtime/correlation/summary",
        "/runtime/correlation/hotspots",
        "/runtime/correlation/blast-radius",
        "/runtime/correlation/findings",
        "/runtime/correlation/recommendations",
        "/runtime/health/summary",
        "/runtime/slo/status",
        "/runtime/triage/summary",
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

    # Extract last correlation snapshot
    last_corr = next((r for r in reversed(results) if r.get("path") == "/runtime/correlation" and r.get("ok")), None)
    score = None
    severity = None
    hotspots = None
    unknowns = None
    recs = None
    if last_corr:
        d = last_corr.get("data") or {}
        score = d.get("correlation_score")
        severity = d.get("severity")
        hotspots = d.get("correlated_hotspots")
        unknowns = d.get("unknowns")
        recs = d.get("recommendations")

    # Validate endpoint payloads (avoid false PASS on gateway not_found 200 payloads)
    expected_contract = "37B-GRAPH-RUNTIME-CORRELATION-01"
    corr_payload_ok = True
    for r in results:
        if r.get("path", "").startswith("/runtime/correlation"):
            d = r.get("data") if isinstance(r.get("data"), dict) else {}
            if d.get("contract_version") != expected_contract:
                corr_payload_ok = False
                break

    verdict = "PASS"
    if any(not r.get("ok") for r in results):
        verdict = "FAIL"
    if not corr_payload_ok:
        verdict = "FAIL"
    if errors:
        verdict = "FAIL"
    if metrics.get("ok") is not True:
        verdict = "FAIL"
    if not all(bool(v) for v in (metrics.get("present") or {}).values()):
        verdict = "FAIL"

    report = []
    report.append("# GRAPH-RUNTIME-CORRELATION-01 (FASE 37B) Burn-in\n")
    report.append(f"Gateway: `{GATEWAY}`\n")
    report.append(f"Duration: `{DURATION_MINUTES}m`\n")
    report.append("## Results\n")
    report.append(f"requests_total: `{len(results)}`\n")
    report.append(f"errors_total: `{len(errors)}`\n")
    report.append("\n## Correlation Snapshot\n")
    report.append(f"correlation_score: `{score}`\n")
    report.append(f"severity: `{severity}`\n")
    report.append(f"unknowns: `{json.dumps(unknowns, ensure_ascii=False) if unknowns is not None else None}`\n")
    report.append("\n### Correlated Hotspots (bounded)\n")
    if isinstance(hotspots, list):
        report.append("```json")
        report.append(json.dumps(hotspots[:10], ensure_ascii=False))
        report.append("```\n")
    else:
        report.append("NO DISPONIBLE\n")
    report.append("\n### Recommendations (bounded)\n")
    if isinstance(recs, list):
        report.append("```json")
        report.append(json.dumps(recs[:10], ensure_ascii=False))
        report.append("```\n")
    else:
        report.append("NO DISPONIBLE\n")

    report.append("## Metrics Presence (/metrics)\n")
    report.append(f"status_code: `{metrics.get('status_code')}`\n")
    report.append(f"present: `{json.dumps(metrics.get('present', {}), ensure_ascii=False)}`\n")

    report.append("\n## Verdict\n")
    report.append(f"{verdict}\n")

    try:
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(report))
    except Exception:
        pass

    return 0 if verdict == "PASS" else 10


if __name__ == "__main__":
    raise SystemExit(main())
