"""FASE OBS-31A.1: Prometheus Authority Audit Tests.

Validates Prometheus as source_of_truth primary for AI-LAB.
Tests cover:
- Target classification (new live_target API + legacy backward compat)
- Freshness calculation
- Duplicate detection
- unexpected_down vs expected_offline separation
- Label validation
- Critical ailab_* metric checking
- Full authority audit
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from runtime.observability.prometheus_audit import (
    PrometheusTargetStatus,
    TargetHealth,
    FreshnessLevel,
    LabelSeverity,
    _KNOWN_TARGETS,
    classify_scrape_target,
    audit_prometheus_targets,
    build_prometheus_audit_summary,
    run_prometheus_authority_audit,
    check_critical_metrics,
    calculate_freshness,
    get_scrape_age_seconds,
    detect_duplicate_jobs,
    validate_target_labels,
    fetch_prometheus_targets,
    PROMETHEUS_AUDIT_CONTRACT_VERSION,
)


def _make_live_target(
    job: str = "ai-lab-gateway",
    instance: str = "192.168.1.30:8008",
    health: str = "up",
    last_error: str = "",
    last_scrape_duration: float = 0.003,
    scrape_interval: str = "15s",
    labels: dict | None = None,
    age_seconds: int = 5,
) -> dict:
    base_labels = {"cluster": "ai-lab", "env": "homelab", "instance": instance, "job": job}
    if labels:
        base_labels.update(labels)
    last_scrape = (datetime.now(timezone.utc) - timedelta(seconds=age_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "labels": base_labels,
        "health": health,
        "lastError": last_error,
        "lastScrapeDuration": last_scrape_duration,
        "scrapeInterval": scrape_interval,
        "lastScrape": last_scrape,
    }


def _make_known(job: str = "ai-lab-gateway", expected_offline: bool = False,
                critical: bool = True, role: str = "gateway") -> dict:
    for kt in _KNOWN_TARGETS:
        if kt["job"] == job:
            return dict(kt)
    return {"job": job, "endpoint": "host:9100", "role": role,
            "expected_offline": expected_offline, "critical": critical,
            "expected_labels": {}, "instances": ["host:9100"]}


# ── Target Classification ──

class TestClassifyScrapeTargetLive:
    def test_classify_healthy(self):
        known = _make_known("ai-lab-gateway")
        live = _make_live_target()
        entry = classify_scrape_target(known, live_target=live)
        assert entry.status == PrometheusTargetStatus.HEALTHY.value
        assert entry.health == TargetHealth.UP.value
        assert entry.freshness == FreshnessLevel.FRESH.value
        assert entry.critical is True

    def test_classify_unexpected_down(self):
        known = _make_known("ai-lab-gateway")
        live = _make_live_target(health="down", last_error="connection refused")
        entry = classify_scrape_target(known, live_target=live)
        assert entry.status == PrometheusTargetStatus.UNEXPECTED_DOWN.value
        assert entry.health == TargetHealth.DOWN.value
        assert entry.error_message == "connection refused"

    def test_classify_expected_offline_down(self):
        known = _make_known("ai-lab-gpu-rx7900xt")
        live = _make_live_target(job="ai-lab-gpu-rx7900xt", health="down",
                                 instance="192.168.1.60:9182",
                                 labels={"gpu": "rx7900xt"})
        entry = classify_scrape_target(known, live_target=live)
        assert entry.status == PrometheusTargetStatus.EXPECTED_OFFLINE.value
        assert not entry.critical

    def test_classify_expected_offline_up(self):
        known = _make_known("ai-lab-gpu-rx7900xt")
        live = _make_live_target(job="ai-lab-gpu-rx7900xt", health="up",
                                 instance="192.168.1.60:9182",
                                 labels={"gpu": "rx7900xt"})
        entry = classify_scrape_target(known, live_target=live)
        assert entry.status == PrometheusTargetStatus.HEALTHY.value

    def test_classify_degraded_duration(self):
        known = _make_known("ai-lab-gateway")
        live = _make_live_target(last_scrape_duration=15.0, scrape_interval="15s")
        entry = classify_scrape_target(known, live_target=live)
        assert entry.status == PrometheusTargetStatus.DEGRADED.value

    def test_classify_stale_unknown_health(self):
        known = _make_known("ai-lab-gateway")
        live = _make_live_target(health="unknown")
        entry = classify_scrape_target(known, live_target=live)
        assert entry.status == PrometheusTargetStatus.STALE.value

    def test_classify_orphan_no_live(self):
        known = _make_known("ai-lab-gateway")
        entry = classify_scrape_target(known)
        assert entry.status == PrometheusTargetStatus.ORPHAN.value
        assert entry.inventory_only is True

    def test_classify_not_in_known(self):
        unknown_target = {"job": "unknown-exporter", "endpoint": "host:9999",
                          "role": "unknown", "expected_offline": False, "critical": False,
                          "expected_labels": {}}
        entry = classify_scrape_target(unknown_target, error="no_such_target")
        assert entry.status == PrometheusTargetStatus.STALE.value


class TestClassifyScrapeTargetLegacy:
    def test_legacy_healthy(self):
        target = _make_known("ai-lab-gateway")
        entry = classify_scrape_target(target, is_up=True, scrape_duration_ms=200)
        assert entry.status == "healthy"

    def test_legacy_expected_offline(self):
        target = _make_known("ai-lab-gpu-rx7900xt")
        entry = classify_scrape_target(target, is_up=False)
        assert entry.status == "expected_offline"

    def test_legacy_degraded(self):
        target = _make_known("ai-lab-gateway")
        entry = classify_scrape_target(target, is_up=False)
        assert entry.status == "degraded"

    def test_legacy_stale(self):
        target = _make_known("ai-lab-gateway")
        entry = classify_scrape_target(target, is_up=None, error="connection_timeout")
        assert entry.status == "stale"

    def test_legacy_duration_degraded(self):
        target = _make_known("ai-lab-gateway")
        entry = classify_scrape_target(target, is_up=True, scrape_duration_ms=15000,
                                       scrape_interval_seconds=15)
        assert entry.status == "degraded"


# ── Freshness ──

class TestFreshness:
    def test_freshness_fresh(self):
        now = datetime.now(timezone.utc)
        ts = (now - timedelta(seconds=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        status = calculate_freshness(ts, 15)
        assert status == FreshnessLevel.FRESH.value

    def test_freshness_stale(self):
        now = datetime.now(timezone.utc)
        ts = (now - timedelta(seconds=45)).strftime("%Y-%m-%dT%H:%M:%SZ")
        status = calculate_freshness(ts, 15)
        assert status == FreshnessLevel.STALE.value

    def test_freshness_aged(self):
        now = datetime.now(timezone.utc)
        ts = (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        status = calculate_freshness(ts, 15)
        assert status == FreshnessLevel.AGED.value

    def test_freshness_unknown_empty(self):
        status = calculate_freshness("", 15)
        assert status == FreshnessLevel.UNKNOWN.value

    def test_freshness_unknown_invalid(self):
        status = calculate_freshness("not-a-date", 15)
        assert status == FreshnessLevel.UNKNOWN.value

    def test_scrape_age_seconds(self):
        age = get_scrape_age_seconds("2026-05-22T09:00:00Z")
        assert age > 0.0

    def test_scrape_age_zero_for_empty(self):
        age = get_scrape_age_seconds("")
        assert age == 0.0


# ── Duplicate Detection ──

class TestDuplicateDetection:
    def test_detect_duplicates(self):
        targets = [
            {"labels": {"job": "ai-lab-gpu-metrics", "instance": "192.168.1.50:9183"}},
            {"labels": {"job": "ai-lab-gpu-metrics", "instance": "192.168.1.60:9183"}},
            {"labels": {"job": "ai-lab-gateway", "instance": "192.168.1.30:8008"}},
        ]
        dups = detect_duplicate_jobs(targets)
        assert "ai-lab-gpu-metrics" in dups
        assert len(dups["ai-lab-gpu-metrics"]) == 2
        assert "ai-lab-gateway" not in dups

    def test_no_duplicates(self):
        targets = [
            {"labels": {"job": "ai-lab-gateway", "instance": "192.168.1.30:8008"}},
            {"labels": {"job": "ai-lab-router", "instance": "192.168.1.30:8083"}},
        ]
        dups = detect_duplicate_jobs(targets)
        assert len(dups) == 0

    def test_duplicate_empty(self):
        dups = detect_duplicate_jobs([])
        assert len(dups) == 0


# ── Label Validation ──

class TestLabelValidation:
    def test_labels_match(self):
        issues = validate_target_labels(
            {"cluster": "ai-lab", "env": "homelab", "instance": "host:8008", "job": "test"},
            {"cluster": "ai-lab", "env": "homelab"},
        )
        assert len(issues) == 0

    def test_labels_missing(self):
        issues = validate_target_labels(
            {"instance": "host:8008", "job": "test"},
            {"cluster": "ai-lab", "env": "homelab"},
        )
        assert any(i["severity"] == LabelSeverity.MISSING.value for i in issues)

    def test_labels_mismatch(self):
        issues = validate_target_labels(
            {"cluster": "wrong", "instance": "host:8008", "job": "test"},
            {"cluster": "ai-lab"},
        )
        assert any(i["severity"] == LabelSeverity.MISMATCH.value for i in issues)

    def test_required_labels_missing(self):
        issues = validate_target_labels({}, {})
        missing = [i for i in issues if i["severity"] == LabelSeverity.MISSING.value]
        assert any(i["label"] == "instance" for i in missing)
        assert any(i["label"] == "job" for i in missing)

    def test_gpu_label_present(self):
        issues = validate_target_labels(
            {"gpu": "rx9070", "instance": "host:9182", "job": "test"},
            {"gpu": "rx9070"},
        )
        assert len(issues) == 0


# ── Audit Prometheus Targets (legacy up_map compat) ──

class TestAuditPrometheusTargetsLegacy:
    def test_legacy_audit_with_up_map(self):
        up_map = {
            "ai-lab-gateway": True,
            "ai-lab-router": True,
            "ai-lab-live-api": True,
            "ai-lab-cadvisor": True,
            "ai-lab-node": True,
            "ai-lab-gpu-rx9070": True,
            "ai-lab-gpu-metrics": True,
        }
        results = audit_prometheus_targets(up_map=up_map)
        assert len(results) >= 13
        healthy = sum(1 for r in results if r["status"] == "healthy")
        expected_offline = sum(1 for r in results if r["status"] == "expected_offline")
        assert healthy >= 7
        assert expected_offline == 1

    def test_legacy_audit_empty_up_map(self):
        results = audit_prometheus_targets(up_map={})
        assert len(results) >= 13
        stale = sum(1 for r in results if r["status"] == "stale")
        expected_offline = sum(1 for r in results if r["status"] == "expected_offline")
        assert stale >= 14  # 15 non-expected_offline targets, all stale
        assert expected_offline == 1

    def test_legacy_audit_all_down(self):
        results = audit_prometheus_targets(
            up_map={t["job"]: False for t in _KNOWN_TARGETS}
        )
        degraded = sum(1 for r in results if r["status"] == "degraded")
        expected_offline = sum(1 for r in results if r["status"] == "expected_offline")
        assert degraded >= 13
        assert expected_offline == 1


# ── Build Prometheus Audit Summary ──

class TestBuildPrometheusAuditSummary:
    def test_summary_with_results(self):
        results = [{"job": "test", "status": "healthy", "critical": True,
                     "expected_offline": False}]
        summary = build_prometheus_audit_summary(results)
        assert summary["contract_version"] == "OBS-31A"
        assert summary["total_targets"] == 1
        assert summary["classification"]["healthy"] == 1
        assert summary["critical_targets"]["healthy"] == 1

    def test_summary_classification_counts(self):
        results = [
            {"job": "a", "status": "healthy", "critical": True, "expected_offline": False},
            {"job": "b", "status": "healthy", "critical": False, "expected_offline": False},
            {"job": "c", "status": "expected_offline", "critical": False, "expected_offline": True},
            {"job": "d", "status": "unexpected_down", "critical": True, "expected_offline": False},
        ]
        summary = build_prometheus_audit_summary(results)
        assert summary["classification"]["healthy"] == 2
        assert summary["classification"]["expected_offline"] == 1
        assert summary["classification"]["unexpected_down"] == 1
        assert summary["critical_targets"]["healthy"] == 1
        assert summary["critical_targets"]["total"] == 2


# ── Full Authority Audit ──

class TestRunPrometheusAuthorityAudit:
    def test_authority_audit_has_contract(self):
        result = run_prometheus_authority_audit(prometheus_url="http://nonexistent:9090")
        assert result["contract_version"] == PROMETHEUS_AUDIT_CONTRACT_VERSION
        assert "timestamp" in result
        assert "classification" in result
        assert "critical_targets" in result
        assert "targets" in result
        assert "freshness_summary" in result
        assert "label_summary" in result

    def test_authority_audit_unreachable_prometheus(self):
        result = run_prometheus_authority_audit(prometheus_url="http://nonexistent:9091")
        assert result["status"] == "error" or result["fetch_time_ms"] > 0
        assert len(result.get("targets", [])) >= 13


# ── Critical Metrics ──

class TestCriticalMetrics:
    def test_critical_metrics_unreachable(self):
        result = check_critical_metrics(prometheus_url="http://nonexistent:9090")
        assert result["contract_version"] == PROMETHEUS_AUDIT_CONTRACT_VERSION
        assert result["total_checked"] > 0
        assert result["found"] == 0
        assert result["missing"] == result["total_checked"]
        assert result["coverage_pct"] == 0.0

    def test_critical_metrics_has_results_dict(self):
        result = check_critical_metrics(prometheus_url="http://nonexistent:9090")
        assert isinstance(result["metrics"], dict)
        for metric in result["metrics"]:
            assert metric.startswith("ailab_")


# ── Known Targets ──

class TestKnownTargets:
    def test_known_targets_contains_all_roles(self):
        roles = {t["role"] for t in _KNOWN_TARGETS}
        for expected in ("gateway", "router", "live-api", "containers", "host",
                         "gpu", "gpu-compute", "tunnel", "docker", "unifi",
                         "storage", "windows"):
            assert expected in roles, f"Missing role: {expected}"

    def test_known_targets_expected_offline_separated(self):
        offline = [t for t in _KNOWN_TARGETS if t.get("expected_offline")]
        assert len(offline) == 1
        assert offline[0]["job"] == "ai-lab-gpu-rx7900xt"

    def test_known_targets_critical_count(self):
        critical = [t for t in _KNOWN_TARGETS if t.get("critical")]
        assert len(critical) >= 3  # gateway, gpu-rx9070, gpu-metrics

    def test_known_targets_duplicate_job_noted(self):
        multi = [t for t in _KNOWN_TARGETS if t.get("note") == "multi_instance_job"]
        assert len(multi) == 1
        assert len(multi[0].get("instances", [])) == 2


# ── JSON Safety ──

class TestJsonSafety:
    def test_classify_result_json_safe(self):
        known = _make_known("ai-lab-gateway")
        live = _make_live_target()
        entry = classify_scrape_target(known, live_target=live)
        d = entry.to_dict()
        json.dumps(d)
        assert isinstance(d["labels"], dict)
        assert isinstance(d["label_issues"], list)

    def test_audit_result_json_safe(self):
        results = [{"job": "test", "status": "healthy", "critical": True,
                     "expected_offline": False}]
        summary = build_prometheus_audit_summary(results)
        json.dumps(summary)

    def test_authority_audit_json_safe(self):
        result = run_prometheus_authority_audit(prometheus_url="http://nonexistent:9090")
        json.dumps(result)


# ── Contract Version ──

class TestContractVersion:
    def test_contract_version_set(self):
        assert PROMETHEUS_AUDIT_CONTRACT_VERSION == "OBS-31A.1"

    def test_authority_audit_contract(self):
        result = run_prometheus_authority_audit(prometheus_url="http://nonexistent:9090")
        assert result["contract_version"] == "OBS-31A.1"


# ── Edge Cases ──

class TestEdgeCases:
    def test_live_target_without_labels(self):
        known = _make_known("ai-lab-gateway")
        now_str = (datetime.now(timezone.utc) - timedelta(seconds=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        live = {"health": "up", "lastError": "", "lastScrapeDuration": 0.001,
                "scrapeInterval": "15s", "lastScrape": now_str}
        entry = classify_scrape_target(known, live_target=live)
        assert entry.status == PrometheusTargetStatus.HEALTHY.value

    def test_fetch_prometheus_unreachable(self):
        result = fetch_prometheus_targets("http://nonexistent:9999", timeout=1)
        assert result["status"] == "error"
        assert "fetch_time_ms" in result

    def test_audit_live_fallback(self):
        results = audit_prometheus_targets(prometheus_url="http://nonexistent:9090")
        assert len(results) >= 13
        for r in results:
            if r["job"] in ("ai-lab-gpu-rx7900xt",):
                assert r["status"] == "expected_offline"
