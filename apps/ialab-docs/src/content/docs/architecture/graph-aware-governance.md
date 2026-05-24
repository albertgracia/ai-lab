---
title: "Graph-Aware Governance"
summary: "Gobernanza informada por topología: hotspots, blast radius, gravity centers y riesgo de acoplamiento. Framework bounded y determinista."
order: 31
---

La gobernanza en AI-LAB no solo observa el runtime: usa **topología del codebase** como señal para priorizar riesgos.

## Qué aporta GitNexus (topología)

- **Hotspots**: módulos con fan-in / fan-out elevados.
- **Blast radius**: severidad estimada por dependencia/transitividad.
- **Gravity centers**: módulos centrales (alta centralidad) que condicionan el resto.
- **Correlaciones**: relación entre topología y señales (SLO, triage, alerting).

## Contrato del framework (bounded)

- Máximos (hard cap): hotspots 20, gravity centers 10, blast radius 20, findings 20, correlations 20.
- TTL cache bounded.
- Read-only: no muta runtime.

## Endpoints runtime

```text
GET /runtime/graph/summary
GET /runtime/graph/hotspots
GET /runtime/graph/blast-radius
GET /runtime/graph/governance
GET /runtime/graph/correlations
GET /runtime/graph/metrics
```

## Métricas Prometheus

- `ailab_graph_hotspots_total`
- `ailab_graph_governance_findings_total`
- `ailab_graph_gravity_centers_total`
- `ailab_graph_high_blast_radius_total`

## Diagrama: señal topológica → gobernanza

```mermaid
flowchart TD
  GN[GitNexus topology
  (imports)] --> GR[Graph Reasoning
  bounded engine]
  P[Prometheus
  authority] --> GR
  T[Autonomous Triage
  signals] --> GR
  GR --> GOV[Governance
  prioritization]
  GR --> OPS[Operational reporting
  (evidence-bound)]
```
