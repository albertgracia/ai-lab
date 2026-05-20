---
title: "FASE 28.3 — Sandbox Write Runtime"
summary: "Executor de mutaciones sandbox con Python I/O (nunca subprocess), snapshot SHA-256 pre-mutación, rollback con validación checksum post-restore, governance con chmod prohibition, rate limiting, budget por workflow, artifact registry con lineage DAG, auditoría JSONL con mutation_class y 7 métricas Prometheus."
order: 82
---

## Objetivo

Extender el runtime agentic para escribir archivos exclusivamente dentro de `/tmp/opencode/sandbox/` y `/opt/ai-lab/sandbox/`, con snapshots pre-mutación, rollback checksum-based, governance completo, y rastro de auditoría.

## Filosofía

```
28.2 → readonly executor (comandos seguros, shell=False)
28.3 → sandbox write executor (Python I/O, governance, rollback) ← ESTAMOS AQUÍ
28.4 → tool contracts (futuro)
```

**Principio clave:** sandbox = filesystem capability runtime gobernado, NO shell unrestricted dentro de `/tmp`.

## Archivos nuevos (8)

### `runtime/agentic/sandbox_fs.py`

Filesystem foundation con boundary enforcement:

- `SANDBOX_ROOTS` — `/tmp/opencode/sandbox/` y `/opt/ai-lab/sandbox/`
- `resolve_sandbox_path()` — canonical path resolution
- `is_within_sandbox()` — boundary check
- `detect_symlink_escape()` — bloquea symlinks fuera del sandbox
- `detect_path_traversal()` — bloquea `../`, `~`, etc.
- `check_path_depth(max_depth=8)` — evita nesting arbitrario
- `is_extension_allowed()` / `is_extension_blocked()` — extension filter
- `BLOCKED_EXTENSIONS`: `.socket`, `.service`, `.mount`, `.timer`, `.path`, `.target`

### `runtime/agentic/sandbox_registry.py`

Catálogo de 11 operaciones sandbox con `SandboxOperationSpec`:

| Operación | Extensiones | Max size | Risk | Governance |
|-----------|------------|----------|------|------------|
| `create_file` | All allowed | 1MB | medium | |
| `append_file` | All allowed | 1MB | medium | |
| `replace_file` | All allowed | 1MB | medium | |
| `create_directory` | — | — | low | |
| `write_json` | `.json` | 2MB | low | |
| `write_yaml` | `.yaml/.yml` | 1MB | low | |
| `write_markdown` | `.md` | 2MB | low | |
| `generate_report` | `.md` | 5MB | low | |
| `generate_config` | `.json/.yaml/.toml/.ini` | 512KB | low | |
| `generate_script` | `.py/.sh` | 1MB | medium | ✅ siempre |
| `sandbox_transform` | Todos | 5MB | low | |

- `MutationClass` enum: `CREATE`, `APPEND`, `REPLACE`, `TRANSFORM`, `GENERATE`, `ROLLBACK`
- `is_allowed_operation()` — valida extensión, tamaño, tipo
- `op_for_intent()` — mapeo intent string → operación

### `runtime/agentic/mutation_context.py`

`MutationExecutionContext` extiende `RuntimeExecutionContext`:

- `sandbox_root`, `mutation_class`, `mutation_type`
- `dry_run_only_write` flag
- `current_workflow_artifacts`, `current_workflow_bytes` — budget counters
- `is_executable()` — permite `READONLY` y `SANDBOX_WRITE`

### `runtime/agentic/sandbox_policies.py`

Governance sandbox:

- `check_sandbox_governance()` — verifica: phase ≥ 28.3, intent es sandbox write, path dentro de boundary, sin symlink/traversal, extensión permitida, profundidad dentro de límite
- `detect_chmod_intent()` — detecta `chmod +x`, `chmod 755`, `+x`, etc. → **siempre bloqueado**
- `assess_sandbox_risk()` — `.py`/`.sh` siempre `medium` como mínimo
- `CHMOD_PATTERNS` — 10 patrones de chmod prohibidos en sandbox

### `runtime/agentic/rollback_engine.py`

Reemplaza `rollback_placeholder.py` con engine real:

- `Snapshotter.take_snapshot()` — backup pre-mutación en `{sandbox_root}/.rollback/{workflow_id}/{action_id}/`
- SHA-256 checksum antes de mutar
- `RollbackEngine.restore()` — restore + **validación checksum post-restore**
- `RollbackEngine.rollback_workflow()` — restore completo por workflow
- `write_original_path_marker()` — metadato para inferir path original
- `RollbackResult` con `checksum_validated` y `restored_checksum`

### `runtime/agentic/artifact_registry.py`

Registro de outputs con lineage DAG:

- `ArtifactEntry` con: `artifact_id`, `path`, `checksum_sha256`, `size_bytes`, `mutation_type`, `workflow_id`, `action_id`, `parent_workflow_id`, `parent_artifact_id`, `generated_by_action`
- `ArtifactRegistry.register()` — JSONL append
- `ArtifactRegistry.list()`, `get()`, `get_by_workflow()`
- `ArtifactRegistry.get_lineage()` — DAG de ancestros
- `ArtifactRegistry.count_by_workflow()` / `total_bytes_by_workflow()` — budget queries

### `runtime/agentic/sandbox_audit.py`

Append-only JSONL con:

- `SandboxAuditEntry`: `timestamp`, `execution_id`, `workflow_id`, `action_id`, `mutation_class`, `mutation_type`, `target_path`, `before_checksum`, `after_checksum`, `rollback_available`, `rollback_path`, `status`, `error`
- `write_sandbox_audit()`, `read_sandbox_audit()`, `get_sandbox_audit_stats()`

### `runtime/agentic/sandbox_executor.py`

`SandboxWriteExecutor` — orquestador con:

- **Feature flags:** `ENABLE_SANDBOX_WRITE = False`, `DRY_RUN = True` (secure by default)
- **Budget:** `MAX_ARTIFACTS_PER_WORKFLOW = 100`, `MAX_WORKFLOW_BYTES = 25MB`
- **Rate limiting:** 10 writes/min por workflow (token bucket)
- Pipeline por acción: `governance → budget → rate limit → snapshot → mutate (Python I/O) → checksum → artifact registry → audit`
- **Rollback automático** en error de mutación
- **NUNCA usa subprocess** para writes — solo `open()`, `pathlib`, `shutil`, `json.dump()`

## Archivos modificados (9)

### `runtime/agentic/workflow_state.py`

- Nuevo estado: `MUTATING`
- Nuevas transiciones: `EXECUTING → MUTATING`, `MUTATING → DONE/FAILED`, `FAILED → ROLLED_BACK`, `DONE → ROLLED_BACK`

### `runtime/agentic/permissions.py`

- `_SANDBOX_WRITE_INTENTS` — 11 intents de escritura sandbox
- `_SCOPE_ALLOWED_IN_PHASE["28.3"] = {"readonly", "workspace_write_reserved"}`
- `classify_permission_scope()` — sandbox intents → `WORKSPACE_WRITE_RESERVED`
- `"create_file"` removido de `_FORBIDDEN_INTENTS`

### `runtime/agentic/execution_context.py`

- `DryRunReason.SANDBOX_DISABLED = "sandbox_disabled"`
- `is_executable()` — ahora permite `SANDBOX_WRITE` y `READONLY`

### `runtime/telemetry/prometheus_metrics.py`

7 métricas nuevas:

| Métrica | Tipo | Labels |
|---------|------|--------|
| `ailab_sandbox_mutations_total` | Counter | type, result |
| `ailab_sandbox_rollbacks_total` | Counter | reason |
| `ailab_sandbox_policy_denied_total` | Counter | intent, reason |
| `ailab_sandbox_artifacts_total` | Gauge | |
| `ailab_sandbox_escape_attempts_total` | Counter | detection_method |
| `ailab_sandbox_checksum_mismatch_total` | Counter | |
| `ailab_sandbox_mutation_duration_seconds` | Histogram | type |

### `runtime/gateway/openai_gateway.py`

- Feature flag `AI_LAB_ENABLE_SANDBOX_WRITE` (default `false`)
- Import condicional de `SandboxWriteExecutor`
- Pipeline bifurcación: si sandbox write enabled + intents sandbox → `SandboxWriteExecutor`

### `runtime/llm/router_api.py`

3 nuevos endpoints GET:

| Endpoint | Descripción |
|----------|-------------|
| `GET /agentic/artifacts?limit=50` | Lista artifacts recientes |
| `GET /agentic/artifacts/{id}` | Artifact específico + lineage |
| `GET /agentic/rollback/{workflow_id}` | Información de rollback disponible |

## Endpoints internos

```
GET /agentic/state            → execution_mode, phase, executor_enabled
GET /agentic/executions       → audit trail readonly
GET /agentic/executions/stats → estadísticas audit
GET /agentic/artifacts        → artifacts sandbox
GET /agentic/artifacts/{id}   → artifact + lineage
GET /agentic/rollback/{id}    → rollback info
```

## Feature flags

| Variable | Default | Propósito |
|----------|---------|-----------|
| `AI_LAB_ENABLE_SANDBOX_WRITE` | `false` | Habilita executor sandbox write real |
| `AI_LAB_ENABLE_PLANNER` | `false` | Habilita pipeline agentic completo |

## Seguridad

1. **NO subprocess** para writes — solo `open()`, `pathlib`, `shutil`
2. **NO chmod** — 10 patrones detectados y bloqueados
3. **Symlink escape detection** — `os.path.realpath()` en cada operación
4. **Path depth limit** — máximo 8 niveles de nesting
5. **Extensiones bloqueadas** — `.socket`, `.service`, `.mount`, etc.
6. **Secure by default** — flags `false`/`True`, dry-run por defecto

## Tests

122 tests en `tests/test_sandbox_28_3.py`:

| Categoría | Tests |
|-----------|-------|
| SandboxFS | 21 |
| SandboxRegistry | 14 |
| SandboxPolicies | 13 |
| SandboxAudit | 5 |
| ArtifactRegistry | 10 |
| RollbackEngine | 9 |
| MutationContext | 10 |
| WorkflowState (MUTATING) | 9 |
| Permissions 28.3 | 9 |
| SandboxExecutor | 9 |
| Mutation helpers | 11 |
| Sandbox intent classification | 6 |
