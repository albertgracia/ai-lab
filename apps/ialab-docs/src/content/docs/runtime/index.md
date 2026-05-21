---
title: "Runtime AI-LAB"
summary: "Documentación del runtime de AI-LAB: estado actual, capa de madurez, topología, modelos activos y baseline pre-Multi-GPU."
order: 1
---

## Qué contiene

- **Estado actual del runtime** — control-plane, backend, modelos activos, servicios, endpoints y checkpoints principales
- **Capa de madurez del runtime** (FASE 30A-30H) — runtime generation, model state awareness, degraded mode, governance visibility, route semantics, operational reporting, evidence enforcement
- **Baseline pre-Multi-GPU** — por qué se pospuso, qué se cerró, estado listo para FASE 31A

## Fases cubiertas

| FASE | Descripción |
|------|-------------|
| 30A | Runtime state foundation & maturity descriptors |
| 30B | Model state awareness (active/loaded/discoverable) |
| 30C | Single-node explicit degraded mode |
| 30D | Topology role & failure domain taxonomy |
| 30E | Governance visibility refinement |
| 30F | Cognitive route semantics |
| 30G | Operational reporting discipline |
| 30H | Runtime evidence enforcement |
| 30I | Runtime sensor fusion (Prometheus-backed, 13 dominios, GPU metrics en vivo) |

## Checkpoint actual

**CP-30I-RUNTIME-SENSOR-FUSION-STABLE** — FASE 30I completada, sensor fusion con 13 dominios, 29 tests PASS, endpoint /runtime/sensors operativo.
