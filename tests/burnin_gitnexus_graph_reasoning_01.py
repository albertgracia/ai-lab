#!/usr/bin/env python3
"""GITNEXUS-GRAPH-AWARE-REASONING-01 Burn-in: Graph reasoning engine.

Validates under repeated calls:
- no crashes after 100+ iterations
- bounded results (< 20 hotspots, blast radius, governance findings, correlations)
- consistent contract version
- metrics remain stable

Usage:
    python3 tests/burnin_gitnexus_graph_reasoning_01.py [--iterations 100]
"""

import json
import os
import sys
import time
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from runtime.graph_reasoning.gitnexus_graph_reasoning import (
    GRAPH_CONTRACT_VERSION,
    build_gitnexus_graph_snapshot,
    get_graph_hotspots,
    get_graph_blast_radius,
    get_graph_governance_findings,
    get_graph_correlations,
    get_graph_metrics,
    record_graph_metrics,
    reset_graph_reasoning_state,
    _MAX_HOTSPOTS,
    _MAX_BLAST_RADIUS,
    _MAX_GOVERNANCE_FINDINGS,
    _MAX_CORRELATIONS,
)


def run_burn_in(iterations: int = 100) -> dict:
    print(f"[BURN-IN] Starting graph reasoning burn-in: {iterations} iterations")

    reset_graph_reasoning_state()
    start = time.time()

    for i in range(iterations):
        build_gitnexus_graph_snapshot()
        if (i + 1) % 25 == 0:
            print(f"[BURN-IN]  {i+1}/{iterations}...")
            sys.stdout.flush()

    elapsed = time.time() - start
    print(f"[BURN-IN]  Completed: {iterations} iterations in {elapsed:.2f}s")

    hotspots = get_graph_hotspots()
    blast = get_graph_blast_radius()
    gov = get_graph_governance_findings()
    corr = get_graph_correlations()
    metrics = get_graph_metrics()

    report = {
        "burn_in_status": "completed",
        "total_iterations": iterations,
        "elapsed_seconds": round(elapsed, 2),
        "avg_per_call": round(elapsed / iterations, 3),
        "hotspots_total": hotspots.get("total_hotspots", 0),
        "hotspots_displayed": hotspots.get("displayed", 0),
        "blast_radius_total": blast.get("total_analyzed", 0),
        "blast_radius_displayed": blast.get("displayed", 0),
        "governance_findings_total": gov.get("total_findings", 0),
        "governance_findings_displayed": gov.get("displayed", 0),
        "correlations_total": corr.get("total_correlations", 0),
        "correlations_displayed": corr.get("displayed", 0),
        "metrics": metrics,
        "contract_version": hotspots.get("contract_version"),
        "bounded_checks": {
            "hotspots_within_max": hotspots.get("displayed", 0) <= _MAX_HOTSPOTS,
            "blast_radius_within_max": blast.get("displayed", 0) <= _MAX_BLAST_RADIUS,
            "governance_within_max": gov.get("displayed", 0) <= _MAX_GOVERNANCE_FINDINGS,
            "correlations_within_max": corr.get("displayed", 0) <= _MAX_CORRELATIONS,
            "contract_version_match": hotspots.get("contract_version") == GRAPH_CONTRACT_VERSION,
        },
    }

    print(f"\n[BURN-IN] Results:")
    print(f"  Hotspots: {hotspots.get('displayed')} (max {_MAX_HOTSPOTS})")
    print(f"  Blast radius: {blast.get('displayed')} (max {_MAX_BLAST_RADIUS})")
    print(f"  Governance findings: {gov.get('displayed')} (max {_MAX_GOVERNANCE_FINDINGS})")
    print(f"  Correlations: {corr.get('displayed')} (max {_MAX_CORRELATIONS})")
    print(f"  Avg per call: {report['avg_per_call']:.3f}s")
    print(f"  Contract version: {report['contract_version']}")

    for check, ok in report["bounded_checks"].items():
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {check}")

    all_pass = all(report["bounded_checks"].values())
    print(f"\n[BURN-IN] Overall: {'PASS' if all_pass else 'FAIL'}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Graph reasoning burn-in")
    parser.add_argument("--iterations", type=int, default=100, help="Number of iterations")
    args = parser.parse_args()
    report = run_burn_in(iterations=args.iterations)
    print(json.dumps(report, indent=2, ensure_ascii=False))
