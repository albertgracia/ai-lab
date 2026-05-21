---
title: "Sensor Fusion Pipeline"
summary: "Pipeline de adquisición, fusión y exposición semántica de sensores en AI-LAB: desde Prometheus y LM Studio hasta OBSERVED_RUNTIME y respuestas del LLM."
order: 16
---

## Pipeline

```mermaid
flowchart LR
    P[Prometheus]
    GX[GPU exporters]
    LMS[LM Studio API]
    RE[Runtime endpoints]

    GX --> P
    P --> SF[sensor_fusion.py]
    LMS --> SF
    RE --> SF

    SF --> SS[sensor_snapshot]
    SF --> GPS[gpu_operational_summaries]
    SF --> ORT[OBSERVED_RUNTIME]
    ORT --> EG[evidence_guard]
    EG --> R[respuesta grounded]
```

## Etapas

1. adquisición de señales
2. normalización por dominio
3. derivación de topología
4. cálculo de confidence
5. construcción de summaries compactos
6. inyección en `OBSERVED_RUNTIME`
7. sanitización post-respuesta

## Resultado

Un contrato operacional reusable por:

- `/runtime/sensors`
- `OBSERVED_RUNTIME`
- evidence guard
- respuestas cortas GPU
