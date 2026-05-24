"""PROMETHEUS-ALERTING-COGNITIVE-01: bounded alerting validation tests.

Focus: YAML validity, rule parseability, metric existence, threshold
coherence, recording rule validity, label determinism, severity consistency.
"""

from __future__ import annotations

import sys
import os
import json
import tempfile
import yaml
from pathlib import Path

sys.path.insert(0, "/opt/ai-lab")

RULES_PATH = Path("/opt/ai-lab/monitorizacion/prometheus/rules/ai-lab-cognitive-alerts.yml")

EXPECTED_ALERTS = [
    "AI-LABFederationSafeMode",
    "AI-LABFederationConstrained",
    "AI-LABReplayStorm",
    "AI-LABStormHeuristicTriggered",
    "AI-LABAuthorityEscalationDetected",
    "AI-LABInvalidLineage",
    "AI-LABHighReplayRisk",
    "AI-LABStaleEvidence",
    "AI-LABDeepLineage",
    "AI-LABSLOViolation",
    "AI-LABSLOSafeMode",
    "AI-LABSLORegistryInconsistent",
    "AI-LABGatewayUnavailable",
    "AI-LABLMStudioUnavailable",
    "AI-LABDeprecatedAliasReappeared",
    "AI-LABNoRoutableModels",
    "AI-LABGovernanceViolations",
    "AI-LABHighRiskArchitecture",
]

EXPECTED_RECORDING_RULES = [
    "ai_lab:federation_guard_events_rate5m",
    "ai_lab:evidence_replay_rate5m",
    "ai_lab:slo_violations_rate5m",
    "ai_lab:architecture_risk_score",
    "ai_lab:runtime_health_score",
]

EXPECTED_CATEGORIES = {
    "federation_guards",
    "evidence_lineage",
    "cognitive_slo",
    "model_registry",
    "architecture_governance",
}

VALID_SEVERITIES = {"critical", "warning", "info"}


def _load_rules() -> dict:
    with open(RULES_PATH) as f:
        return yaml.safe_load(f)


def test_yaml_is_valid():
    data = _load_rules()
    assert isinstance(data, dict)
    assert "groups" in data


def test_has_two_groups():
    data = _load_rules()
    assert len(data["groups"]) == 2


def test_alert_group_config():
    data = _load_rules()
    alert_group = data["groups"][0]
    assert alert_group["name"] == "ai_lab_cognitive_alerts"
    assert alert_group["interval"] == "30s"
    assert alert_group["limit"] == 20


def test_recording_group_config():
    data = _load_rules()
    recording_group = data["groups"][1]
    assert recording_group["name"] == "ai_lab_cognitive_recording_rules"
    assert recording_group["interval"] == "60s"
    assert recording_group["limit"] == 10


def test_all_expected_alerts_present():
    data = _load_rules()
    alert_names = {r["alert"] for r in data["groups"][0]["rules"] if "alert" in r}
    for name in EXPECTED_ALERTS:
        assert name in alert_names, f"Missing alert: {name}"
    assert len(alert_names) == len(EXPECTED_ALERTS)


def test_all_expected_recording_rules_present():
    data = _load_rules()
    record_names = {r["record"] for r in data["groups"][1]["rules"] if "record" in r}
    for name in EXPECTED_RECORDING_RULES:
        assert name in record_names, f"Missing recording rule: {name}"
    assert len(record_names) == len(EXPECTED_RECORDING_RULES)


def test_no_duplicate_alert_names():
    data = _load_rules()
    alert_names = [r["alert"] for r in data["groups"][0]["rules"] if "alert" in r]
    assert len(alert_names) == len(set(alert_names))


def test_all_alerts_have_labels():
    data = _load_rules()
    for r in data["groups"][0]["rules"]:
        if "alert" in r:
            assert "labels" in r, f"Missing labels in {r['alert']}"
            assert "severity" in r["labels"], f"Missing severity in {r['alert']}"
            assert "team" in r["labels"], f"Missing team in {r['alert']}"
            assert "category" in r["labels"], f"Missing category in {r['alert']}"


def test_severity_values_are_valid():
    data = _load_rules()
    for r in data["groups"][0]["rules"]:
        if "alert" in r:
            assert r["labels"]["severity"] in VALID_SEVERITIES, \
                f"Invalid severity {r['labels']['severity']} in {r['alert']}"


def test_critical_alerts_have_correct_severity():
    data = _load_rules()
    critical_alerts = [
        "AI-LABFederationSafeMode",
        "AI-LABReplayStorm",
        "AI-LABStormHeuristicTriggered",
        "AI-LABInvalidLineage",
        "AI-LABSLOSafeMode",
        "AI-LABSLORegistryInconsistent",
        "AI-LABGatewayUnavailable",
        "AI-LABLMStudioUnavailable",
        "AI-LABNoRoutableModels",
    ]
    for r in data["groups"][0]["rules"]:
        if "alert" in r:
            if r["alert"] in critical_alerts:
                assert r["labels"]["severity"] == "critical", \
                    f"{r['alert']} should be critical, got {r['labels']['severity']}"
            else:
                assert r["labels"]["severity"] == "warning", \
                    f"{r['alert']} should be warning, got {r['labels']['severity']}"


def test_all_categories_are_used():
    data = _load_rules()
    categories = {r["labels"]["category"] for r in data["groups"][0]["rules"] if "alert" in r}
    assert categories == EXPECTED_CATEGORIES, f"Missing categories: {EXPECTED_CATEGORIES - categories}"


def test_all_alerts_have_annotations():
    data = _load_rules()
    for r in data["groups"][0]["rules"]:
        if "alert" in r:
            assert "annotations" in r, f"Missing annotations in {r['alert']}"
            assert "summary" in r["annotations"], f"Missing summary in {r['alert']}"
            assert "description" in r["annotations"], f"Missing description in {r['alert']}"


def test_expr_not_empty():
    data = _load_rules()
    for r in data["groups"][0]["rules"]:
        if "alert" in r:
            expr = r.get("expr", "")
            assert expr, f"Empty expr in {r['alert']}"


def test_recording_rules_have_valid_expr():
    data = _load_rules()
    for r in data["groups"][1]["rules"]:
        if "record" in r:
            expr = r.get("expr", "")
            assert expr, f"Empty expr in {r['record']}"
            assert isinstance(expr, str), f"expr not string in {r['record']}"


def test_recording_rules_no_labels():
    data = _load_rules()
    for r in data["groups"][1]["rules"]:
        if "record" in r:
            assert "labels" not in r, f"Recording rule {r['record']} should not have labels"


def test_alert_labels_are_deterministic():
    data = _load_rules()
    for r in data["groups"][0]["rules"]:
        if "alert" in r:
            labels = r["labels"]
            assert isinstance(labels, dict)
            for k, v in labels.items():
                assert isinstance(k, str)
                assert isinstance(v, str)


def test_no_alerts_with_same_expr_different_name():
    data = _load_rules()
    expr_to_names = {}
    for r in data["groups"][0]["rules"]:
        if "alert" in r:
            expr = str(r.get("expr", ""))
            expr_to_names.setdefault(expr, []).append(r["alert"])
    for expr, names in expr_to_names.items():
        assert len(names) == 1, f"Duplicate expr '{expr}' in alerts: {names}"


def test_increase_ranges_are_valid():
    data = _load_rules()
    valid_ranges = ["5m", "10m"]
    for r in data["groups"][0]["rules"]:
        if "alert" in r:
            expr = str(r.get("expr", ""))
            if "increase(" in expr or "rate(" in expr:
                has_valid_range = any(f"[{vr}]" in expr for vr in valid_ranges)
                assert has_valid_range, f"Invalid range in {r['alert']}: {expr}"


def test_no_unbounded_labels():
    data = _load_rules()
    for r in data["groups"][0]["rules"]:
        if "alert" in r:
            for k in r["labels"]:
                assert k not in ("alertname", "job", "instance"), \
                    f"Unbounded label {k} in {r['alert']}"
            for k in r.get("annotations", {}):
                assert k not in ("alertname", "job", "instance"), \
                    f"Unbounded label {k} in annotations of {r['alert']}"


def test_recording_rule_expr_parses():
    data = _load_rules()
    for r in data["groups"][1]["rules"]:
        if "record" in r:
            expr = r["expr"]
            assert "clamp_max" in expr or "rate" in expr or "(" in expr, \
                f"Recording rule {r['record']} has overly simple expr"
            assert len(expr) > 10, f"Recording rule {r['record']} expr too short"


def test_architecture_risk_score_bounded():
    data = _load_rules()
    for r in data["groups"][1]["rules"]:
        if r.get("record") == "ai_lab:architecture_risk_score":
            expr = r["expr"]
            assert "clamp_max" in expr, "architecture_risk_score should use clamp_max"


def test_runtime_health_score_normalized():
    data = _load_rules()
    for r in data["groups"][1]["rules"]:
        if r.get("record") == "ai_lab:runtime_health_score":
            expr = r["expr"]
            assert "/ 5" in expr, "runtime_health_score should be normalized by 5"


def test_rules_file_size_bounded():
    size = os.path.getsize(RULES_PATH)
    assert size < 50000, f"Rules file too large: {size} bytes"


def test_alerts_have_no_sensitive_data():
    data = _load_rules()
    raw = RULES_PATH.read_text()
    sensitive = ["password", "secret", "token", "api_key"]
    for word in sensitive:
        assert word not in raw.lower(), f"Sensitive word '{word}' found in rules"


def test_alerting_validator_module():
    from runtime.observability.alerting_validator import (
        ALERTING_CONTRACT_VERSION,
        AlertState,
        RecordingRuleState,
        AlertingValidationResult,
        count_critical_firing,
        count_warning_firing,
    )
    assert ALERTING_CONTRACT_VERSION == "PROMETHEUS-ALERTING-COGNITIVE-01"
    a = AlertState(name="test", state="firing", severity="critical")
    assert a.to_dict()["name"] == "test"
    r = RecordingRuleState(name="test_rec", value=1.0)
    assert r.to_dict()["name"] == "test_rec"
    vr = AlertingValidationResult(
        contract_version="v1", timestamp=100.0,
        prometheus_reachable=True, gateway_reachable=True,
    )
    d = vr.to_dict()
    assert d["contract_version"] == "v1"
    assert d["prometheus_reachable"] is True
    assert count_critical_firing([{"severity": "critical", "state": "firing"}]) == 1
    assert count_warning_firing([{"severity": "warning", "state": "firing"}]) == 1
    assert count_critical_firing([{"severity": "warning", "state": "firing"}]) == 0


def test_validator_failsafe_on_unreachable():
    from runtime.observability.alerting_validator import validate_prometheus_rules
    result = validate_prometheus_rules(now=1000.0)
    assert result.contract_version == "PROMETHEUS-ALERTING-COGNITIVE-01"
    assert isinstance(result.prometheus_reachable, bool)
    assert isinstance(result.gateway_reachable, bool)
    assert isinstance(result.errors, list)


def test_get_alerting_summary():
    from runtime.observability.alerting_validator import get_alerting_summary
    summary = get_alerting_summary(now=1000.0)
    assert "contract_version" in summary
    assert "critical_firing" in summary
    assert "warning_firing" in summary
    assert "prometheus_reachable" in summary
    assert "gateway_reachable" in summary
    assert "alerts" in summary
    assert "recording_rules" in summary
