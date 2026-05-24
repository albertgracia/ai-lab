---
title: "Runtime Topology Intelligence"
summary: "Topología operational: dependencias, authority chains, blast radius y drift. Separación active/inventory/discoverable."
order: 33
---

AI-LAB expone topología como señal operacional (no como diagrama estático).

## Endpoints

```text
GET /runtime/topology
GET /runtime/topology/dependencies
GET /runtime/topology/authority
GET /runtime/topology/blast-radius
GET /runtime/topology/confidence
GET /runtime/topology/drift
```

## Semántica clave

- **active**: componente operando ahora.
- **inventory**: existe pero no está en operación.
- **discoverable**: visible por discovery, no necesariamente operativo.

## Diagrama: topología runtime

```mermaid
flowchart TD
  GW[Gateway :8008] --> LM[LM Studio :1234]
  GW --> P[Prometheus :9090]
  GW --> G[Grafana :3000]
  GW --> GN[GitNexus]
  GW --> R[Router :8083]
  GW --> L[Live API :8084]
```
