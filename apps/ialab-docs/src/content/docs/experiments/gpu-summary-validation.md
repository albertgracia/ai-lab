---
title: "GPU Summary Validation"
summary: "Validación específica de summaries GPU compactos: métricas vivas, source_of_truth, freshness, confidence y compatibilidad del alias gpu_summary."
order: 29
---

## Objetivo

Comprobar que AI-LAB responde sobre GPUs usando summaries compactos en vez de solo inventario.

## Señales verificadas

- métricas vivas RX9070
- no métricas inventadas RX7900XT
- `source_of_truth`
- `freshness`
- `confidence`
- alias backward compatible `gpu_summary`
