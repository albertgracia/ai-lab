# Capability Registry — Hermes Enterprise

**Location:** `runtime/hermes/capabilities/`
**Version:** 1.0.0
**Status:** DECLARATIVE — Skeleton only, no runtime enforcement
**Based on:** ADR-002-CAPABILITY-REGISTRY

## Purpose

The Capability Registry defines every bounded domain of operation that Hermes can exercise. Each capability is a declarative contract specifying:

- **Identity:** id, name, version, purpose
- **Domain binding:** which SOUL domains it operates in
- **Tools:** required and optional MCP servers and runtime tools
- **Contracts:** inputs, outputs, reports
- **Governance:** permissions, forbidden actions, evidence requirements
- **Resilience:** fallback strategies when primary MCP is unavailable

## Capabilities

| ID | Name | Domain | Read-only |
|----|------|--------|-----------|
| `ai-lab-runtime` | AI-LAB Runtime Operations | ai-lab | ✅ |
| `marketplace-operator` | Marketplace Read-only Operations | marketplace | ✅ |
| `observability` | Observability Operations | observability | ✅ |
| `gitnexus-analysis` | GitNexus Code Analysis | gitnexus | ✅ |
| `deployment-review` | Deployment Review | ai-lab, gitnexus | ✅ |
| `incident-response` | Incident Response | ai-lab, observability | ✅ |

## Files

| File | Purpose |
|------|---------|
| `capability.schema.json` | JSON Schema validating all capability YAML files |
| `ai-lab-runtime.yaml` | AI-LAB Runtime Operations |
| `marketplace-operator.yaml` | Marketplace Read-only Operations |
| `observability.yaml` | Observability Operations |
| `gitnexus-analysis.yaml` | GitNexus Code Analysis |
| `deployment-review.yaml` | Deployment Review |
| `incident-response.yaml` | Incident Response |
| `README.md` | This file |

## Governance

All capabilities are read-only (no write access). No runtime enforcement is active. YAML files must pass `capability.schema.json` validation.

## References

- ADR-002: `docs/hermes/ADR-002-CAPABILITY-REGISTRY.md`
- SOUL: `runtime/hermes/soul/`
- Enterprise Design: `docs/hermes/HERMES-ENTERPRISE-DESIGN-01.md`
