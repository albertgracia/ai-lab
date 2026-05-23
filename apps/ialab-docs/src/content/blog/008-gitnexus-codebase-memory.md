---
title: "Giving AI-LAB Real Codebase Memory with GitNexus"
date: "2026-05-23"
summary: "How AI-LAB integrates GitNexus as structural codebase memory — dependency graphs, blast radius analysis, ownership cognition, and deterministic structural risk scoring."
tags:
  - ai-lab
  - gitnexus
  - codebase
  - cognition
  - architecture
---

# Giving AI-LAB Real Codebase Memory with GitNexus

AI-LAB has evolved from a simple LLM gateway into a runtime with operational cognition. It monitors itself via Prometheus, reasons about its state via sensor fusion, and makes governance decisions based on evidence.

But there was a gap: **AI-LAB had no structural understanding of its own codebase.**

When the runtime detected a governance drift in the `authority` module, it couldn't reason about which other modules depended on it. When a validation invariant failed in `tool_registry.py`, there was no way to trace which execution flows would break.

GitNexus closes that gap.

## The Three Truth Layers

AI-LAB now operates on three distinct truth layers, each with a different responsibility:

```
Prometheus        →  Runtime authority truth   (what is happening now)
OperationalTruth  →  Semantic runtime truth    (what the runtime knows)
GitNexus          →  Codebase structural truth (what the code looks like)
```

These three layers are independent but correlated. A spike in `ailab_governance_blocked_total` from Prometheus can be cross-referenced against GitNexus to determine which module has the widest blast radius — and which deployment should be prioritized.

## How GitNexus Integrates

### Local AST Scanning, No External Dependencies

The codebase memory module at `runtime/codebase/gitnexus_memory.py` scans Python AST in `/opt/ai-lab/runtime/`. It parses `import` statements, builds a directed dependency graph, and derives structural properties — all deterministically.

```python
modules = _scan_runtime_modules()       # 62 modules discovered
edges   = _build_import_graph(modules)  # ~274 directed edges
```

### Ownership Mapping

Every module maps to a runtime domain via `OWNERSHIP_DOMAINS`:

```python
OWNERSHIP_DOMAINS = {
    "authority":     ["runtime/authority"],
    "governance":    ["runtime/governance"],
    "gateway":       ["runtime/gateway"],
    "codebase":      ["runtime/codebase"],
    "incidents":     ["runtime/incidents"],
    ...
}
```

This means an import from `runtime/governance/` into `runtime/authority/` is a cross-domain dependency — governance depends on authority.

### Blast Radius via BFS

When a module changes, the blast radius engine traverses the dependency graph via BFS:

```python
def _build_blast_radius(modules, edges):
    # For each module, BFS to find all impacted modules
    # Severity: 1-2 = low, 3-5 = medium, 6+ = high
```

If `runtime/gateway/openai_gateway.py` changes, the blast radius reveals which `runtime/llm/`, `runtime/router/`, and `runtime/telemetry/` modules are transitively affected.

### Structural Risk Detection

Three risk types are detected:

- **High coupling**: module imports 5+ other modules
- **High reverse coupling**: module is imported by 5+ other modules
- **Wide blast radius**: module impacts 6+ other modules on change

These produce a **structural health score** (0-100):

```python
score = base (100)
       - high_risks * 5
       - medium_risks * 2
       - edge_density penalty
```

## Gateway Endpoints

The codebase memory is exposed via eight runtime endpoints:

| Endpoint | Description |
|---|---|
| `GET /runtime/codebase/summary` | Structural health overview |
| `GET /runtime/codebase/modules` | Module inventory with domains |
| `GET /runtime/codebase/dependencies` | Full dependency edge list |
| `GET /runtime/codebase/blast-radius` | Blast radius by module |
| `GET /runtime/codebase/ownership` | Domain ownership map |
| `GET /runtime/codebase/topology` | Module-domain topology |
| `GET /runtime/codebase/risks` | Structural risk inventory |
| `GET /runtime/codebase/score` | Deterministic health score |

All endpoints return JSON with a `determinant_signature` for reproducibility.

## Integration Points

### Governance

The governance registry includes `codebase_memory_health` as a monitored domain. If structural health drops below 50, governance flags it as a degradation.

### Validation

Four DEV-36X invariants validate codebase memory integrity:

| Invariant | Purpose |
|---|---|
| `INVARIANT-CODEBASE-MEMORY-GROUNDED` | Modules and edges must be non-zero |
| `INVARIANT-NO-PHANTOM-MODULES` | All modules must be real directories |
| `INVARIANT-BLAST-RADIUS-DETERMINISM` | Same codebase → same blast radius |
| `INVARIANT-NO-RUNTIME-STATE-CONTAMINATION` | No `runtime/state/` in codebase graph |

### Incident Intelligence

Incident detection for the `codebase` domain fires when:

- Structural health score < 50 (high severity)
- High-risk count > 3 (high severity)
- Wide blast radius detected (medium severity)

### Cognitive Compression

The cognitive summarizer includes `compress_codebase_signals()` which surfaces codebase health, high risks, hotspots, and wide blast radius in the operational summary.

## Metrics

Six Prometheus counters track codebase structural health:

- `ailab_codebase_modules_total`
- `ailab_codebase_dependency_edges_total`
- `ailab_codebase_structural_health_score`
- `ailab_codebase_hotspots_total`
- `ailab_codebase_risks_total`
- `ailab_codebase_ownership_domains_total`
- `ailab_codebase_memory_freshness_seconds`

## Why Not a Full IDE Integration?

GitNexus is not a code analysis platform. It's a **structural memory layer**. It doesn't need to understand semantics, execution paths, or data flow. It answers three questions:

1. What does the codebase look like structurally?
2. What breaks if I change X?
3. Who owns what?

That's all the runtime needs for operational cognition.

## Current State

- **Index**: 460 files, 10,145 nodes, 15,369 edges (GitNexus v1.6.5)
- **Modules**: 62 runtime modules, ~274 dependency edges
- **Score**: varies by codebase state, typically 20-80
- **Cache**: 30-second TTL with deterministic invalidation
- **Tests**: 31 tests, all passing deterministically
