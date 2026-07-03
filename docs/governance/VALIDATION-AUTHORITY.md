# Validation Authority

## Overview

AI-LAB implements a **read-only validation authority layer** that evaluates proposed actions against operator intent, observability triage, evidence availability, rollback requirements, and governance policy. No auto-execution. No mutations.

**Contract version:** `VALIDATION-AUTHORITY-01`

## What It Does

| Function | Description |
|----------|-------------|
| `build_validation_decision()` | Evaluates a proposed action request against all signals (intent, triage, evidence, rollback, governance) and returns a structured decision |
| `validate_action_request()` | Convenience wrapper for quick validation from plain text |
| `assess_evidence()` | Checks evidence completeness per action type against operator intent, triage status, and context |
| `assess_rollback()` | Determines rollback availability and auto-generates rollback steps for known action types |
| `assess_approval_requirement()` | Returns approval level (none/operator/admin/emergency) based on risk and action type |

## What It Does NOT Do

| Not done | Reason |
|----------|--------|
| Auto-execution | Hardcoded `safe_to_auto_execute: false` |
| Mutations | Read-only — no state changes, no service restarts, no code changes |
| Remediation | Decision engine only — execution is a separate domain |
| Background loops | Synchronous request/response only |
| Replace governance | Sits on top of operator intent, triage, and governance policy |

## Decision Model

Four decision outcomes:

| Decision | Meaning |
|----------|---------|
| `allow` | Action is safe to execute (read-only, low risk, or default/unknown) |
| `require_more_evidence` | Insufficient evidence for a risky action — provide missing evidence first |
| `require_approval` | Action needs approval at the specified level before execution |
| `block` | Action is too dangerous or violates policy — cannot proceed |

Approval levels:

| Level | Required For |
|-------|-------------|
| `none` | Read-only actions (gateway-health, explain-route) |
| `operator` | Medium risk (prepare-deploy, rollback-plan) |
| `admin` | High risk (restart-gateway, deploy-change, push-code) |
| `emergency` | Critical risk / destructive actions (reset-hard, delete-logs, disable-prometheus, disable-slo) |

## Action Classification

| Action Type | Risk | Decision Flow |
|-------------|------|--------------|
| `gateway-health` | low | allow (read-only) |
| `explain-route` | low | allow (read-only) |
| `default` | low | allow (unknown actions) |
| `prepare-deploy` | medium | evidence → require_more_evidence / require_approval |
| `rollback-plan` | medium | require_approval (inherent) |
| `restart-gateway` | high | evidence → require_more_evidence / require_approval |
| `deploy-change` | high | evidence + rollback → require_more_evidence / require_approval |
| `push-code` | high | evidence + rollback → require_more_evidence / require_approval |
| `delete-logs` | critical | evidence threshold → block / require_more_evidence / require_approval |
| `disable-prometheus` | critical | evidence threshold → block / require_more_evidence / require_approval |
| `disable-slo` | critical | evidence threshold → block / require_more_evidence / require_approval |
| `reset-hard` | critical | evidence threshold → block / require_more_evidence / require_approval |

## Decision Logic

```
destructive action → evidence ≤1  → block
                      evidence < missing → require_more_evidence
                      else → require_approval (emergency)

critical risk → evidence missing → block
                else → require_approval (emergency)

high risk     → evidence missing → require_more_evidence
                no rollback + high impact → require_more_evidence
                else → require_approval (admin)

medium risk   → rollback-plan → require_approval (operator)
                evidence missing → require_more_evidence
                else → require_approval (operator)

low risk      → read-only or default → allow
                else evidence → allow / require_more_evidence
```

## Evidence Requirements

| Action Type | Required Evidence |
|-------------|------------------|
| gateway-health | gateway_health_endpoint |
| explain-route | routing_history, operator_intent |
| prepare-deploy | git_status, test_results, triage_status |
| rollback-plan | previous_snapshot, change_log |
| restart-gateway | gateway_health_endpoint, triage_status, reason_provided |
| push-code | git_status_clean, test_results, triage_status |
| deploy-change | git_status_clean, test_results, triage_status, rollback_plan |
| delete-logs | log_path_confirmation, backup_available, operator_consent |
| disable-prometheus | prometheus_health, alert_rules_backup, operator_consent, emergency_justification |
| disable-slo | slo_impact_analysis, operator_consent, emergency_justification |
| reset-hard | full_backup, operator_consent, emergency_justification |
| default | operator_intent, triage_status |

## Triage Integration

The decision engine integrates with the observability triage layer:

- **triage severity = high**: escalates `allow` → `require_approval`
- **triage severity = critical**: blocks all high/critical risk actions (`block`)
- **triage severity = critical**: adds precaution note to `require_approval` decisions

## Operator Intent Integration

The decision engine integrates with operator intent reasoning:

- Unsafe action markers from operator intent escalate `allow` → `require_approval`
- Operator intent category provides implicit `reason_provided` evidence
- Operator intent `requires_approval` flag propagates to approval assessment

## Rollback Model

| Action Type | Rollback Behavior |
|-------------|------------------|
| Read-only | No rollback needed (auto-true) |
| restart-gateway | Auto-generates steps (systemctl restart, verify, restore) |
| Destructive (delete-logs, reset-hard, disable-*) | False unless explicit `rollback_plan` in context |
| High-impact (deploy, push, prepare) | Must have rollback plan for approval; auto-suggests steps if missing |
| rollback-plan | N/A |

## Schema (GET /api/validation/authority)

```json
{
  "validation_id": "VA-1748736000-restart-gateway",
  "timestamp": 1748736000.0,
  "requested_action": "restart gateway",
  "action_type": "restart-gateway",
  "operator_intent": { "category": "FAST_INFRASTRUCTURE", "risk": "high", ... },
  "risk": "high",
  "severity": "medium",
  "evidence": ["gateway_health_endpoint", "triage_status", "reason_provided"],
  "missing_evidence": [],
  "preconditions": ["working tree must be clean", "tests must pass", "rollback plan must be available"],
  "validation_plan": ["check evidence", "verify operator intent", "evaluate triage", "assess rollback", "determine approval"],
  "rollback_plan": ["systemctl restart ailab-gateway", "curl /health", "restore from snapshot"],
  "has_rollback": true,
  "expected_impact": "MEDIUM risk action affecting 1 component(s): gateway",
  "affected_components": ["gateway"],
  "requires_approval": true,
  "approval_level": "admin",
  "safe_to_execute": false,
  "safe_to_auto_execute": false,
  "decision": "require_approval",
  "reason": "high risk action requires admin approval",
  "confidence": 0.85,
  "next_steps": ["submit for admin approval", "ensure rollback plan is ready"],
  "contract_version": "VALIDATION-AUTHORITY-01"
}
```

## Endpoint

```
GET /api/validation/authority?text=<request>
```

Returns a complete validation decision. Available through the Live API (port 8084).

## Examples

### Read-only action
```
GET /api/validation/authority?text=show+gateway+health
→ decision: "allow", safe_to_execute: true
```

### High-risk action with full context
```
GET /api/validation/authority?text=restart+gateway&operator_intent={"category":"FAST_INFRASTRUCTURE"}&triage=...
→ decision: "require_approval", approval_level: "admin"
```

### Destructive action without evidence
```
GET /api/validation/authority?text=reset+--hard
→ decision: "block", approval_level: "emergency"
```

### Unknown action
```
GET /api/validation/authority?text=what+is+the+weather
→ decision: "allow" (low risk default)
```

## Limitations

- `safe_to_auto_execute` is hardcoded `false` — no auto-execution in this phase
- Evidence assessment is heuristic (text matching, not semantic)
- Does not enforce rollback execution — only checks plan availability
- Confidence calculation is linear (0.7 * evidence_ratio + 0.3)
- No feedback loop from execution outcomes
- Operator intent must be provided externally (not auto-extracted in this phase)
- Prometheus-based evidence relies on API availability
