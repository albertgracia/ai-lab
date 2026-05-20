---
title: "FASE 28.1 — Planner Runtime Skeleton"
summary: "Esqueleto del planner agentico con DAG readonly, dependencias deterministas, permission scopes, governance pre-hooks y estados preparados para ejecución futura. Sin ejecución real todavia."
order: 80
---

## Objetivo

Evolucionar el pipeline agentic existente (FASE 28.0 simulation-only) hacia un Planner Runtime real, pero SIN ejecución real todavía. Preparar la carretera para FASE 28.2–28.8.

## Filosofia

```
28.1 → prepara la carretera (DAG, permisos, governance, estados)
28.2 → governance hooks/contracts
28.3 → readonly executor (empieza a circular)
28.4 → tool contracts
28.5 → sandbox write simulation
28.6 → rollback engine
28.7 → approval execution gates
28.8 → write execution controlada
```

## Archivos modificados

### `runtime/agentic/planner.py`

**WorkflowAction** extendido con campos DAG:

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `dependencies` | `list[str]` | action_ids de los que depende |
| `permission_scope` | `str` | Scope de permiso (`readonly`, `forbidden`, etc.) |
| `rollback_hint` | `str` | Pista de como revertir (reservado) |
| `expected_output` | `str` | Que deberia producir la accion |

**AgenticPlan** extendido con governance:

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `dag_edges` | `list[tuple[str,str]]` | Aristas del DAG |
| `permission_scope` | `str` | Scope global del plan |
| `requires_approval` | `bool` | Si requiere aprobacion (siempre False en 28.1) |
| `max_nodes` | `int` | Maximo 8 nodos |
| `max_depth` | `int` | Profundidad maxima 3 |
| `governance_result` | `dict` | Resultado de validacion |

**Planner.plan()** mejorado:
- Rechaza intents BLOCKED (modify_config, create_file, restart_service, install_package, run_command)
- Rechaza intents no reconocidos (return None)
- Construye DAG con `build_dag()`
- Enforces max_nodes=8, max_depth=3
- Clasifica permission_scope global

### `runtime/agentic/workflow_state.py`

4 nuevos estados reservados:

| Estado | Proposito | Activo en 28.1 |
|--------|-----------|----------------|
| `GOVERNED` | Plan validado por governance | ✅ |
| `READY_FOR_EXECUTION` | Plan listo para ejecutarse | ✅ (transicion) |
| `EXECUTING_RESERVED` | Ejecucion en progreso (FASE 28.3+) | 🔒 Definido, sin transiciones |
| `ROLLBACK_RESERVED` | Rollback en progreso (FASE 28.6+) | 🔒 Definido, sin transiciones |

### `runtime/agentic/intents.py`

8 nuevos KNOWN_INTENTS para patrones de planes conocidos:

| Intent | Descripcion |
|--------|-------------|
| `check_gateway_health` | Verificar estado del gateway |
| `check_runtime_status` | Verificar estado general del runtime |
| `inspect_streams` | Inspeccionar estado de streams |
| `check_gpu_status` | Verificar estado de GPU |
| `analyze_timeouts` | Analizar timeouts y latencia |
| `check_models` | Verificar modelos cargados |
| `inspect_slo_state` | Inspeccionar estado SLO |
| `check_services` | Verificar servicios del sistema |

FORBIDDEN_INTENT_PATTERNS extendido con: `docker stop/rm/kill`, `systemctl stop/disable`, `curl | bash/sh`, `ignore previous`, `override`, `planner`, `self-modify`, `self-heal`.

## Archivos nuevos

### `runtime/agentic/permissions.py`

Define PermissionScope enum con 5 niveles:

| Scope | Permitido en 28.1 | Fase activa |
|-------|-------------------|-------------|
| `readonly` | ✅ | Siempre |
| `workspace_write_reserved` | ❌ | FASE 28.5+ |
| `runtime_write_reserved` | ❌ | FASE 28.6+ |
| `privileged_reserved` | ❌ | FASE 28.7+ |
| `forbidden` | 🚫 | Nunca |

### `runtime/agentic/governance_hooks.py`

Interfaz de governance con:

- `validate_plan_against_policy(plan)` → `GovernanceResult`
- `classify_permissions(plan)` → `PermissionScope`
- `detect_forbidden_actions(plan)` → `list[str]`

Reglas 28.1:
- `permission_scope != READONLY` → `allowed=False`
- Patrones prohibidos → `allowed=False`
- Intents no reconocidos → `allowed=False`
- `requires_approval=False`

## Metricas Prometheus

| Metrica | Tipo | Labels |
|---------|------|--------|
| `ailab_planner_plans_total` | Counter | `plan_type` |
| `ailab_planner_dag_nodes_total` | Histogram | `plan_type` (buckets 1-8) |
| `ailab_planner_blocked_total` | Counter | `blocked_reason` |
| `ailab_planner_permission_scope_total` | Counter | `scope` |
| `ailab_planner_validation_failures_total` | Counter | `reason` |

## Feature Flags

| Flag | Default | Proposito |
|------|---------|-----------|
| `AI_LAB_ENABLE_PLANNER` | `false` | Habilita el planner |
| `AI_LAB_PLANNER_DRY_RUN` | `true` | Dry-run obligatorio |

## Tests

13 tests, 42 assertions. Ejecutar:

```bash
python3 tests/test_planner_28_1.py
```

| Test | Input | Expected |
|------|-------|----------|
| readonly plan valido | "revisa el gateway" | Plan, DAG 4 nodos, READONLY |
| dependencias DAG | "revisa runtime" | DAG con edges, sin ciclos |
| prompt ambiguo | "haz algo" | None (rechazado) |
| write malicioso | "escribe en /etc/config" | None (bloqueado) |
| sudo attempt | sudo + restart | FORBIDDEN scope |
| docker mutation | docker rm | Detectado en patterns |
| planner recursion | planner recursion | Detectado en patterns |
| permission scope readonly | check intent | READONLY |
| permission scope forbidden | restart intent | FORBIDDEN |
| max nodes enforced | 11 intents | Truncado a 8 |
| max depth enforced | N/A | Depth ≤ 3 |
| governance result | plan valido | GovernanceResult completo |
| workflow state governed | EVALUATED→GOVERNED | Transicion valida |
| workflow state reserved | Nuevos estados | Definidos, sin transiciones |

## Criterio PASS

- [x] WorkflowAction con dependencies, permission_scope, expected_output, rollback_hint
- [x] AgenticPlan con dag_edges, permission_scope, governance_result
- [x] DAG deterministico: mismos intents → mismo plan
- [x] Maximo 8 nodos, profundidad maxima 3
- [x] READONLY unico scope permitido en 28.1
- [x] Cualquier write/edit/rm/sudo → FORBIDDEN → bloqueado
- [x] 4 estados reservados (GOVERNED, READY_FOR_EXECUTION, EXECUTING_RESERVED, ROLLBACK_RESERVED)
- [x] 8 nuevos KNOWN_INTENTS
- [x] GovernanceResult completo
- [x] 5 metricas Prometheus
- [x] Feature flags: enable=false, dry_run=true
- [x] 42 tests assertions pasan
- [x] 0 side effects, 0 ejecucion real, 0 mutations, 0 crashes
