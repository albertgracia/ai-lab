# ADR-006: Dynamic Governance

**Status:** DRAFT — Design only
**Date:** 2026-07-03
**Based on:** AGENTS.md Rule #13, HERMES-ENTERPRISE-ARCHITECTURE-AUDIT-01

---

## Context

AGENTS.md Rule #13 states:
> Governance level must be dynamic, not hardcoded. The governance_level in the descriptor of maturity must be resolved from control_plane.get_governance_state().

The enterprise audit confirmed this rule is violated — governance level is hardcoded in `builder.py`.

Additionally:
- No formal definition of what each governance mode allows/blocks
- No governance resolver that translates control plane state → governance mode
- No governance endpoint that returns the current mode with confidence

## Decision

Create `runtime/hermes/governance/` with a formal governance system.

---

## Design

### 1. Governance Modes (`modes.json`)

```json
{
  "version": "1.0.0",
  "modes": {
    "NORMAL": {
      "description": "Full operational capacity. All capabilities available under default permissions.",
      "allows": [
        "All read-only operations",
        "All MCP queries",
        "GitNexus analysis",
        "Report generation",
        "Health checks",
        "Status queries"
      ],
      "blocks": [
        "Write operations without explicit approval",
        "Infrastructure modifications",
        "Service restarts",
        "Configuration changes"
      ],
      "default_capability_behavior": "read_only",
      "requires_approval": ["write", "configure", "restart"]
    },
    "ELEVATED": {
      "description": "Increased scrutiny. All operations require explicit approval.",
      "allows": [
        "All read-only operations",
        "Approved write operations with rollback plan",
        "Deployment review with explicit approval",
        "Incident response with explicit approval"
      ],
      "blocks": [
        "Automatic write operations",
        "Unapproved configuration changes",
        "Service restarts without plan",
        "Any operation without evidence chain"
      ],
      "default_capability_behavior": "requires_approval",
      "requires_approval": ["all operations", "write", "configure", "restart", "deploy"]
    },
    "DEGRADED": {
      "description": "Runtime is operating with reduced capacity. Only critical observation allowed.",
      "allows": [
        "Health checks",
        "Status queries",
        "Incident reporting",
        "Read-only MCP queries",
        "GitNexus read-only queries"
      ],
      "blocks": [
        "All write operations",
        "All tool execution",
        "Deployment review",
        "Marketplace audit",
        "Any non-critical operation"
      ],
      "default_capability_behavior": "blocked_except_observe",
      "requires_approval": []
    },
    "LOCKDOWN": {
      "description": "Emergency mode. Only observation and incident reporting.",
      "allows": [
        "Health checks (read-only)",
        "Active incident reporting"
      ],
      "blocks": [
        "All non-essential operations",
        "All write operations",
        "All MCP queries except health",
        "All tool execution",
        "All GitNexus queries",
        "Report generation",
        "Marketplace queries"
      ],
      "default_capability_behavior": "blocked",
      "requires_approval": []
    }
  }
}
```

### 2. Governance Resolver

The Governance Resolver translates control plane state into a governance mode:

```python
# Pseudocode — resolver logic
def resolve_governance_mode(control_plane_state: dict) -> str:
    """
    Determine governance mode from control plane signals.
    
    Input source: control_plane.get_governance_state() or /runtime/governance endpoint
    """
    signals = control_plane_state
    
    # Lockdown triggers (highest priority)
    if signals.get("emergency_mode"):
        return "LOCKDOWN"
    
    # Degraded triggers
    if signals.get("degradation_level") in ("HEAVY", "EMERGENCY"):
        return "DEGRADED"
    
    # Elevated triggers
    if signals.get("degradation_level") == "LIGHT":
        return "ELEVATED"
    
    if signals.get("slo_state") == "RED":
        return "ELEVATED"
    
    if signals.get("vram_pressure") > 0.9:
        return "ELEVATED"
    
    # Normal
    return "NORMAL"
```

**Trigger signals:**

| Signal | Source | Threshold → Mode |
|--------|--------|-----------------|
| `emergency_mode` | DegradationManager | true → LOCKDOWN |
| `degradation_level` | DegradationManager | HEAVY/EMERGENCY → DEGRADED |
| `degradation_level` | DegradationManager | LIGHT → ELEVATED |
| `slo_state` | RuntimeSLOManager | RED → ELEVATED |
| `vram_pressure` | RuntimeSLOManager | >0.9 → ELEVATED |
| `gpu_pressure` | RuntimeSLOManager | >0.9 → ELEVATED |
| `timeout_rate` | RuntimeSLOManager | >0.1 → ELEVATED |
| Default | — | — → NORMAL |

### 3. Governance Endpoint

```json
GET /runtime/governance

Response:
{
  "mode": "NORMAL",
  "source": "control_plane",
  "resolved_at": "2026-07-03T12:00:00Z",
  "trigger_signals": {
    "slo_state": "GREEN",
    "degradation_level": "NONE",
    "emergency_mode": false,
    "vram_pressure": 0.45,
    "gpu_pressure": 0.60,
    "timeout_rate": 0.02
  },
  "capabilities": {
    "ai-lab-runtime": "allowed",
    "marketplace-operator": "allowed",
    "observability": "allowed",
    "gitnexus-analysis": "allowed",
    "deployment-review": "requires_approval",
    "incident-response": "allowed"
  }
}
```

### 4. Capability-Governance Matrix

```json
{
  "capability_governance": {
    "ai-lab-runtime": {
      "NORMAL": "allowed",
      "ELEVATED": "requires_approval",
      "DEGRADED": "allowed",
      "LOCKDOWN": "allowed"
    },
    "marketplace-operator": {
      "NORMAL": "allowed",
      "ELEVATED": "allowed",
      "DEGRADED": "blocked",
      "LOCKDOWN": "blocked"
    },
    "observability": {
      "NORMAL": "allowed",
      "ELEVATED": "allowed",
      "DEGRADED": "allowed",
      "LOCKDOWN": "blocked"
    },
    "gitnexus-analysis": {
      "NORMAL": "allowed",
      "ELEVATED": "allowed",
      "DEGRADED": "allowed",
      "LOCKDOWN": "blocked"
    },
    "deployment-review": {
      "NORMAL": "requires_approval",
      "ELEVATED": "requires_approval",
      "DEGRADED": "blocked",
      "LOCKDOWN": "blocked"
    },
    "incident-response": {
      "NORMAL": "allowed",
      "ELEVATED": "allowed",
      "DEGRADED": "allowed",
      "LOCKDOWN": "allowed"
    }
  }
}
```

### 5. Transition Rules

| From → To | Allowed? | Anti-flapping |
|-----------|----------|---------------|
| NORMAL → ELEVATED | ✅ Immediate | 30s min between transitions |
| NORMAL → DEGRADED | ✅ Immediate | 30s min |
| NORMAL → LOCKDOWN | ✅ Immediate | Immediate (emergency) |
| ELEVATED → NORMAL | ✅ After 60s stable | Cooldown period |
| ELEVATED → DEGRADED | ✅ Immediate | 30s min |
| ELEVATED → LOCKDOWN | ✅ Immediate | Immediate |
| DEGRADED → NORMAL | ✅ After 120s stable | Double cooldown |
| DEGRADED → ELEVATED | ✅ Immediate | 30s min |
| DEGRADED → LOCKDOWN | ✅ Immediate | Immediate |
| LOCKDOWN → any | ❌ Manual only | Requires operator intervention |

---

## Impact

| Aspect | Before | After |
|--------|--------|-------|
| Governance level | Hardcoded in builder.py | Dynamic from control_plane |
| Mode definitions | None | 4 formal modes with allows/blocks |
| Capability binding | None | Per-capability governance matrix |
| Endpoint | None | /runtime/governance with fallback |
| Anti-flapping | DegradationManager only | Full transition rules |

## Risks

- Resolver could oscillate between modes → Mitigation: anti-flapping rules + min transition intervals
- Capabilities blocked in DEGRADED may hide critical information → Mitigation: ai-lab-runtime and incident-response remain allowed in all modes
- LOCKDOWN requires manual exit → Risk accepted (security over convenience)

## Status

**DRAFT** — Design approved for architecture phase. Implementation deferred to E-01 (pre-requisite for all other ADRs).
