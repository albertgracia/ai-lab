"""GITNEXUS-GRAPH-AWARE-REASONING-01: unit tests for graph reasoning engine."""

from __future__ import annotations

import sys
import time
from typing import Any

sys.path.insert(0, "/opt/ai-lab")

from runtime.graph_reasoning.gitnexus_graph_reasoning import (
    GRAPH_CONTRACT_VERSION,
    build_gitnexus_graph_snapshot,
    get_graph_reasoning_summary,
    get_graph_hotspots,
    get_graph_blast_radius,
    get_graph_governance_findings,
    get_graph_correlations,
    get_graph_metrics,
    record_graph_metrics,
    reset_graph_reasoning_state,
    clear_graph_cache,
)


# ── Contract ─────────────────────────────────────────────────────────

def test_contract_version():
    assert GRAPH_CONTRACT_VERSION == "GRAPH-01"


# ── Summary / Snapshots ─────────────────────────────────────────────

def test_build_gitnexus_graph_snapshot_returns_dict():
    snap = build_gitnexus_graph_snapshot()
    assert isinstance(snap, dict)


def test_snapshot_has_required_keys():
    snap = build_gitnexus_graph_snapshot()
    for key in ("modules_total", "edges_total", "gravity_centers",
                "gravity_centers_total", "contract_version"):
        assert key in snap, f"Missing key: {key}"


def test_snapshot_contract_version():
    snap = build_gitnexus_graph_snapshot()
    assert snap.get("contract_version") == GRAPH_CONTRACT_VERSION


def test_get_graph_reasoning_summary_returns_dict():
    summ = get_graph_reasoning_summary()
    assert isinstance(summ, dict)


def test_summary_matches_snapshot():
    summ = get_graph_reasoning_summary()
    snap = build_gitnexus_graph_snapshot()
    assert summ.get("modules_total") == snap.get("modules_total")
    assert summ.get("edges_total") == snap.get("edges_total")


# ── Hotspots ────────────────────────────────────────────────────────

def test_get_graph_hotspots_returns_dict():
    result = get_graph_hotspots()
    assert isinstance(result, dict)


def test_hotspots_has_required_keys():
    result = get_graph_hotspots()
    for key in ("hotspots", "total_hotspots", "displayed", "contract_version"):
        assert key in result, f"Missing key: {key}"


def test_hotspots_contract_version():
    result = get_graph_hotspots()
    assert result.get("contract_version") == GRAPH_CONTRACT_VERSION


def test_hotspots_bounded():
    result = get_graph_hotspots()
    assert result.get("displayed", 0) <= 20


def test_hotspot_entries_have_required_fields():
    result = get_graph_hotspots()
    for h in result.get("hotspots", []):
        for key in ("module", "domain", "fan_in", "fan_out", "blast_radius", "governance_risk"):
            assert key in h, f"Missing key {key} in hotspot {h.get('module')}"


# ── Blast Radius ────────────────────────────────────────────────────

def test_get_graph_blast_radius_returns_dict():
    result = get_graph_blast_radius()
    assert isinstance(result, dict)


def test_blast_radius_has_required_keys():
    result = get_graph_blast_radius()
    for key in ("blast_radius_analysis", "total_analyzed", "displayed",
                "severity_distribution", "contract_version"):
        assert key in result, f"Missing key: {key}"


def test_blast_radius_contract_version():
    result = get_graph_blast_radius()
    assert result.get("contract_version") == GRAPH_CONTRACT_VERSION


def test_blast_radius_bounded():
    result = get_graph_blast_radius()
    assert result.get("displayed", 0) <= 20


def test_blast_radius_severity_distribution():
    result = get_graph_blast_radius()
    dist = result.get("severity_distribution", {})
    for sev in ("critical", "high", "medium", "low"):
        assert sev in dist, f"Missing severity: {sev}"


# ── Governance Findings ─────────────────────────────────────────────

def test_get_graph_governance_findings_returns_dict():
    result = get_graph_governance_findings()
    assert isinstance(result, dict)


def test_governance_findings_has_required_keys():
    result = get_graph_governance_findings()
    for key in ("governance_findings", "total_findings", "displayed",
                "severity_count", "contract_version"):
        assert key in result, f"Missing key: {key}"


def test_governance_findings_contract_version():
    result = get_graph_governance_findings()
    assert result.get("contract_version") == GRAPH_CONTRACT_VERSION


def test_governance_findings_bounded():
    result = get_graph_governance_findings()
    assert result.get("displayed", 0) <= 20


# ── Correlations ────────────────────────────────────────────────────

def test_get_graph_correlations_returns_dict():
    result = get_graph_correlations()
    assert isinstance(result, dict)


def test_correlations_has_required_keys():
    result = get_graph_correlations()
    for key in ("correlations", "total_correlations", "displayed", "contract_version"):
        assert key in result, f"Missing key: {key}"


def test_correlations_contract_version():
    result = get_graph_correlations()
    assert result.get("contract_version") == GRAPH_CONTRACT_VERSION


def test_correlations_bounded():
    result = get_graph_correlations()
    assert result.get("displayed", 0) <= 20


# ── Metrics ─────────────────────────────────────────────────────────

def test_get_graph_metrics_returns_dict():
    metrics = get_graph_metrics()
    assert isinstance(metrics, dict)


def test_graph_metrics_has_required_keys():
    metrics = get_graph_metrics()
    for key in ("ailab_graph_hotspots_total", "ailab_graph_critical_modules_total",
                "ailab_graph_high_blast_radius_total", "ailab_graph_governance_findings_total",
                "ailab_graph_federation_coupling_total", "ailab_graph_gravity_centers_total"):
        assert key in metrics, f"Missing key: {key}"


def test_graph_metrics_all_numeric():
    metrics = get_graph_metrics()
    for key, val in metrics.items():
        assert isinstance(val, (int, float)), f"{key} is not numeric: {type(val)}"


def test_record_graph_metrics_no_error():
    record_graph_metrics()


# ── Cache & Reset ───────────────────────────────────────────────────

def test_clear_graph_cache():
    clear_graph_cache()
    snap = build_gitnexus_graph_snapshot()
    assert isinstance(snap, dict)


def test_reset_graph_reasoning_state():
    result = reset_graph_reasoning_state()
    assert isinstance(result, dict)
    assert result.get("status") == "reset"
    assert result.get("contract_version") == GRAPH_CONTRACT_VERSION


# ── Concurrency Safety ──────────────────────────────────────────────

def test_concurrent_calls():
    import threading
    errors = []

    def call_fn(fn, name):
        try:
            for _ in range(5):
                r = fn()
                assert isinstance(r, dict)
        except Exception as e:
            errors.append((name, str(e)))

    fns = [
        (build_gitnexus_graph_snapshot, "snapshot"),
        (get_graph_hotspots, "hotspots"),
        (get_graph_blast_radius, "blast_radius"),
        (get_graph_governance_findings, "governance"),
        (get_graph_correlations, "correlations"),
    ]

    threads = []
    for fn, name in fns:
        t = threading.Thread(target=call_fn, args=(fn, name))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert not errors, f"Errors in concurrent tests: {errors}"
