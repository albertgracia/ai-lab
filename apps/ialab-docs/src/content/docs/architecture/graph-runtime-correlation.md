---
title: "Graph Runtime Correlation"
summary: "Roadmap 37A: correlación entre topología (GitNexus) y señales runtime (SLO, triage, alerting) para priorización operacional."
order: 36
---

Esta fase conecta **estructural truth** (GitNexus) con **runtime truth** (Prometheus/SLO/Triage).

## Objetivo

- Detectar cuándo un hotspot topológico se convierte en riesgo operacional real.
- Priorizar incidentes por blast radius + evidencias + SLO.

## Inputs

- Graph reasoning (`/runtime/graph/*`)
- SLO (`/runtime/slo/*`, `/slo/health`)
- Triage (`/runtime/triage/*`)
- Alerting (Prometheus `ALERTS`)

## Output esperado

- Correlation score por módulo/dominio.
- Explicación (por qué correlaciona).
- Recomendaciones bounded y no destructivas.

```mermaid
flowchart LR
  GN[GitNexus] --> C[Correlation Engine]
  SLO[SLO] --> C
  T[Triage] --> C
  A[Alerts] --> C
  C --> P[Prioritized actions
  (safe by default)]
```
