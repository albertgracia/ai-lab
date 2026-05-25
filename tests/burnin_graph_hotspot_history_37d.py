"""FASE 37D: Graph Hotspot History burn-in.

Validates live HTTP endpoints + /metrics exposure.

Writes report to /tmp/GRAPH-HOTSPOT-HISTORY-01.md

Run:
  python3 tests/burnin_graph_hotspot_history_37d.py
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
REPORT_PATH = "/tmp/GRAPH-HOTSPOT-HISTORY-01.md"


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
        "ailab_hotspot_history_snapshots_total",
        "ailab_hotspot_history_recurring_total",
        "ailab_hotspot_history_drift_score",
        "ailab_hotspot_history_increasing_total",
        "ailab_hotspot_history_decreasing_total",
        "ailab_hotspot_history_unknowns_total",
        "ailab_hotspot_history_recommendations_total",
        "ailab_hotspot_history_persistence_enabled",
    ]
    present = {k: (k in txt) for k in wanted}
    return {"ok": ok, "status_code": r.status_code, "present": present}


def _write_report(*, verdict: str, results: list[dict], errors: list[dict], metrics: dict) -> None:
    last = next((r for r in reversed(results) if r.get("path") == "/runtime/hotspot-history/latest" and r.get("ok")), None)
    snapshots_total = None
    drift_score = None
    recurring_total = None
    increasing_total = None
    decreasing_total = None
    persistence = None
    recs_total = None

    if last:
        d = last.get("data") or {}
        snap = d.get("snapshot") or {}
        snapshots_total = d.get("snapshot", {}).get("snapshots_total") if isinstance(d.get("snapshot"), dict) else None
        persistence = (snap.get("persistence") or {}).get("mode") if isinstance(snap, dict) else None

    drift = next((r for r in reversed(results) if r.get("path") == "/runtime/hotspot-history/drift" and r.get("ok")), None)
    if drift:
        dd = drift.get("data") or {}
        drift_score = dd.get("drift_score")

    rec = next((r for r in reversed(results) if r.get("path") == "/runtime/hotspot-history/recurring" and r.get("ok")), None)
    if rec:
        recurring_total = (rec.get("data") or {}).get("total")

    tr = next((r for r in reversed(results) if r.get("path") == "/runtime/hotspot-history/trends" and r.get("ok")), None)
    if tr:
        td = tr.get("data") or {}
        increasing_total = td.get("increasing_total")
        decreasing_total = td.get("decreasing_total")

    reco = next((r for r in reversed(results) if r.get("path") == "/runtime/hotspot-history/recommendations" and r.get("ok")), None)
    if reco:
        recs_total = (reco.get("data") or {}).get("total")

    lines = []
    lines.append("# GRAPH-HOTSPOT-HISTORY-01 burn-in\n\n")
    lines.append(f"- gateway: `{GATEWAY}`\n")
    lines.append(f"- duration_minutes: {DURATION_MINUTES}\n")
    lines.append(f"- verdict: **{verdict}**\n")
    lines.append(f"- drift_score: `{drift_score}`\n")
    lines.append(f"- recurring_hotspots: `{recurring_total}`\n")
    lines.append(f"- increasing_total: `{increasing_total}`\n")
    lines.append(f"- decreasing_total: `{decreasing_total}`\n")
    lines.append(f"- persistence_mode: `{persistence}`\n")
    lines.append(f"- recommendations_total: `{recs_total}`\n\n")

    lines.append("## Metrics Presence\n\n")
    for k, v in (metrics.get("present") or {}).items():
        lines.append(f"- {k}: {v}\n")

    lines.append("\n## Endpoint Results (sample)\n\n")
    for r in results[-14:]:
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
        "/runtime/hotspot-history",
        "/runtime/hotspot-history/summary",
        "/runtime/hotspot-history/latest",
        "/runtime/hotspot-history/trends",
        "/runtime/hotspot-history/recurring",
        "/runtime/hotspot-history/drift",
        "/runtime/hotspot-history/blast-radius",
        "/runtime/hotspot-history/recommendations",
        # dependencies
        "/runtime/critical-path/summary",
        "/runtime/critical-path/modules?top_n=10",
        "/runtime/critical-path/chokepoints",
        "/runtime/critical-path/blast-radius",
        "/runtime/correlation/summary",
        "/runtime/health/summary",
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

    expected_contract = "37D-GRAPH-HOTSPOT-HISTORY-01"
    payload_ok = True
    for r in results:
        p = r.get("path", "")
        if p.startswith("/runtime/hotspot-history"):
            d = r.get("data") if isinstance(r.get("data"), dict) else {}
            if d.get("contract_version") != expected_contract:
                payload_ok = False
                break
            if d.get("error") == "unknown_hotspot_history_endpoint":
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
