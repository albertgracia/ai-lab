---
title: "Prometheus Runtime Integration"
summary: "Cómo AI-LAB integra Prometheus en el runtime: query client, cache TTL, timeout, dominios y métricas que alimentan sensor fusion."
order: 20
---

## Rol de Prometheus

Prometheus no es solo observabilidad pasiva. Es fuente de verdad operativa para el runtime.

## Componentes

- `PrometheusQueryClient`
- cache TTL 5s
- timeout 2s
- `query_instant()`
- `get_target_up()`
- `query_gpu_metrics()`

## Señales clave

- estado de targets
- métricas GPU
- SLO state
- degradation level
- system node
- route families

## Garantía operacional

Si Prometheus falla:

- el runtime no inventa datos
- degrada a `NO DISPONIBLE`
- mantiene contract semantics
