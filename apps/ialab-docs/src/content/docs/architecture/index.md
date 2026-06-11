---
title: "Arquitectura del Runtime"
summary: "Arquitectura real del runtime AI-LAB: dominios (bounded contexts), truth layers, evidencia, autoridad, precisión, fastpath y cognición estructural."
order: 3
---

## Qué contiene

- **AI-LAB Runtime Domains** — mapa real de dominios (authority/validation/precision/operator_intent, orchestration, intelligence, structural cognition, memory, governance).
- **Federation Governance Bootstrap (01)** — registry + contracts + agent isolation (sin mover lógica todavía).
- **Runtime Observability Fabric** — tejido de observabilidad del runtime.
- **Sensor Fusion Pipeline** — flujo completo de sensores hasta summaries operacionales.
- **Evidence-Bound Runtime** — disciplina operacional para que el LLM no invente infraestructura.
- **Storage Archive Policy** — governance del archive histórico y separación de tiers.
- **Pre-Multi-GPU Baseline** — baseline estable antes de scheduler y placement Multi-GPU.
- **AnythingLLM Role** — memoria documental, auditor RAG, consumidor oficial de documentación canónica.
- **Cognitive Health Layer (37A)** — capa de salud del runtime: bounded, read-only, metadata-only, fail-safe. Contrato `37A-COGNITIVE-HEALTH-LAYER-01`.

## Alineación reciente

- ARCH-STABILIZATION-PASS-01
- 36A / 36B / 36C
- OBS-HF-LMSTUDIO-OPERATIONAL-TRUTH
- WORKTREE-GOVERNANCE-CLEANUP

## Fases cubiertas

- `30H`
- `30I`
- `30I-B`
- `30I-C`
- `30I-D`
- `STORAGE-HARDENING`

## Checkpoint actual

Esta sección está alineada a un runtime stabilization-first y governance-first. No asume Multi-GPU activo.

## Estado estable

La arquitectura ya tiene capa de evidencia, contrato de sensores y política de archive. No es todavía una arquitectura Multi-GPU.

## Próximos pasos

- mantener la baseline pre-Multi-GPU
- no mezclar scheduler con observability contract
- documentar authority + precision + operator intent como núcleo cognitivo
- consolidar documentación AnythingLLM como memoria documental oficial
