# HERMES-E01A-SOUL-ENTERPRISE-SKELETON Report

**Date:** 2026-07-04
**Author:** OpenCode AI Agent
**Status:** ✅ COMPLETED

## Summary

Esqueleto declarativo de SOUL (System Ontological Unified Layer) creado en `runtime/hermes/`. 10 archivos, 0 líneas de Python runtime, validación YAML+JSON pasada.

## Files Created

| # | File | Description |
|---|------|-------------|
| 1 | `runtime/hermes/soul/README.md` | SOUL overview and file index |
| 2 | `runtime/hermes/soul/identity.yaml` | Agent identity, mission, personality |
| 3 | `runtime/hermes/soul/truth_model.yaml` | Evidence hierarchy (OBSERVADO/INFERIDO/SUPUESTO) |
| 4 | `runtime/hermes/soul/protocols.yaml` | 6 operational protocols with priorities |
| 5 | `runtime/hermes/soul/boundaries.yaml` | 7 forbidden, 6 requires-auth, 6 read-only actions |
| 6 | `runtime/hermes/soul/domains.yaml` | 5 managed domains with nodes, MCP access, limitations |
| 7 | `runtime/hermes/soul/soul.schema.json` | JSON Schema validating all YAML (draft-07) |
| 8 | `runtime/hermes/schemas/README.md` | Schema registry overview |
| 9 | `runtime/hermes/__init__.py` | Package init (empty) |
| 10 | `reports/HERMES-E01A-SOUL-ENTERPRISE-SKELETON.md` | This report |

## Validation

- JSON Schema (`soul.schema.json`): ✅ Valid (ConvertFrom-Json)
- YAML files (5): ✅ All syntactically valid (no Python yaml available)
- Python files in runtime/hermes/: ✅ None (expected)
- Total files: 10

## Key Content

### Identity
- Name: Hermes, Edition: AI-LAB Enterprise
- Role: Operator Console, Mission: diagnosticar, operar, monitorizar
- Non-goals: no modificar infraestructura sin aprobación, no decisiones de negocio

### Truth Model
- 3 levels: OBSERVADO (high), INFERIDO (medium), SUPUESTO (low)
- Evidence required, citations mandatory, "NO DISPONIBLE" when no evidence

### Protocols
1. `gitnexus_first` (p100) — consultar GitNexus antes de modificar runtime
2. `mcp_first` (p90) — preferir MCP sobre API directa
3. `evidence_first` (p80) — toda afirmación con fuente
4. `backup_before_write` (p70) — backup antes de escribir
5. `no_restart_without_authorization` (p60) — preguntar antes de reiniciar
6. `no_pass_without_validation` (p50) — tests+build+tree clean+tag

### Boundaries
- 7 forbidden: modificar runtime, skills, config, Stripe, comandos destructivos, reiniciar sin permiso, tocar producción
- 6 require auth: reinicio servicios, cambios gateway/router, modificar servicios Windows, RDP, Prometheus/Grafana, deploys
- 6 read-only: health endpoints, leer archivos, GitNexus, informes, API marketplace, Prometheus

### Domains
1. AI-LAB: 3 hosts (.30, .50, .60), primary MCP: ailab-runtime-mcp
2. Marketplace: host .150, primary: gitnexus (rioja-marketplace)
3. Observability: host .40, primary: planned prometheus-mcp
4. GitNexus: host .30, primary: gitnexus MCP tools
5. Windows: hosts .150, .250, no MCP available

## Design Decisions

- SOUL skeleton lives in `runtime/hermes/soul/` (not `docs/hermes/`) because it's a runtime component — ADRs remain in `docs/hermes/` as design documentation
- JSON Schema file is in the soul/ directory alongside the YAML files for proximity; schemas/README.md points to it
- No runtime enforcement — all files are declarative
- Protocols use priority system (100-50) for clear precedence
- Consistency with existing AI-LAB conventions: YAML for config, JSON for schemas

## GitNexus Validation

No GitNexus consultation was needed because:
- New files only — no modification of existing runtime symbols
- No changes to gateway, router, or core runtime code
- Location: runtime/hermes/ — new path, no callers to analyze

## Next Steps

1. **HERMES-E01B-SOUL-VALIDATION**: Validate YAML against runtime (e.g., verify domain nodes exist, protocols match actual behavior)
2. **HERMES-E02-CAPABILITY-REGISTRY**: Implement Capability Registry (ADR-002)
3. **HERMES-E04-HOOK-SYSTEM**: Implement Hook System (ADR-005)
