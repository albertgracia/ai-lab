---
title: "FASE 28 — Governed Autonomy Runtime"
summary: "Implementación completa del runtime agentic gobernado: simulation, planner, readonly executor, sandbox write, rollback, burn-ins, seguridad y límites."
order: 10
---

## Resumen

La FASE 28 transformó AI-LAB de un gateway LLM a un runtime agentic gobernado con 10 capas de seguridad. El LLM propone cambios, el runtime evalúa, el humano aprueba, y el sandbox ejecuta. Nunca al revés.

## Arquitectura general

```
Cliente → Gateway (:8008)
  → Action Intent Layer (LLM genera intents, no tool_calls)
  → Planner (intents → acciones reales + DAG)
  → Dry-Run Engine (simula sin ejecutar)
  → Risk Engine (determinista, nunca el LLM decide)
  → Explainability Layer (resumen en lenguaje natural)
  → Approval Gate (tickets HMAC, TTL, single-use)
  → Executor (sandbox: ulimit + chroot + net iso)
  → Verifier (checksums, service health, side effects)
  → Rollback (transaction boundaries + snapshots)
  → Replay (plan diffing, 3 versiones)
```

## Subfases implementadas

### FASE 28.0 — Simulation-Only Mode

Checkpoint: **Simulation-only mode (sin tag independiente)**

- Feature flag `AGENTIC_EXECUTION_ENABLED=false`
- Pipeline completo pero executor no-op
- Propósito: 3-5 días de tráfico simulado para detectar planes absurdos
- Métricas, replay y audit emiten igual que en real

### FASE 28.1 — Planner Runtime Skeleton

Checkpoint: **CP-28.1-PLANNER-RUNTIME-SKELETON-STABLE**

- Action Intent Layer: LLM genera intents estructurados, no tool_calls
- Planner: normaliza intents del catálogo `KNOWN_INTENTS` a acciones reales
- Dry-run obligatorio con diff preview
- Risk scoring determinista (reglas fijas, no LLM)

### FASE 28.2 — Readonly Executor

Checkpoint: **CP-28.2-READONLY-EXECUTOR-STABLE**
Burn-in: **CP-28.2-B-READONLY-BURNIN-STABLE** (74/74 tests)

- Ejecución de acciones de solo lectura
- Confinamiento: ulimit + path allowlist
- Verificador post-ejecución
- Rollback transaccional

### FASE 28.3 — Sandbox Write Runtime

Checkpoint: **CP-28.3-SANDBOX-WRITE-STABLE**
Burn-in: **CP-28.3-B-SANDBOX-WRITE-BURNIN-STABLE**

- Ejecución de acciones de escritura en sandbox
- Confinamiento multicapa:
  - Filesystem: solo paths allowlist + chroot
  - Network: solo localhost:1234 (LM Studio)
  - Procesos: max 5 (ulimit -u 5)
  - Memoria: 256MB (ulimit -v 262144)
  - CPU time: 60s (ulimit -t 60)
  - Timeout: 30s por acción

## Modelo de permisos (5 niveles)

| Nivel | Intents | Approval | Path scope |
|-------|---------|----------|------------|
| readonly | read_config, read_state, observe_runtime | Nunca | /opt/ai-lab/ (read) |
| workspace_write | + modify_config, create_file | Tras dry-run | config/, prompts/, profiles/ |
| runtime_write | + restart_service | Ticket firmado | + policies/, agentic/ |
| privileged | + install_package | Doble ticket | + .venv/ (solo pip) |
| forbidden | — | Siempre bloqueado | /etc/, /home/, gateway/, llm/ |

## Approval Gate

- Tickets HMAC firmados: plan_hash + dry_run_hash + expires_at
- Tipos de approval: workspace_confirm (5 min), runtime_confirm (2 min), privileged_confirm (1 min)
- Single-use: cada ticket solo se usa una vez
- Plan deduplication: 409 Conflict si ya ejecutado

## Rollback transaccional

```python
Transaction(
    state="PREPARING → EXECUTING → COMMITTED | ROLLING_BACK → ROLLED_BACK",
    snapshots={...},
    executed_actions=["action-1", "action-2"],
    failed_action="action-3"
)
```

Rollback parcial: si la acción 2 de 3 falla, solo se revierten las acciones 1 y 2.

## Observabilidad

12 métricas Prometheus nuevas:
- Planner: `ailab_agentic_plans_total`, `ailab_agentic_risk_score`
- Approval: `ailab_agentic_approvals_requested/granted/rejected/expired`
- Execution: `ailab_agentic_executions_total`, `ailab_agentic_actions_total`, `ailab_agentic_execution_duration_ms`
- Rollback: `ailab_agentic_rollbacks_total`
- Governance: `ailab_agentic_governance_blocks_total`

## Prohibiciones en esta iteración

- ❌ Multi-agent swarm (sin orquestador maduro)
- ❌ Auto-aprobación (viola human-in-the-loop)
- ❌ Self-modifying runtime (el agente NUNCA modifica su propio código)
- ❌ Bash sin sandbox (siempre ulimit + chroot + path allowlist)
- ❌ Sub-agentes recursivos (max_plan_depth = 1)
- ❌ Docker obligatorio (opcional en 28.8)
- ❌ Acceso a internet desde sandbox (solo localhost:1234)

## Checkpoints

- CP-28.1-PLANNER-RUNTIME-SKELETON-STABLE
- CP-28.2-READONLY-EXECUTOR-STABLE
- CP-28.2-B-READONLY-BURNIN-STABLE
- CP-28.3-SANDBOX-WRITE-STABLE
- CP-28.3-B-SANDBOX-WRITE-BURNIN-STABLE
