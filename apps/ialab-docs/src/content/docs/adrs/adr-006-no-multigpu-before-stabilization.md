---
title: "ADR-006 — No Multi-GPU Before Stabilization"
summary: "Decidir explícitamente retrasar Multi-GPU hasta que maturity/governance/precision/memory estén estables."
order: 46
---

# ADR-006 — No Multi-GPU Before Stabilization

## Contexto

Multi-GPU añade scheduling, placement y nuevos failure domains.

## Problema

Si se introduce Multi-GPU antes de:

- autoridad sólida,
- precisión semántica,
- governance visible,
- burn-in y SLO baseline,

entonces el runtime acumula drift y el troubleshooting se vuelve no determinista.

## Decisión

Mantener un estado pre-Multi-GPU hasta cerrar estabilización y madurez.

## Consecuencias

- Roadmap más realista.
- Menos riesgo operacional.

## Tradeoffs

- Menos throughput potencial a corto plazo.

## Riesgos evitados

- Scheduler “mágico” sin contratos.
- Operación sin verdad operacional consistente.
