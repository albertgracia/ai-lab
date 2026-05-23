---
title: "Runtime Truth Layers"
summary: "Arquitectura de las tres capas de verdad del runtime AI-LAB: Prometheus, OperationalTruth y GitNexus. Separación de responsabilidades y correlación entre fuentes."
order: 10
---

# Runtime Truth Layers

AI-LAB operates on three independent truth layers, each with distinct responsibilities, sources, and consumers.

## The Three Layers

```
┌─────────────────────────────────────────────────────────┐
│                 RUNTIME TRUTH LAYERS                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────┐  ┌────────────────────────┐  │
│  │    Prometheus        │  │    OperationalTruth     │  │
│  │  Runtime Authority   │  │  Semantic Runtime Truth │  │
│  │                      │  │                        │  │
│  │  • Gateway metrics   │  │  • Sensor fusion        │  │
│  │  • GPU metrics       │  │  • Runtime maturity     │  │
│  │  • Scrape targets    │  │  • Degradation state    │  │
│  │  • Alert rules       │  │  • Domain confidence    │  │
│  │  • TTFB/latency      │  │  • Evidence catalog     │  │
│  └──────────┬───────────┘  └───────────┬────────────┘  │
│             │                          │               │
│             └──────────┬───────────────┘               │
│                        │                               │
│             ┌──────────▼───────────┐                   │
│             │     GitNexus         │                   │
│             │  Codebase Structural │                   │
│             │      Truth           │                   │
│             │                      │                   │
│             │  • AST scanning      │                   │
│             │  • Dependency graph  │                   │
│             │  • Blast radius      │                   │
│             │  • Ownership mapping │                   │
│             │  • Structural risks  │                   │
│             └──────────────────────┘                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### 1. Prometheus — Runtime Authority Truth

**Source**: Gateway (:8008/metrics), Router (:8083/metrics), Live API (:8084/metrics), GPU exporters (:9182, :9183), node_exporter (:9100)

**Responsibility**: What is happening right now in the runtime.

- Request counts, latencies, streaming stats
- GPU temperature, VRAM, load
- Scrape health of all targets
- Alert rule evaluation

**Consumed by**: Grafana dashboards, alertmanager, sensor fusion, fastpath

**Contract**: Standard Prometheus exposition format. No semantic interpretation — raw numerical data.

### 2. OperationalTruth — Semantic Runtime Truth

**Source**: `runtime/semantics/runtime_maturity.py`, `runtime/context/sensor_fusion.py`, `runtime/governance/`, `runtime/validation/`

**Responsibility**: What the runtime knows about itself, semantically.

- Domain health confidence scores
- Degradation state (which domains, why)
- Evidence catalog for governance decisions
- Runtime maturity level
- Topology mode inference

**Consumed by**: Reporting engine, cognitive compression, incidents, governance, operator UI

**Contract**: Dict-based with `freshness`, `confidence`, `determinant_signature`. No raw metrics — interpreted state.

### 3. GitNexus — Codebase Structural Truth

**Source**: `runtime/codebase/` — AST scan of `/opt/ai-lab/runtime/`

**Responsibility**: What the codebase looks like structurally.

- Module inventory (62 modules)
- Dependency graph (274 directed edges)
- Blast radius per module (BFS traversal)
- Ownership mapping (24 domains)
- Structural risks (high coupling, reverse coupling, wide blast)
- Health score (0-100)

**Consumed by**: Validation invariants, governance registry, incident intelligence, cognitive compression, reporting

**Contract**: JSON with `determinant_signature`. Same codebase → same graph → same signature.

## Correlation Between Layers

### Prometheus ↔ OperationalTruth

- Prometheus raw counters → sensor fusion → domain confidence
- GPU metrics → operational summaries → GPU health state

### OperationalTruth ↔ GitNexus

- Governance degradation alerts → codebase blast radius check
- Incident intelligence → codebase ownership and hotspot enrichment

### Prometheus ↔ GitNexus

- Prometheus `ailab_governance_blocked_total` spike → GitNexus governance module reverse coupling check
- No direct coupling — correlated via OperationalTruth

## Design Rules

### RULE-TL-1

Prometheus is the only runtime authority source. No codebase memory can override Prometheus metrics.

### RULE-TL-2

OperationalTruth is the only semantic interpreter. Raw Prometheus metrics go through sensor fusion before reaching cognitive layers.

### RULE-TL-3

GitNexus is grounded, deterministic, and read-only. No autonomous modifications. No runtime state indexing.

### RULE-TL-4

Cross-layer correlation is additive, not substitutive. A governance incident enriched with codebase blast radius does not replace the incident — it supplements it.

### RULE-TL-5

No layer depends on another for core functionality. If GitNexus is unavailable, the runtime continues operating on Prometheus + OperationalTruth.

## Layer Stack

```
FastPath / Cognitive Summary
        │
  OperationalTruth (semantic interpretation)
        │
  Prometheus (raw metrics)  ───  GitNexus (structural codebase)
        │                              │
  GPU / Gateway / Router          AST scan / import graph
```

Each layer is independently observable, independently testable, and independently versioned via `determinant_signature`.
