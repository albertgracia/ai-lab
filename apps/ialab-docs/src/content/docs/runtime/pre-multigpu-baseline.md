---
title: "Baseline Pre-Multi-GPU"
summary: "Documento de baseline previo a FASE 31A: por qué se pospuso Multi-GPU, qué se cerró antes, riesgos mitigados y estado listo."
order: 30
---

## Por qué se pospuso Multi-GPU

Multi-GPU se pospuso porque el runtime necesitaba madurez semántica antes de gestionar múltiples nodos de inferencia heterogéneos. Intentar orquestar RX9070 + RX7900XT sin:

- Model state awareness (active/loaded/discoverable)
- Degraded mode explícito
- Governance visibility
- Route semantics
- Evidence-bound reporting

...habría producido un sistema frágil, no observable y propenso a alucinaciones operacionales.

## Qué se cerró antes de Multi-GPU

| Área | FASE | Checkpoint |
|------|------|------------|
| Runtime state foundation | 30A | CP-30A-RUNTIME-STATE-FOUNDATION-STABLE |
| Model state awareness | 30B | CP-30B-MODEL-STATE-AWARE-STABLE |
| Single-node degraded mode | 30C | CP-30C-DEGRADED-MODE-EXPLICIT-STABLE |
| Topology & failure domain | 30D | CP-30D-TOPOLOGY-FAILURE-DOMAIN-STABLE |
| Governance visibility | 30E | CP-30E-GOVERNANCE-VISIBILITY-STABLE |
| Cognitive route semantics | 30F | CP-30F-ROUTE-SEMANTICS-STABLE |
| Operational reporting | 30G | CP-30G-OPERATIONAL-REPORTING-STABLE |
| Evidence enforcement | 30H | CP-30H-RUNTIME-EVIDENCE-ENFORCEMENT-STABLE |
| Gateway hardening | 29.0 | Gateway hardening completado |
| Real streaming | 29.2 | CP-29.2-B-STREAMING-BURNIN-STABLE |
| Three-model runtime | 29.3 | CP-29.3-THREE-MODEL-RUNTIME-STABLE |
| SLO enforcement | 29.4 | CP-29.4-SLO-ENFORCEMENT-STABLE |
| Error taxonomy | 29.4.4 | CP-29.4.4-ERROR-TAXONOMY-STABLE |

## Riesgos mitigados

| Riesgo | Mitigación |
|--------|------------|
| Reportes inventando hardware | Evidence enforcement (FASE 30H) |
| Modelos fantasma en estado desconocido | Model state awareness (FASE 30B) |
| Degradación silenciosa en nodo único | Degraded mode explícito (FASE 30C) |
| Gobernanza opaca con 2 nodos | Governance visibility (FASE 30E) |
| Enrutamiento a nodo caído sin semántica | Route semantics (FASE 30F) |
| Alucinaciones en informes operacionales | Evidence guard + NO DISPONIBLE (FASE 30H) |

## Estado listo para FASE 31A

- ✅ Runtime estable con identidad operacional
- ✅ Model state tracker con TTL y normalización
- ✅ Degraded mode en nodo único
- ✅ Governance visible y refinado
- ✅ Route semantics por familia
- ✅ Reporting disciplinado con evidence guard
- ✅ 157 maturity tests PASS
- ✅ 38 tags git desde CP-21B-STABLE

## Modelo previsto para RX7900XT

| Atributo | Valor |
|----------|-------|
| Nodo | 192.168.1.60 |
| GPU | RX7900XT (20GB VRAM) |
| Modelo previsto | gpt-oss-20b-derestricted Q4_K_M |
| Uso previsto | Report, heavy cognitive, security audit, IDS design, architecture planning, long reasoning |
| Estado actual | Nodo apagado, modelo sin cargar |

## Rol previsto del RX7900XT

- Reportes pesados (actualmente en qwen2.5-14b)
- Cognitive load alto (arquitectura, planificación)
- Security audit e IDS design
- Long reasoning chains
- Descarga de carga cognitiva desde RX9070

## Lo que NO está listo para Multi-GPU

- ❌ Scheduler contracts
- ❌ Warm pool
- ❌ Queue arbitration
- ❌ Failover chains
- ❌ VRAM-aware routing
- ❌ Cognitive route placement entre nodos

Estos son requisitos de FASE 31A en adelante.
