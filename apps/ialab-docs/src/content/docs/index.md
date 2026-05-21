---
title: "AI-LAB Docs"
summary: "Índice principal de la documentación técnica de AI-LAB: runtime, arquitectura, observabilidad, governance, experimentos, esquemas y roadmap operativo."
order: 1
---

## Qué contiene

- **Runtime**: estado actual, capa de madurez, sensor fusion, semántica de sensores y contrato `OBSERVED_RUNTIME`.
- **Architecture**: observability fabric, pipeline de sensor fusion, reporting evidence-bound, storage archive policy y baseline pre-Multi-GPU.
- **Observability**: Prometheus, GPU metrics, dominios de sensores, dashboards y calidad de fuentes.
- **Governance**: enforcement, trust boundaries y archive governance.
- **Experiments**: burn-ins y validaciones de grounding para qwen y summaries GPU.
- **Schemas**: contratos normalizados de `OBSERVED_RUNTIME`, `sensor_snapshot`, `gpu_operational_summary` y archive manifests.
- **Roadmap**: baseline pre-Multi-GPU y readiness de FASE 31.

## Fases cubiertas

- `30H` — Runtime Evidence Enforcement
- `30H.1` — Universal Evidence Guard
- `30H.2` — Runtime Context Injection
- `30I` — Runtime Sensor Fusion
- `30I-B` — Sensor Fusion Hardening
- `30I-C` — Sensor Summary Exposure
- `30I-D` — Sensor Semantics Normalization
- `STORAGE-HARDENING` — External Archive Policy

## Checkpoint actual

**CP-DOC-30I-RUNTIME-SENSOR-FUSION-DOCS-STABLE**

## Estado estable

AI-LAB ya no opera solo como LLM + routing + prompts. Opera como runtime observacional cognitivo con evidencia respaldada por Prometheus, sensor fusion, reporting evidence-bound, semántica de GPUs y governance de storage.

## Próximos pasos

- Refinar presentación de respuestas cortas GPU sobre el contrato 30I-D.
- Mantener baseline estable antes de reactivar trabajo Multi-GPU.
