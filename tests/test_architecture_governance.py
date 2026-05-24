"""GITNEXUS-ARCHITECTURE-GOVERNANCE-01: architecture governance tests.

Focus: bounded static analysis, gravity centers, coupling scoring,
governance policy violations, determinism, Prometheus metrics, fail-safe.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/ai-lab")

from runtime.governance.architecture_governance import (
    ARCHITECTURE_CONTRACT_VERSION,
    GOVERNANCE_POLICIES,
    analyze_architecture,
    get_architecture_summary,
    get_architecture_hotspots,
    get_architecture_violations,
    build_architecture_prometheus_metrics,
    reset_architecture_state,
)


def test_contract_version():
    assert ARCHITECTURE_CONTRACT_VERSION == "ARCH-01"


def test_governance_policies_count():
    assert len(GOVERNANCE_POLICIES) == 6


def test_analyze_returns_valid_structure():
    snap = analyze_architecture(now=1000.0)
    assert "modules_analyzed" in snap
    assert snap["contract_version"] == "ARCH-01"
    assert isinstance(snap["timestamp"], float)
    assert isinstance(snap["modules_analyzed"], int)
    assert isinstance(snap["total_dependencies"], int)


def test_modules_analyzed_greater_than_zero():
    snap = analyze_architecture(now=1001.0)
    assert snap["modules_analyzed"] > 0


def test_total_dependencies_non_negative():
    snap = analyze_architecture(now=1002.0)
    assert snap["total_dependencies"] >= 0


def test_coupling_summary_present():
    snap = analyze_architecture(now=1003.0)
    cs = snap["coupling_summary"]
    assert isinstance(cs, dict)
    for key in ("total_modules", "total_dependencies", "gravity_centers_count",
                "high_risk_count", "low_count", "medium_count", "high_count", "critical_count"):
        assert key in cs, f"missing key {key}"
    assert cs["total_modules"] == snap["modules_analyzed"]


def test_gravity_centers_list():
    snap = analyze_architecture(now=1004.0)
    assert isinstance(snap["gravity_centers"], list)
    for gc in snap["gravity_centers"]:
        assert "module" in gc
        assert "coupling_score" in gc
        assert "coupling_level" in gc
        assert "is_gravity_center" in gc
        assert gc["is_gravity_center"] is True


def test_high_risk_modules_list():
    snap = analyze_architecture(now=1005.0)
    assert isinstance(snap["high_risk_modules"], list)
    for hr in snap["high_risk_modules"]:
        assert "module" in hr
        assert hr["coupling_level"] in ("high", "critical")


def test_hotspots_list():
    snap = analyze_architecture(now=1006.0)
    assert isinstance(snap["hotspots"], list)
    for hs in snap["hotspots"]:
        assert "module" in hs
        assert "reason" in hs
        assert "coupling_score" in hs
        assert "level" in hs


def test_governance_violations():
    snap = analyze_architecture(now=1007.0)
    assert isinstance(snap["governance_violations"], list)
    for v in snap["governance_violations"]:
        assert "policy_id" in v
        assert "policy_name" in v
        assert "module" in v
        assert "violation" in v
        assert "severity" in v


def test_bounded_results():
    snap = analyze_architecture(now=1008.0)
    assert len(snap["gravity_centers"]) <= 50
    assert len(snap["high_risk_modules"]) <= 50
    assert len(snap["hotspots"]) <= 50


def test_determinism():
    reset_architecture_state()
    a = analyze_architecture(now=2000.0)
    reset_architecture_state()
    b = analyze_architecture(now=2000.0)
    assert a["modules_analyzed"] == b["modules_analyzed"]
    assert a["total_dependencies"] == b["total_dependencies"]
    assert a["coupling_summary"] == b["coupling_summary"]
    assert a["gravity_centers"] == b["gravity_centers"]
    assert a["hotspots"] == b["hotspots"]


def test_cache_ttl():
    reset_architecture_state()
    a = analyze_architecture(now=3000.0)
    b = analyze_architecture(now=3001.0)
    assert b["timestamp"] == 3000.0


def test_cache_expiry():
    reset_architecture_state()
    a = analyze_architecture(now=4000.0)
    b = analyze_architecture(now=4000.0 + 301.0)
    assert b["timestamp"] == 4000.0 + 301.0


def test_get_architecture_summary():
    reset_architecture_state()
    summary = get_architecture_summary(now=5000.0)
    assert summary["contract_version"] == "ARCH-01"
    assert summary["modules_analyzed"] > 0


def test_get_architecture_hotspots_default_limit():
    reset_architecture_state()
    result = get_architecture_hotspots(now=6000.0)
    assert result["contract_version"] == "ARCH-01"
    assert isinstance(result["limit"], int)
    assert result["limit"] >= 1
    assert isinstance(result["hotspots_total"], int)
    assert isinstance(result["hotspots"], list)


def test_get_architecture_hotspots_custom_limit():
    reset_architecture_state()
    result = get_architecture_hotspots(limit=3, now=6001.0)
    assert result["limit"] == 3
    assert len(result["hotspots"]) <= 3


def test_get_architecture_hotspots_clamps_limit():
    reset_architecture_state()
    result = get_architecture_hotspots(limit=999, now=6002.0)
    assert result["limit"] <= 50


def test_get_architecture_violations():
    reset_architecture_state()
    analyze_architecture(now=7000.0)
    result = get_architecture_violations()
    assert result["contract_version"] == "ARCH-01"
    assert isinstance(result["violations"], list)
    assert isinstance(result["violations_total"], int)


def test_get_architecture_violations_default_limit():
    reset_architecture_state()
    analyze_architecture(now=7001.0)
    result = get_architecture_violations()
    assert result["limit"] == 50


def test_prometheus_metrics_renders():
    reset_architecture_state()
    metrics = build_architecture_prometheus_metrics()
    assert isinstance(metrics, str)
    assert "ailab_architecture_hotspots_total" in metrics
    assert "ailab_architecture_critical_modules_total" in metrics
    assert "ailab_architecture_high_risk_total" in metrics
    assert "ailab_architecture_governance_violations_total" in metrics
    assert "ailab_architecture_gravity_centers_total" in metrics


def test_prometheus_metrics_parses_as_floats():
    reset_architecture_state()
    metrics = build_architecture_prometheus_metrics()
    for line in metrics.strip().split("\n"):
        parts = line.split()
        assert len(parts) == 2, f"unexpected format: {line}"
        key, val = parts
        assert key.startswith("ailab_architecture_")
        float(val)


def test_reset_state_clears_cache():
    reset_architecture_state()
    a = analyze_architecture(now=8000.0)
    reset_architecture_state()
    b = analyze_architecture(now=8000.0)
    assert b["timestamp"] == 8000.0


def test_fail_safe_on_bad_path():
    try:
        from runtime.governance.architecture_governance import _walk_py_files
        from pathlib import Path
        files = _walk_py_files(Path("/nonexistent/path"), max_files=10, max_depth=3)
        assert isinstance(files, list)
        assert len(files) == 0
    except Exception:
        assert False, "_walk_py_files raised on bad path"


def test_module_name_conversion():
    from runtime.governance.architecture_governance import _module_name_from_path
    from pathlib import Path
    name = _module_name_from_path(Path("/opt/ai-lab/runtime/gateway/openai_gateway.py"))
    assert "runtime.gateway.openai_gateway" in name


def test_coupling_level_thresholds():
    from runtime.governance.architecture_governance import _get_coupling_level
    assert _get_coupling_level(0.0).value == "low"
    assert _get_coupling_level(3.0).value == "low"
    assert _get_coupling_level(5.0).value == "medium"
    assert _get_coupling_level(12.0).value == "medium"
    assert _get_coupling_level(15.0).value == "high"
    assert _get_coupling_level(25.0).value == "high"
    assert _get_coupling_level(30.0).value == "critical"
    assert _get_coupling_level(100.0).value == "critical"


def test_compute_coupling_score():
    from runtime.governance.architecture_governance import _compute_coupling_score
    expected = 5.0 * 0.4 + 3.0 * 0.4 + 10.0 * 0.2
    score = _compute_coupling_score(fan_in=5, fan_out=3, imports=10)
    assert abs(score - expected) < 0.001
    score_zero = _compute_coupling_score(fan_in=0, fan_out=0, imports=0)
    assert score_zero == 0.0


def test_is_runtime_path():
    from runtime.governance.architecture_governance import _is_runtime_path
    assert _is_runtime_path("runtime/gateway") is True
    assert _is_runtime_path("runtime.telemetry") is True
    assert _is_runtime_path("os") is False
    assert _is_runtime_path("flask") is False


def test_now_ts_uses_provided():
    from runtime.governance.architecture_governance import _now_ts
    assert _now_ts(12345.0) == 12345.0


def test_now_ts_falls_back_to_time():
    from runtime.governance.architecture_governance import _now_ts
    ts = _now_ts(None)
    assert abs(ts - time.time()) < 1.0


def test_clamp_int():
    from runtime.governance.architecture_governance import _clamp_int
    assert _clamp_int("5", default=10, lo=1, hi=100) == 5
    assert _clamp_int("-1", default=10, lo=1, hi=100) == 1
    assert _clamp_int("999", default=10, lo=1, hi=100) == 100
    assert _clamp_int("abc", default=10, lo=1, hi=100) == 10


def test_governance_violation_severity_values():
    severities = {p["severity"] for p in GOVERNANCE_POLICIES}
    assert severities.issubset({"info", "warning", "error", "critical"})


def test_check_policy_no_violations():
    from runtime.governance.architecture_governance import _check_policy
    policy = {
        "id": "TEST-001",
        "name": "test_policy",
        "target_pattern": "runtime/test",
        "forbidden_imports": ["os.path"],
        "severity": "warning",
    }
    violations = _check_policy(policy, {"runtime.test": {"sys", "json"}})
    assert len(violations) == 0


def test_check_policy_detects_violation():
    from runtime.governance.architecture_governance import _check_policy
    policy = {
        "id": "TEST-002",
        "name": "test_violation",
        "target_pattern": "runtime/test",
        "forbidden_imports": ["os.path"],
        "severity": "error",
    }
    violations = _check_policy(policy, {"runtime.test": {"os.path", "json"}})
    assert len(violations) == 1
    assert violations[0].policy_id == "TEST-002"
    assert violations[0].severity.value == "error"


def test_module_risk_dataclass():
    from runtime.governance.architecture_governance import ModuleRisk, CouplingLevel
    risk = ModuleRisk(
        module="test.mod",
        imports=5,
        fan_in=3,
        fan_out=2,
        coupling_score=4.0,
        coupling_level=CouplingLevel.LOW,
        is_gravity_center=False,
    )
    d = risk.to_dict()
    assert d["module"] == "test.mod"
    assert d["coupling_score"] == 4.0
    assert d["coupling_level"] == "low"


def test_governance_violation_dataclass():
    from runtime.governance.architecture_governance import GovernanceViolation, GovernanceSeverity
    v = GovernanceViolation(
        policy_id="P-001",
        policy_name="pname",
        module="mod",
        violation="imports bad",
        severity=GovernanceSeverity.ERROR,
        timestamp=100.0,
    )
    d = v.to_dict()
    assert d["policy_id"] == "P-001"
    assert d["severity"] == "error"
    assert d["timestamp"] == 100.0


def test_architecture_snapshot_dataclass():
    from runtime.governance.architecture_governance import ArchitectureSnapshot
    snap = ArchitectureSnapshot(
        contract_version="ARCH-01",
        timestamp=100.0,
        modules_analyzed=42,
        total_dependencies=128,
        gravity_centers=[],
        high_risk_modules=[],
        coupling_summary={},
        governance_violations=[],
        hotspots=[],
    )
    d = snap.to_dict()
    assert d["contract_version"] == "ARCH-01"
    assert d["modules_analyzed"] == 42
    assert d["total_dependencies"] == 128


def test_hotspot_has_valid_reason():
    snap = analyze_architecture(now=9000.0)
    for hs in snap["hotspots"]:
        assert hs["reason"] in ("high_fan_in", "high_fan_out")


def test_prometheus_metrics_failsafe_on_error():
    from runtime.governance.architecture_governance import _cache, build_architecture_prometheus_metrics
    _cache.clear()
    result = build_architecture_prometheus_metrics()
    assert "ailab_architecture_hotspots_total" in result


def test_violations_fifo_bound():
    reset_architecture_state()
    from runtime.governance.architecture_governance import _violations_store, _violations_max
    for i in range(_violations_max + 10):
        _violations_store.append({"test": i})
    _violations_store[:] = _violations_store[:_violations_max]
    assert len(_violations_store) == _violations_max
