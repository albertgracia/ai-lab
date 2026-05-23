---
title: "Codebase Structural Cognition"
summary: "Documentación técnica de la integración GitNexus como memoria estructural del código fuente: dependency graphs, blast radius, ownership mapping, structural risks y cognitive pipeline."
order: 35
---

# Codebase Structural Cognition

## Overview

AI-LAB's codebase structural cognition module (`runtime/codebase/`) provides deterministic, grounded understanding of the runtime's own source code structure. It answers three operational questions:

1. **What does the codebase look like structurally?** — module inventory, dependency graph, domain topology
2. **What breaks if I change X?** — blast radius analysis via BFS traversal
3. **Who owns what?** — ownership mapping from module paths to operational domains

## Architecture

```
runtime/codebase/
├── __init__.py              # Public API exports
├── contracts.py             # Dataclasses, OWNERSHIP_DOMAINS, constants
└── gitnexus_memory.py       # AST scanner, graph builder, risk engine
```

### Truth Separation

AI-LAB maintains three independent truth layers:

| Layer | Source | Responsibility |
|---|---|---|
| **Prometheus** | Gateway :8008/metrics | Runtime authority truth — what is happening now |
| **OperationalTruth** | Sensor fusion + maturity | Semantic runtime truth — what the runtime knows |
| **GitNexus** | `runtime/codebase/` AST scan | Codebase structural truth — what the code looks like |

### Deterministic by Construction

Every codebase memory call produces a `determinant_signature` — a SHA-256 hash of the module list, edge list, and risk inventory. Same codebase → same signature. This enables:

- Reproducible blast radius analysis
- Change detection via signature comparison
- Validation invariants that check determinism

### Cache Layer

A TTL-based cache (default 30 seconds) prevents re-scanning on every request. Cache state is exposed via `get_codebase_cache_state()`.

## Module Scanning

### AST Import Parsing

`_parse_imports()` reads each `.py` file, parses its AST, and extracts all `import` and `from ... import` statements:

```python
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            targets.append(alias.name)
    elif isinstance(node, ast.ImportFrom):
        if node.module:
            targets.append(node.module)
```

Edges are filtered to only `runtime.*` imports between tracked modules.

### Ownership Domains

Each module path maps to an operational domain via `OWNERSHIP_DOMAINS`:

| Domain | Module Paths |
|---|---|
| `authority` | `runtime/authority` |
| `governance` | `runtime/governance` |
| `validation` | `runtime/validation` |
| `gateway` | `runtime/gateway` |
| `incidents` | `runtime/incidents` |
| `codebase` | `runtime/codebase` |
| `observability` | `runtime/observability` |
| `reporting` | `runtime/reporting` |
| `telemetry` | `runtime/telemetry` |
| `infrastructure` | `runtime/infrastructure` |
| ... | ... (24 domains total) |

## Blast Radius Engine

The blast radius is computed via BFS traversal through reverse dependency edges:

```python
for each module:
    impacted = {module}
    queue = [module]
    while queue:
        current = queue.pop(0)
        for dependent, deps in dep_map.items():
            if current in deps and dependent not in visited:
                visited.add(dependent)
                impacted.add(dependent)
                queue.append(dependent)
```

Severity classification:

| Impacted modules | Severity |
|---|---|
| 1-2 | low |
| 3-5 | medium |
| 6+ | high |

## Structural Risk Detection

Three risk types are identified automatically:

### High Coupling
Module imports 5+ other modules. Indicates the module has wide-ranging external dependencies.

### High Reverse Coupling
Module is imported by 5+ other modules. Indicates the module is a hub — changes here propagate widely.

### Wide Blast Radius
Module change impacts 6+ other modules via transitive dependency chains.

### Authority Dependency Spread
Detected when the authority module is imported by 3+ other domains — indicating operational dependency concentration.

## Structural Health Score

The score formula:

```
base = 100
base -= high_risks * 5      (max -50)
base -= medium_risks * 2     (max -30)
base -= edge_density penalty (max -15 if density > 5.0)
score = max(10, min(100, base))
```

Levels:

| Score | Level |
|---|---|
| >= 80 | healthy |
| 50-79 | degraded |
| < 50 | critical |

## Gateway API

All endpoints under `GET /runtime/codebase/*` return JSON with `determinant_signature`.

### Summary

```
GET /runtime/codebase/summary
Response: { contract_version, summary, score, freshness, gitnexus_stats, determinant_signature }
```

### Modules

```
GET /runtime/codebase/modules
Response: { contract_version, modules: [{ path, module_name, domain, file_count }], ... }
```

### Dependencies

```
GET /runtime/codebase/dependencies
Response: { contract_version, edges: [{ source, target, edge_type }], modules, ... }
```

### Blast Radius

```
GET /runtime/codebase/blast-radius?module_path=gateway
Response: { results: [{ module_path, affected_domains, total_impacted, severity }], ... }
```

### Ownership

```
GET /runtime/codebase/ownership
Response: { domains: [{ domain, paths, file_count }], ... }
```

### Topology

```
GET /runtime/codebase/topology
Response: { modules_total, domains_total, edges_total, hotspots, domain_dependency_matrix }
```

### Risks

```
GET /runtime/codebase/risks
Response: { risks: [{ risk_type, domain, severity, description }], score, ... }
```

### Score

```
GET /runtime/codebase/score
Response: { score: { structural_health_score, level, modules_total, ... } }
```

## Metrics

Six Prometheus counters track codebase memory:

| Metric | Type | Description |
|---|---|---|
| `ailab_codebase_modules_total` | Gauge | Total scanned modules |
| `ailab_codebase_dependency_edges_total` | Gauge | Total dependency edges |
| `ailab_codebase_structural_health_score` | Gauge | Current health score (0-100) |
| `ailab_codebase_hotspots_total` | Gauge | Modules with >= 3 dependencies |
| `ailab_codebase_risks_total` | Gauge | Total structural risks |
| `ailab_codebase_ownership_domains_total` | Gauge | Unique ownership domains |
| `ailab_codebase_memory_freshness_seconds` | Gauge | Seconds since last memory generation |

## Integration Points

### Governance Integration

The governance registry includes `codebase_memory_health` as a monitored domain. Structural health score < 50 triggers a governance degradation flag.

### Validation Integration

Four invariants ensure codebase memory integrity:

| Invariant | Blocking | Description |
|---|---|---|
| `INVARIANT-CODEBASE-MEMORY-GROUNDED` | No | Pass if modules > 0 and edges > 0 |
| `INVARIANT-NO-PHANTOM-MODULES` | No | Pass if level != unknown or modules > 0 |
| `INVARIANT-BLAST-RADIUS-DETERMINISM` | No | Pass if same signature in strict mode |
| `INVARIANT-NO-RUNTIME-STATE-CONTAMINATION` | Yes | Fail-blocking if any module path contains `runtime/state` |

### Incident Intelligence

`detect_codebase_incidents()` fires when:
- Structural health score < 50 (high/critical)
- High-risk count > 3 (high)
- Wide blast radius detected (medium)

Incident reports are enriched with codebase ownership and hotspots.

### Cognitive Compression

`compress_codebase_signals()` in `cognitive_compression.py` surfaces:
- Structural health score and level
- High risk count
- Hotspot modules
- Wide blast radius entries

### Operational Reporting

`build_codebase_memory_summary()` in `reporting_engine.py` exposes:
- `structural_health_score`
- `modules_total`, `edges_total`
- `high_risks`, `medium_risks`
- `hotspots`, `domain_dependencies`
- `freshness`

## Runbooks

See:

- [Safe Refactor Workflow](/runbooks/safe-refactor-workflow)
- [Blast Radius Review](/runbooks/blast-radius-review)
- [Dependency Risk Analysis](/runbooks/dependency-risk-analysis)
- [Runtime-Codebase Correlation](/runbooks/runtime-codebase-correlation)
- [Incident-to-Module Analysis](/runbooks/incident-to-module-analysis)
