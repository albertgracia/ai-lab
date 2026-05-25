#!/usr/bin/env python3
"""FASE 37E: Governance Drift Detection — critical-path burn-in.

Tests endpoint health, response shape, contract version, and metric exposure
against a running gateway instance (default http://127.0.0.1:8008).

Usage:
    python3 tests/burnin_governance_drift_detection_37e.py [--base-url http://127.0.0.1:8008]
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8008"
ENDPOINTS = [
    "/runtime/governance-drift",
    "/runtime/governance-drift/summary",
    "/runtime/governance-drift/events",
    "/runtime/governance-drift/domains",
    "/runtime/governance-drift/recommendations",
    "/runtime/governance-drift/reset",
]
REQUIRED_METRICS = [
    "ailab_governance_drift_score",
    "ailab_governance_drift_governance_confidence",
    "ailab_governance_drift_events_total",
    "ailab_governance_drift_domains_total",
    "ailab_governance_drift_critical_domains_total",
    "ailab_governance_drift_unknowns_total",
    "ailab_governance_drift_recommendations_total",
    "ailab_governance_drift_health_delta_avg",
]


def _fetch(path: str, timeout: int = 10) -> tuple[int, str]:
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except Exception as e:
        return 0, str(e)


def test_endpoint_200(path: str) -> list[str]:
    fails: list[str] = []
    code, body = _fetch(path)
    if code != 200:
        fails.append(f"    {path}: expected 200, got {code}")
        return fails
    try:
        data = json.loads(body)
    except Exception:
        fails.append(f"    {path}: invalid JSON")
        return fails
    if data.get("status") != "ok":
        fails.append(f"    {path}: status != ok")
    if path != "/runtime/governance-drift/reset":
        cv = data.get("contract_version") or ""
        if "37E" not in cv:
            fails.append(f"    {path}: contract_version missing 37E prefix ({cv})")
    return fails


def test_metrics() -> list[str]:
    fails: list[str] = []
    code, body = _fetch("/metrics", timeout=15)
    if code != 200:
        fails.append(f"    /metrics: expected 200, got {code}")
        return fails
    for m in REQUIRED_METRICS:
        if m not in body:
            fails.append(f"    /metrics: missing metric '{m}'")
    return fails


def main() -> int:
    print(f"FASE 37E burn-in — base URL: {BASE_URL}\n")
    total = 0
    failures: list[str] = []

    # --- Warmup: snapshot often includes lazy imports ---
    print("  Warming up: /runtime/governance-drift ...")
    _fetch("/runtime/governance-drift")
    time.sleep(0.5)

    # --- Endpoint tests ---
    for ep in ENDPOINTS:
        total += 1
        fails = test_endpoint_200(ep)
        if fails:
            failures.extend(fails)
        else:
            status = "PASS" if not fails else "FAIL"
            print(f"  [{status}] {ep}")

    # --- Metrics tests ---
    total += 1
    fails = test_metrics()
    if fails:
        failures.extend(fails)
        print(f"  [FAIL] /metrics (governance_drift)")
    else:
        print(f"  [PASS] /metrics (governance_drift)")

    # --- Summary ---
    print(f"\n{'=' * 50}")
    total_endpoints = len(ENDPOINTS) + 1  # +1 for metrics
    passed = total_endpoints - len([f for f in failures if "/metrics" in f or any(ep in f for ep in ENDPOINTS)])
    passed = total_endpoints - len(failures)
    print(f"  Total: {total_endpoints}  Passed: {passed}  Failed: {len(failures)}")
    if failures:
        print(f"\n  Failures ({len(failures)}):")
        for f in failures:
            print(f"    {f}")
        return 1
    else:
        print("\n  ✅ FASE 37E burn-in PASS")
        return 0


if __name__ == "__main__":
    sys.exit(main())
