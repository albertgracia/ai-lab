# Autonomous Observability Triage

## Overview

AI-LAB implements a **read-only autonomous observability triage layer** that:

- Collects live Prometheus targets snapshot
- Integrates with the existing runtime triage engine (FASE 36D)
- Links findings to Operator Intent Reasoning (FASE 36C)
- Produces structured triage reports with evidence, severity, causes, impact, and safe next steps

**Contract version:** `OBSERVABILITY-TRIAGE-01`

## What It Does

| Function | Description |
|----------|-------------|
| `collect_prometheus_snapshot()` | Fetches live Prometheus targets, returns structured snapshot (active/down targets, fetch time) |
| `build_observability_triage_report()` | Combines Prometheus data + runtime triage incidents + optional operator intent into a complete report |

## What It Does NOT Do

| Not done | Reason |
|----------|--------|
| Auto-remediation | Hardcoded `safe_to_auto_execute: false` |
| Mutations | Read-only — no state changes, no service restarts |
| Background loops | Synchronous request/response only |
| Prometheus/Grafana config changes | Not scraped or modified |

## Severity Model

| Severity | Criteria |
|----------|----------|
| `info` | All targets up, no active triage incidents |
| `medium` | 1 target down, or warning-level triage incidents |
| `high` | 2-3 targets down, fetch error, or high-severity incidents |
| `critical` | 4+ targets down, no targets reachable, or critical incidents |

## Schema (GET /api/observability/triage)

```json
{
  "triage_id": "OBS-TRIAGE-<timestamp>-<incident_count>",
  "timestamp": 1782919774.0,
  "source": "observability_triage",
  "component": "prometheus_targets",
  "components_affected": ["prometheus_targets", "slo_degradation"],
  "status": "active | healthy",
  "severity": "info | medium | high | critical",
  "symptom": "Human-readable symptom description",
  "evidence": ["prometheus_targets:active=10,down=0,fetch_ms=42", "target_down:ai-lab-gpu-rx7900xt/1.60:9182"],
  "evidence_summary": {
    "active_prometheus_targets": 10,
    "down_prometheus_targets": 0,
    "active_triage_incidents": 2,
    "prometheus_status": "ok | error",
    "sources_available": ["prometheus_api", "runtime_triage"]
  },
  "likely_causes": ["scrape_target_down:ai-lab-gpu-rx7900xt", "LM Studio unavailable"],
  "likely_root_causes": [{"cause": "...", "confidence": "medium", "source": "heuristic"}],
  "confidence": 0.85,
  "impact": "2/10 Prometheus targets down; 1 high, 0 critical active incidents",
  "recommended_actions": [
    {
      "action": "investigate_down_target:ai-lab-gpu-rx7900xt",
      "target": "1.60:9182",
      "reason": "Prometheus target is down",
      "requires_approval": true,
      "safe_to_auto_execute": false
    }
  ],
  "requires_approval": true,
  "safe_to_auto_execute": false,
  "operator_intent_link": null,
  "next_validation_commands": [
    "curl -s http://192.168.1.30:8008/health | jq .",
    "curl -s 'http://192.168.1.40:9090/api/v1/targets' | jq ..."
  ],
  "contract_version": "OBSERVABILITY-TRIAGE-01",
  "prometheus_snapshot": {"status": "ok", "active_total": 10, "down_total": 0, "fetch_time_ms": 42},
  "triage_summary": {"total_incidents": 0, "total_critical": 0, "total_high": 0, "total_warning": 0}
}
```

## Evidence Model

Every triage report includes:

1. **Prometheus targets evidence**: active/down counts, fetch time, per-target health
2. **Runtime triage evidence**: incidents from FASE 36D autonomous triage engine
3. **Operator intent evidence** (optional): classification, risk, approval requirements
4. **Sources available**: which data sources were reachable/unreachable

Evidence is bounded to 20 entries maximum.

## Operator Approval Model

| Condition | `requires_approval` |
|-----------|-------------------|
| Severity `info` or `medium` | `false` |
| Severity `high` or `critical` | `true` |
| Any action targeting down targets | `true` |
| Prometheus unreachable | `true` |

`safe_to_auto_execute` is always `false` in this phase.

## API Endpoint

```
GET /api/observability/triage
  ?operator_intent=<text>       # optional: link triage to operator intent
```

**Live API** (port 8084): `http://192.168.1.30:8084/api/observability/triage`

**Gateway** (port 8008): `http://192.168.1.30:8008/runtime/triage/*` (FASE 36D endpoints)

## Integration with Operator Intent

When `?operator_intent=why+is+gateway+slow` is passed, the triage report includes:

```json
"operator_intent_link": {
  "input": "why is gateway slow",
  "classification": "observability_query",
  "risk": "low",
  "requires_approval": false
}
```

## Future Remediation Path

When auto-remediation is enabled (future phase):

1. Triage identifies incident with evidence
2. Classification determines safe-to-auto-execute
3. Operator consent via `requires_approval` flag
4. Execution via `runtime/observability/remediation_executor.py`
5. Post-remediation validation via triage re-run

## Implementation Files

| File | Purpose |
|------|---------|
| `runtime/observability/observability_triage.py` | Triage engine: Prometheus snapshot + report builder |
| `runtime/state/live_api.py` | Live API endpoint `/api/observability/triage` |
| `tests/test_observability_triage.py` | 34 tests (schema, severity, evidence, operator intent, safety) |
| `docs/observability/AUTONOMOUS-OBSERVABILITY-TRIAGE.md` | This document |

## Tests

```bash
python -m unittest tests.test_observability_triage -v
```

34 tests covering: schema, severity classification, evidence collection, operator intent linking, `safe_to_auto_execute` enforcement, `requires_approval` logic, next validation commands, fail-safe on unavailable sources.
