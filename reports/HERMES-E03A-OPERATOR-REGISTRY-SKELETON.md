# HERMES-E03A-OPERATOR-REGISTRY-SKELETON

**Date:** 2026-07-04
**Author:** OpenCode AI Agent
**Status:** ✅ COMPLETED

## Summary

Operator Registry Enterprise creado en `runtime/hermes/operators/`. 7 archivos, 5 operadores declarativos vinculados al Capability Registry, 0 líneas de Python runtime.

## Files Created

| # | File | Description |
|---|------|-------------|
| 1 | `operator.schema.json` | JSON Schema validando todos los operadores |
| 2 | `ai-lab-runtime.yaml` | Runtime Health Check (readonly) |
| 3 | `marketplace-operator.yaml` | Marketplace Audit (readonly) |
| 4 | `observability-operator.yaml` | Observability Query (readonly) |
| 5 | `deployment-review.yaml` | Deployment Readiness Review (advisory) |
| 6 | `incident-response.yaml` | Incident Triage (advisory) |
| 7 | `README.md` | Registry overview + concept definitions |

## Operators Declared

| ID | Name | Execution Mode | Capability | Domains | Priority |
|----|------|---------------|------------|---------|----------|
| `runtime-health-check` | Runtime Health Check | readonly | ai-lab-runtime | ai-lab | 80 |
| `marketplace-audit` | Marketplace Audit | readonly | marketplace-operator | marketplace | 60 |
| `observability-query` | Observability Query | readonly | observability | observability | 50 |
| `deployment-review` | Deployment Readiness Review | advisory | deployment-review | ai-lab, gitnexus | 70 |
| `incident-triage` | Incident Triage | advisory | incident-response | ai-lab, observability | 90 |

## Key Design

### Execution Modes
- **readonly**: Solo lectura, sin efectos secundarios (3 operators)
- **advisory**: Análisis y propuesta, sin ejecución (2 operators)
- **execute**: No utilizado aún — reservado para fases futuras

### Operator vs Capability (ORM Semantics)
- **Capability** (Capability Registry): *what* — dominio de operación, permisos, fallback
- **Operator** (Operator Registry): *how* — workflow concreto, steps, validación, criterios de éxito/fallo
- Un operador vincula a 1+ capabilities; una capability puede tener múltiples operadores

### Protocol Governance
Cada operador referencia protocols de SOUL que debe cumplir:
- `evidence_first` (p80) — todos los operadores lo requieren
- `mcp_first` (p90) — operadores con MCP dependency
- `gitnexus_first` (p100) — deployment-review
- `no_restart_without_authorization` (p60) — operadores con acceso a servicios

## Schema (operator.schema.json)

- 20 required fields (id, name, version, description, capabilities, domains, execution_mode, required_mcp, required_skills, required_protocols, inputs, outputs, validation, reports, rollback, forbidden_actions, truth_model, priority, success_criteria, failure_conditions)
- Execution mode enum: readonly, advisory, execute
- Validation sub-object: pre_conditions + post_conditions
- Rollback sub-object: strategy (manual, automatic, none) + description
- Priority integer 1-100

## Validations

| Check | Result |
|-------|--------|
| JSON Schema syntax | ✅ Valid |
| 5 operator YAML files present | ✅ All expected |
| Capability references exist | ✅ All 5 reference 6 existing capabilities |
| MCP references valid | ✅ ailab-runtime-mcp, gitnexus only |
| No circular dependencies | ✅ Operators → capabilities only (no op→op) |
| Protocol references exist in SOUL | ✅ All 6 protocols referenced correctly |
| .py files in operators/ | ✅ None |
| Total files | ✅ 7 |

## Dependencies by Operator

| Operator | Required Capabilities | Required MCP | Required Protocols |
|----------|----------------------|--------------|-------------------|
| runtime-health-check | ai-lab-runtime | ailab-runtime-mcp | mcp_first, evidence_first, no_restart |
| marketplace-audit | marketplace-operator | gitnexus | mcp_first, evidence_first |
| observability-query | observability | — | evidence_first |
| deployment-review | deployment-review | ailab-runtime-mcp, gitnexus | gitnexus_first, mcp_first, evidence_first, backup_before_write, no_restart, no_pass |
| incident-triage | incident-response | ailab-runtime-mcp | evidence_first, no_restart |

## What Was NOT Implemented

- **Steps execution**: El schema incluye `steps` (opcional) pero los YAML no los declaran — enforcement futuro en E-03C
- **Runtime connector**: No hay código Python para cargar/dispachar operadores
- **Operator dispatch**: No hay enrutamiento automático
- **Hooks binding**: ADR-003 menciona hooks, pero el hook system no existe aún (E-04)
- **Observability metrics**: No hay métricas Prometheus para operadores
- **Marketplace/Prometheus MCP**: Referenciados como "future" en el spec pero no incluidos como required_mcp en ningún operador

## References

- ADR-003: `docs/hermes/ADR-003-OPERATOR-REGISTRY.md`
- Capability Registry: `runtime/hermes/capabilities/`
- SOUL: `runtime/hermes/soul/`
- Enterprise Design: `docs/hermes/HERMES-ENTERPRISE-DESIGN-01.md`
