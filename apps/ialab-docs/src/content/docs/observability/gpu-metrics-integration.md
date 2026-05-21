---
title: "GPU Metrics Integration"
summary: "Integración de métricas GPU en vivo: exporter, Prometheus, sensor fusion y summaries operacionales de RX9070/RX7900XT."
order: 21
---

## Métricas integradas

- temperatura
- carga GPU
- potencia
- fan RPM
- VRAM usada
- VRAM total
- VRAM libre

## Transformación

Las métricas crudas se compactan y normalizan antes de llegar al LLM.

No se expone:

- flood de series raw
- nombres internos no normalizados
- inferencias sin separar de observación

## Caso actual

- RX9070 -> métricas vivas
- RX7900XT -> inventario expected_offline sin métricas vivas
