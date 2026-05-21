---
title: "Runtime Maturity Layer"
summary: "Cómo AI-LAB pasó de routing reactivo a un runtime observacional cognitivo con evidencia, semántica de sensores y contratos operacionales explícitos."
order: 11
---

## Visión

El runtime de AI-LAB ya no es una suma de prompts y rutas. Ahora tiene una capa de madurez operacional que separa:

- inventario
- estado observado
- estado derivado
- confianza
- freshness
- evidence level

## Evolución por hitos

```text
FASE 29  → observabilidad y protección runtime
FASE 30H → evidence enforcement
FASE 30I → sensor fusion
FASE 30I-B → hardening
FASE 30I-C → GPU summaries compactos
FASE 30I-D → normalización semántica
```

## Qué aporta esta capa

1. **Observed vs derived separation**
Todo dato observado queda separado del dato derivado para evitar mezclar evidencia con interpretación.

2. **Per-domain confidence**
La confianza se calcula por dominio, no como un valor global único.

3. **Freshness explícita**
El runtime no finge actualidad. Distingue `fresh`, `stale`, `expired` y `unavailable`.

4. **Inventory semantics**
Un nodo inventariado no equivale a un nodo operativo. RX7900XT es el caso canónico.

5. **LLM grounding operacional**
El modelo recibe contratos observables, no solo texto libre.

## Regla de madurez

Un runtime está listo para evolucionar cuando puede describirse a sí mismo sin inventar:

- qué nodo está activo
- qué nodo está inventariado
- qué métricas son observadas
- qué estados son derivados
- qué confianza merece cada dominio

Eso es exactamente lo que cierra 30I-D.
