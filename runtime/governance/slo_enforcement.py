"""AI-LAB SLO Enforcement — read-only SLO evaluation layer.

Collects live metrics, evaluates against defined Service Level Objectives,
calculates budget and burn rate, and produces structured SLO reports.

NO enforcement actions. NO mutations. Read-only evaluation.
"""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

SLO_ENFORCEMENT_CONTRACT_VERSION = "SLO-ENFORCEMENT-01"
SAFE_TO_AUTO_EXECUTE = False

GATEWAY_BASE = os.environ.get("AI_LAB_GATEWAY_URL", "http://192.168.1.30:8008")
ROUTER_BASE = os.environ.get("AI_LAB_ROUTER_URL", "http://192.168.1.30:8083")
LIVE_API_BASE = os.environ.get("AI_LAB_LIVE_API_URL", "http://192.168.1.30:8084")
PROMETHEUS_BASE = os.environ.get("AI_LAB_PROMETHEUS_URL", "http://192.168.1.40:9090")

DEFAULT_TIMEOUT = 5
HEALTHY_CACHE_TTL = 10  # seconds


def _http_get(url: str, timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return {"ok": True, "status": resp.status, "data": json.loads(body) if body else {}}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": str(e)}
    except urllib.error.URLError as e:
        return {"ok": False, "status": 0, "error": f"connection failed: {e.reason}"}
    except (json.JSONDecodeError, TimeoutError, OSError) as e:
        return {"ok": False, "status": 0, "error": str(e)}


SLO_DEFINITIONS: list[dict[str, Any]] = [
    {
        "slo_id": "gateway_availability",
        "component": "gateway",
        "description": "Gateway /health responds 200",
        "target": 1.0,
        "warning_threshold": 0.95,
        "critical_threshold": 0.80,
        "higher_is_better": True,
        "unit": "ratio",
    },
    {
        "slo_id": "router_availability",
        "component": "router",
        "description": "Router /health responds 200",
        "target": 1.0,
        "warning_threshold": 0.95,
        "critical_threshold": 0.80,
        "higher_is_better": True,
        "unit": "ratio",
    },
    {
        "slo_id": "slo_endpoint_operational",
        "component": "slo",
        "description": "Gateway /slo/health responds 200",
        "target": 1.0,
        "warning_threshold": 0.95,
        "critical_threshold": 0.80,
        "higher_is_better": True,
        "unit": "ratio",
    },
    {
        "slo_id": "cognitive_health_score",
        "component": "runtime",
        "description": "Cognitive health score > 70",
        "target": 70.0,
        "warning_threshold": 60.0,
        "critical_threshold": 40.0,
        "higher_is_better": True,
        "unit": "score",
    },
    {
        "slo_id": "gateway_latency_p50",
        "component": "gateway",
        "description": "Gateway request latency p50 < 2000ms",
        "target": 2000.0,
        "warning_threshold": 3000.0,
        "critical_threshold": 5000.0,
        "higher_is_better": False,
        "unit": "ms",
    },
    {
        "slo_id": "gateway_latency_p95",
        "component": "gateway",
        "description": "Gateway request latency p95 < 8000ms",
        "target": 8000.0,
        "warning_threshold": 12000.0,
        "critical_threshold": 20000.0,
        "higher_is_better": False,
        "unit": "ms",
    },
    {
        "slo_id": "degradation_normal",
        "component": "runtime",
        "description": "Degradation level is NORMAL (0)",
        "target": 0,
        "warning_threshold": 1,
        "critical_threshold": 2,
        "higher_is_better": False,
        "unit": "level",
    },
    {
        "slo_id": "prometheus_targets_up",
        "component": "observability",
        "description": "At least one Prometheus target is up",
        "target": 1.0,
        "warning_threshold": 0.5,
        "critical_threshold": 0.0,
        "higher_is_better": True,
        "unit": "ratio",
    },
    {
        "slo_id": "gpu_rx9070_online",
        "component": "gpu",
        "description": "RX9070 GPU exporter is reachable",
        "target": 1.0,
        "warning_threshold": 0.5,
        "critical_threshold": 0.0,
        "higher_is_better": True,
        "unit": "boolean",
    },
    {
        "slo_id": "operator_intent_operational",
        "component": "governance",
        "description": "Operator Intent endpoint responds",
        "target": 1.0,
        "warning_threshold": 0.5,
        "critical_threshold": 0.0,
        "higher_is_better": True,
        "unit": "boolean",
    },
    {
        "slo_id": "observability_triage_operational",
        "component": "governance",
        "description": "Observability Triage endpoint responds",
        "target": 1.0,
        "warning_threshold": 0.5,
        "critical_threshold": 0.0,
        "higher_is_better": True,
        "unit": "boolean",
    },
    {
        "slo_id": "validation_authority_operational",
        "component": "governance",
        "description": "Validation Authority endpoint responds",
        "target": 1.0,
        "warning_threshold": 0.5,
        "critical_threshold": 0.0,
        "higher_is_better": True,
        "unit": "boolean",
    },
    {
        "slo_id": "live_api_operational",
        "component": "runtime",
        "description": "Live API responds to status check",
        "target": 1.0,
        "warning_threshold": 0.5,
        "critical_threshold": 0.0,
        "higher_is_better": True,
        "unit": "boolean",
    },
]

SLO_BUDGET_WINDOW_SECONDS = 300  # 5-minute evaluation window
BURN_RATE_WARNING = 0.7
BURN_RATE_CRITICAL = 1.0


def collect_slo_snapshot() -> dict[str, Any]:
    ts = time.time()
    gateway_health = _http_get(f"{GATEWAY_BASE}/health")
    slo_health = _http_get(f"{GATEWAY_BASE}/slo/health")
    router_health = _http_get(f"{ROUTER_BASE}/health")

    gateway_status = None
    slo_enabled = False
    slo_state = "disabled"
    degradation_level = 0
    if slo_health.get("ok"):
        sd = slo_health.get("data", {})
        slo_enabled = sd.get("enabled", False)
        slo_state = sd.get("state", "disabled")
        degradation_level = sd.get("degradation_level", sd.get("level", 0))

    if gateway_health.get("ok"):
        gd = gateway_health.get("data", {})
        gateway_status = {
            "service": gd.get("service", gd.get("status", "unknown")),
            "status": gd.get("status", gd.get("service", "unknown")),
            "uptime": gd.get("uptime", gd.get("uptime_seconds", 0)),
        }

    latency_p50 = None
    latency_p95 = None
    cognitive_health_score = None
    cognitive_health: dict[str, Any] = {}
    runtime_health = _http_get(f"{ROUTER_BASE}/runtime/health")
    if runtime_health.get("ok"):
        rh = runtime_health.get("data", {})
        cognitive_health = rh
        cognitive_health_score = rh.get("health_score", rh.get("score"))
    latency_ep = _http_get(f"{ROUTER_BASE}/runtime/health/latency")
    if latency_ep.get("ok"):
        ld = latency_ep.get("data", {})
        latency_p50 = ld.get("p50_ms") or ld.get("latency_p50_ms") or ld.get("p50")
        latency_p95 = ld.get("p95_ms") or ld.get("latency_p95_ms") or ld.get("p95")

    prometheus_snapshot: dict[str, Any] = {}
    prometheus_total = 0
    prometheus_up = 0
    prom = _http_get(f"{PROMETHEUS_BASE}/api/v1/targets")
    if prom.get("ok"):
        pd = prom.get("data", {})
        prometheus_snapshot = pd
        active = pd.get("data", {}).get("activeTargets", [])
        prometheus_total = len(active)
        prometheus_up = sum(1 for t in active if t.get("health") == "up")
    elif slo_health.get("ok") and slo_health["data"].get("prometheus"):
        ps = slo_health["data"]["prometheus"]
        prometheus_total = ps.get("total_targets", 0)
        prometheus_up = ps.get("up_targets", 0)
        prometheus_snapshot = ps

    gpu_online = False
    gpu = _http_get(f"{LIVE_API_BASE}/api/status.json")
    if gpu.get("ok"):
        gd = gpu.get("data", {})
        gpus = gd.get("gpu", [])
        for g in gpus:
            if g.get("node") == "RX9070":
                gpu_online = g.get("vram_total_gib", 0) > 0

    governance_endpoints: dict[str, bool] = {}
    for name, url in [
        ("operator_intent", f"{LIVE_API_BASE}/api/operator/intent?text=test"),
        ("observability_triage", f"{LIVE_API_BASE}/api/observability/triage"),
        ("validation_authority", f"{LIVE_API_BASE}/api/validation/authority?text=test"),
    ]:
        r = _http_get(url, timeout=3)
        governance_endpoints[name] = r.get("ok", False)

    live_api_ok = governance_endpoints.get("operator_intent", False) or gateway_health.get("ok", False)

    error_rate = None
    try:
        req = urllib.request.Request(f"{GATEWAY_BASE}/metrics")
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            metrics_text = resp.read().decode("utf-8")
            for line in metrics_text.splitlines():
                if line.startswith("ailab_errors_total "):
                    parts = line.split()
                    if len(parts) >= 2:
                        error_rate = float(parts[1])
    except Exception:
        pass

    return {
        "timestamp": ts,
        "gateway": {
            "health": gateway_health,
            "slo": {"enabled": slo_enabled, "state": slo_state, "degradation_level": degradation_level},
            "status": gateway_status,
            "latency_p50_ms": latency_p50,
            "latency_p95_ms": latency_p95,
            "error_rate": error_rate,
        },
        "router": {"health": router_health},
        "cognitive_health": cognitive_health,
        "cognitive_health_score": cognitive_health_score,
        "prometheus": {
            "total_targets": prometheus_total,
            "up_targets": prometheus_up,
            "raw": prometheus_snapshot,
        },
        "gpu": {"rx9070_online": gpu_online},
        "governance": governance_endpoints,
        "live_api_ok": live_api_ok,
    }


def _evaluate_single_slo(
    slo_def: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    slo_id = slo_def["slo_id"]
    higher_is_better = slo_def["higher_is_better"]
    target = slo_def["target"]
    warning_th = slo_def["warning_threshold"]
    critical_th = slo_def["critical_threshold"]

    current_value, evidence = _extract_slo_value(slo_id, snapshot)

    if current_value is None:
        return {
            "slo_id": slo_id,
            "component": slo_def["component"],
            "objective": slo_def["description"],
            "current_value": None,
            "target": target,
            "status": "insufficient_data",
            "severity": "unknown",
            "unit": slo_def["unit"],
            "budget_remaining": 0.0,
            "burn_rate": 0.0,
            "confidence": 0.0,
            "evidence": evidence,
            "recommendation": "No data available to evaluate this SLO",
            "requires_approval": False,
            "safe_to_auto_execute": SAFE_TO_AUTO_EXECUTE,
        }

    if higher_is_better:
        if current_value >= target:
            budget = min(1.0, (current_value - critical_th) / (target - critical_th)) if target != critical_th else 1.0
        else:
            budget = max(0.0, (current_value - critical_th) / (target - critical_th)) if target != critical_th else 0.0
    else:
        if current_value <= target:
            budget = min(1.0, (critical_th - current_value) / (critical_th - target)) if critical_th != target else 1.0
        else:
            budget = max(0.0, (critical_th - current_value) / (critical_th - target)) if critical_th != target else 0.0

    budget = max(0.0, min(1.0, budget))
    burn_rate = 1.0 - budget if budget < 1.0 else 0.0

    if higher_is_better:
        if current_value >= target:
            status = "pass"
            severity = "info"
        elif current_value >= warning_th:
            status = "pass"
            severity = "info"
        elif current_value > critical_th:
            status = "warning"
            severity = "warning"
        else:
            status = "critical"
            severity = "critical"
    else:
        if current_value <= target:
            status = "pass"
            severity = "info"
        elif current_value <= warning_th:
            status = "pass"
            severity = "info"
        elif current_value < critical_th:
            status = "warning"
            severity = "warning"
        else:
            status = "critical"
            severity = "critical"

    recommendation = _build_recommendation(slo_id, status, current_value, target)
    requires_approval = status in ("critical",)

    return {
        "slo_id": slo_id,
        "component": slo_def["component"],
        "objective": slo_def["description"],
        "current_value": current_value,
        "target": target,
        "status": status,
        "severity": severity,
        "unit": slo_def["unit"],
        "budget_remaining": round(budget, 4),
        "burn_rate": round(burn_rate, 4),
        "confidence": round(0.9 if current_value is not None else 0.0, 3),
        "evidence": evidence,
        "recommendation": recommendation,
        "requires_approval": requires_approval,
        "safe_to_auto_execute": SAFE_TO_AUTO_EXECUTE,
    }


def _extract_slo_value(
    slo_id: str,
    snapshot: dict[str, Any],
) -> tuple[Any, list[str]]:
    evidence: list[str] = []

    if slo_id == "gateway_availability":
        gwh = snapshot.get("gateway", {}).get("health", {})
        if gwh.get("ok") and gwh.get("status") == 200:
            evidence.append(f"gateway_health_200:{GATEWAY_BASE}/health")
            return 1.0, evidence
        evidence.append(f"gateway_health_failed:{gwh.get('error', 'unknown')}")
        return 0.0, evidence

    if slo_id == "router_availability":
        rh = snapshot.get("router", {}).get("health", {})
        if rh.get("ok") and rh.get("status") == 200:
            evidence.append(f"router_health_200:{ROUTER_BASE}/health")
            return 1.0, evidence
        evidence.append(f"router_health_failed:{rh.get('error', 'unknown')}")
        return 0.0, evidence

    if slo_id == "slo_endpoint_operational":
        sh = snapshot.get("gateway", {}).get("slo", {})
        if sh.get("enabled") or sh.get("state") != "disabled":
            evidence.append(f"slo_endpoint_enabled:{sh.get('state','unknown')}")
            return 1.0, evidence
        evidence.append(f"slo_endpoint_disabled_or_unreachable:{sh.get('state','unknown')}")
        return 0.0, evidence

    if slo_id == "cognitive_health_score":
        score = snapshot.get("cognitive_health_score")
        if score is not None:
            evidence.append(f"cognitive_health_score:{score}")
            return score, evidence
        evidence.append("cognitive_health_score:unavailable")
        return None, evidence

    if slo_id == "gateway_latency_p50":
        lat = snapshot.get("gateway", {}).get("latency_p50_ms")
        if lat is not None:
            evidence.append(f"gateway_latency_p50:{lat}ms")
            return lat, evidence
        evidence.append("gateway_latency_p50:unavailable")
        return None, evidence

    if slo_id == "gateway_latency_p95":
        lat = snapshot.get("gateway", {}).get("latency_p95_ms")
        if lat is not None:
            evidence.append(f"gateway_latency_p95:{lat}ms")
            return lat, evidence
        evidence.append("gateway_latency_p95:unavailable")
        return None, evidence

    if slo_id == "degradation_normal":
        dl = snapshot.get("gateway", {}).get("slo", {}).get("degradation_level", None)
        if dl is not None:
            evidence.append(f"degradation_level:{dl}")
            return dl, evidence
        evidence.append("degradation_level:unavailable")
        return None, evidence

    if slo_id == "prometheus_targets_up":
        up = snapshot.get("prometheus", {}).get("up_targets", 0)
        total = snapshot.get("prometheus", {}).get("total_targets", 0)
        ratio = up / max(total, 1)
        evidence.append(f"prometheus_targets:{up}/{total}")
        return ratio, evidence

    if slo_id == "gpu_rx9070_online":
        online = snapshot.get("gpu", {}).get("rx9070_online", False)
        evidence.append(f"gpu_rx9070_online:{online}")
        return 1.0 if online else 0.0, evidence

    if slo_id == "operator_intent_operational":
        ok = snapshot.get("governance", {}).get("operator_intent", False)
        evidence.append(f"operator_intent_endpoint:{ok}")
        return 1.0 if ok else 0.0, evidence

    if slo_id == "observability_triage_operational":
        ok = snapshot.get("governance", {}).get("observability_triage", False)
        evidence.append(f"observability_triage_endpoint:{ok}")
        return 1.0 if ok else 0.0, evidence

    if slo_id == "validation_authority_operational":
        ok = snapshot.get("governance", {}).get("validation_authority", False)
        evidence.append(f"validation_authority_endpoint:{ok}")
        return 1.0 if ok else 0.0, evidence

    if slo_id == "live_api_operational":
        ok = snapshot.get("live_api_ok", False)
        evidence.append(f"live_api_self_check:{ok}")
        return 1.0 if ok else 0.0, evidence

    return None, ["unknown_slo_id"]


def _build_recommendation(
    slo_id: str,
    status: str,
    current_value: Any,
    target: Any,
) -> str:
    if status == "pass":
        return "No action required"
    if status == "insufficient_data":
        return "Verify endpoint availability and connectivity"
    if status == "warning":
        RECS = {
            "gateway_availability": "Check gateway process and systemd status",
            "router_availability": "Check router process and port 8083",
            "slo_endpoint_operational": "Enable AI_LAB_ENABLE_SLO_ENFORCEMENT or verify SLO modules",
            "cognitive_health_score": "Review cognitive health layer for degradation sources",
            "gateway_latency_p50": "Investigate p50 latency increase — check GPU or model load",
            "gateway_latency_p95": "Investigate p95 latency spike — check streaming or queue backlog",
            "degradation_normal": "Runtime degradation is active — review DegradationManager",
            "prometheus_targets_up": "Check Prometheus targets and network connectivity to 1.40",
            "gpu_rx9070_online": "Verify GPU exporter on 192.168.1.50:9182",
            "operator_intent_operational": "Verify operator_intent module is importable",
            "observability_triage_operational": "Verify observability_triage module is importable",
            "validation_authority_operational": "Verify validation_authority module is importable",
            "live_api_operational": "Live API self-check failed — verify port 8084",
        }
        return RECS.get(slo_id, "Review SLO and check component health")
    if status == "critical":
        CRIT_RECS = {
            "gateway_availability": "CRITICAL: Gateway unreachable — immediate investigation required",
            "router_availability": "CRITICAL: Router unreachable — API routes may be degraded",
            "slo_endpoint_operational": "CRITICAL: SLO system unavailable — no runtime protection",
            "cognitive_health_score": "CRITICAL: Health score critically low — runtime may be unstable",
            "gateway_latency_p50": "CRITICAL: p50 latency exceeds critical threshold — service degradation",
            "gateway_latency_p95": "CRITICAL: p95 latency exceeds critical threshold — severe degradation",
            "degradation_normal": "CRITICAL: Degradation at critical level — emergency routing active",
            "prometheus_targets_up": "CRITICAL: No Prometheus targets reachable — observability blind",
            "gpu_rx9070_online": "CRITICAL: GPU RX9070 offline — inference unavailable",
            "operator_intent_operational": "CRITICAL: Operator Intent unavailable — governance incomplete",
            "observability_triage_operational": "CRITICAL: Observability Triage unavailable — governance incomplete",
            "validation_authority_operational": "CRITICAL: Validation Authority unavailable — governance incomplete",
            "live_api_operational": "CRITICAL: Live API unavailable — runtime observability broken",
        }
        return CRIT_RECS.get(slo_id, "CRITICAL: Immediate investigation required")
    return "Unknown SLO status"


def evaluate_slos(
    snapshot: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if snapshot is None:
        snapshot = collect_slo_snapshot()
    return [_evaluate_single_slo(slo, snapshot) for slo in SLO_DEFINITIONS]


def _calculate_burn_rate(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(evaluations)
    passed = sum(1 for e in evaluations if e["status"] == "pass")
    warning = sum(1 for e in evaluations if e["status"] == "warning")
    critical = sum(1 for e in evaluations if e["status"] == "critical")
    insufficient = sum(1 for e in evaluations if e["status"] == "insufficient_data")

    healthy_pct = passed / max(total, 1)
    critical_pct = critical / max(total, 1)

    burn_rate = round(critical_pct / max(1 - healthy_pct, 0.01), 4) if critical > 0 else 0.0

    return {
        "total_slos": total,
        "pass": passed,
        "warning": warning,
        "critical": critical,
        "insufficient_data": insufficient,
        "healthy_ratio": round(healthy_pct, 4),
        "critical_ratio": round(critical_pct, 4),
        "burn_rate": burn_rate,
        "budget_remaining": round(1.0 - critical_pct, 4),
        "timestamp": time.time(),
    }


def build_slo_report() -> dict[str, Any]:
    ts = time.time()
    snapshot = collect_slo_snapshot()
    evaluations = evaluate_slos(snapshot)
    burn = _calculate_burn_rate(evaluations)
    overall_status = "pass"
    overall_severity = "info"

    if burn["critical"] > 0:
        overall_status = "critical"
        overall_severity = "critical"
    elif burn["warning"] > 0:
        overall_status = "warning"
        overall_severity = "warning"

    critical_slos = [e for e in evaluations if e["status"] == "critical"]
    warning_slos = [e for e in evaluations if e["status"] == "warning"]

    recommendations: list[str] = []
    for e in critical_slos + warning_slos:
        rec = e["recommendation"]
        if rec and rec not in recommendations and rec != "No action required":
            recommendations.append(f"[{e['severity'].upper()}] {e['slo_id']}: {rec}")

    return {
        "report_id": f"SLO-{int(ts)}",
        "timestamp": ts,
        "overall_status": overall_status,
        "overall_severity": overall_severity,
        "contract_version": SLO_ENFORCEMENT_CONTRACT_VERSION,
        "evaluation_window_seconds": SLO_BUDGET_WINDOW_SECONDS,
        "snapshot": snapshot,
        "slos": evaluations,
        "budget": burn,
        "critical_slos": [e["slo_id"] for e in critical_slos],
        "warning_slos": [e["slo_id"] for e in warning_slos],
        "recommendations": recommendations,
        "requires_approval": overall_status == "critical",
        "safe_to_auto_execute": SAFE_TO_AUTO_EXECUTE,
    }
