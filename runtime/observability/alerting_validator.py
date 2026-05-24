"""PROMETHEUS-ALERTING-COGNITIVE-01: bounded, fail-safe alerting validation.

Read-only validation of Prometheus rule states, metric availability,
and alert firing conditions. Never modifies runtime state.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.request import urlopen, Request
from urllib.error import URLError


ALERTING_CONTRACT_VERSION = "PROMETHEUS-ALERTING-COGNITIVE-01"

_RULES_ENDPOINT = "http://192.168.1.40:9090/api/v1/rules"
_METRICS_ENDPOINT = "http://192.168.1.30:8008/metrics"
_GATEWAY_HEALTH = "http://192.168.1.30:8008/health"
_GUARDS_SUMMARY = "http://192.168.1.30:8008/runtime/guards/summary"
_SLO_STATUS = "http://192.168.1.30:8008/runtime/slo/status"

_TIMEOUT = 10
_MAX_RESULTS = 50


@dataclass(frozen=True)
class AlertState:
    name: str
    state: str
    severity: str
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    value: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "severity": self.severity,
            "labels": dict(self.labels),
            "annotations": dict(self.annotations),
            "value": float(self.value),
        }


@dataclass(frozen=True)
class RecordingRuleState:
    name: str
    value: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": float(self.value) if self.value is not None else None,
        }


@dataclass(frozen=True)
class AlertingValidationResult:
    contract_version: str
    timestamp: float
    prometheus_reachable: bool
    gateway_reachable: bool
    alerts: list[dict[str, Any]] = field(default_factory=list)
    recording_rules: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "timestamp": float(self.timestamp),
            "prometheus_reachable": self.prometheus_reachable,
            "gateway_reachable": self.gateway_reachable,
            "alerts_count": len(self.alerts),
            "recording_rules_count": len(self.recording_rules),
            "alerts": list(self.alerts),
            "recording_rules": list(self.recording_rules),
            "errors": list(self.errors),
        }


def _fetch_json(url: str, *, timeout: int = _TIMEOUT) -> dict[str, Any] | None:
    try:
        req = Request(url, method="GET")
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, OSError, json.JSONDecodeError, ValueError) as exc:
        return None


def validate_prometheus_rules(*, now: float | None = None) -> AlertingValidationResult:
    ts = now if now is not None else time.time()
    errors: list[str] = []

    rules_data = _fetch_json(_RULES_ENDPOINT)
    prometheus_reachable = rules_data is not None
    if not prometheus_reachable:
        errors.append("prometheus_unreachable")

    alerts: list[AlertState] = []
    recording_rules: list[RecordingRuleState] = []

    if rules_data:
        try:
            groups = rules_data.get("data", {}).get("groups", [])
            for group in groups:
                for rule in group.get("rules", []):
                    rtype = rule.get("type", "")
                    rname = rule.get("name", "unknown")
                    if rtype == "alerting":
                        alerts.append(AlertState(
                            name=rname,
                            state=rule.get("state", "unknown"),
                            severity=rule.get("labels", {}).get("severity", "unknown"),
                            labels=rule.get("labels", {}),
                            annotations=rule.get("annotations", {}),
                            value=rule.get("health", "ok") == "ok" and 1.0 or 0.0,
                        ))
                    elif rtype == "recording":
                        recording_rules.append(RecordingRuleState(
                            name=rname,
                            value=rule.get("health", "ok") == "ok" and 1.0 or 0.0,
                        ))
        except Exception as exc:
            errors.append(f"parse_error: {exc}")

    alerts_sorted = sorted(alerts, key=lambda a: (a.severity, a.name))
    alerts_limited = alerts_sorted[:_MAX_RESULTS]

    gateway_data = _fetch_json(_GATEWAY_HEALTH)
    gateway_reachable = gateway_data is not None

    return AlertingValidationResult(
        contract_version=ALERTING_CONTRACT_VERSION,
        timestamp=ts,
        prometheus_reachable=prometheus_reachable,
        gateway_reachable=gateway_reachable,
        alerts=[a.to_dict() for a in alerts_limited],
        recording_rules=[r.to_dict() for r in recording_rules],
        errors=errors,
    )


def count_critical_firing(alerts: list[dict[str, Any]]) -> int:
    return sum(
        1 for a in alerts
        if a.get("severity") == "critical" and a.get("state") == "firing"
    )


def count_warning_firing(alerts: list[dict[str, Any]]) -> int:
    return sum(
        1 for a in alerts
        if a.get("severity") == "warning" and a.get("state") == "firing"
    )


def get_alerting_summary(*, now: float | None = None) -> dict[str, Any]:
    result = validate_prometheus_rules(now=now)
    d = result.to_dict()
    d["critical_firing"] = count_critical_firing(d.get("alerts", []))
    d["warning_firing"] = count_warning_firing(d.get("alerts", []))
    return d
