---
title: "AI-LAB Docs — Estado Actual"
summary: "Documentación oficial de AI-LAB: plataforma de ingeniería con runtime evidence-bound, Hermes Enterprise Governance, AnythingLLM Knowledge Base, Marketplace Digital Twin y GitNexus Structural Cognition."
order: 1
---

AI-LAB es una plataforma de ingeniería de IA que opera como **runtime evidence-bound** con gobernanza declarativa, knowledge base enterprise, cognición estructural y separación público/privado de documentación.

Esta documentación es la **fuente de verdad pública** del laboratorio.

---

## Componentes del Ecosistema

### Hermes Enterprise Core ✅

Capa de governance declarativo del runtime. 6 componentes, 185 tests PASS:

| Componente | Estado | Detalle |
|------------|--------|---------|
| **SOUL** | ✅ | Identidad, truth model, protocolos y boundaries |
| **Capability Registry** | ✅ | 6 capabilities críticas con validación cruzada |
| **Operator Registry** | ✅ | 5 operadores con 12 validaciones profundas |
| **Hook Registry** | ⚠️ | 9 lifecycle hooks declarativos (`enabled: false`) |
| **MCP Registry** | ✅ | 5 servidores MCP declarativos |
| **Dynamic Governance** | ✅ | 4 modos (NORMAL/ELEVATED/DEGRADED/LOCKDOWN) |
| **Status Endpoint** | ✅ | `GET /hermes/status` en endpoint dedicado |

Documentación completa en [Hermes Enterprise](/hermes/).

### AnythingLLM Enterprise ✅

Knowledge Base multi-workspace con RAG validado al 100%:

- **1304 vectores** en 7 workspaces activos
- Embedder `multilingual-e5-small` (Q8_0, 384-dim)
- Chunk size 800, overlap 100
- **RAG E2E validation: 100% PASS**
- Baseline congelada en `CP-ANYTHINGLLM-ENTERPRISE-04-COMPLETE`

Documentación en [AnythingLLM Enterprise](/architecture/anythingllm-enterprise/).

### Marketplace Digital Twin ✅

Rioja Marketplace replicado como Digital Twin observacional:

- Repositorio indexado en GitNexus (1,421 nodos, 2,231 aristas)
- MCP read-only vía Hermes Marketplace Operator
- Frontend público en `marketplace.labrazahome.com`
- Backend Go + Fiber v2, PostgreSQL 17

### GitNexus — Code Intelligence ✅

Cognición estructural del codebase:

- `ai-lab` indexado (20,327 símbolos, 32,455 relaciones, 300 execution flows)
- `rioja-marketplace` indexado (1,421 nodos)
- Impact analysis, context tool, rename tool, detect_changes
- **GITNEXUS-FIRST policy**: consulta pre-cambio obligatoria

### Observabilidad ✅

Stack completo de observabilidad operacional:

- **Prometheus**: source of truth de métricas (100+ métricas `ailab_*`)
- **Grafana**: visualización (15 dashboards, 19 alertas)
- **Loki**: agregación de logs del runtime
- **SLO Enforcement**: 14 métricas runtime, 4 niveles de degradación, adaptive concurrency

### Public/Private Docs Separation ✅

La documentación Astro está separada en dos builds:

| Build | Alcance | URL |
|-------|---------|-----|
| **Público** | Documentación general, arquitectura, Hermes, AnythingLLM, roadmap | `ai-lab.labrazahome.com` |
| **Privado** | Runbooks, incidentes, históricos, detalle operativo interno | `blog-ai-lab.labrazahome.com` |

Mecanismo: `private-content-filter.json` (46 entradas) + `_redirects` en Cloudflare + sidebar condicional (`AILAB_PUBLIC_BUILD`).

---

## Estado del Runtime

AI-LAB opera con un **evidence-bound runtime** donde:

- La **autoridad** (Prometheus) está separada de la **cognición**
- La **verdad operacional** (OperationalTruth) interpreta semánticamente las métricas
- La **cognición estructural** (GitNexus) es señal complementaria, no autoridad
- El **routing** es 100% determinista — el LLM no decide qué modelo usar
- La **gobernanza** (Hermes Dynamic Governance) es explícita y verificable
- El **fastpath operacional** permite respuestas compactas para consultas ligeras

Modelos activos: `llama-3.1-8b-instruct` (operacional), `qwen2.5-coder-14b-instruct` (coding/report/architecture), `nomic-embed-text-v1.5` (embedding).

---

## Roadmap Siguiente

| Prioridad | Fase | Descripción |
|-----------|------|-------------|
| 1 | **HERMES-E08** | Activar primer lifecycle hook real |
| 2 | **HERMES-E09** | Governance enforcement activo (bloqueo real de capacidades) |
| 3 | **Marketplace** | Validación acceso servicios, Stripe real, Inventory API, documentación |
| 4 | **Multi-GPU** | Reactivar nodo RX7900XT + scheduler (post requisitos) |
| 5 | **Gateway refactor** | Descomposición del monolito `openai_gateway.py` (~5700 líneas) |

Roadmap detallado en [Roadmap](/roadmap/).

---

## Checkpoints Clave

| Checkpoint | Componente |
|------------|------------|
| `CP-HERMES-ENTERPRISE-CORE-01` | Hermes Enterprise Core (6 componentes, 185 tests) |
| `CP-E07-ENTERPRISE-RUNTIME-STATUS-ENDPOINT-STABLE` | GET /hermes/status |
| `CP-ANYTHINGLLM-ENTERPRISE-04-COMPLETE` | Knowledge Base Enterprise (1304 vectores) |
| `CP-AI-LAB-ASTRO-DOCS-REFRESH-01` | Actualización masiva documentación |
| `CP-ASTRO-PUBLIC-PRIVATE-SEPARATION-01` | Separación público/privado |
| `CP-31B-RUNTIME-SEMANTIC-MATURITY-STABLE` | Madurez semántica del runtime |
| `CP-36B-RUNTIME-PRECISION-MODE-STABLE` | Precisión operacional |
| `CP-SLO-ENFORCEMENT-01` | SLO enforcement framework |
| `CP-MULTIGPU-READINESS-01` | Multi-GPU readiness assessment (37/100) |
