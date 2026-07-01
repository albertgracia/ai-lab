# SLO Enforcement

## Overview

AI-LAB implements a **read-only SLO enforcement evaluation layer** that continuously evaluates whether the platform is operating inside defined Service Level Objectives. Collects live metrics from Gateway, Router, Prometheus, GPU exporter, and governance endpoints, evaluates against SLO targets, calculates budget and burn rate, and produces structured SLO reports.

No enforcement actions. No mutations. Read-only evaluation.

**Contract version:** `SLO-ENFORCEMENT-01`

## What It Does

| Function | Description |
|----------|-------------|
| `collect_slo_snapshot()` | Collects live data from all SLO-relevant endpoints (Gateway, Router, Prometheus, Live API, GPU) |
| `evaluate_slos()` | Evaluates all SLO definitions against the current snapshot |
| `build_slo_report()` | Builds a complete SLO report with evaluations, budget, burn rate, and recommendations |

## What It Does NOT Do

| Not done | Reason |
|----------|--------|
| Auto-remediation | Hardcoded `safe_to_auto_execute: false` |
| Mutations | Read-only — no state changes, no service restarts, no code changes |
| Execute enforcement actions | Detection and recommendation only |
| Background loops | Synchronous request/response only |

## SLO Definitions (13 SLOs)

| SLO ID | Component | Target | Warning | Critical | Higher Is Better |
|--------|-----------|--------|---------|----------|-----------------|
| `gateway_availability` | gateway | 1.0 | 0.95 | 0.80 | Yes |
| `router_availability` | router | 1.0 | 0.95 | 0.80 | Yes |
| `slo_endpoint_operational` | slo | 1.0 | 0.95 | 0.80 | Yes |
| `cognitive_health_score` | runtime | 70.0 | 60.0 | 40.0 | Yes |
| `gateway_latency_p50` | gateway | 2000ms | 3000ms | 5000ms | No |
| `gateway_latency_p95` | gateway | 8000ms | 12000ms | 20000ms | No |
| `degradation_normal` | runtime | 0 | 1 | 2 | No |
| `prometheus_targets_up` | observability | 1.0 | 0.5 | 0.0 | Yes |
| `gpu_rx9070_online` | gpu | 1.0 | 0.5 | 0.0 | Yes |
| `operator_intent_operational` | governance | 1.0 | 0.5 | 0.0 | Yes |
| `observability_triage_operational` | governance | 1.0 | 0.5 | 0.0 | Yes |
| `validation_authority_operational` | governance | 1.0 | 0.5 | 0.0 | Yes |
| `live_api_operational` | runtime | 1.0 | 0.5 | 0.0 | Yes |

## Evaluation Model

Each SLO is evaluated independently against the live snapshot:

1. **Data collection**: Collect live metrics from Gateway `/health`, `/slo/health`, Router `/health`, Router `/runtime/health/latency`, Prometheus `/api/v1/targets`, Live API `/api/status.json`, and governance endpoints
2. **Value extraction**: Extract the current value for each SLO from the snapshot
3. **Threshold comparison**: Compare against target, warning threshold, and critical threshold
4. **Status classification**: pass / warning / critical / insufficient_data
5. **Budget and burn rate**: Budget remaining (0-1) and burn rate based on distance from target

### Status Logic (higher_is_better)

| Condition | Status | Severity |
|-----------|--------|----------|
| value >= target | pass | info |
| value >= warning threshold | pass | info |
| value > critical threshold | warning | warning |
| value <= critical threshold | critical | critical |

### Status Logic (lower_is_better)

| Condition | Status | Severity |
|-----------|--------|----------|
| value <= target | pass | info |
| value <= warning threshold | pass | info |
| value < critical threshold | warning | warning |
| value >= critical threshold | critical | critical |

## Budget & Burn Rate

- **Budget remaining**: 0.0-1.0 based on distance from critical threshold to target
- **Burn rate**: 1.0 - budget (0 when no budget consumed)
- **Global burn rate**: critical ratio / max(1 - healthy ratio, 0.01)

## Schema

### GET /api/slo/status (compact)

```json
{
  "route_family": "cognitive",
  "overall_status": "pass | warning | critical",
  "total_slos": 13,
  "pass": 13,
  "warning": 0,
  "critical": 0,
  "critical_slos": [],
  "warning_slos": [],
  "requires_approval": false,
  "safe_to_auto_execute": false,
  "contract_version": "SLO-ENFORCEMENT-01"
}
```

### GET /api/slo/report (full)

```json
{
  "route_family": "cognitive",
  "report": {
    "report_id": "SLO-1748736000",
    "timestamp": 1748736000.0,
    "overall_status": "pass",
    "overall_severity": "info",
    "contract_version": "SLO-ENFORCEMENT-01",
    "evaluation_window_seconds": 300,
    "snapshot": { ... },
    "slos": [
      {
        "slo_id": "gateway_availability",
        "component": "gateway",
        "objective": "Gateway /health responds 200",
        "current_value": 1.0,
        "target": 1.0,
        "status": "pass",
        "severity": "info",
        "unit": "ratio",
        "budget_remaining": 1.0,
        "burn_rate": 0.0,
        "confidence": 0.9,
        "evidence": ["gateway_health_200:http://192.168.1.30:8008/health"],
        "recommendation": "No action required",
        "requires_approval": false,
        "safe_to_auto_execute": false
      }
    ],
    "budget": {
      "total_slos": 13,
      "pass": 13,
      "warning": 0,
      "critical": 0,
      "insufficient_data": 0,
      "healthy_ratio": 1.0,
      "critical_ratio": 0.0,
      "burn_rate": 0.0,
      "budget_remaining": 1.0
    },
    "critical_slos": [],
    "warning_slos": [],
    "recommendations": [],
    "requires_approval": false,
    "safe_to_auto_execute": false
  }
}
```

## Data Sources

| SLO | Source Endpoint | Port |
|-----|----------------|------|
| Gateway availability | `GET /health` | 8008 |
| Router availability | `GET /health` | 8083 |
| SLO endpoint | `GET /slo/health` | 8008 |
| Cognitive health | `GET /runtime/health/latency` | 8083 |
| Prometheus targets | `GET /api/v1/targets` | 9090 |
| GPU status | `GET /api/status.json` | 8084 |
| Governance endpoints | `GET /api/operator/intent`, triage, validation | 8084 |

## Deployment

- Endpoints: `GET /api/slo/status` and `GET /api/slo/report`
- Available through: Live API (port 8084)
- No configuration required — reads environment variables for URLs:
  - `AI_LAB_GATEWAY_URL` (default: `http://192.168.1.30:8008`)
  - `AI_LAB_ROUTER_URL` (default: `http://192.168.1.30:8083`)
  - `AI_LAB_LIVE_API_URL` (default: `http://192.168.1.30:8084`)
  - `AI_LAB_PROMETHEUS_URL` (default: `http://192.168.1.40:9090`)

## Limitations

- `safe_to_auto_execute` is hardcoded `false` — no auto-remediation in this phase
- SLOs are evaluated on request (synchronous), not continuously
- Budget and burn rate are point-in-time (no historical sliding window in this layer)
- Latency and health data depend on Router `/runtime/health/*` endpoints
- Governance SLOs check endpoint availability only, not semantic correctness
- No integration with the existing `cognitive_slo.py` framework (separate evaluation layer)
