---
title: "AI-LAB Docs"
summary: "Índice principal de la documentación técnica de AI-LAB: runtime, arquitectura, observabilidad, governance, experimentos, esquemas y roadmap operativo."
order: 1
---

## Qué contiene

- **Runtime**: estado actual, madurez, sensor fusion, semántica, authority/precision y contratos operacionales. Incluye Hermes Enterprise como capa de governance (SOUL, Capabilities, Operators, Hooks, MCP, Dynamic Governance, Status Endpoint).
- **Architecture**: dominios reales (bounded contexts), truth layers, evidence-bound runtime, baseline pre-Multi-GPU.
- **Observability**: Prometheus, GPU metrics, dominios de sensores, dashboards (15), métricas (100+), alertas (19).
- **Governance**: trust boundaries, operational truth, confidence semantics, worktree governance, phase closure protocol, AnythingLLM reindex automation.
- **Experiments**: burn-ins y validaciones de grounding para qwen y summaries GPU.
- **AnythingLLM**: Knowledge Base Enterprise con 7 workspaces activos y 1304 vectores.
- **Hermes Enterprise**: SOUL, Capability Registry, Operator Registry, Hook Registry, MCP Registry, Dynamic Governance, GET /hermes/status en :8095. 185 tests PASS.
- **Marketplace Digital Twin**: Rioja Marketplace indexado en GitNexus, MCP read-only, Hermes Marketplace Operator.
- **GitNexus**: Code intelligence, impact analysis, structural cognition.
- **Schemas**: contratos normalizados de OBSERVED_RUNTIME, sensor_snapshot, gpu_operational_summary y archive manifests.
- **Phase Closure Protocol**: protocolo obligatorio de cierre de fase con evaluación documental, build, reindexación AnythingLLM y validación de recuperación.
- **Roadmap**: stabilization-first, governance-first, Hermes Enterprise Core completado, AnythingLLM Enterprise baseline congelada, preparación pre-Multi-GPU.

## Fases cubiertas

- `30H` a `30I-G` — Evidence enforcement, sensor fusion, grounding
- `OBS-31A` a `31B` — Observabilidad authority audit, madurez semántica
- `35C` — Authority-backed cognition
- `35D` — Operational fast-path
- `36A` — Operational incident intelligence
- `36B` — Precision semantics
- `36C` — Operator intent reasoning (metadata, no ejecución)
- `36D` — Autonomous observability triage
- `37A` — Cognitive health layer
- `37B` — Graph-runtime correlation
- `37C` — Critical path analysis
- `37D` — Graph hotspot history
- `37E` — Governance drift detection
- `38A` — Runtime deep audit
- `38B` — Gateway shutdown graceful
- `38C` — GitNexus NAPI error triage
- `38D` — Runtime stability snapshot
- `39A` — OpenCode gateway contract hardening
- `39B` — Runtime observability alerts
- `39C` — Cognitive health followup
- `39E` — Runtime stabilization release close
- `40A` — Post-release SLO drift watch
- `HERMES-E01A` a `E07` — Hermes Enterprise Core completo
- `ANYTHINGLLM-ENTERPRISE-01` a `04` — Knowledge Base Enterprise baseline
- `MARKETPLACE-GITNEXUS-ENABLE-01/02` — Marketplace Digital Twin

## Secciones añadidas

- **Hermes Enterprise**: SOUL, Capability Registry, Operator Registry, Hook Registry, MCP Registry, Dynamic Governance, Status Endpoint :8095.
- **AnythingLLM Enterprise**: 7 workspaces, 1304 vectores, multilingual-e5-small, RAG E2E 100%.
- **Marketplace Digital Twin**: Rioja Marketplace indexado en GitNexus, MCP read-only, Hermes Marketplace Operator.
- **Codebase Structural Cognition**: integración GitNexus, dependency graph, blast radius, ownership, structural risk scoring.
- **Runtime Truth Layers**: Prometheus, OperationalTruth y GitNexus.
- **SLO Enforcement**: 14 métricas runtime, 4 niveles de degradación, adaptive concurrency.

## Checkpoints principales

Desde el baseline 30I-D se alcanzaron:
- `CP-35D-OPERATIONAL-FAST-PATH-STABLE`
- `CP-36A-OPERATIONAL-INCIDENT-INTELLIGENCE-STABLE`
- `CP-36B-RUNTIME-PRECISION-MODE-STABLE`
- `CP-36C-OPERATOR-INTENT-REASONING-STABLE`
- `CP-FEDERATION-COMPLETE`, `CP-CANONICAL-MODEL-REGISTRY`, `CP-COGNITIVE-SLO`
- `CP-37A` a `CP-37E` (cognitive health, correlation, critical path, hotspot, governance drift)
- `CP-38A` a `CP-38D` (deep audit, graceful shutdown, error triage, stability snapshot)
- `CP-39A` a `CP-39E` (contract hardening, alerts, followup, release close)
- `CP-40A` (post-release SLO drift watch)
- `CP-HERMES-ENTERPRISE-CORE-01`, `CP-E07-ENTERPRISE-RUNTIME-STATUS-ENDPOINT-STABLE`
- `CP-HERMES-DOCS-ASTRO-ENTERPRISE-01`
- `CP-ANYTHINGLLM-ENTERPRISE-04-COMPLETE`
- `CP-AI-LAB-ASTRO-DOCS-REFRESH-01` — actualización masiva de documentación (277 págs, 0 errores)
- `CP-ASTRO-PUBLIC-PRIVATE-SEPARATION-01` — separación público/privado con build filter
- `CP-SLO-ENFORCEMENT-01`, `CP-VALIDATION-AUTHORITY-01`, `CP-AUTONOMOUS-OBSERVABILITY-TRIAGE-01`, `CP-OPERATOR-INTENT-REASONING-01`, `CP-MULTIGPU-READINESS-01`

## Estado estable

AI-LAB ya no opera como "LLM + prompts". Opera como runtime **evidence-bound** con:
- autoridad (Prometheus) separada de cognición,
- verdad operacional semántica (OperationalTruth),
- cognición estructural (GitNexus) como señal complementaria,
- governance explícita y verificable (Hermes Enterprise Dynamic Governance),
- routing determinista con fastpath operacional,
- Knowledge Base Enterprise (AnythingLLM, 1304 vectores, RAG 100%),
- y baseline congelada pre-Multi-GPU.

## Próximos pasos

- HERMES-E08: activar primer lifecycle hook real
- HERMES-E09: governance enforcement activo
- AI-LAB-ASTRO-DOCS-REFRESH-01B: refresh continuo de documentación con separación público/privado
- ANYTHINGLLM-ENTERPRISE-05: cuando exista necesidad funcional real
- Validar acceso a .150 para secretos/servicios de Marketplace
- Multi-GPU cuando RX7900XT se reactive
