---
title: "Arquitectura del Ecosistema AI-LAB"
summary: "Arquitectura actual del ecosistema AI-LAB: runtime evidence-bound, Hermes Enterprise Governance, AnythingLLM Knowledge Base, GitNexus Structural Cognition, Marketplace Digital Twin y observabilidad."
order: 3
---

## Visión General

AI-LAB no es un servidor de inferencia tradicional. Opera como un **ecosistema de plataforma** con capas independientes pero integradas: runtime cognitivo, gobernanza declarativa, memoria documental, cognición estructural y observabilidad.

---

## Componentes Implementados

| Componente | Estado | Capa |
|------------|--------|------|
| **Runtime Core** (gateway + router + live-api) | ✅ Implementado | Público |
| **Hermes Enterprise Governance** | ✅ Implementado | Público |
| **AnythingLLM Knowledge Base** | ✅ Implementado | Público |
| **GitNexus Structural Cognition** | ✅ Implementado | Público |
| **Marketplace Digital Twin** | ✅ Implementado | Público (operacional) |
| **Observabilidad** (Prometheus/Grafana) | ✅ Implementado | Público (métricas) |

---

## Capas del Runtime

### 1. Inference Layer

Backend de inferencia basado en LM Studio. Sirve modelos en VRAM y expone API compatible con OpenAI.

- Determinista: el LLM **nunca** decide su propio routing
- Separación estricta entre modelos activos, cargados, descubiertos y desactivados
- Dos modelos productivos: uno operacional (respuestas ligeras) y uno de coding/report/architecture

### 2. Gateway Layer

Entrypoint único OpenAI-compatible (`ailab-gateway`). Responsable de:

- Inyección de contexto cognitivo
- Clasificación de ruta determinista (greeting markers + QWEN_ESCALATION_REASONS)
- Aplicación de perfiles cognitivos (modelo, tokens, temperatura, tools, memoria)
- Evaluación SLO y protección adaptativa del runtime
- Streaming real (relay directo desde LM Studio)
- Sanitización y guards de seguridad

### 3. Governance Layer (Hermes Enterprise)

Capa de governance declarativo:

- **SOUL**: identidad, propósito y verdad del runtime enterprise
- **Capability Registry**: qué puede hacer el runtime
- **Operator Registry**: cómo se ejecutan las capacidades
- **Hook Registry**: eventos del lifecycle (todos en modo declarativo)
- **MCP Registry**: servidores de herramientas externas
- **Dynamic Governance**: 4 modos de operación con resolución automática
- **Status Endpoint**: GET /hermes/status como fuente oficial de observabilidad

### 4. Knowledge Layer (AnythingLLM)

Memoria documental oficial del laboratorio.

- 7 workspaces activos, 1,304 vectores
- Embedder multilingüe (`multilingual-e5-small`)
- RAG E2E validado al 100%
- Baseline congelada y versionada

### 5. Structural Intelligence (GitNexus)

Cognición estructural del codebase mediante AST scanning.

- `ai-lab`: 20,327 símbolos, 32,455 relaciones, 300 execution flows
- `rioja-marketplace`: 1,421 nodos, 2,231 aristas
- Tools: impact analysis, context 360°, rename, detect_changes, route_map
- Política GITNEXUS-FIRST: consulta pre-cambio obligatoria

### 6. Marketplace Digital Twin

Mirror observacional del ecosistema Rioja Marketplace.

- MCP read-only vía GitNexus + Hermes Marketplace Operator
- Frontend: Next.js 15 (público en marketplace.labrazahome.com)
- Backend: Go + Fiber v2, PostgreSQL 17
- Propósito: comprensión arquitectónica, análisis de impacto, depuración

### 7. Observability Layer

Stack completo de métricas y alertas.

- **Prometheus**: source of truth (100+ métricas `ailab_*`, 19 alertas)
- **Grafana**: visualización (15 dashboards, TIER 1 y TIER 2)
- **Loki**: logs del runtime
- **SLO Enforcement**: 4 niveles de degradación, adaptive concurrency, circuit breakers

---

## Mapa Arquitectónico

```
                     ┌──────────────────────────────┐
                     │       Clientes Externos       │
                     │  (OpenCode, OpenWebUI, API)   │
                     └──────────────┬───────────────┘
                                    │
                     ┌──────────────▼───────────────┐
                     │      Gateway (ailab-gateway)  │
                     │   Routing → Profile → SLO    │
                     │   → Inference → Response     │
                     └──────┬───────────────┬───────┘
                            │               │
              ┌─────────────▼───┐   ┌───────▼──────────┐
              │  LM Studio     │   │  AnythingLLM     │
              │  (Inferencia)  │   │  (Knowledge Base) │
              └────────────────┘   └──────────────────┘
                            │               │
              ┌─────────────▼───────────────▼──────────┐
              │         Capas de Verdad (Truth)        │
              │  Prometheus  │  OperationalTruth       │
              │  GitNexus    │  (semántica)            │
              └────────────────────────────────────────┘
                            │
              ┌─────────────▼──────────────────────────┐
              │      Hermes Enterprise Governance      │
              │  SOUL → Capability → Operator → Hook   │
              │  → MCP → Dynamic Governance → Status   │
              └────────────────────────────────────────┘
```

---

## Estado por Capa

| Capa | Madurez | Observabilidad | Tests |
|------|---------|---------------|-------|
| Runtime Core | ✅ Production | ✅ 100+ métricas | ✅ Burn-in validado |
| Governance | ✅ Implementado (declarativo) | ✅ GET /hermes/status | ✅ 185 tests |
| Knowledge Base | ✅ Production (baseline frozen) | ✅ API RAG | ✅ 100% E2E |
| Structural Intel | ✅ Production | ✅ API GitNexus | ✅ Integrado en CI |
| Marketplace DT | ✅ Operativo con riesgos | ⚠️ Sin Prometheus | ⚠️ Parcial |
| Observabilidad | ✅ Production | ✅ 15 dashboards | ✅ 19 alertas activas |

---

## Próximos Pasos

| Prioridad | Fase | Descripción |
|-----------|------|-------------|
| 1 | **HERMES-E08** | Activar primer lifecycle hook real |
| 2 | **HERMES-E09** | Governance enforcement activo |
| 3 | **Marketplace** | Acceso a servicios, Stripe real, Inventory API |
| 4 | **Multi-GPU** | Reactivar nodo secundario + scheduler |
| 5 | **Gateway** | Refactor del monolito (~5700 líneas) |
