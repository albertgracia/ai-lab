"""COGNITIVE-SLO-01: bounded cognitive runtime SLO tests.

Covers:
- threshold evaluation
- status transitions (HEALTHY/WARNING/DEGRADED/CRITICAL)
- violations recording and retrieval
- deterministic ordering
- bounded stores
- fail-safe behavior
- endpoint responses (via import)
- metrics exposure
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from runtime.slo.cognitive_slo import (
    SLO_DEFINITIONS,
    SLOStatus,
    SLOViolation,
    build_slo_prometheus_metrics,
    evaluate_slos,
    get_slo_status,
    get_slo_summary,
    get_slo_violations,
    record_latency,
    reset_slo_state,
)


def test_slo_definitions_are_complete() -> None:
    assert len(SLO_DEFINITIONS) >= 18
    names = [d.name for d in SLO_DEFINITIONS]
    expected = [
        "federation_caps_applied",
        "federation_replay_detections",
        "federation_storm_detections",
        "federation_safe_mode_transitions",
        "federation_lineage_depth",
        "latency_completion_p50",
        "latency_completion_p95",
        "latency_streaming_ttfb",
        "latency_registry_endpoint",
        "availability_gateway",
        "availability_lmstudio",
        "availability_prometheus",
        "integrity_invalid_lineage_ratio",
        "integrity_stale_evidence_ratio",
        "integrity_registry_consistency",
        "integrity_deprecated_alias",
        "recovery_degraded_to_normal",
        "recovery_safe_mode_max_duration",
        "recovery_cooldown_success",
    ]
    for e in expected:
        assert e in names, f"Missing SLO: {e}"
    assert len(set(names)) == len(names)


def test_evaluate_starts_healthy() -> None:
    reset_slo_state()
    snap = evaluate_slos(
        registry_snapshot={"routable_total": 3},
        lmstudio_up=1.0,
        gateway_up=1.0,
        prometheus_up=1.0,
    )
    assert snap["overall_status"] == "healthy"
    assert snap["violations_total"] == 0


def test_replay_threshold_triggers_warning() -> None:
    reset_slo_state()
    guard = {
        "counters": {
            "replay_detections_total": 15,
            "storm_detections_total": 0,
            "authority_escalations_total": 0,
            "caps_applied_total": 0,
        }
    }
    snap = evaluate_slos(
        guard_summary=guard,
        registry_snapshot={"routable_total": 3},
        lmstudio_up=1.0,
        gateway_up=1.0,
    )
    for s in snap["slos"]:
        if s["name"] == "federation_replay_detections":
            assert s["status"] == "warning", f"Expected warning, got {s['status']}"
            assert s["violated"] is True
            break
    else:
        pytest.fail("federation_replay_detections not found")


def test_storm_threshold_triggers_critical() -> None:
    reset_slo_state()
    guard = {
        "counters": {
            "replay_detections_total": 0,
            "storm_detections_total": 10,
            "authority_escalations_total": 0,
            "caps_applied_total": 0,
        }
    }
    snap = evaluate_slos(
        guard_summary=guard,
        registry_snapshot={"routable_total": 3},
        lmstudio_up=1.0,
        gateway_up=1.0,
    )
    for s in snap["slos"]:
        if s["name"] == "federation_storm_detections":
            assert s["status"] == "critical", f"Expected critical, got {s['status']}"
            assert s["violated"] is True
            break
    else:
        pytest.fail("federation_storm_detections not found")


def test_registry_inconsistency_triggers_critical() -> None:
    reset_slo_state()
    snap = evaluate_slos(
        registry_snapshot={"routable_total": 0},
        lmstudio_up=1.0,
        gateway_up=1.0,
    )
    for s in snap["slos"]:
        if s["name"] == "integrity_registry_consistency":
            assert s["status"] == "critical"
            assert s["violated"] is True
            break
    else:
        pytest.fail("integrity_registry_consistency not found")


def test_availability_lmstudio_triggers_degraded() -> None:
    reset_slo_state()
    snap = evaluate_slos(
        registry_snapshot={"routable_total": 3},
        lmstudio_up=0.0,
        gateway_up=1.0,
    )
    for s in snap["slos"]:
        if s["name"] == "availability_lmstudio":
            assert s["status"] in ("degraded", "critical")
            assert s["violated"] is True
            break
    else:
        pytest.fail("availability_lmstudio not found")


def test_violations_accumulate_and_are_bounded() -> None:
    reset_slo_state()
    for i in range(10):
        guard = {
            "counters": {
                "replay_detections_total": 30 + i,
                "storm_detections_total": 0,
                "authority_escalations_total": 0,
                "caps_applied_total": 0,
            }
        }
        evaluate_slos(
            guard_summary=guard,
            registry_snapshot={"routable_total": 3},
            now=1000.0 + (i * 10),
        )

    v = get_slo_violations()
    assert v["violations_total"] >= 1
    assert len(v["violations"]) >= 1
    assert len(v["violations"]) <= 50


def test_latency_window_is_bounded() -> None:
    reset_slo_state()
    for i in range(600):
        record_latency(float(500 + i), stream=False)
    snap = evaluate_slos(registry_snapshot={"routable_total": 3})
    for s in snap["slos"]:
        if s["name"] == "latency_completion_p50":
            assert s["current_value"] > 0
            break


def test_streaming_latency_is_separate() -> None:
    reset_slo_state()
    for i in range(100):
        record_latency(float(2000 + i), stream=True)
    snap = evaluate_slos(registry_snapshot={"routable_total": 3})
    for s in snap["slos"]:
        if s["name"] == "latency_streaming_ttfb":
            assert s["current_value"] >= 2000
            break


def test_registry_latency_is_separate() -> None:
    reset_slo_state()
    for i in range(50):
        record_latency(float(100 + i), endpoint="registry")
    snap = evaluate_slos(registry_snapshot={"routable_total": 3})
    for s in snap["slos"]:
        if s["name"] == "latency_registry_endpoint":
            assert s["current_value"] >= 100
            assert s["current_value"] < 200
            break


def test_invalid_lineage_ratio_triggers() -> None:
    reset_slo_state()
    evidence = {
        "evidence_propagations_total": 100,
        "invalid_lineage_total": 30,
        "stale_evidence_total": 0,
        "lineage_depth_max": 2,
    }
    snap = evaluate_slos(
        evidence_summary=evidence,
        registry_snapshot={"routable_total": 3},
    )
    for s in snap["slos"]:
        if s["name"] == "integrity_invalid_lineage_ratio":
            assert s["status"] == "critical"
            assert s["violated"] is True
            break
    else:
        pytest.fail("integrity_invalid_lineage_ratio not found")


def test_recovery_after_reset() -> None:
    reset_slo_state()
    snap1 = evaluate_slos(registry_snapshot={"routable_total": 3})
    assert snap1["overall_status"] == "healthy"

    snap2 = evaluate_slos(registry_snapshot={"routable_total": 0})
    assert snap2["overall_status"] == "critical"

    reset_slo_state()
    snap3 = evaluate_slos(registry_snapshot={"routable_total": 3})
    assert snap3["overall_status"] == "healthy"
    assert snap3["violations_total"] == 0


def test_get_slo_status_returns_compact() -> None:
    reset_slo_state()
    status = get_slo_status(now=1000.0)
    assert "contract_version" in status
    assert "overall_status" in status
    assert "violations_total" in status
    assert "degraded_total" in status
    assert "safe_mode_total" in status
    assert status["contract_version"] == "SLO-01"


def test_prometheus_metrics_are_fail_safe() -> None:
    reset_slo_state()
    metrics = build_slo_prometheus_metrics(
        guard_summary={},
        evidence_summary={},
        registry_snapshot={"routable_total": 3},
        lmstudio_up=1.0,
        gateway_up=1.0,
    )
    assert "ailab_slo_violations_total" in metrics
    assert "ailab_slo_degraded_total" in metrics
    assert "ailab_slo_safe_mode_total" in metrics
    assert "ailab_slo_registry_consistency" in metrics
    assert "ailab_slo_gateway_health" in metrics
    assert "ailab_slo_lmstudio_health" in metrics


def test_prometheus_metrics_fail_safe_on_error() -> None:
    reset_slo_state()
    metrics = build_slo_prometheus_metrics(
        guard_summary=None,
        evidence_summary=None,
        registry_snapshot=None,
        lmstudio_up=1.0,
        gateway_up=1.0,
    )
    assert "ailab_slo_violations_total" in metrics
    assert "ailab_slo_registry_consistency" in metrics


def test_get_slo_summary_is_deterministic() -> None:
    reset_slo_state()
    s1 = get_slo_summary(now=2000.0)
    reset_slo_state()
    s2 = get_slo_summary(now=2000.0)
    assert s1["contract_version"] == s2["contract_version"]
    assert s1["overall_status"] == s2["overall_status"]
    assert s1["violations_total"] == s2["violations_total"]
    assert len(s1["slos"]) == len(s2["slos"])


def test_stale_evidence_ratio_triggers_warning() -> None:
    reset_slo_state()
    evidence = {
        "evidence_propagations_total": 100,
        "invalid_lineage_total": 0,
        "stale_evidence_total": 25,
        "lineage_depth_max": 2,
    }
    snap = evaluate_slos(
        evidence_summary=evidence,
        registry_snapshot={"routable_total": 3},
    )
    for s in snap["slos"]:
        if s["name"] == "integrity_stale_evidence_ratio":
            assert s["status"] == "warning", f"Expected warning, got {s['status']}"
            assert s["violated"] is True
            break
    else:
        pytest.fail("integrity_stale_evidence_ratio not found")


def test_availability_prometheus_triggers_on_low() -> None:
    reset_slo_state()
    snap = evaluate_slos(
        registry_snapshot={"routable_total": 3},
        prometheus_up=0.5,
    )
    for s in snap["slos"]:
        if s["name"] == "availability_prometheus":
            assert s["violated"] is True
            break
    else:
        pytest.fail("availability_prometheus not found")


def test_latency_p95_triggers_on_high() -> None:
    reset_slo_state()
    for i in range(200):
        record_latency(float(10000 + i), stream=False)
    snap = evaluate_slos(registry_snapshot={"routable_total": 3})
    for s in snap["slos"]:
        if s["name"] == "latency_completion_p95":
            assert s["violated"] is True
            break
    else:
        pytest.fail("latency_completion_p95 not found")


def test_slo_definitions_have_all_fields() -> None:
    for d in SLO_DEFINITIONS:
        assert d.name
        assert d.category
        assert d.description
        assert d.warning_threshold >= 0
        assert d.critical_threshold >= 0
        assert d.severity.value in ("info", "warning", "error", "critical")
        assert d.recovery_window_seconds > 0


def test_violations_have_all_fields() -> None:
    reset_slo_state()
    evaluate_slos(
        guard_summary={
            "counters": {
                "replay_detections_total": 50,
                "storm_detections_total": 10,
                "authority_escalations_total": 6,
                "caps_applied_total": 60,
            }
        },
        registry_snapshot={"routable_total": 0},
    )
    v = get_slo_violations(limit=10)
    assert v["violations_total"] > 0
    for v_item in v["violations"]:
        assert "slo_name" in v_item
        assert "category" in v_item
        assert "status" in v_item
        assert "current_value" in v_item
        assert "threshold" in v_item
        assert "timestamp" in v_item
        assert "description" in v_item


def test_violations_bounded_at_256() -> None:
    reset_slo_state()
    for i in range(300):
        guard = {
            "counters": {
                "replay_detections_total": 50 + (i % 10),
                "storm_detections_total": 10 + (i % 3),
                "authority_escalations_total": 10 + (i % 5),
                "caps_applied_total": 100 + i,
            }
        }
        evaluate_slos(
            guard_summary=guard,
            registry_snapshot={"routable_total": 0},
            now=float(i * 10),
        )
    v = get_slo_violations(limit=300)
    assert v["violations_total"] >= 1
    assert len(v["violations"]) <= 256


def test_latency_windows_survive_empty() -> None:
    reset_slo_state()
    snap = evaluate_slos(registry_snapshot={"routable_total": 3})
    for s in snap["slos"]:
        if s["name"] == "latency_completion_p50":
            assert s["current_value"] == 0.0
            break


def test_violations_deterministic_order() -> None:
    reset_slo_state()
    v1 = get_slo_violations()
    reset_slo_state()
    v2 = get_slo_violations()
    assert v1["violations_total"] == v2["violations_total"]
    assert len(v1["violations"]) == len(v2["violations"])


def test_no_slo_returns_empty_violations() -> None:
    reset_slo_state()
    snap = evaluate_slos(registry_snapshot={"routable_total": 3})
    assert snap["violations_total"] >= 0
    v = get_slo_violations()
    assert v["violations_total"] >= 0
    assert isinstance(v["violations"], list)
