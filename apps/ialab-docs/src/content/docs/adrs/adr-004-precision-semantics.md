---
title: "ADR-004 — Precision Semantics"
summary: "Definir precisión como integridad de evidencia (partial/conflicts/stale) y degradación visible."
order: 44
---


## Contexto

El runtime observa múltiples fuentes con diferentes niveles de freshness y confianza.

## Problema

- Sin semántica de precisión, el runtime puede presentar respuestas como “seguras” aunque falte evidencia.

## Decisión

- Exponer marcadores de precisión (`partial_state_total`, `authority_conflicts_total`, `stale_evidence_total`).
- Hacer degradación explícita y visible.

## Consecuencias

- Operación entiende el “por qué” de respuestas conservadoras.
- Reduce regresiones silenciosas.

## Tradeoffs

- Más complejidad en reporting.

## Riesgos evitados

- “Confidence inflation”.
- Drift cognitivo por evidencia parcial.
