---
title: "AI-LAB Runtime Current State Audit 01"
summary: "Auditoría read-only del estado actual del runtime AI-LAB antes de retomar fases de evolución. Reconciliación con documentación Astro/AnythingLLM."
date: "2026-06-11"
tags:
  - audit
  - runtime
  - read-only
  - drift
---

# AI-LAB Runtime Current State Audit 01

**Fecha:** 2026-06-11
**Modo:** READ-ONLY
**Origen:** SMB workspace (E:\opencode\ai-lab)
**Runtime reachable:** Sí vía MCP (gateway proxy)

---

## 1. Git Status

**Working tree:** dirty (cambios de fases doc previas)
**HEAD:** `ecb9bd6` (main, origin/main)
**Último tag:** sin tag en HEAD
**Cambios pendientes:** 4 modificados + 6 untracked (todo documentación)

---

## 2. Servicios Verificados

### Gateway (ai-lab-openai-gateway)
- **Puerto:** 8008
- **Estado:** OK (200 desde MCP)
- **Service ID:** `ai-lab-openai-gateway`
- **Contract version:** `37A-COGNITIVE-HEALTH-LAYER-01`
- **Chat traffic:** 0 requests recientes (latency counters en 0)
- **Watchdog:** enabled, 2402 triggers acumulados (último trigger: ~1781178592)

### Router (ai-lab-router)
- **Puerto:** 8083
- **Estado:** OK (200 desde MCP)
- **Rol real:** API interna (no entrypoint de chat en producción — confirmado)

### Docs (Astro)
- **Build:** PASS (261 páginas, 22.34s)
- **Config:** starlight, tailwind, mermaid, react

### Metrics Dashboard
- **NO VERIFICADO** — requiere acceso directo a métricas live (192.168.1.30:3010)
- **NO DISPONIBLE** desde SMB

### MCP Semantic Gateway / LAN Gateway
- **NO VERIFICADO** — no hay MCP tools específicas para estos endpoints
- **NO DISPONIBLE** desde alcance actual

---

## 3. Endpoints Consultados

| Endpoint | Estado | Observación |
|---|---|---|
| `GET /health` (:8008) | OK 200 | Gateway responde como `ai-lab-openai-gateway` |
| `GET /health` (:8083) | OK 200 | Router responde |
| `GET /runtime/health` | OK | Score 79.6 (warning) |
| `GET /runtime/health/latency` | OK | 0 requests — sin tráfico reciente |
| `GET /runtime/slo/status` | OK | overall_status: healthy (con 80 violations históricas) |
| `GET /runtime/slo/violations` | OK | 80 violations `availability_lmstudio` (históricas) |
| `GET /runtime/incidents/report` | OK | 4 incidentes activos |
| `GET /runtime/operator-summary` | OK | overall_state: unknown |
| `GET /runtime/maturity` | NO DISPONIBLE | Endpoint no expuesto vía MCP |
| `GET /runtime/governance` | NO DISPONIBLE | Endpoint no expuesto vía MCP |
| `GET /runtime/topology` | NO DISPONIBLE | Endpoint no expuesto vía MCP |
| `GET /runtime/grounding` | NO DISPONIBLE | Endpoint no expuesto vía MCP |
| `GET /v1/models` (LM Studio) | NO DISPONIBLE | Sin acceso directo a LM Studio |

---

## 4. Observabilidad

### Prometheus
- **NO VERIFICADO** — 192.168.1.40:9090 no accesible desde SMB
- **NO DISPONIBLE** desde alcance actual

### Alertas AI-LAB (19 reglas documentadas)
- **NO VERIFICADO** — no hay endpoint Prometheus disponible

### Métricas runtime principales
- `ailab_requests_total`: 0 (sin tráfico reciente)
- `ailab_greeting_fastpath_total`: NO DISPONIBLE
- `ailab_qwen_escalation_total`: NO DISPONIBLE
- `ailab_llama_fastpath_total`: NO DISPONIBLE

---

## 5. Nodos de Inferencia

### 192.168.1.50 — RX9070
- **Online:** ✅
- **Score:** 0.9
- **Modelos:** 11
- **Latencia media:** 2.87ms
- **Estado GPU:** active
- **Coincide con documentación:** ✅

### 192.168.1.60 — RX7900XT
- **Online:** ❌
- **Score:** 0.1
- **Modelos:** 0
- **Estado GPU:** inactive
- **Coincide con documentación:** ✅ (expected_offline)

### 192.168.1.250 — NAS-N5
- **Online:** ❌
- **Score:** 0.1
- **Modelos:** 0
- **Documentado en AI-LAB-INFRASTRUCTURE.md:** ✅ (como NAS-N5, storage + LM Studio secundario)
- **Documentado en AGENTS.md:** ❌ **NO** — no aparece en ninguna sección de runtime

### 192.168.1.30 — Primary Control Plane
- **NO VERIFICADO** — no aparece en nodos del runtime health
- **AGENTS.md dice:** control-plane en .30
- **AI-LAB-INFRASTRUCTURE.md dice:** gateway/router en .50
- **DRIFT:** conflicto entre AGENTS.md y AI-LAB-INFRASTRUCTURE.md sobre dónde está el gateway

---

## 6. Comparativa Documentación vs Estado Real

### Drifts Identificados

| Documento | Afirma | Realidad | Drift |
|---|---|---|---|
| AGENTS.md | Control-plane en 192.168.1.30 | Runtime health responde desde .50, gateway se reporta como single node | **POSIBLE DRIFT** — .30 no verificado, .50 responde como gateway |
| AGENTS.md | 3 nodos: .30, .50, .60 | Runtime reporta 3 nodos: .50, .60, .250 | **DRIFT CONFIRMADO** — .250 no documentado en AGENTS.md |
| AGENTS.md | `qwen3.6-27b` = DESACTIVADO | .50 reporta 11 modelos activos | **NO VERIFICABLE** desde aquí |
| AI-LAB-INFRASTRUCTURE.md | .250 = NAS-N5, LM Studio secundario | Offline, score 0.1 | OK (documentado como infra, no estado) |
| AI-LAB-INFRASTRUCTURE.md | .50 tiene Gateway + Router | Runtime responde como gateway | ✅ **CONFIRMADO** |
| Astro docs | Routing determinista con 3 modelos | Sin tráfico reciente para verificar | No contradictorio |
| Astro docs (anythingllm-role) | AnythingLLM como memoria documental | No indexado en Astro aún (fase previa) | **DRIFT LEVE** — contenido creado pero no reindexado |

### Observaciones adicionales

- **Health score 79.6 (warning):** causado por .250 offline, .60 offline, y authority freshness gaps
- **SLO violations:** 80 violaciones históricas de `availability_lmstudio` — LM Studio ha sido inalcanzable repetidamente
- **Watchdog:** 2402 triggers — alta tasa de reactivaciones
- **Validation score:** 56.3/100 — 9 blocking failures
- **Codebase health:** 20/100 (critical)
- **Contract version:** 37A-COGNITIVE-HEALTH-LAYER-01 — por encima del último checkpoint documentado (CP-36B)

---

## 7. Incidentes Activos

| ID | Dominio | Severidad | Descripción |
|---|---|---|---|
| INC-AUTHORITY-MERGED-... | authority | HIGH | Authority freshness unavailable + prometheus_targets gaps |
| INC-VALIDATION-MERGED-... | validation | HIGH | 9 blocking failures, score 56.3/100, 3 safety gates down |
| INC-INFRASTRUCTURE-... | infrastructure | MEDIUM | 1 orphan discoverable node |
| INC-CODEBASE-MERGED-... | codebase | **CRITICAL** | Structural health 20/100, 93 high risks |

**Total dominios afectados (blast radius):** 9 (authority, validation, governance, reporting, observability, topology, gpu, routing, fastpath)

---

## 8. HARD_FACTS

1. Gateway responde OK en :8008, contrato 37A (post-36B)
2. Router responde OK en :8083
3. Solo 1/3 nodos de inferencia online (192.168.1.50)
4. Nodo 192.168.1.250 (NAS-N5) existe en infraestructura pero **NO** en AGENTS.md
5. Health score en 79.6 (warning) por nodos offline + authority gaps
6. 4 incidentes activos, el más grave: codebase structural health 20/100 (crítico)
7. 80 violaciones SLO históricas por LM Studio no accesible
8. 2402 watchdog triggers acumulados
9. Sin tráfico de chat reciente (latency counters = 0)
10. Contract version 37A sugiere avance no documentado en AGENTS.md (que dice CP-36B)

---

## 9. UNKNOWNS

| Item | Estado |
|---|---|
| Estado real de 192.168.1.30 (control-plane) | NO DISPONIBLE |
| Prometheus reachability | NO DISPONIBLE |
| Reglas de alerta cargadas | NO DISPONIBLE |
| MCP Semantic Gateway | NO DISPONIBLE |
| MCP LAN Gateway | NO DISPONIBLE |
| LM Studio models list | NO DISPONIBLE |
| Metrics Dashboard (live SSR) | NO DISPONIBLE |
| Estado Qdrant | NO DISPONIBLE |
| Estado Postgres | NO DISPONIBLE |
| Modelo qwen3.6-27b activo o no | NO DISPONIBLE |
| GitNexus index freshness | NO DISPONIBLE |

---

## 10. Riesgos

| Riesgo | Severidad | Descripción |
|---|---|---|
| Authority freshness offline | ALTA | Prometheus no accesible o stale — toda autoridad cognitiva degradada |
| Validation score 56.3 | ALTA | 9 blocking failures impiden operación segura |
| Codebase health 20/100 | CRÍTICA | 93 riesgos estructurales altos en el código |
| Single node online | MEDIA | Si .50 cae, no hay failover |
| Drift AGENTS.md vs infra | MEDIA | .250 no documentado, .30 vs .50 conflicto |
| Watchdog 2402 triggers | MEDIA | Alta tasa de reactivaciones sugiere inestabilidad |
| Contract 37A no documentado | MEDIA | El runtime avanzó más allá de la documentación (CP-36B es el último tag) |

---

## 11. Próxima Fase Recomendada

**FASE RECOMENDADA: 37A-COGNITIVE-HEALTH-LAYER-DOC**

### Justificación
El runtime ya opera con contrato `37A-COGNITIVE-HEALTH-LAYER-01`, que está por encima del último checkpoint documentado (CP-36B). Es prioritario:

1. **Documentar** el estado actual del contrato 37A antes de seguir evolucionando
2. **Resolver** authority freshness (Prometheus reachability) y validation blocking failures
3. **Reconciliar** AGENTS.md con AI-LAB-INFRASTRUCTURE.md (nodo .250, ubicación real del gateway)
4. **Reindexar** AnythingLLM con la nueva documentación de arquitectura
5. **Reducir** incidentes activos antes de nuevas fases cognitivas

### No recomendado hasta resolver
- Multi-GPU
- Operator Intent Reasoning (36C)
- Autonomous Observability Triage (36D)

---

## 12. Resumen

| Categoría | Hallazgo |
|---|---|
| Servicios OK | Gateway, Router |
| Servicios degradados | Authority, Validation |
| Servicios caídos | .60, .250 |
| Incidentes críticos | Codebase health 20/100 |
| Drift documental | AGENTS.md vs AI-LAB-INFRASTRUCTURE.md (.250 ausente, .30 vs .50) |
| Contract drift | Runtime en 37A, docs en CP-36B |
| Riesgo principal | Authority freshness + validation blocking impiden operación segura |
| Prioridad | Documentar 37A → resolver authority → resolver validation → reindexar AnythingLLM |

**Estado operacional real: DEGRADED** (health 79.6, 4 incidentes activos, single node online, authority offline)
