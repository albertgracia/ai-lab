---
title: "ROADMAP Legacy — AI-LAB Arquitectura Final"
summary: "Hoja de ruta histórica previa al baseline 30I-D. Se conserva como referencia legacy y no sustituye la estructura roadmap normalizada actual."
order: 99
---

> Documento legacy preservado por trazabilidad. La referencia operativa actual para roadmap vive en `/docs/roadmap/`.

## Visión

AI-LAB debe convertirse en un **runtime cognitivo local-first estable**: OpenCode / OpenWebUI / APIs → AI-LAB Router → perfiles cognitivos → memoria semántica limpia → tools controladas → scheduler multi-GPU → LM Studio nodes → observabilidad completa.

---

## FASE 20A — Modelo principal Qwen 2.5 Coder 14B

**Estado:** completada

Migración del modelo por defecto del router a `qwen/qwen2.5-coder-14b-instruct` para las rutas `fast`, `general` y `coding`. Las rutas ligeras (`minimal`, `casual`, `greeting`, `observe`) mantienen `llama-3.1-8b-instruct`.

Ver: `/docs/fase-20a-migracion-qwen2.5-14b`

---

## FASE 20B — Limpieza wrappers legacy

**Estado:** completada

Eliminación de HARD_FACTS automáticos, Plan Mode, reasoning wrappers, structured JSON y tool forcing de las rutas `fast`, `general` y `coding`.

Ver: `/docs/fase-20b-limpieza-wrappers-legacy`

---

## FASE 20C — Normalización de prompts runtime

**Estado:** completada

Separación definitiva de prompts por tipo de ruta sin cambiar arquitectura.

---

## FASE 21 — Perfiles cognitivos

**Estado:** 21A + 21A.1 + 21B completadas

---

## FASE 22 — Tool Runtime controlado

**Estado:** 22A + 22B completadas

---

## FASE 23 — Memoria semántica estable

**Estado:** 23A completada

---

## FASE 24 — Observabilidad cognitiva

**Estado:** avanzada

---

## FASE 25 — Scheduler multi-GPU

**Objetivo histórico:** decidir dinámicamente entre RX9070, RX7900XT y otros nodos LM Studio según carga y modelo.

---

## FASE 28 — Governed Agentic Runtime

**Estado:** implementada por subfases.

---

## FASE 30 — AI-LAB v1.0 estable

### Subfases completadas

| Subfase | Checkpoint | Descripción |
|---------|------------|-------------|
| 30A | CP-30A-RUNTIME-STATE-FOUNDATION-STABLE | Runtime state foundation & maturity descriptors |
| 30B | CP-30B-MODEL-STATE-AWARE-STABLE | Model state awareness |
| 30H | CP-30H-RUNTIME-EVIDENCE-ENFORCEMENT-STABLE | Evidence enforcement |
| 30I | CP-30I-RUNTIME-SENSOR-FUSION-STABLE | Sensor fusion Prometheus-backed |
| 30I-B | CP-30I-B-SENSOR-FUSION-HARDENED-STABLE | Hardening |
| 30I-C | CP-30I-C-SENSOR-SUMMARY-EXPOSURE-STABLE | GPU summaries compactos |
| 30I-D | CP-30I-D-SENSOR-SEMANTICS-NORMALIZED-STABLE | Contrato semántico normalizado |
| STORAGE | CP-STORAGE-HARDENING-ARCHIVE-POLICY-STABLE | Archive governance |

### Nota

La planificación activa previa a Multi-GPU ya no se documenta aquí, sino en:

- `/docs/roadmap/pre-multigpu-readiness/`
- `/docs/roadmap/phase-31-readiness/`
