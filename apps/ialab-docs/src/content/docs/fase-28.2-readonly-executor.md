---
title: "FASE 28.2 — Executor Readonly Runtime"
summary: "Ejecutor readonly con subprocess seguro (shell=False), catálogo de comandos validados, governance pre-ejecución, audit trail JSONL con hashes SHA-256 y 6 métricas Prometheus."
order: 81
---

## Objetivo

Implementar el primer executor real del pipeline agentic: **ReadonlyExecutor**. Ejecuta comandos readonly (`ls`, `cat`, `curl`, `docker ps`, `systemctl status`, etc.) a través de `subprocess.run` con `shell=False`, validación estricta de argumentos y registro completo en audit trail.

## Filosofía

```
28.1 → planner DAG + permisos + governance
28.2 → readonly executor (comandos seguros, shell=False) ← ESTAMOS AQUÍ
28.3 → rollback engine
28.4 → tool contracts
28.5 → sandbox write simulation
28.6 → rollback automatizado
28.7 → approval execution gates
28.8 → write execution controlada
```

## Archivos nuevos (7)

### `runtime/agentic/readonly_registry.py`

Catálogo declarativo de comandos readonly permitidos:

- `SAFE_READONLY_COMMANDS: dict[str, ReadonlyCommandSpec]` — 27 comandos con `category`, `risk`, `local_only`, `requires_args_validation`
- `FORBIDDEN_READONLY_COMMANDS: set[str]` — 20+ comandos prohibidos
- `FORBIDDEN_READONLY_PATTERNS: set[str]` — patrones bloqueados (`systemctl restart`, `docker stop`, etc.)
- `DANGEROUS_OPERATORS`, `DANGEROUS_REDIRECTS`, `DANGEROUS_TOKENS` — tokens bloqueados en readonly
- `FIND_ALLOWED_PATHS` — `/opt/ai-lab`, `/tmp`, `/var/log`, `/home/albert`
- `DOCKER_ALLOWED_SUBCOMMANDS` — solo `ps`, `stats`, `inspect`, `logs`
- `RFC1918_PATTERNS` — solo IPs locales para curl
- `ExecutionCapability` enum: `READONLY`, `SANDBOX_WRITE`, `SYSTEM_WRITE`

### `runtime/agentic/safe_runner.py`

Wrapper `subprocess.run` con `shell=False`:

- `validate_command()` — validación pre-ejecución: shlex parsing, forbidden tokens, redirects, operators, args específicos por comando
- `run_safe()` — ejecuta el comando validado, captura stdout/stderr, calcula hashes SHA-256 truncados a 16 chars
- `SafeRunnerResult` — dataclass con `command`, `exit_code`, `stdout`, `stderr`, `duration_ms`, `blocked`, `blocked_reason`, `stdout_hash`, `stderr_hash`

Validaciones específicas:
- **curl**: no `-o`/`-O`/`--output`, target solo RFC1918
- **find**: path explícito requerido, solo en `FIND_ALLOWED_PATHS`
- **journalctl**: no `-f`/`--follow`, `--lines` max 500
- **docker**: solo `ps`/`stats`/`inspect`/`logs`, no `exec`/`cp`/`compose`/etc.
- **systemctl**: solo `status`/`is-active`/`is-enabled`, no `restart`/`stop`/`start`/etc.

### `runtime/agentic/execution_context.py`

Contexto de ejecución para el runtime agentic:

- `ExecutionMode` enum: `SIMULATION`, `READONLY`, `SANDBOX_WRITE`, `AUTONOMOUS`
- `CURRENT_EXECUTION_MODE = ExecutionMode.READONLY`
- `DryRunReason` enum: `FEATURE_FLAG`, `GOVERNANCE_BLOCK`, `RISK_BLOCK`, `READONLY_PHASE`
- `RuntimeExecutionContext` dataclass: `execution_id`, `mode`, `phase`, `dry_run`, `dry_run_reason`

### `runtime/agentic/readonly_policies.py`

Políticas de governance pre-ejecución:

- `check_governance()` — verifica intentos prohibidos (`restart_service`, `install_package`) vs comandos validados
- `assess_risk()` — clasifica riesgo por intent/tool/target
- `check_scope()` — verifica targets contra scopes permitidos

### `runtime/agentic/execution_audit.py`

Audit trail en JSONL:

- `write_execution_audit()` — escribe entrada en `runtime/state/execution_audit.jsonl`
- `build_audit_entry()` — construye entrada con `execution_mode`, `dry_run`, `dry_run_reason`, action, result
- `read_execution_audit()` — lee últimas N entradas
- `get_audit_stats()` — estadísticas: total, blocked, success, failed

### `runtime/agentic/readonly_executor.py`

`RealReadonlyExecutor` — el executor real:

- Feature flags: `ENABLE_EXECUTOR=False`, `DRY_RUN=True` por defecto
- `execute()` — itera acciones del plan, aplica governance, ejecuta `run_safe()`, escribe audit trail
- Si `DRY_RUN=True` → `SimulationExecutor.execute_with_context()` con `dry_run_reason`
- Si `ENABLE_EXECUTOR=True` y `DRY_RUN=False` → ejecución real con shell=False

### `runtime/agentic/rollback_placeholder.py`

Stub para FASE 28.3:

- `RollbackPlaceholder.rollback()` → siempre `success=False` con `reason="rollback_not_implemented_before_FASE_28.3"`

## Archivos modificados (6)

### `runtime/agentic/executor.py`

- `SimulationExecutor.execute_with_context()` — nuevo método estático que simula ejecución registrando `dry_run_reason` y `execution_mode`

### `runtime/agentic/workflow_state.py`

- `WorkflowState.EXECUTING` añadido
- Transiciones: `READY_FOR_EXECUTION → EXECUTING`, `SIMULATING → EXECUTING`, `EXECUTING → DONE/FAILED`

### `runtime/agentic/permissions.py`

- `_CURRENT_PHASE` actualizado de `"28.1"` a `"28.2"`

### `runtime/agentic/__init__.py`

- Docstring actualizado a FASE 28.2

### `runtime/gateway/openai_gateway.py`

- Import de `RealReadonlyExecutor`, `RuntimeExecutionContext`, `ExecutionMode`, `DryRunReason`
- Pipeline agentic (L1433-1502) modificado:
  - Si `AI_LAB_ENABLE_PLANNER=True` y `AI_LAB_PLANNER_DRY_RUN=False` → `RealReadonlyExecutor.execute()`
  - Si no → `SimulationExecutor.execute_with_context()` con `dry_run_reason`
  - Audit event incluye `execution_mode`, `dry_run`, `dry_run_reason`

### `runtime/llm/router_api.py`

- 3 endpoints GET nuevos:
  - `GET /agentic/executions` — últimos N entries del audit trail
  - `GET /agentic/executions/stats` — estadísticas de ejecución
  - `GET /agentic/state` — estado actual del executor

### `runtime/telemetry/prometheus_metrics.py`

- 6 métricas nuevas:
  - `ailab_executor_commands_total` — comandos por resultado/riesgo
  - `ailab_executor_blocked_total` — bloqueos por razón
  - `ailab_executor_governance_blocks_total` — governance blocks por intent
  - `ailab_executor_dry_run_total` — dry-runs por razón
  - `ailab_executor_duration_ms` — duración por modo
  - `ailab_executor_validation_failures_total` — fallos de validación por razón

## Tests

`tests/test_executor_28_2.py`: 84 tests, 168+ assertions.

| Sección | Tests | Cubre |
|---------|-------|-------|
| SafeRunner Validation | 24 | allowed/forbidden commands, patterns, operators, redirects, curl/find/journalctl/docker/systemctl |
| SafeRunner Execution | 7 | run, block, hash, to_dict, timeout, shlex fail |
| ReadonlyRegistry | 8 | catalog, spec fields, forbidden overlap, patterns, RFC1918 |
| ExecutionContext | 8 | mode enum, dry_run reasons, default context, is_executable, to_dict |
| ReadonlyPolicies | 10 | governance restart/install/run, risk levels, scope check |
| ExecutionAudit | 6 | build entry, write+read, empty, stats, timestamp, phase |
| ReadonlyExecutor | 4 | flags, simulation fallback, empty plan, timeline |
| RollbackPlaceholder | 2 | not_implemented, to_dict |
| WorkflowState | 6 | EXECUTING exists, transitions |
| PermissionsPhase282 | 5 | scope allowed, classification |
| PlannerCompatibility | 5 | plan creation, action fields, timeline transitions |

## Métricas

```
ailab_executor_commands_total{result="success|blocked|failed", risk="low|medium|high"}
ailab_executor_blocked_total{reason="forbidden_pattern|command_not_found|etc"}
ailab_executor_governance_blocks_total{intent="restart_service|install_package"}
ailab_executor_dry_run_total{reason="feature_flag|readonly_phase|governance_block|risk_block"}
ailab_executor_duration_ms{mode="readonly|simulating"}
ailab_executor_validation_failures_total{reason="shlex_error|empty_command|etc"}
```

## Tags

`CP-28.2-READONLY-EXECUTOR-STABLE`
