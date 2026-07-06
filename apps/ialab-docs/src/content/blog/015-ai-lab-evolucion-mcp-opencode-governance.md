---
title: "AI-LAB evoluciona: MCP Semantic Gateway, OpenCode y gobierno operacional del runtime"
date: "2026-05-28"
summary: "AI-LAB pasa de runtime local a plataforma gobernada para agentes: MCP Semantic Gateway, integración OpenCode Windows vía SSH tunnel, gobierno de memoria Qdrant, GitNexus como policy gate y capa de salud cognitiva."
tags:
  - ai-lab
  - mcp
  - opencode
  - qdrant
  - gitnexus
  - cognitive-health
  - governance
---


## Introducción

AI-LAB deja de ser un runtime local aislado para convertirse en una plataforma gobernada accesible desde agentes externos. Esta entrada resume los hitos recientes que han transformado el laboratorio: MCP Semantic Gateway, integración OpenCode Windows, gobierno de memoria Qdrant, incident governance, GitNexus como policy gate para cambios críticos y la capa de salud cognitiva.

## MCP Semantic Gateway

El primer MCP Semantic Gateway (`ailab-mcp-semantic-gateway`) se ha implementado como un servidor read-only que expone tres tools:

- **ailab_status** — estado de Gateway y Router
- **ailab_runtime_health** — salud cognitiva detallada del runtime
- **ailab_route_preview** — clasificación heurística de ruta sin inferencia real

Características clave del despliegue:
- Servicio systemd activo
- Bind seguro a `127.0.0.1:8091` — sin exposición LAN
- Endpoint Streamable HTTP en `/mcp`
- Sin cambios en Gateway/Router existentes
- Sin Qdrant writes
- 13/13 tests pytest pasando
- Tags: `CP-MCP-SEMANTIC-GATEWAY-01-STABLE`

### ¿Por qué no se expone LAN todavía?

El MCP Gateway no tiene autenticación configurada actualmente (`AILAB_MCP_TOKEN` no está definido). Por seguridad, el servicio se bindea exclusivamente a `127.0.0.1`. El acceso desde agentes externos se realiza mediante SSH tunnel, no exponiendo puertos a la red local.

## Integración OpenCode Windows vía SSH Tunnel

La conexión desde OpenCode en Windows al MCP Semantic Gateway en Ubuntu se realiza mediante SSH tunnel reverso:

```
Windows localhost:8091 → SSH tunnel → Ubuntu 127.0.0.1:8091
```

- OpenCode config: `mcp.ailab` apunta a `http://127.0.0.1:8091/mcp`
- Validación E2E completa desde Windows
- Backup creado antes de modificar configuración
- Tag: `CP-MCP-OPENCODE-WINDOWS-CONNECTION-01-STABLE`

## Gobierno de memoria Qdrant

La auditoría `QDRANT-MEMORY-GOVERNANCE-AUDIT-01` encontró 8 colecciones activas sin políticas de retención: `agent_knowledge`, `ai_lab_memory`, `cognitive_history`, `incidents`, `optimizer_history`, `routing_history`, `runtime_snapshots`, `working_memory`.

Hallazgos principales:
- Qdrant verde, sin problemas de rendimiento
- Sin TTL/retention en colecciones — crecimiento indefinido
- `routing_history` e `incidents` con crecimiento relevante
- Incidentes históricos con `resolved=false` generan riesgo de contaminación
- `agent_knowledge` almacena texto completo de skills en payload

Se formalizó una política de gobierno (`CP-QDRANT-MEMORY-GOVERNANCE-POLICY-01-STABLE`) que clasifica colecciones por criticidad, establece retención, define inyección contextual segura y resuelve incidentes con trazabilidad.

## Memory Injection Telemetry

Telemetría activa verificada (`MEMORY-INJECTION-BURNIN-01 PASS`): `memory_injected`, `chars_injected`, `estimated_tokens_injected`, `collections_used`, `matches_total`, `route_family`, `prompt_tokens_after_memory`. No se almacenan prompts completos. Persistencia Qdrant verificada y corregida. Tag: `CP-MEMORY-INJECTION-QDRANT-PERSISTENCE-FIX-01-STABLE`.

## Incident Governance

Schema formal implementado (`CP-INCIDENTS-GOVERNANCE-SCHEMA-01-STABLE`): `incident_id`, `resolution_status`, `retention_class`, `archived`, `duplicate_count`, `first_seen_at`, `last_seen_at`, `affected_component`, `schema_version`. 49/49 tests pasando. Solo afecta a incidentes futuros.

## GitNexus como policy gate para cambios críticos

Política `GITNEXUS-GOVERNED-RUNTIME-CHANGE-POLICY-01` formalizada:
- `openai_gateway.py` clasificado como alto blast-radius (`impactedCount: 47`, `risk: HIGH`)
- Cambios en runtime crítico requieren: GitNexus impact/context/query, HARD_FACTS/INFERIDO/UNKNOWNS, matriz de tests obligatoria y smoke runtime
- Tag: `CP-GITNEXUS-GOVERNED-RUNTIME-CHANGE-POLICY-01-STABLE`

## Runtime Stability

- **GATEWAY-SHUTDOWN-GRACEFUL-01**: Gateway devuelve 503 durante shutdown, métrica `ailab_gateway_shutdown_rejections_total`
- **POST-RELEASE-SLO-DRIFT-WATCH-CLOSE-01**: Sin SLO drift, sin alert noise, sin phantom regression
- Gateway/Router/GitNexus activos y estables

## Cognitive Health Layer

Endpoint `/runtime/health` con score, nodos, routing-confidence, watchdog, latencia y degradaciones. Métricas: `ailab_cognitive_health_score`, `routing_confidence`, `nodes_online`, `watchdog_triggers_total`. Phantom RX9070 corregido, nodo `.50` online con `success_rate: 1.0`. Health score actual: **89.6/100**.

## Estado actual de nodos

| Nodo | IP | GPU | Estado |
|------|-----|-----|--------|
| .50 | inference GPU node | RX9070 | Online (4 modelos) |
| .250 | storage node | — | Online (6 modelos) |
| .60 | inventory node | RX7900XT | Offline (esperado) |

## Incidencia documentada pendiente

**`ailab-router/auto` contra LM Studio no respondió desde OpenCode.** MCP tools funcionan correctamente. Pendiente diagnóstico read-only de router, gateway y LM Studio endpoints. No resuelto en esta fase.

## Próximos pasos

1. Observación continuada con SSH tunnel
2. Configurar `AILAB_MCP_TOKEN` + LAN controlada (Opción B)
3. Implementar tools semánticas reales (sommelier, analyze_label, price_estimate)
4. Diagnosticar `ailab-router/auto` contra LM Studio
5. Integración Rioja Marketplace
6. Multi-GPU runtime scheduler

## Cierre ejecutivo

AI-LAB ha evolucionado de un conjunto de servicios locales a una **plataforma gobernada para agentes**: con MCP como capa de acceso controlado, Qdrant como memoria con políticas, GitNexus como guardián de cambios críticos, OpenCode como primer consumidor externo y salud cognitiva para medir el sistema en tiempo real. El runtime es observable, medible y gobernado sin haber comprometido la seguridad ni la estabilidad de los servicios core.
