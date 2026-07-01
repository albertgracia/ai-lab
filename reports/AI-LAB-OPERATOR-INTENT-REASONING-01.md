# AI-LAB-OPERATOR-INTENT-REASONING-01

**Status:** PASS

**Date:** 2026-07-01

## Objective

Implement deterministic operator intent classification with risk assessment,
approval requirements, target identification, and recommended action.

## Background

FASE 36C already implemented `analyze_operator_intent()` with 18 intent categories,
safety guards, and Gateway wiring. This phase extends it with an execution-aware
schema and read-only Live API exposure.

## Schema Extensions

| Field | Values | Description |
|-------|--------|-------------|
| `risk` | low / medium / high / critical | Risk level based on category + action terms |
| `requires_approval` | true / false | Whether human approval is needed |
| `allowed_modes` | observe / plan / build / execute | Which operational modes are safe |
| `target` | gateway / router / live-api / prometheus / grafana / lm-studio / git / filesystem / unknown | System component affected |
| `recommended_action` | answer / ask_clarification / propose_command / block / require_approval | What the system should do |

## Implementation

**File: `runtime/operator_intent/operator_intent_reasoning.py`**

- Added `_EXECUTION_TERMS`, `_GIT_TERMS`, `_RESTART_TERMS`, `_DELETE_TERMS`, `_DEPLOY_TERMS`
- Added `_target_from_text()`, `_risk_from_category_and_text()`, `_requires_approval()`, `_allowed_modes()`, `_recommended_action()`
- Added English status markers to FAST_STATUS ("ai-lab health", "gateway health", "show me")
- Added "delete all" to `_DANGEROUS_TERMS`
- Extended `OperatorIntentResult` dataclass with 5 new fields
- Extended `analyze_operator_intent()` to compute and return new fields

**File: `runtime/state/live_api.py`**

- Added `GET /api/operator/intent?text=<query>` endpoint
- Returns full operator intent analysis (read-only)

## Test Results

```
25/25 operator intent tests PASS
28/28 fastpath routing priority tests PASS
25/25 operational fastpath tests PASS
12/12 federation role execution tests PASS
```

### New tests

| Test | Category | Risk | Action |
|------|----------|------|--------|
| `test_trivia_not_operator` | UNKNOWN | low | answer |
| `test_restart_gateway_is_high_risk_requires_approval` | UNKNOWN | high | require_approval |
| `test_show_health_is_low_risk` | FAST_STATUS | low | answer |
| `test_delete_logs_is_critical` | UNKNOWN | critical | block |
| `test_push_to_origin_main_is_high_risk` | UNKNOWN | high | require_approval |
| `test_prepare_rollback_plan_is_planning` | PLANNING | medium | ask_clarification |
| `test_rm_rf_is_critical_blocked` | UNKNOWN | critical | block |
| `test_deploy_change_is_high_risk` | UNKNOWN | high | require_approval |
| `test_prometheus_target_down_is_observability` | FAST_OBSERVABILITY | low | answer |

## Live API Validation

```
/operator/intent?text=restart%20gateway
  → cat=UNKNOWN risk=high target=gateway action=require_approval

/operator/intent?text=What%20is%202%2B2%3F
  → cat=UNKNOWN risk=low action=answer

/operator/intent?text=show%20me%20AI-LAB%20health
  → cat=FAST_STATUS risk=low action=answer

/operator/intent?text=delete%20all%20logs
  → cat=UNKNOWN risk=critical action=block
```

## Files Changed

| File | Change |
|------|--------|
| `runtime/operator_intent/operator_intent_reasoning.py` | Extended schema (risk, approval, target, modes, action) + English patterns |
| `runtime/state/live_api.py` | Added `GET /api/operator/intent` |
| `tests/test_operator_intent_reasoning_36c.py` | 10 new tests for extended schema |

## Rollback

```bash
cp /opt/ai-lab/runtime/operator_intent/operator_intent_reasoning.py.bak.20260701-opintent \
   /opt/ai-lab/runtime/operator_intent/operator_intent_reasoning.py
cp /opt/ai-lab/runtime/state/live_api.py.bak.20260701-opintent \
   /opt/ai-lab/runtime/state/live_api.py
kill -TERM $(systemctl show ailab-live-api.service -p MainPID | cut -d= -f2)
```

## Remaining

- No behavioral enforcement yet (read-only classification)
- Future: wire into Gateway to block dangerous requests before LLM
