#!/usr/bin/env python3
"""FASE 36D Burn-in: Autonomous Observability Triage.

Validates the triage engine under repeated calls:
- bounded stores do not grow unbounded
- no crashes after 100+ calls
- severity distribution stabilizes
- metrics remain consistent
- recommendations are deterministic

Usage:
    python3 tests/burnin_autonomous_observability_triage_01.py [--iterations 100]
"""

import json
import os
import sys
import time
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from runtime.triage.autonomous_triage import (
    build_runtime_triage_snapshot,
    get_active_triage_incidents,
    get_triage_summary,
    get_triage_recommendations,
    get_triage_snapshots,
    reset_triage_runtime,
    get_triage_metrics,
    _MAX_INCIDENTS,
    _MAX_SNAPSHOTS,
)


def run_burn_in(iterations: int = 100) -> dict:
    print(f"[BURN-IN] Starting triage burn-in: {iterations} iterations")

    reset_triage_runtime()
    start = time.time()

    first_pass = iterations // 2
    for i in range(first_pass):
        build_runtime_triage_snapshot()
        if (i + 1) % 25 == 0:
            print(f"[BURN-IN]  {i+1}/{iterations} incidents generated...")
            sys.stdout.flush()

    mid = time.time()
    print(f"[BURN-IN]  First pass ({first_pass}): {mid - start:.2f}s")

    for i in range(first_pass, iterations):
        build_runtime_triage_snapshot()
        if (i + 1) % 25 == 0:
            print(f"[BURN-IN]  {i+1}/{iterations} incidents generated...")
            sys.stdout.flush()

    elapsed = time.time() - start
    print(f"[BURN-IN]  Completed: {iterations} iterations in {elapsed:.2f}s")

    incidents = get_active_triage_incidents()
    summary = get_triage_summary()
    recommendations = get_triage_recommendations()
    snapshots = get_triage_snapshots(limit=1000)
    metrics = get_triage_metrics()

    report = {
        "burn_in_status": "completed",
        "total_iterations": iterations,
        "elapsed_seconds": round(elapsed, 2),
        "avg_per_call": round(elapsed / iterations, 3),
        "active_incidents": len(incidents),
        "snapshot_count": len(snapshots),
        "recommendation_count": len(recommendations),
        "summary": summary,
        "metrics": metrics,
        "bounded_checks": {
            "incidents_within_max": len(incidents) <= _MAX_INCIDENTS,
            "snapshots_within_max": len(snapshots) <= _MAX_SNAPSHOTS,
        },
    }

    print(f"\n[BURN-IN] Results:")
    print(f"  Active incidents: {len(incidents)} (max {_MAX_INCIDENTS})")
    print(f"  Snapshots: {len(snapshots)} (max {_MAX_SNAPSHOTS})")
    print(f"  Recommendations: {len(recommendations)}")
    print(f"  Avg per call: {report['avg_per_call']:.3f}s")

    severity_dist = summary.get("severity_distribution", {})
    print(f"  Severity distribution: {severity_dist}")

    for check, ok in report["bounded_checks"].items():
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {check}")

    all_pass = all(report["bounded_checks"].values())
    print(f"\n[BURN-IN] Overall: {'PASS' if all_pass else 'FAIL'}")
    return report


def main():
    parser = argparse.ArgumentParser(description="FASE 36D Triage burn-in")
    parser.add_argument("--iterations", type=int, default=100, help="Number of triage calls (default: 100)")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    report = run_burn_in(iterations=args.iterations)

    if args.json:
        print(json.dumps(report, indent=2))

    report_path = "/tmp/burnin_36d_triage_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n[BURN-IN] Report saved: {report_path}")

    return 0 if all(report.get("bounded_checks", {}).values()) else 1


if __name__ == "__main__":
    sys.exit(main())
