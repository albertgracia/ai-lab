---
title: "Architecture Stabilization Map (ARCH-STABILIZATION-PASS-01)"
summary: "Mapa de estabilización arquitectónica: desacoplos mínimos, consistencia de métricas gateway y extracción de handlers para reducir fragilidad sin cambiar comportamiento."
order: 5
---

# Architecture Stabilization Map (ARCH-STABILIZATION-PASS-01)

ARCH-STABILIZATION-PASS-01 fue un esfuerzo de estabilización: cambios pequeños, verificables y orientados a reducir fragilidad, no a añadir features.

## Principios

- Cambios mínimos.
- Sin modificar comportamiento operacional.
- Compilación y tests como gate.

## Mapa (alto nivel)

```mermaid
flowchart TD
  subgraph BEFORE[Antes]
    OG[openai_gateway.py\n(gateway supernodo)] --> PM[prometheus metrics\n(shims divergentes)]
    OG --> RAPI[runtime api routes\n(mezcladas)]
    INIT[runtime/__init__.py\n(re-export pesado)] --> MANY[múltiples imports]
  end

  subgraph AFTER[Después]
    OG2[openai_gateway.py\n(entrypoint)] --> GM[gateway_metrics.py\n(source-of-truth]
    OG2 --> ROUTES[runtime_api_routes.py\n(handlers extraídos)]
    INIT2[runtime/*/__init__.py\n(import-light + lazy __getattr__)] --> LESS[menos acoplamiento]
  end
```

## Qué se ganó

- Métricas coherentes en gateway (un único source-of-truth).
- Menos acoplamiento por re-export.
- Handlers de rutas runtime extraídos para limitar el crecimiento del gateway.

## Qué NO cambió

- APIs públicas.
- Comportamiento del gateway.
- Estado vivo (`runtime/state/*`).
