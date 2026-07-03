# Operator Intent Reasoning

**Contract version:** 36C

## Purpose

Deterministic classification of operator requests before execution. Allows AI-LAB to decide:

- observe / explain / diagnose / plan / propose / execute / block / require approval

This layer reasons about **what kind of operational action is safe**, but never executes or authorizes actions.

## API

### Library

```python
from runtime.operator_intent import analyze_operator_intent

result = analyze_operator_intent("restart the gateway")
# {
#   "category": "UNKNOWN",
#   "risk": "high",
#   "requires_approval": True,
#   "target": "gateway",
#   "allowed_modes": ["observe"],
#   "recommended_action": "require_approval",
#   ...
# }
```

### Live API

```
GET /api/operator/intent?text=<query>
```

Returns full operator intent analysis (read-only).

## Schema

| Field | Description |
|-------|-------------|
| `contract_version` | Version identifier ("36C") |
| `category` | OperatorIntentCategory enum (18 values) |
| `confidence` | Score (0-1), label (high/medium/low), degradation |
| `risk` | low / medium / high / critical |
| `requires_approval` | Whether human approval is needed before acting |
| `allowed_modes` | Which modes are safe: observe, plan, build, execute |
| `target` | Affected component: gateway, router, prometheus, git, etc. |
| `recommended_action` | answer / ask_clarification / propose_command / block / require_approval |
| `safety` | Execution authority, action markers, dangerous markers, guards |
| `ambiguity` | Whether intent is mixed or ambiguous, with candidates |
| `authority` | Freshness and gaps from authority snapshot |
| `precision` | Precision report for partial/degraded state |
| `explainability` | What data sources were used |

## Risk Rules

| Condition | Risk |
|-----------|------|
| `unsafe_action_markers` present (rm -rf, delete all, reboot...) | critical |
| Implementation / code change request | high |
| Execution terms (deploy, push, apply...) | high |
| Restart terms | high |
| Planning, remediation discussion | medium |
| Action markers present (non-dangerous) | medium |
| No markers, observe/status query | low |

## Recommended Action

| Condition | Action |
|-----------|--------|
| Risk = critical | block |
| Risk = high or requires approval | require_approval |
| Category = UNKNOWN, risk = low | answer |
| Risk = medium | ask_clarification |
| Other | propose_command |

## Integration Points

- **Gateway** (`openai_gateway.py:716`): Stores `_operator_intent` in payload (metadata only)
- **Live API** (`/api/operator/intent`): Read-only classification endpoint
- **Domain registry** (`domain_registry.py`): Registered as `operator_intent` domain
- **Federation** (`role_router.py`): Domain-routed through federation guards
