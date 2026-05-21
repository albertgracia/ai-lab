---
title: "Runtime Trust Boundaries"
summary: "Límites de confianza entre observación, inventario, derivación y generación LLM dentro del runtime AI-LAB."
order: 25
---

## Fronteras

- `observed_state` -> lo que se observó
- `inventory_state` -> lo que existe como inventario
- `derived_state` -> lo que el runtime dedujo
- `response_text` -> lo que el LLM produce

## Regla

El LLM nunca debe elevar inventario a evidencia observada.

Ejemplo:

- RX7900XT existe en inventario
- no por eso está online
- no por eso tiene métricas vivas
- no por eso es routable
