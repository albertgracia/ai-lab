---
title: "Roadmap"
summary: "Roadmap realista stabilization-first con Hermes Enterprise Core completado, AnythingLLM Enterprise baseline, y próxima gobernanza activa."
order: 8
---


## Known issues operativos

| Issue | Estado |
|-------|--------|
| `openai_gateway.py` monolito | ~5700 líneas, risk HIGH, pendiente de auditoría y refactor |
| LM Studio sin modelo cargado | `POST /chat/completions` responde "No models loaded" — no siempre tiene el modelo activo tras reinicio |
| Router/LM Studio diagnosis | Pendiente de diagnosis cuando LM Studio esté estable |
| Stash antiguo pre-sync-mcp | Pendiente de revisión y limpieza |
| URL Grafana confundida con AnythingLLM | Grafana v12.0.2 en puerto 3001 del host de control. AnythingLLM está en host de inferencia |

---

## IMPLEMENTADO

### Runtime stabilization — Blocks 37-40

| Fase | Descripción | Estado |
|------|-------------|--------|
| Block 37 | Cognitive Health & Graph Analysis (37A-37E) | ✅ |
| Block 38 | Runtime Stability (38A-38D: deep audit, graceful shutdown, error triage, runtime snapshot) | ✅ |
| Block 39 | Release Hardening (39A-39E: gateway contracts, observability alerts, cognitive followup, stabilization close) | ✅ |
| Block 40 | Post-Release SLO Drift Watch (40A) | ✅ |

### Hermes Enterprise Core — 6 componentes

| Componente | Tests | Estado |
|------------|-------|--------|
| **SOUL** (Self-organizing Unified Logic) — sistema declarativo de identidad, propósito y verdad del runtime enterprise | 27 tests | ✅ |
| **Capability Registry** — registro declarativo de capacidades con validación de dependencias, versiones y slots | 24 tests | ✅ |
| **Operator Registry** — 12 validaciones profundas (IDs únicos, capabilities, MCP, protocols, execution_mode, domains, forbidden_actions, reports, success_criteria, truth_model) | 17 tests | ✅ |
| **Hook Registry** — 9 lifecycle hooks declarativos (`enabled: false, mode: declarative_only`) | Skeleton completo | ✅ |
| **MCP Registry** — 5 servidores MCP declarados (ai-lab-runtime, rioja-marketplace, prometheus, marketplace-mcp, filesystem) | Skeleton completo | ✅ |
| **Dynamic Governance** — ADR-006: 4 modos (NORMAL/ELEVATED/DEGRADED/LOCKDOWN), `GovernanceResolver` con 6 señales trigger, anti-flapping 30s, capability-governance matrix (6 caps × 4 modos) | 45 tests | ✅ |
| **`GET /hermes/status`** — endpoint en `:8095` con 14 bloques: service, version, build, git, enterprise, soul, capabilities, operators, hooks, mcp, governance, architecture, tests, status | 72 tests | ✅ |

**Total:** 185 tests PASS. Checkpoints: `CP-HERMES-ENTERPRISE-CORE-01`, `CP-E07-ENTERPRISE-RUNTIME-STATUS-ENDPOINT-STABLE`.

### AnythingLLM Enterprise — Knowledge Base

| Componente | Detalle | Estado |
|------------|---------|--------|
| Import canónico | 84 documentos importados desde el filesystem | ✅ |
| Validación multilingual | Soportados ES/EN/FR/DE/IT/PT, 0 errores de codificación | ✅ |
| Migración embedder | `text-embedding-multilingual-e5-small` (Q8_0, 384-dim) — reemplaza a `nomic-embed-text-v1.5` | ✅ |
| Chunking tuning | Chunk size 800, overlap 100 | ✅ |
| Evidence reports | 53 documentos en workspace evidence-reports | ✅ |
| Marketplace docs | 7 documentos sobre Rioja Marketplace | ✅ |
| Observabilidad + IDS | 2 documentos sobre stack de observabilidad | ✅ |
| Runbooks + Stack 2026 | 8 documentos operativos | ✅ |
| MCP + A2A | 19 documentos sobre protocolos MCP y A2A | ✅ |

**Totales:** 1304 vectores, 7 workspaces activos. RAG E2E validation: 100%. Baseline congelada en `CP-ANYTHINGLLM-ENTERPRISE-04-COMPLETE`.

**Workspaces configurados:**
- `ai-lab-core-runtime`
- `ai-lab-architecture-governance`
- `ai-lab-operations-runbooks`
- `ai-lab-marketplace-docs`
- `ai-lab-enterprise-hermes`
- `ai-lab-evidence-reports`
- `ai-lab-stack-2026`

### Marketplace Digital Twin — Rioja Marketplace

| Componente | Detalle | Estado |
|------------|---------|--------|
| Indexación GitNexus | 1421 nodes, 2231 edges — estructura completa de rutas, handlers y modelos | ✅ |
| MCP read-only | Validado y operativo desde Hermes | ✅ |
| Hermes Marketplace Operator | Operator registrado y validado en el registry | ✅ |
| Backend | Go + Fiber v2 en red privada, PostgreSQL 17 | ✅ |
| Frontend | Next.js 15 + React 19 RC | ✅ |
| URL pública | `marketplace.labrazahome.com` | ✅ |

### Astro Docs — Public/Private Separation

| Componente | Detalle | Estado |
|------------|---------|--------|
| Clasificación de sensibilidad | Auditadas 212 páginas: 35% PUBLIC_SAFE, 64% PRIVATE_ONLY | ✅ |
| Build filter | `private-content-filter.json` (33 entries) elimina paths PRIVATE_ONLY antes del build público | ✅ |
| Sidebar condicional | `AILAB_PUBLIC_BUILD` env var oculta secciones Private/Runbooks/Incidents en build público | ✅ |
| Redirects edge | `_redirects` bloquea rutas privadas en Cloudflare Pages | ✅ |
| Pipeline CI/CD | `publish-astro-public.ps1` y `publish-astro-private.ps1` en `scripts/phase-closure/` | ✅ |
| Público (Cloudflare) | `ai-lab.labrazahome.com` — 171 páginas, 0 IPs internas | ✅ |
| Privado (Traefik) | `blog-ai-lab.labrazahome.com` — 277 páginas con contenido completo | ✅ |

**Checkpoints:** `CP-AI-LAB-ASTRO-DOCS-REFRESH-01`, `CP-ASTRO-PUBLIC-PRIVATE-SEPARATION-01`.

### GitNexus — Code Intelligence

| Capacidad | Detalle | Estado |
|-----------|---------|--------|
| Repos indexados | `ai-lab` (20327 symbols) + `rioja-marketplace` (1421 nodes) | ✅ |
| Impact analysis | `impact()` con blast radius por depth (d1/d2/d3), risk assessment | ✅ |
| Context tool | `context()` con 360° de referencias, procesos participantes | ✅ |
| Rename tool | `rename()` multi-file con confianza graph/text_search | ✅ |
| detect_changes | Pre-commit analysis con procesos afectados | ✅ |
| Cypher queries | Consultas directas al knowledge graph | ✅ |
| GITNEXUS-FIRST policy | Consulta pre-cambio obligatoria para runtime, gateway, router, scheduler, marketplace, IDS, Hermes | ✅ |

### Observability Stack

| Componente | Rol |
|------------|-----|
| Prometheus | Source of truth (métricas, alertas) |
| Grafana | Visualización (15 dashboards) |
| Loki | Logs del runtime |
| node_exporter | Métricas de host |
| cadvisor | Métricas de contenedores |

**Métricas:** 100+ métricas `ailab_*` (perfiles, latencia, tools, memoria, calidad, streaming, GPU, SLO, report grounding, lifecycle). 19 reglas de alerta activas con health=ok. 15 dashboards Grafana en carpeta AI-LAB (TIER 1: operación diaria, TIER 2: troubleshooting).

### Modelos activos

| Modelo | Rol | Estado |
|--------|-----|--------|
| `llama-3.1-8b-instruct` | PRIMARY_OPERATIONAL_MODEL (minimal, greetings, observe, light prompts) | ✅ |
| `qwen2.5-coder-14b-instruct` | PRIMARY_CODING_MODEL (coding, report, architecture, reasoning, creative) | ✅ |
| `nomic-embed-text-v1.5` | Embedding (temporal — migrado a e5-small en AnythingLLM) | ✅ |
| `qwen3.6-27b` | DESACTIVADO (disponible para tests manuales) | ✅ Desactivado |
| `qwen2.5-coder-32b` | DOWN (nodo RX7900XT apagado) | ❌ Nodo offline |

---

## PENDIENTE

### Hermes Enterprise — Próximas fases

| Fase | Descripción | Estado |
|------|-------------|--------|
| **HERMES-E08** | Activar primer lifecycle hook real (hook execution runtime) | 📋 Planificado |
| **HERMES-E09** | Governance enforcement activo — conectar `GovernanceResolver` al runtime para bloqueo real de capacidades | 📋 Planificado |
| **ANYTHINGLLM-ENTERPRISE-05** | Nueva fase de Knowledge Base cuando exista necesidad funcional real | 📋 Bloqueado |

### Marketplace — Próximos pasos

| Tarea | Descripción | Estado |
|-------|-------------|--------|
| Acceso a `.150` | Validar secretos, servicios y conectividad con Marketplace backend | 📋 Pendiente |
| Stripe real | Integración de pagos reales (actualmente en sandbox) | 📋 Planificado |
| Inventory API | Endpoints de gestión de inventario | 📋 Planificado |
| Documentación Marketplace | Páginas Astro dedicadas al ecosistema Marketplace | 📋 Planificado |

### Multi-GPU Scheduling

| Requisito | Estado |
|-----------|--------|
| Reactivación de nodo RX7900XT | ❌ Nodo apagado |
| Scheduler contracts definidos | 📋 Pendiente |
| Prerrequisitos cerrados (30H→31B) | ✅ Cerrados desde CP-31B |
| Readiness assessment | 37/100 — `CP-MULTIGPU-READINESS-01` |

**Estado:** No documentado como funcionalidad operativa cerrada. Pendiente de reactivación del nodo RX7900XT y definición de scheduler contracts.

---

## Resumen de checkpoints

| Checkpoint | Componente | Estado |
|------------|------------|--------|
| `CP-30I-G-RUNTIME-GROUNDING-STABLE` | Deterministic Runtime Grounding | ✅ |
| `CP-OBS-31A.5-EXECUTOR-STABLE` | Observability Quick Wins | ✅ |
| `CP-31B-RUNTIME-SEMANTIC-MATURITY-STABLE` | Runtime Semantic Maturity | ✅ |
| `CP-35C-LIVE-AUTHORITY-BACKED-COGNITION-STABLE` | Live Authority Cognition | ✅ |
| `CP-35D-OPERATIONAL-FAST-PATH-STABLE` | Operational Fast Path | ✅ |
| `CP-36A-OPERATIONAL-INCIDENT-INTELLIGENCE-STABLE` | Incident Intelligence | ✅ |
| `CP-36B-RUNTIME-PRECISION-MODE-STABLE` | Runtime Precision Mode | ✅ |
| `CP-36C-OPERATOR-INTENT-REASONING-STABLE` | Operator Intent Reasoning | ✅ |
| `CP-36D-AUTONOMOUS-OBSERVABILITY-TRIAGE-STABLE` | Autonomous Observability Triage | ✅ |
| `CP-HERMES-ENTERPRISE-CORE-01` | Hermes Enterprise Core (6 componentes) | ✅ |
| `CP-ANYTHINGLLM-ENTERPRISE-04-COMPLETE` | AnythingLLM Knowledge Base (1304 vectores) | ✅ |
| `CP-AI-LAB-ASTRO-DOCS-REFRESH-01` | Astro Docs Refresh (277 págs, 0 errores) | ✅ |
| `CP-ASTRO-PUBLIC-PRIVATE-SEPARATION-01` | Public/Private Docs Separation (build filter) | ✅ |
| `CP-MULTIGPU-READINESS-01` | Multi-GPU Readiness Assessment (37/100) | 📋 |

---

## Próximas prioridades

1. **Hermes E08/E09** — Activar lifecycle hooks reales y governance enforcement conectado al runtime
2. **Marketplace hardening** — Acceso a `.150`, Stripe real, Inventory API, documentación
3. **Astro Docs Refresh continuo** — Alinear documentación con estado real del runtime
4. **Refactor gateway** — Reducir monolito `openai_gateway.py` (~5700 líneas)
5. **Multi-GPU** — Reactivar RX7900XT y completar readiness assessment
6. **LM Studio diagnosis** — Estabilizar carga de modelos post-reinicio
7. **AnythingLLM-05** — Nueva fase Knowledge Base cuando haya necesidad funcional

## Roadmap futuro oficial

- `HERMES-E08` — Hook execution runtime (lifecycle hooks reales)
- `HERMES-E09` — Governance enforcement activo
- `ASTRO-DOCS-REFRESH-01B` — Refresh continuo de documentación con separación público/privado
- `MARKETPLACE-DOCS-01` — Documentación Astro del ecosistema Marketplace
- `GATEWAY-REFACTOR-01` — Descomposición del monolito openai_gateway.py
- `MULTIGPU-SCHEDULER-01` — Scheduler Multi-GPU (post reactivación RX7900XT)
- `ANYTHINGLLM-ENTERPRISE-05` — Nueva fase Knowledge Base
- `PILOT-TECNICO-01` — Pilot técnico del runtime gobernado
- `PILOT-OPERADOR-01` — Pilot con operadores reales
