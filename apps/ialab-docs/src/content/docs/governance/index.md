---
title: "Governance AI-LAB"
summary: "Documentación de gobernanza del runtime: herramientas, policies, evidence enforcement, governance visibility y reglas operacionales."
order: 2
---

## Qué contiene

- **Evidence enforcement** (FASE 30H) — catálogo de evidencia, strict evidence mode, denylists, supresión de alucinaciones, NO DISPONIBLE
- **Runtime trust boundaries** — límites de confianza del runtime, confidence per-domain, observed/derived separation
- **Archive governance** — manifests, exclusiones, recursividad y storage hygiene como parte del runtime governance
- **Governance visibility** (FASE 30E) — transparencia de decisiones de gobernanza
- **Tool policies** (FASE 22A-22B) — 3 modos de tools, bash sanitizer, confirmation gate
- **Operational Truth vs Discoverable** — separación active/loaded/discoverable/disabled y anti-drift.
- **Worktree governance** — reglas de staging, runtime/state, commits y tags.
- **Phase closure protocol (01)** — checklist obligatorio para cierre de fase: evaluación documental, Astro build, reindexación AnythingLLM y validación de recuperación.
- **AnythingLLM reindex automation** — script PowerShell para automatizar el reindexado de AnythingLLM tras cambios documentales, con modos dry-run, apply y smoke queries.

## Principios

- El runtime no puede afirmar lo que no observa
- NO DISPONIBLE si falta evidencia
- Prevención > sanitización
- Toda decisión de governance debe ser visible
- Confianza per-domain, no global

## Estado

Governance se aplica como disciplina transversal: evidencia, confianza por dominio, límites de autoridad y trazabilidad de cambios.
