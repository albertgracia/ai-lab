---
title: "AI-LAB Docs"
summary: "Índice principal de la documentación técnica de AI-LAB: runtime, arquitectura, observabilidad, governance, experimentos, esquemas y roadmap operativo."
order: 1
---

## Qué contiene

- **Runtime**: estado actual, madurez, sensor fusion, semántica, authority/precision y contratos operacionales.
- **Architecture**: dominios reales (bounded contexts), truth layers, evidence-bound runtime, baseline pre-Multi-GPU.
- **Observability**: Prometheus, GPU metrics, dominios de sensores, dashboards y calidad de fuentes.
- **Governance**: trust boundaries, operational truth, confidence semantics, worktree governance.
- **Experiments**: burn-ins y validaciones de grounding para qwen y summaries GPU.
- **AnythingLLM**: memoria documental, rol en la arquitectura, separación de responsabilidades y ciclo documental.
- **Schemas**: contratos normalizados de `OBSERVED_RUNTIME`, `sensor_snapshot`, `gpu_operational_summary` y archive manifests.
- **Phase Closure Protocol**: protocolo obligatorio de cierre de fase con evaluación documental, build, reindexación AnythingLLM y validación de recuperación.
- **Roadmap**: stabilization-first, governance-first y preparación pre-Multi-GPU (sin prometer scheduler inmediato).

## Fases cubiertas

- `30H` — Runtime Evidence Enforcement
- `30H.1` — Universal Evidence Guard
- `30H.2` — Runtime Context Injection
- `30I` — Runtime Sensor Fusion
- `30I-B` — Sensor Fusion Hardening
- `30I-C` — Sensor Summary Exposure
- `30I-D` — Sensor Semantics Normalization
- `STORAGE-HARDENING` — External Archive Policy

## Alineación reciente

- `35C` — Authority-backed cognition
- `36A` — Operational incident intelligence
- `36B` — Precision semantics
- `36C` — Operator intent reasoning (metadata, no ejecución)
- `ANYTHINGLLM-01` — AnythingLLM integración documental (memoria documental, consumidor oficial, rol en arquitectura)
- `ARCH-STABILIZATION-PASS-01`
- `WORKTREE-GOVERNANCE-CLEANUP`
- `OBS-HF-LMSTUDIO-OPERATIONAL-TRUTH`

## Nuevas secciones

- **Codebase Structural Cognition**: integración GitNexus, dependency graph, blast radius, ownership, structural risk scoring.
- **Runtime Truth Layers**: las tres capas de verdad del runtime — Prometheus, OperationalTruth y GitNexus.
- **Experiments**: GitNexus Structural Memory Integration (DEV-36X).

## Fases añadidas

- `DEV-36X` — Codebase Memory Integration (GitNexus, dependency graph, blast radius, ownership, structural cognition)

## Estado estable

AI-LAB ya no opera como “LLM + prompts”. Opera como runtime **evidence-bound** con:

- autoridad (Prometheus) separada de cognición,
- verdad operacional semántica (OperationalTruth),
- cognición estructural (GitNexus) como señal complementaria,
- governance explícita y verificable,
- y routing determinista con fastpath operacional.

## Próximos pasos

- Consolidar documentación de domains reales (authority/precision/operator_intent).
- Madurar memoria (Qdrant) con governance clara: implemented vs experimental vs planned.
- Mantener baseline estable antes de reactivar Multi-GPU.
