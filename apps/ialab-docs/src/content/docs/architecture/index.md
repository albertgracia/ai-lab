---
title: "Arquitectura del Runtime"
summary: "Arquitectura del runtime observacional: observability fabric, sensor fusion pipeline, evidence-bound runtime, storage archive policy y baseline pre-Multi-GPU."
order: 3
---

## Qué contiene

- **Runtime Observability Fabric** — tejido de observabilidad del runtime.
- **Sensor Fusion Pipeline** — flujo completo de sensores hasta summaries operacionales.
- **Evidence-Bound Runtime** — disciplina operacional para que el LLM no invente infraestructura.
- **Storage Archive Policy** — governance del archive histórico y separación de tiers.
- **Pre-Multi-GPU Baseline** — baseline estable antes de scheduler y placement Multi-GPU.

## Fases cubiertas

- `30H`
- `30I`
- `30I-B`
- `30I-C`
- `30I-D`
- `STORAGE-HARDENING`

## Checkpoint actual

**CP-DOC-30I-RUNTIME-SENSOR-FUSION-DOCS-STABLE**

## Estado estable

La arquitectura ya tiene capa de evidencia, contrato de sensores y política de archive. No es todavía una arquitectura Multi-GPU.

## Próximos pasos

- mantener la baseline pre-Multi-GPU
- no mezclar scheduler con observability contract
