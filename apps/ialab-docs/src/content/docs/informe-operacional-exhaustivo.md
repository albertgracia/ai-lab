---
title: "Informe Operacional Exhaustivo — AI-LAB"
summary: "Reporte NOC completo del estado actual de AI-LAB en 192.168.1.30, incluyendo routing, modelos, GPU, SLO, planner, servicios y estado de fases."
order: 81
---

**Nodo Principal:** 192.168.1.30
**Clasificacion:** Runtime Observed Report
**Modo:** Grounded Runtime Reporting (FASE 29.4.2)
**Tipo:** NOC / Operacional / Infraestructura IA
**Estado General:** OPERATIVO Y ESTABLE
**Checkpoint Runtime:** CP-29.4.2-REPORT-PRESENTATION-STABLE

---

## 1. Executive Summary

El entorno AI-LAB desplegado en 192.168.1.30 se encuentra actualmente operativo como plataforma de inferencia IA, routing cognitivo y observabilidad avanzada para workloads LLM locales.

La infraestructura ha evolucionado desde un gateway OpenAI-compatible basico hacia un runtime cognitivo multi-route con:

- routing adaptativo por perfil
- proteccion SLO dinamica
- observabilidad Prometheus/Grafana
- clasificacion cognitiva
- planner agentic skeleton
- enforcement runtime
- report grounding contextual

Durante las ultimas fases (29.3.x, 29.4.x, 28.1) se estabilizo el runtime con mejoras criticas:

- reduccion TTFB -29%
- 0 crashes
- 0 orphan streams
- 100% success rate en burn-in
- proteccion adaptativa GPU/VRAM
- degradacion dinamica
- aislamiento de modelos deshabilitados

## 2. Identidad del Runtime

| Campo | Valor |
|-------|-------|
| Host principal | 192.168.1.30 |
| Hostname logico | ubuntu-ialab |
| Runtime | AI-LAB Cognitive Runtime |
| Estado | ONLINE |
| Tipo de despliegue | Single-node cognitive runtime |
| Arquitectura | Gateway + Router + Telemetry + Agentic Skeleton |
| Perfil operativo | Produccion experimental estabilizada |
| Runtime generation | FASE 29.4.2 |
| Planner runtime | FASE 28.1 |
| Enforcement runtime | FASE 29.4 |

## 3. Estado Global del Sistema

| Subsistema | Estado |
|------------|--------|
| Gateway OpenAI-compatible | ✅ Operativo |
| Router cognitivo | ✅ Operativo |
| Runtime SLO | ✅ Operativo |
| Observabilidad | ✅ Operativa |
| Planner skeleton | ✅ Operativo |
| Governance | ✅ Operativo |
| Agentic execution | ⚠ Skeleton solamente |
| Sandbox write | ❌ Pendiente |
| Executor readonly | ❌ Pendiente |

## 4. Arquitectura Runtime Actual

```
CLIENT
   ↓
AI-LAB Gateway (:8008)
   ↓
Capability Router
   ↓
Tool Request Classifier
   ↓
Priority Lane Scheduler
   ↓
Runtime SLO Manager
   ↓
Model Routing Layer
   ├── llama-3.1-8b-instruct
   ├── qwen2.5-coder-14b-instruct
   └── nomic-embed
```

## 5. Servicios Observados

### Servicios Core

| Servicio | Estado | Funcion |
|----------|--------|---------|
| ailab-gateway | ✅ | API OpenAI-compatible (:8008) |
| ailab-router | ✅ | Routing cognitivo (:8083) |
| ailab-live-api | ✅ | Estado runtime live (:8084) |
| ailab-live-state | ✅ | Snapshot runtime |
| ailab-heartbeat | ✅ | Health signaling |
| ailab-docs | ✅ | Astro documentation (:4322) |
| ailab-metrics | ✅ | Export Prometheus (:3010) |

### Servicios Support

| Servicio | Estado |
|----------|--------|
| stream_sanitizer | ✅ |
| capability_router | ✅ |
| prompt classifier | ✅ |
| runtime context builder | ✅ |

### Servicios Observability

| Servicio | Estado |
|----------|--------|
| Prometheus (192.168.1.40:9090) | ✅ |
| Grafana (192.168.1.40:3000) | ✅ |
| Metrics exporter | ✅ |
| Runtime telemetry | ✅ |

## 6. Routing Cognitivo

| Route Family | Estado | Modelo Primario |
|--------------|--------|-----------------|
| minimal | ✅ | llama-3.1-8b |
| observe | ✅ | llama-3.1-8b |
| cognitive | ✅ | qwen2.5-coder |
| report | ✅ | qwen2.5-coder |
| embeddings | ✅ | nomic-embed |

**Routing Tightening (FASE 29.3.1):** Implementado correctamente:

- greetings → llama fastpath
- lightweight prompts → llama
- qwen escalation control
- qwen3.6 excluido de discovery
- observe override activo

**Impacto validado:**

| Metrica | Resultado |
|---------|-----------|
| TTFB reduction | -29% |
| p50 TTFB | 804ms |
| Success rate | 100% |
| Gateway crashes | 0 |
| qwen3.6 runtime usage | 0 |

## 7. Runtime SLO Enforcement

**Runtime SLO Manager:** Estados GREEN / YELLOW / RED.

| SLO | Estado |
|-----|--------|
| TTFB p50 | ✅ |
| TTFB p95 | ✅ |
| Timeout rate | ✅ |
| GPU pressure | ✅ |
| VRAM pressure | ✅ |
| Orphan streams | ✅ |
| Gateway crashes | ✅ |

**Degradation Levels:** NORMAL ✅, LIGHT ✅, HEAVY (Observado), EMERGENCY (Observado).

**Protecciones activas:** forced llama routing, qwen protection, adaptive concurrency, stream backlog monitoring, runtime pressure awareness, circuit breaker observability.

## 8. Modelos IA Disponibles

### Active Runtime Models

| Modelo | Estado | Rol |
|--------|--------|-----|
| llama-3.1-8b-instruct | ✅ ACTIVE | Fastpath / lightweight |
| qwen/qwen2.5-coder-14b-instruct | ✅ ACTIVE | Cognitive / report |
| text-embedding-nomic-embed-text-v1.5 | ✅ ACTIVE | Embeddings / RAG |

### Disabled / Inventory Models

| Modelo | Estado | Clasificacion |
|--------|--------|---------------|
| qwen/qwen3.6-27b | ⚠ DISABLED | Inventory only |
| lmstudio-community/qwen2.5-coder-14b-instruct | ❌ DEPRECATED | NON_ROUTABLE (alias → qwen/qwen2.5-coder-14b-instruct) |

:::caution
qwen3.6 NO participa en routing activo. Solo existe como modelo descubierto/inventario.
:::

## 9. Infraestructura GPU

### Nodo Activo

| Campo | Valor |
|-------|-------|
| GPU | AMD Radeon RX9070 |
| VRAM | 16 GB |
| Estado | ONLINE |
| Runtime role | Primary inference node |
| Latencia observada | ~2.9ms |
| Scheduler mode | Single-node burn-in |

### Nodo Inventario

| Campo | Valor |
|-------|-------|
| GPU | RX7900XT |
| VRAM | 20 GB |
| Estado | INVENTORY / OFFLINE |
| Clasificacion | No critico |
| Uso runtime | Ninguno |

:::note
RX7900XT NO esta marcado como fallo critico. Solo forma parte del inventario de nodos.
:::

## 10. Observabilidad

**Dashboards Grafana activos:**

- **AI Governance:** parser failures, hallucination guard, rate limiting, governance blocked
- **Cognitive Profiles:** requests by profile, model by profile, route family
- **Runtime Protection:** SLO state, degradation level, GPU pressure, VRAM pressure, timeout storms, circuit breakers
- **Production Burn-In:** route distribution, latency p95, prompt inflation, memory recall, error families

## 11. Planner Runtime (FASE 28.1)

**PLANNER RUNTIME SKELETON:** OPERATIVO

| Componente | Estado |
|------------|--------|
| Intent parser | ✅ |
| DAG planner | ✅ |
| Dry-run engine | ✅ |
| Risk engine | ✅ |
| Explainability | ✅ |
| Approval gate | ✅ |
| Workflow state machine | ✅ |
| Governance hooks | ✅ |

**Componentes pendientes:** Executor readonly ❌, Sandbox write ❌, Rollback engine real ❌, Real execution runtime ❌.

## 12. Runtime Health

| Metrica | Resultado |
|---------|-----------|
| Requests procesadas | 306 |
| Failures | 0 |
| Gateway crashes | 0 |
| Orphan streams | 0 |
| qwen3.6 activations | 0 |
| Success rate | 100% |

**GPU Runtime:** GPU utilization control funcional, adaptive concurrency funcional, qwen throttling operativo, llama fastpath estable.

## 13. Seguridad Operacional

| Proteccion | Estado |
|------------|--------|
| Tool budget limiting | ✅ |
| Tool policy disabled | ✅ |
| Stream sanitizer | ✅ |
| Prompt classification | ✅ |
| Governance engine | ✅ |
| Runtime enforcement | ✅ |
| Circuit breaker observability | ✅ |

## 14. Estado de Madurez

| Area | Nivel |
|------|-------|
| Runtime inference | Alto |
| Observabilidad | Alto |
| Routing cognitivo | Alto |
| SLO enforcement | Alto |
| Governance | Medio-Alto |
| Agentic execution | Skeleton |
| Autonomous execution | No implementado |

## 15. Riesgos Actuales

**Moderados:**
- single-node runtime
- dependencia GPU RX9070
- planner aun sin executor real
- qwen runtime sensible a presion VRAM

**Bajos:**
- gateway instability
- orphan streams
- routing drift
- qwen leakage

## 16. Recomendaciones Estrategicas

**Prioridad Alta — FASE 28.2:** Implementar executor readonly, governance contracts, runtime execution gates.

**Prioridad Media — FASE 28.3+:** Implementar sandbox write runtime, rollback snapshots reales, execution verification, planner DAG dependencies reales.

**Prioridad Baja — Futuro:** multi-node scheduler, distributed inference, VRAM-aware cross-node routing, autonomous remediation.

## 17. Conclusion Final

AI-LAB en 192.168.1.30 ya no es simplemente un servidor LM Studio local.

Actualmente funciona como un **Runtime cognitivo observabilidad-first** con routing adaptativo, proteccion SLO, governance runtime, telemetria avanzada, planner agentic skeleton y runtime grounding contextual.

El sistema se encuentra en **ESTADO OPERACIONAL ESTABLE** y las fases 29.3.x, 29.4.x y 28.1 han estabilizado correctamente inferencia, routing, proteccion runtime, reporting, observabilidad y groundwork agentic sin introducir regresiones operacionales.
