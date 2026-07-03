# Operator Registry — Hermes Enterprise

**Location:** `runtime/hermes/operators/`
**Version:** 1.0.0
**Status:** DECLARATIVE — Skeleton only, no runtime enforcement
**Based on:** ADR-003-OPERATOR-REGISTRY

## What is an Operator?

An **operator** is a structured, repeatable workflow that Hermes executes against a capability. Each operator:

- Belongs to one or more **capabilities** (from the Capability Registry)
- Has explicit typed inputs and outputs
- Requires specific MCP servers, tools, and skills
- Has a defined execution mode, truth model, and priority
- Defines success criteria and failure conditions
- Produces standardized reports

Operators replace ad-hoc execution with contracts. They are discoverable, observable, and governable.

## Operator vs Capability

| Aspect | Capability | Operator |
|--------|-----------|----------|
| **Purpose** | What Hermes can do | How Hermes does it |
| **Granularity** | Coarse (domain-level) | Fine (workflow-level) |
| **Binding** | Binds to domains | Binds to capabilities |
| **Contracts** | I/O + permissions + fallback | I/O + steps + validation + rollback |
| **Execution** | No execution logic | Has steps and success criteria |

A capability says "I can monitor AI-LAB runtime". An operator says "Here is exactly how I check health: step 1 → curl gateway, step 2 → check SLO, step 3 → verify models".

## Relationship with SOUL

- Operators reference SOUL **protocols** via `required_protocols`
- Operators reference SOUL **domains** via `domains`
- Operators inherit SOUL **truth_model** evidence requirements
- Operators must respect SOUL **boundaries** (forbidden actions)

## Relationship with Skills

- Operators can require specific agent **skills** via `required_skills`
- Skills provide the underlying knowledge; operators provide the workflow structure
- Example: `deployment-review` requires `deployment-procedures` skill

## Relationship with MCP

- Operators declare required MCP servers via `required_mcp`
- MCP provides the execution interface; operators define the orchestration
- If an MCP server is unavailable, the operator's `fallback_strategy` applies (from the capability)
- MCP connection health can be validated in pre-conditions

## Relationship with Governance

- `execution_mode` determines what the operator can do:
  - `readonly` — never modifies anything
  - `advisory` — analyzes and proposes, does not execute
  - `execute` — can make changes (requires authorization)
- `authorization_required` gates execution on human approval
- `forbidden_actions` prevent specific dangerous operations
- `priority` enables scheduling and conflict resolution

## Roadmap

| Phase | What | Status |
|-------|------|--------|
| E-03A | Skeleton: schema + YAML definitions | ✅ COMPLETED |
| E-03B | Operator validation (lint YAML against schema) | 📋 Planned |
| E-03C | Operator dispatch engine (runtime connector) | 📋 Planned |
| E-03D | Operator observability (metrics + reports) | 📋 Planned |

## Operators

| ID | Capability | Mode | Domains | Priority |
|----|-----------|------|---------|----------|
| `runtime-health-check` | ai-lab-runtime | readonly | ai-lab | 80 |
| `marketplace-audit` | marketplace-operator | readonly | marketplace | 60 |
| `observability-query` | observability | readonly | observability | 50 |
| `deployment-review` | deployment-review | advisory | ai-lab, gitnexus | 70 |
| `incident-triage` | incident-response | advisory | ai-lab, observability | 90 |

## References

- ADR-003: `docs/hermes/ADR-003-OPERATOR-REGISTRY.md`
- Capability Registry: `runtime/hermes/capabilities/`
- SOUL: `runtime/hermes/soul/`
- Enterprise Design: `docs/hermes/HERMES-ENTERPRISE-DESIGN-01.md`
