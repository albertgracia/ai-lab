# SOUL — System Ontological Unified Layer

**Location:** `runtime/hermes/soul/`
**Version:** 1.0.0
**Status:** DECLARATIVE — Skeleton only, no runtime enforcement
**Based on:** ADR-001-SOUL

## Purpose

SOUL is the identity layer of the Hermes Enterprise Agent. It defines:

- **Who** Hermes is (identity)
- **How** Hermes knows (truth model)
- **How** Hermes acts (protocols)
- **What** Hermes must NOT do (boundaries)
- **What** Hermes oversees (domains)

## Files

| File | Purpose | Status |
|------|---------|--------|
| `identity.yaml` | Agent identity, mission, role | ✅ DECLARED |
| `truth_model.yaml` | Evidence hierarchy (OBSERVADO/INFERIDO/SUPUESTO) | ✅ DECLARED |
| `protocols.yaml` | Operational protocols | ✅ DECLARED |
| `boundaries.yaml` | Forbidden/allowed actions | ✅ DECLARED |
| `domains.yaml` | Managed domains | ✅ DECLARED |
| `soul.schema.json` | JSON Schema validating all YAML | ✅ DECLARED |

## Governance

SOUL is declarative only. No runtime enforcement is active.
All YAML files must pass `soul.schema.json` validation.
Enforcement will be implemented in future phases (E-01B+).

## References

- ADR-001-SOUL: `docs/hermes/ADR-001-SOUL.md`
- Enterprise Design: `docs/hermes/HERMES-ENTERPRISE-DESIGN-01.md`
