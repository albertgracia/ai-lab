# HERMES-E02A-CAPABILITY-REGISTRY-SKELETON

**Date:** 2026-07-04
**Author:** OpenCode AI Agent
**Status:** ✅ COMPLETED

## Summary

Capability Registry skeleton creado en `runtime/hermes/capabilities/`. 8 archivos, 6 capabilities declarativas, 0 líneas de Python runtime.

## Files Created

| # | File | Description |
|---|------|-------------|
| 1 | `capability.schema.json` | JSON Schema validando todas las capabilities |
| 2 | `ai-lab-runtime.yaml` | AI-LAB Runtime Operations |
| 3 | `marketplace-operator.yaml` | Marketplace Read-only Operations |
| 4 | `observability.yaml` | Observability Operations |
| 5 | `gitnexus-analysis.yaml` | GitNexus Code Analysis |
| 6 | `deployment-review.yaml` | Deployment Review |
| 7 | `incident-response.yaml` | Incident Response |
| 8 | `README.md` | Registry overview |

## Capabilities Declared

| ID | Domain | MCP Required | Dependencies | Read-only |
|----|--------|-------------|--------------|-----------|
| `ai-lab-runtime` | ai-lab | ailab-runtime-mcp | — | ✅ |
| `marketplace-operator` | marketplace | gitnexus | gitnexus-analysis | ✅ |
| `observability` | observability | — | — | ✅ |
| `gitnexus-analysis` | gitnexus | gitnexus | — | ✅ |
| `deployment-review` | ai-lab, gitnexus | ailab-runtime-mcp, gitnexus | ai-lab-runtime, gitnexus-analysis | ✅ |
| `incident-response` | ai-lab, observability | ailab-runtime-mcp | ai-lab-runtime, observability | ✅ |

## Extended Fields (Beyond ADR-002)

Each YAML includes fields beyond the ADR JSON schema:

- `purpose` — one-line operational purpose
- `required_mcp` / `optional_mcp` — separated MCP requirements
- `inputs` — typed input parameters with descriptions
- `outputs` — typed outputs with format specifications
- `permissions` — read_only, governance_levels, requires_authorization, max_concurrent
- `forbidden_actions` — explicit list of prohibited actions
- `evidence_requirements` — min_confidence, require_citations, require_timestamp, require_source_endpoint
- `fallback_strategy` — primary_fallback, secondary_fallback, description, timeout_seconds
- `reports` — typed with format specification

## Schema Fields (capability.schema.json)

- 15 required fields
- 4 permissions sub-fields with enumerated governance levels
- 4 evidence_requirements sub-fields
- 4 fallback_strategy sub-fields
- Reports with format enum (markdown, json, yaml)
- Domains enum matching SOUL (ai-lab, marketplace, observability, gitnexus, windows)

## Validations

| Check | Result |
|-------|--------|
| JSON Schema syntax | ✅ Valid |
| 6 YAML files present | ✅ All expected |
| Missing capabilities | ✅ None |
| .py files in capabilities/ | ✅ None (expected) |

## Design Decisions

- Individual YAML files (not single registry.json) — follows SOUL pattern for modularity
- YAML over JSON for capabilities — more human-readable and git-diff-friendly than ADR-002's registry.json
- `domains` field is an array — capabilities can span multiple SOUL domains (deployment-review uses ai-lab + gitnexus; incident-response uses ai-lab + observability)
- `fallback_strategy` includes timeout — runtime safety consideration for future enforcement
- `max_concurrent` declared per-capability — enables future concurrency governance
- All capabilities are read-only — consistent with SOUL boundaries

## References

- ADR-002: `docs/hermes/ADR-002-CAPABILITY-REGISTRY.md`
- SOUL: `runtime/hermes/soul/`
- Enterprise Design: `docs/hermes/HERMES-ENTERPRISE-DESIGN-01.md`
