---
title: "ADR-003 — Fastpath + Authority"
summary: "Fastpath operacional debe basarse en autoridad/evidencia y mantener respuestas compactas."
order: 43
---

# ADR-003 — Fastpath + Authority

## Contexto

El operador necesita respuestas rápidas a preguntas operacionales (estado runtime, GPUs, exporters, targets).

## Problema

- Respuestas largas y narrativas son lentas.
- Sin autoridad, el fastpath puede inventar.

## Decisión

- Fastpath responde compacto y evidence-bound.
- Si falta autoridad/freshness: degradar o responder `NO DISPONIBLE`.

## Consecuencias

- Mejor TTFB y consistencia.
- Menor riesgo de drift.

## Tradeoffs

- Menos “bonito” en lenguaje; más operativo.

## Riesgos evitados

- Fastpath que alucina infraestructura.
- Fastpath que promueve inventory/discovery.
