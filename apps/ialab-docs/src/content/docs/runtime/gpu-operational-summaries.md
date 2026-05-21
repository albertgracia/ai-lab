---
title: "GPU Operational Summaries"
summary: "Diseño y uso de los summaries compactos de GPU introducidos en 30I-C y normalizados en 30I-D para respuestas operacionales cortas."
order: 14
---

## Problema que resolvieron

Antes de 30I-C, el runtime respondía correctamente pero de forma ciega a telemetría fina. Usaba principalmente:

- `inference_nodes`
- inventory de modelos
- topología básica

Sin exponer con consistencia:

- temperatura
- potencia
- carga GPU
- VRAM usada/libre
- fan RPM
- source_of_truth
- freshness
- confidence

## Solución

`build_gpu_operational_summary()` y luego `gpu_operational_summaries`.

## Flujo

```mermaid
flowchart LR
    GX[GPU exporter] --> P[Prometheus]
    P --> SF[sensor_fusion.py]
    SF --> SNAP[sensor_snapshot]
    SNAP --> GPS[gpu_operational_summaries]
    GPS --> ANSWER[short GPU answer]
```

## Caso RX9070

- `inventory_state = known`
- `observed_state = online`
- `operational_state = active`
- métricas vivas disponibles

## Caso RX7900XT

- `inventory_state = known`
- `observed_state = expected_offline`
- `operational_state = inactive`
- sin métricas vivas inventadas

## Qué no hace

- no activa Multi-GPU
- no implica scheduler
- no convierte inventory en runtime activo
