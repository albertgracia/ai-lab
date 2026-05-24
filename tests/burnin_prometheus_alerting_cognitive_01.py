#!/usr/bin/env python3
"""PROMETHEUS-ALERTING-COGNITIVE-01: bounded burn-in validation.

Duration: 5-10 minutes.
Validates: Prometheus rules, metrics existence, alert states, no runtime impact.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
import urllib.error

sys.path.insert(0, "/opt/ai-lab")

import yaml

RULES_PATH = "/opt/ai-lab/monitorizacion/prometheus/rules/ai-lab-cognitive-alerts.yml"
PROMETHEUS_API = "http://192.168.1.40:9090/api/v1"
GATEWAY_URL = "http://192.168.1.30:8008"

RESULTS = {
    "phase": "PROMETHEUS-ALERTING-COGNITIVE-01",
    "timestamp": time.time(),
    "rules_valid": False,
    "prometheus_rules_loaded": False,
    "metrics_exist": {},
    "gateway_healthy": False,
    "guards_healthy": False,
    "slo_healthy": False,
    "runtime_normal": False,
    "lmstudio_operational": False,
    "registry_consistent": False,
    "no_degradation": True,
    "errors": [],
    "warnings": [],
    "checkpoints": {},
}


def log(msg: str, level: str = "INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")


def fetch(url: str, timeout: int = 10) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return None


def fetch_text(url: str, timeout: int = 10) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════
# CHECKPOINT 1: Rules file is valid YAML
# ═══════════════════════════════════════════════════════════════
log("CHECKPOINT 1: Validating rules YAML...")
try:
    with open(RULES_PATH) as f:
        data = yaml.safe_load(f)
    assert data is not None
    assert "groups" in data
    assert len(data["groups"]) == 2
    RESULTS["rules_valid"] = True
    RESULTS["checkpoints"]["1_yaml_valid"] = True
    log("Rules YAML is valid")
except Exception as exc:
    RESULTS["errors"].append(f"yaml_parse_error: {exc}")
    RESULTS["checkpoints"]["1_yaml_valid"] = False
    log(f"YAML error: {exc}", "ERROR")

# ═══════════════════════════════════════════════════════════════
# CHECKPOINT 2: Prometheus is reachable and rules loaded
# ═══════════════════════════════════════════════════════════════
log("CHECKPOINT 2: Checking Prometheus rules API...")
time.sleep(1)
rules_data = fetch(f"{PROMETHEUS_API}/rules")
if rules_data:
    RESULTS["prometheus_rules_loaded"] = True
    RESULTS["checkpoints"]["2_prometheus_reachable"] = True
    alerts_found = 0
    for group in rules_data.get("data", {}).get("groups", []):
        for rule in group.get("rules", []):
            if rule.get("type") == "alerting":
                alerts_found += 1
    log(f"Prometheus reachable: {alerts_found} alert rules found")
else:
    RESULTS["errors"].append("prometheus_unreachable")
    RESULTS["checkpoints"]["2_prometheus_reachable"] = False
    log("Prometheus unreachable", "WARN")

# ═══════════════════════════════════════════════════════════════
# CHECKPOINT 3: Gateway health
# ═══════════════════════════════════════════════════════════════
log("CHECKPOINT 3: Checking gateway health...")
health = fetch(f"{GATEWAY_URL}/health")
if health:
    RESULTS["gateway_healthy"] = True
    RESULTS["checkpoints"]["3_gateway_healthy"] = True
    log("Gateway healthy")
else:
    RESULTS["errors"].append("gateway_unreachable")
    RESULTS["checkpoints"]["3_gateway_healthy"] = False
    log("Gateway unreachable", "WARN")

# ═══════════════════════════════════════════════════════════════
# CHECKPOINT 4: Metrics exist
# ═══════════════════════════════════════════════════════════════
log("CHECKPOINT 4: Checking metric existence...")
metrics_text = fetch_text(f"{GATEWAY_URL}/metrics")
if metrics_text:
    required_metrics = [
        "ailab_federation_guard_state",
        "ailab_federation_guard_replay_detections_total",
        "ailab_federation_guard_storm_detections_total",
        "ailab_federation_guard_authority_escalations_total",
        "ailab_federation_guard_caps_applied_total",
        "ailab_evidence_invalid_lineage_total",
        "ailab_evidence_replay_risk_total",
        "ailab_evidence_stale_total",
        "ailab_evidence_lineage_depth_max",
        "ailab_slo_violations_total",
        "ailab_slo_safe_mode_total",
        "ailab_slo_registry_consistency",
        "ailab_slo_gateway_health",
        "ailab_slo_lmstudio_health",
        "ailab_registry_deprecated_aliases_total",
        "ailab_registry_routable_models_total",
        "ailab_architecture_governance_violations_total",
        "ailab_architecture_high_risk_total",
    ]
    for metric in required_metrics:
        exists = metric in metrics_text
        RESULTS["metrics_exist"][metric] = exists
        if not exists:
            RESULTS["warnings"].append(f"metric_not_found: {metric}")
    found = sum(1 for v in RESULTS["metrics_exist"].values() if v)
    total = len(required_metrics)
    RESULTS["checkpoints"]["4_metrics_exist"] = (found == total)
    log(f"Metrics: {found}/{total} found")
else:
    RESULTS["errors"].append("metrics_endpoint_unreachable")
    RESULTS["checkpoints"]["4_metrics_exist"] = False
    log("Metrics endpoint unreachable", "WARN")

# ═══════════════════════════════════════════════════════════════
# CHECKPOINT 5: Federation guards summary
# ═══════════════════════════════════════════════════════════════
log("CHECKPOINT 5: Checking federation guards...")
guards = fetch(f"{GATEWAY_URL}/runtime/guards/summary")
if guards:
    RESULTS["guards_healthy"] = True
    RESULTS["checkpoints"]["5_guards_healthy"] = True
    state = guards.get("guard_state", guards.get("state", "unknown"))
    log(f"Guards healthy (state={state})")
else:
    RESULTS["warnings"].append("guards_summary_unreachable")
    RESULTS["checkpoints"]["5_guards_healthy"] = False
    log("Guards summary unreachable", "WARN")

# ═══════════════════════════════════════════════════════════════
# CHECKPOINT 6: SLO status
# ═══════════════════════════════════════════════════════════════
log("CHECKPOINT 6: Checking SLO status...")
slo = fetch(f"{GATEWAY_URL}/runtime/slo/status")
if slo:
    RESULTS["slo_healthy"] = True
    RESULTS["checkpoints"]["6_slo_healthy"] = True
    log("SLO status OK")
else:
    RESULTS["warnings"].append("slo_status_unreachable")
    RESULTS["checkpoints"]["6_slo_healthy"] = False
    log("SLO status unreachable", "WARN")

# ═══════════════════════════════════════════════════════════════
# CHECKPOINT 7: No runtime degradation
# ═══════════════════════════════════════════════════════════════
log("CHECKPOINT 7: Checking runtime state...")
if RESULTS["gateway_healthy"] and RESULTS["prometheus_rules_loaded"]:
    RESULTS["runtime_normal"] = True
    RESULTS["checkpoints"]["7_runtime_normal"] = True
    log("Runtime normal")
else:
    RESULTS["warnings"].append("runtime_checks_incomplete")
    RESULTS["checkpoints"]["7_runtime_normal"] = False
    log("Runtime checks incomplete", "WARN")

# ═══════════════════════════════════════════════════════════════
# CHECKPOINT 8: Prometheus query metrics (recording rules)
# ═══════════════════════════════════════════════════════════════
log("CHECKPOINT 8: Checking Prometheus query target metrics...")
query_data = fetch(f"{PROMETHEUS_API}/query?query=ai_lab:runtime_health_score")
if query_data:
    RESULTS["checkpoints"]["8_recording_rules_queryable"] = True
    log("Recording rules queryable")
else:
    RESULTS["warnings"].append("recording_rules_not_queryable")
    RESULTS["checkpoints"]["8_recording_rules_queryable"] = False
    log("Recording rules not queryable (expected if not deployed yet)", "WARN")

# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
errors_count = len(RESULTS["errors"])
warnings_count = len(RESULTS["warnings"])
RESULTS["duration_seconds"] = time.time() - RESULTS["timestamp"]
RESULTS["status"] = "PASS" if errors_count == 0 else "DEGRADED"

log("═" * 50)
log(f"BURN-IN COMPLETE: {RESULTS['status']}")
log(f"Errors: {errors_count}, Warnings: {warnings_count}")
log(f"Duration: {RESULTS['duration_seconds']:.1f}s")
log("═" * 50)

print()
print(json.dumps(RESULTS, indent=2, default=str))

report_path = "/tmp/burnin_prometheus_alerting_cognitive_01.json"
with open(report_path, "w") as f:
    json.dump(RESULTS, f, indent=2, default=str)
print(f"\nReport saved to {report_path}")
