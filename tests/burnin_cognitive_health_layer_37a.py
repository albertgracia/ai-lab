"""FASE 37A: Cognitive Health Layer burn-in.

Validates:
- /runtime/health* endpoints respond 200
- /metrics exposes cognitive health metrics
- Generates a bounded report at /tmp/COGNITIVE-HEALTH-LAYER-01.md

Run:
  python3 tests/burnin_cognitive_health_layer_37a.py
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


# Default to localhost to avoid any external rate-limiting between nodes.
GATEWAY = os.getenv("BURNIN_GATEWAY_URL", "http://127.0.0.1:8008")
DURATION_SECONDS = max(30, min(10 * 60, int(os.getenv("BURNIN_DURATION_SECONDS", "90"))))
REPORT_PATH = "/tmp/COGNITIVE-HEALTH-LAYER-01.md"


def _ts() -> float:
    return time.time()


def _get_json(path: str) -> dict:
    r = requests.get(f"{GATEWAY}{path}", timeout=5)
    ok = r.status_code == 200
    data = r.json() if ok else {}
    return {"ok": ok, "status_code": r.status_code, "path": path, "data": data}


def _get_metrics() -> dict:
    r = requests.get(f"{GATEWAY}/metrics", timeout=5)
    ok = r.status_code == 200
    txt = r.text if ok else ""
    wanted = [
        "ailab_cognitive_health_score",
        "ailab_cognitive_health_routing_confidence",
        "ailab_cognitive_health_nodes_online",
        "ailab_cognitive_health_watchdog_triggers_total",
        "ailab_gateway_latency_p95_ms",
    ]
    present = {k: (k in txt) for k in wanted}
    return {"ok": ok, "status_code": r.status_code, "present": present}


def main() -> int:
    started = _ts()
    endpoints = [
        "/runtime/health",
        "/runtime/health/summary",
        "/runtime/health/nodes",
        "/runtime/health/routing-confidence",
        "/runtime/health/watchdog",
        "/runtime/health/latency",
        "/runtime/health/degradations",
    ]

    results: list[dict] = []
    errors: list[dict] = []

    while _ts() - started < DURATION_SECONDS:
        for ep in endpoints:
            try:
                results.append(_get_json(ep))
            except Exception as e:
                errors.append({"ts": _ts(), "endpoint": ep, "error": str(e)})
        time.sleep(3)

    metrics = {}
    try:
        metrics = _get_metrics()
    except Exception as e:
        metrics = {"ok": False, "error": str(e), "present": {}}

    # Summarize
    ok_count = sum(1 for r in results if r.get("ok"))
    total = len(results)
    last_health = next((r for r in reversed(results) if r.get("path") == "/runtime/health" and r.get("ok")), None)
    last_deg = next((r for r in reversed(results) if r.get("path") == "/runtime/health/degradations" and r.get("ok")), None)
    last_lat = next((r for r in reversed(results) if r.get("path") == "/runtime/health/latency" and r.get("ok")), None)

    score = None
    routing_conf = None
    nodes_online = None
    node_scores = None
    watchdog_state = None
    watchdog_triggers = None
    unavailable_fields = None
    unknowns = None
    gpu_states = None
    latency_p50 = None
    latency_p95 = None
    ttfb_p50 = None
    ttfb_p95 = None
    degradations = None
    fallback = None
    if last_health:
        d = last_health.get("data") or {}
        score = d.get("score")
        nodes_online = d.get("nodes_online")
        routing_conf = (d.get("routing_confidence") or {}).get("confidence")
        node_scores = d.get("nodes")
        watchdog_state = d.get("watchdog_state")
        watchdog_triggers = (d.get("watchdog") or {}).get("triggers")
        unavailable_fields = d.get("unavailable_fields")
        unknowns = d.get("unknowns")
        gpu_states = d.get("gpu_states")

    if last_lat:
        ld = last_lat.get("data") or {}
        lat = (ld.get("latency") or {}).get("request_total") or {}
        ttfb = (ld.get("latency") or {}).get("ttfb") or {}
        latency_p50 = lat.get("p50_ms")
        latency_p95 = lat.get("p95_ms")
        ttfb_p50 = ttfb.get("p50_ms")
        ttfb_p95 = ttfb.get("p95_ms")

    if last_deg:
        dd = last_deg.get("data") or {}
        degradations = dd.get("degradations")
        fallback = dd.get("fallback_status")

    report = []
    report.append("# COGNITIVE-HEALTH-LAYER-01 (FASE 37A) Burn-in\n")
    report.append(f"Gateway: `{GATEWAY}`\n")
    report.append(f"Duration: `{DURATION_SECONDS}s`\n")
    report.append("## Endpoint Checks\n")
    report.append(f"Total requests: `{total}`\n")
    report.append(f"OK responses: `{ok_count}`\n")
    report.append(f"Errors: `{len(errors)}`\n")
    report.append("## Last Snapshot\n")
    report.append(f"health_score: `{score}`\n")
    report.append(f"routing_confidence: `{routing_conf}`\n")
    report.append(f"nodes_online: `{nodes_online}`\n")
    report.append(f"rx9070_state: `{(gpu_states or {}).get('rx9070') if isinstance(gpu_states, dict) else None}`\n")
    report.append(f"rx7900xt_state: `{(gpu_states or {}).get('rx7900xt') if isinstance(gpu_states, dict) else None}`\n")
    report.append(f"watchdog_state: `{watchdog_state}`\n")
    report.append(f"watchdog_triggers: `{json.dumps(watchdog_triggers, ensure_ascii=False) if watchdog_triggers is not None else None}`\n")
    report.append(f"unknowns: `{json.dumps(unknowns, ensure_ascii=False) if unknowns is not None else None}`\n")
    report.append(f"unavailable_fields: `{json.dumps(unavailable_fields, ensure_ascii=False) if unavailable_fields is not None else None}`\n")
    report.append(f"degradations: `{json.dumps(degradations, ensure_ascii=False) if degradations is not None else None}`\n")
    report.append(f"fallback_status: `{fallback}`\n")
    report.append("\n## Latency (bounded)\n")
    report.append(f"request_total_p50_ms: `{latency_p50}`\n")
    report.append(f"request_total_p95_ms: `{latency_p95}`\n")
    report.append(f"ttfb_p50_ms: `{ttfb_p50}`\n")
    report.append(f"ttfb_p95_ms: `{ttfb_p95}`\n")

    report.append("\n## Node Scores (bounded)\n")
    if isinstance(node_scores, list):
        # Bound the report size
        report.append("```json")
        report.append(json.dumps(node_scores[:20], ensure_ascii=False))
        report.append("```\n")
    else:
        report.append("NO DISPONIBLE\n")
    report.append("## Metrics Presence (/metrics)\n")
    report.append(f"status_code: `{metrics.get('status_code')}`\n")
    report.append(f"present: `{json.dumps(metrics.get('present', {}), ensure_ascii=False)}`\n")

    # Verdict: must have endpoints + metrics present.
    verdict = "PASS"
    if total > 0 and ok_count == 0:
        verdict = "FAIL"
    if metrics.get("ok") is not True:
        verdict = "FAIL"
    if not all(bool(v) for v in (metrics.get("present") or {}).values()):
        verdict = "FAIL"

    report.append("\n## Verdict\n")
    report.append(f"{verdict}\n")

    try:
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(report))
    except Exception:
        pass

    # Exit non-zero if FAIL
    return 0 if verdict == "PASS" else 10


if __name__ == "__main__":
    raise SystemExit(main())
