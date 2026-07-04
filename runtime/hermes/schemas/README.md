# Hermes Enterprise Schemas

**Location:** `runtime/hermes/schemas/`
**Version:** 1.0.0
**Status:** DECLARATIVE — Schema definitions only

## Purpose

Shared JSON schemas for Hermes Enterprise components.
These schemas validate YAML/JSON configuration files.

## Planned Schemas

| Schema | File | Status |
|--------|------|--------|
| SOUL | `soul.schema.json` (in ../soul/) | ✅ CREATED |
| Capability Registry | `capability_schema.json` | 📋 Planned (E-02) |
| Operator Registry | `operator_schema.json` | 📋 Planned (E-02) |
| MCP Registry | `mcp_server_schema.json` | ✅ CREATED |
| Hook Registry | `hook_schema.json` | 📋 Planned (E-04) |
| Governance | `governance_schema.json` | 📋 Planned (E-01B) |

## Validation

All schemas follow JSON Schema draft-07.
No runtime validation is active yet — schemas are declarative references only.
