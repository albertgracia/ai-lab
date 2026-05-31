---
title: "Operational Truth vs Discoverable"
summary: "Separación activa entre active/loaded/discoverable/disabled y cómo el runtime evita elevar discovery a verdad operacional."
order: 30
---


AI-LAB distingue explícitamente:

- **active**: modelo operativo en uso
- **loaded**: cargado en backend
- **discoverable**: aparece en inventario/listado, pero no implica uso
- **disabled**: prohibido/retirado del routing

La regla: **discoverable no se trata como operational**.

## Pipeline

```mermaid
flowchart TD
  LM[LM Studio /v1/models] --> INV[Discovery inventory]
  PROM[Prometheus evidence] --> AUTH[Authority snapshot]
  INV --> OT[Operational Truth resolver]
  AUTH --> OT
  OT --> OUT[models.active / models.disabled / inventory-only]
  OUT --> FP[FastPath / Reporting]
```

## Riesgos evitados

- “ctx:0” o modelos de inventario reportados como operacionales.
- Confundir “aparece en /models” con “está routable”.

## Señales

- Fastpath debe declarar explícitamente `Discoverable: N (not operational)` cuando aplica.
