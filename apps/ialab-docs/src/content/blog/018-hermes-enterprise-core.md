---
title: "Hermes Enterprise Core: governance declarativo para AI-LAB"
date: "2026-06-28"
summary: "Hermes Enterprise Core completa 6 componentes con 185 tests PASS: SOUL, Capability Registry, Operator Registry, Hook Registry, MCP Registry y Dynamic Governance. Una capa de governance declarativo que no modifica el runtime pero lo hace verificable."
tags:
  - ai-lab
  - hermes
  - governance
  - enterprise
  - architecture
---

## ¿Qué es Hermes Enterprise Core?

Hermes es la capa de governance declarativo de AI-LAB. No ejecuta el runtime — lo describe, lo valida y expone su estado. Es la diferencia entre "esto funciona" y "esto está formalmente gobernado".

Núcleo de la filosofía: si no está declarado, no existe. Si no está validado, no es fiable.

## Los 6 componentes

### SOUL (Self-organizing Unified Logic)

Identidad y propósito del runtime enterprise. Define el truth model, los protocolos de comunicación y los boundaries del sistema. Es la constitución que todo lo demás referencia.

### Capability Registry

Registro declarativo de 6 capacidades críticas: inferencia, memoria, herramientas, observabilidad, gobernanza y cognición estructural. Cada capacidad tiene dependencias, versiones y validación cruzada. 24 tests.

### Operator Registry

5 operadores registrados (runtime, governance, memory, marketplace, incidents) con 12 validaciones profundas cada uno: IDs únicos, capabilities asignadas, protocolos MCP, execution_mode, dominios, forbidden_actions, reports, success_criteria y truth_model. 17 tests.

### Hook Registry

9 lifecycle hooks declarativos en modo `declarative_only` con `enabled: false`. El esqueleto completo está definido pero ningún hook está activo. Esto permite revisar el diseño antes de activar ejecución real.

### MCP Registry

5 servidores MCP declarados: ai-lab-runtime, rioja-marketplace, prometheus, marketplace-mcp y filesystem. Cada uno con herramientas, recursos y modo de integración especificado.

### Dynamic Governance (ADR-006)

Sistema de 4 modos (NORMAL, ELEVATED, DEGRADED, LOCKDOWN) con GovernanceResolver que evalúa 6 señales trigger (slo_state, degradation, emergency, VRAM, GPU, timeout). Anti-flapping 30s, capability-governance matrix (6 capabilities × 4 modos). 45 tests.

## Status Endpoint

`GET /hermes/status` en puerto dedicado (`:8095`). Devuelve 14 bloques: service, version, build, git, enterprise, soul, capabilities, operators, hooks, mcp, governance, architecture, tests y status. Architecture block indica `enterprise_phase: "CORE"`, `next_phase: "E08"`, `readiness: "READY"`.

## Lo que NO hace Hermes (por diseño)

- No ejecuta hooks (todos en `enabled: false`)
- No bloquea capacidades (governance enforcement es E09, planificado)
- No modifica el gateway, router, marketplace, Prometheus ni Grafana
- No cambia el comportamiento del agente en producción
- No afecta al runtime operativo

Hermes es capa declarativa + validación + exposición. El enforcement vendrá después.

## 185 tests PASS

Cada componente tiene su batería de tests:

| Componente | Tests |
|------------|-------|
| SOUL | 27 |
| Capability Registry | 24 |
| Operator Registry | 17 |
| Hook Registry | Skeleton |
| MCP Registry | Skeleton |
| Dynamic Governance | 45 |
| Status Endpoint | 72 |

**Total:** 185 tests PASS. Checkpoint: `CP-HERMES-ENTERPRISE-CORE-01`.

Documentación completa en [docs/hermes/](/docs/hermes/).
