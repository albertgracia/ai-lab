# Hook Registry — Hermes Enterprise

**Location:** `runtime/hermes/hooks/`
**Version:** 1.0.0
**Status:** DECLARATIVE — Skeleton only, no runtime enforcement
**Based on:** ADR-005-HOOK-SYSTEM

## Purpose

The Hook Registry defines lifecycle hooks that can react to events in the Hermes execution flow. Each hook is bound to a lifecycle event and defines what capabilities, MCP servers, and governance rules apply.

## Lifecycle

```
before_request → before_tool → before_write → EXECUTE → after_write → after_tool → after_request
                                                                              ↓
                                                                         on_error
on_incident (triggered asynchronously)
on_shutdown (triggered on Hermes shutdown)
```

## Current Status

- **enforcement:** disabled
- **hooks enabled:** 0
- **activation:** skeleton_only
- **mode:** declarative_only

No hooks are active. All files are declarative references for future enforcement.

## Files

| File | Event | Purpose |
|------|-------|---------|
| `hook.schema.json` | — | JSON Schema validating all hook YAML files |
| `registry.yaml` | — | Registry metadata |
| `lifecycle/before_request.yaml` | before_request | Validate governance, identity, boundaries |
| `lifecycle/after_request.yaml` | after_request | Log result, emit metrics |
| `lifecycle/before_tool.yaml` | before_tool | Validate tool against capability registry |
| `lifecycle/after_tool.yaml` | after_tool | Log tool result, emit metrics |
| `lifecycle/before_write.yaml` | before_write | Check permissions, backup target |
| `lifecycle/after_write.yaml` | after_write | Verify write, emit audit event |
| `lifecycle/on_error.yaml` | on_error | Capture error context, emit alert |
| `lifecycle/on_incident.yaml` | on_incident | Log to Qdrant, emit alert |
| `lifecycle/on_shutdown.yaml` | on_shutdown | Flush metrics, save state |

## References

- ADR-005: `docs/hermes/ADR-005-HOOK-SYSTEM.md`
- Capability Registry: `runtime/hermes/capabilities/`
- Operator Registry: `runtime/hermes/operators/`
- SOUL: `runtime/hermes/soul/`
