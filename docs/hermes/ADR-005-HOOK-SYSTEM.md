# ADR-005: Hook System

**Status:** DRAFT — Design only
**Date:** 2026-07-03
**Based on:** HERMES-ENTERPRISE-ARCHITECTURE-AUDIT-01 (finding: hooks dispersos)

---

## Context

The enterprise audit found 3 hooks scattered across the codebase:
- `governance_hooks.py` (FASE 28.1)
- `qdrant_routing_hook.py` (FASE 23A)
- `watchdog_incident_hook.py` (FASE 30)

No HookRegistry exists. No lifecycle is defined. Hooks are not observable.

## Decision

Create `runtime/hermes/hooks/` with a formal HookRegistry and defined lifecycle.

---

## Design

### 1. Hook Lifecycle

```
Request flow:
┌─────────────┐
│ before_     │ ← validate identity, check boundaries, check governance
│ request()   │
└──────┬──────┘
       │
┌──────▼──────┐
│ before_     │ ← validate tool against capability registry
│ tool()      │
└──────┬──────┘
       │
┌──────▼──────┐
│ before_     │ ← validate write target, check permissions
│ write()     │
└──────┬──────┘
       │
   Execute
       │
┌──────▼──────┐
│ after_      │ ← log result, emit metrics, check for incidents
│ write()     │
└──────┬──────┘
       │
┌──────▼──────┐
│ after_      │ ← log result, emit metrics
│ tool()      │
└──────┬──────┘
       │
┌──────▼──────┐
│ after_      │ ← finalize audit trail, cleanup
│ request()   │
└─────────────┘

Error path:
┌──────────────┐
│ on_error()   │ ← capture error context, emit alert, log to incidents
└──────────────┘

Other lifecycle events:
┌─────────────────┐
│ on_incident()   │ ← triggered when an incident is detected
└─────────────────┘

┌─────────────────┐
│ on_shutdown()   │ ← flush metrics, save state, graceful stop
└─────────────────┘
```

### 2. Hook Schema (`hook_schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "event", "handler"],
  "properties": {
    "id": { "type": "string" },
    "description": { "type": "string" },
    "event": {
      "type": "string",
      "enum": [
        "before_request", "after_request",
        "before_tool", "after_tool",
        "before_write", "after_write",
        "on_error",
        "on_incident",
        "on_shutdown"
      ]
    },
    "handler": {
      "type": "string",
      "description": "Python import path to the handler function"
    },
    "read_only": {
      "type": "boolean",
      "description": "If true, this hook does not modify state"
    },
    "async": {
      "type": "boolean",
      "default": true,
      "description": "If true, hook runs asynchronously (non-blocking)"
    },
    "requires_authorization": {
      "type": "boolean",
      "default": false,
      "description": "If true, this hook only runs when governance level allows"
    },
    "governance_level": {
      "type": "array",
      "items": { "type": "string", "enum": ["normal", "elevated", "degraded", "lockdown"] },
      "description": "Governance levels where this hook is active"
    },
    "priority": {
      "type": "integer",
      "description": "Execution order within lifecycle event (lower = first)"
    }
  }
}
```

### 3. Event Definitions

| Event | When | Blocking? | Purpose | Read-only hooks |
|-------|------|-----------|---------|-----------------|
| `before_request` | Before any operator execution | Yes | Validate governance, identity, boundaries | ✅ all |
| `after_request` | After operator completes | No (async) | Log result, emit metrics, check for incidents | ✅ all |
| `before_tool` | Before a tool/MCP call | Yes | Validate tool against capability registry | ✅ all |
| `after_tool` | After tool returns | No (async) | Log tool result, emit metrics | ✅ all |
| `before_write` | Before any write operation | Yes | Check permissions, backup target | ❌ requires auth |
| `after_write` | After write completes | No (async) | Verify write, emit audit event | ❌ requires auth |
| `on_error` | On any error | No (async) | Capture context, emit alert, log | ✅ all |
| `on_incident` | When incident detected | No (async) | Log to Qdrant, emit alert, notify | ✅ all |
| `on_shutdown` | Before Hermes shuts down | Yes (sync) | Flush metrics, save state | ✅ all |

### 4. Hook Registry (`registry.json` concept)

```json
{
  "version": "1.0.0",
  "hooks": [
    {
      "id": "governance-validation",
      "description": "Validate governance level before allowing operation",
      "event": "before_request",
      "handler": "runtime.hermes.hooks.governance_validator",
      "read_only": true,
      "async": false,
      "requires_authorization": false,
      "governance_level": ["normal", "elevated", "degraded", "lockdown"],
      "priority": 10
    },
    {
      "id": "capability-verification",
      "description": "Verify requested capability is registered and allowed",
      "event": "before_request",
      "handler": "runtime.hermes.hooks.capability_verifier",
      "read_only": true,
      "async": false,
      "requires_authorization": false,
      "governance_level": ["normal", "elevated"],
      "priority": 20
    },
    {
      "id": "tool-authorization",
      "description": "Validate tool call against capability registry and governance",
      "event": "before_tool",
      "handler": "runtime.hermes.hooks.tool_authorizer",
      "read_only": true,
      "async": false,
      "requires_authorization": false,
      "governance_level": ["normal", "elevated"],
      "priority": 10
    },
    {
      "id": "write-backup",
      "description": "Create backup before write operations",
      "event": "before_write",
      "handler": "runtime.hermes.hooks.write_backup",
      "read_only": false,
      "async": false,
      "requires_authorization": true,
      "governance_level": ["elevated"],
      "priority": 10
    },
    {
      "id": "write-verification",
      "description": "Verify write operation success and integrity",
      "event": "after_write",
      "handler": "runtime.hermes.hooks.write_verifier",
      "read_only": false,
      "async": true,
      "requires_authorization": true,
      "governance_level": ["elevated"],
      "priority": 10
    },
    {
      "id": "runtime-metrics",
      "description": "Emit Prometheus metrics after each request",
      "event": "after_request",
      "handler": "runtime.hermes.hooks.runtime_metrics_emitter",
      "read_only": true,
      "async": true,
      "requires_authorization": false,
      "governance_level": ["normal", "elevated", "degraded", "lockdown"],
      "priority": 50
    },
    {
      "id": "incident-logger",
      "description": "Log incidents to Qdrant and emit alerts",
      "event": "on_incident",
      "handler": "runtime.hermes.hooks.incident_logger",
      "read_only": true,
      "async": true,
      "requires_authorization": false,
      "governance_level": ["normal", "elevated", "degraded", "lockdown"],
      "priority": 10
    },
    {
      "id": "error-capture",
      "description": "Capture and log errors with context",
      "event": "on_error",
      "handler": "runtime.hermes.hooks.error_capture",
      "read_only": true,
      "async": true,
      "requires_authorization": false,
      "governance_level": ["normal", "elevated", "degraded", "lockdown"],
      "priority": 10
    },
    {
      "id": "graceful-shutdown",
      "description": "Flush state and stop gracefully",
      "event": "on_shutdown",
      "handler": "runtime.hermes.hooks.graceful_shutdown",
      "read_only": true,
      "async": false,
      "requires_authorization": false,
      "governance_level": ["normal", "elevated", "degraded", "lockdown"],
      "priority": 10
    }
  ]
}
```

### 5. Hook Authorization Rules

| Hook reads state? | Hook writes state? | Requires authorization? |
|-------------------|-------------------|------------------------|
| Yes | No | No (read-only hooks) |
| Yes | Yes | Yes (governance must allow) |
| No | No | No (pure observation) |

### 6. Migration Path

Existing hooks will be migrated to the new system:

| Current location | New handler | Event |
|-----------------|-------------|-------|
| `governance_hooks.validate_plan_against_policy` | `hooks.governance_validator` | `before_request` |
| `qdrant_routing_hook.on_cognitive_event` | `hooks.incident_logger` | `on_incident` + `after_request` |
| `watchdog_incident_hook` | `hooks.incident_logger` | `on_incident` |

---

## Impact

| Aspect | Before | After |
|--------|--------|-------|
| Hook organization | 3 files scattered | Single registry with lifecycle |
| Observability | None | Prometheus metrics per hook |
| Authorization | Implicit | Explicit governance_level per hook |
| Lifecycle | None | 9 events defined |
| Async support | None | Explicit async flag |

## Status

**DRAFT** — Design approved for architecture phase. Implementation deferred to E-04.
