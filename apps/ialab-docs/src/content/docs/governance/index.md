---
title: "Governance AI-LAB"
summary: "Documentación de gobernanza del runtime: herramientas, policies, evidence enforcement, governance visibility y reglas operacionales."
order: 2
---

## Qué contiene

- **Evidence enforcement** (FASE 30H) — catálogo de evidencia, strict evidence mode, denylists, supresión de alucinaciones, NO DISPONIBLE
- **Governance visibility** (FASE 30E) — transparencia de decisiones de gobernanza
- **Tool policies** (FASE 22A-22B) — 3 modos de tools, bash sanitizer, confirmation gate

## Principios

- El runtime no puede afirmar lo que no observa
- NO DISPONIBLE si falta evidencia
- Prevención > sanitización
- Toda decisión de governance debe ser visible

## Checkpoint actual

**CP-30H-RUNTIME-EVIDENCE-ENFORCEMENT-STABLE** — evidence guard con denylists, strict mode, hallucination suppression.
