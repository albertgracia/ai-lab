---
title: "FASE 28 — Governed Agentic Runtime"
summary: "Plan técnico completo para introducir workflows agentic seguros, gobernados y reversibles en AI-LAB. Action Intent Layer, approval con tickets firmados, risk determinista, rollback transaccional, sandbox con confinamiento, simulation-only mode y observabilidad completa."
order: 65
---

## Principio fundacional

```
LLM PROPONE  →  runtime EVALÚA  →  humano APRUEBA  →  sandbox EJECUTA
```

**Nunca al revés.** No hay ejecución directa del LLM. No hay autonomía sin approval explícito. No hay bash automático libre.

## Arquitectura general

```
Cliente (OpenCode)
  │
  ▼
┌─ Gateway (:8008) ────────────────────────────────────────┐
│                                                           │
│  Action Intent Layer   LLM genera intents, no tool_calls  │
│  Planner               Intents → acciones reales + DAG   │
│  Dry-Run Engine        Simula, risk determinista, diff    │
│  Governance            Permisos, allowlist, forbidden     │
│  Explainability Layer  Resumen en lenguaje natural        │
│  Approval Gate         428 + ticket HMAC + TTL            │
│  Executor              Sandbox: ulimit + chroot + net iso │
│  Verifier              Checksums, service health, syntax  │
│  Rollback              Transaction boundaries + snapshots │
│  Replay                Plan diffing (3 versiones)         │
│                                                           │
└───────────────────────────────────────────────────────────┘
  │
  ▼
LM Studio (192.168.1.50:1234)
```

## 10 capas del runtime agentic

### 1. Action Intent Layer

El LLM **NO** genera tool_calls. Genera *intents* estructurados:

```json
{
  "intents": [
    {
      "intent": "modify_config",
      "target": "inference_nodes.json",
      "goal": "reducir latencia bajando prioridad del nodo rx9070"
    }
  ]
}
```

El planner normaliza estos intents a acciones reales (tools, paths validados, dependencias). Esto desacopla el lenguaje natural de la ejecución real.

### 2. Planificación determinista

El planner mapea cada intent del catálogo (`KNOWN_INTENTS`) a acciones concretas:

| Intent | Acciones generadas | Tools | Risk |
|--------|-------------------|-------|------|
| `read_config` | read file | read, glob, grep | LOW |
| `modify_config` | read + edit + verify | read, edit, bash | MEDIUM |
| `restart_service` | systemctl restart | bash(systemctl) | HIGH |
| `install_package` | apt/pip install | bash(apt,pip) | CRITICAL |

### 3. Risk scoring determinista

El riesgo **NUNCA** lo decide el LLM. Se calcula con reglas fijas:

| Categoría | Reglas |
|-----------|--------|
| Intent type | `read_config`=LOW, `modify_config`=MEDIUM, `restart_service`=HIGH |
| Tool concreta | `read`=LOW, `edit`=MEDIUM, `bash`=MEDIUM |
| Path | `/etc/`=CRITICAL, `/opt/ai-lab/config/`=LOW |
| Bash tokens | `cat`=LOW, `systemctl`=HIGH, `apt`=CRITICAL |

### 4. Dry-run obligatorio

Cada plan pasa por simulación **antes** de ejecutarse. El dry-run muestra:

- Qué archivos se leerán/modificarán
- Diff preview de cambios
- Risk score con razones
- Si el rollback es posible
- Tiempo estimado

### 5. Governance

Cada acción del plan pasa por las políticas existentes:
- `apply_tool_policy()` → modos disabled/readonly/agentic
- `sanitize_bash_command()` → token scan
- `blocked_tools.json` → comandos prohibidos (rm -rf, mkfs, shutdown...)
- Path allowlist → solo paths autorizados
- `get_governance_state()` → si LOCKDOWN, no se ejecuta nada

### 6. Explainability Layer

Antes de cada approval, el runtime explica en **lenguaje natural**:

```markdown
🤖 AI-LAB Agent propone:

📋 RESUMEN
Objetivo: Reducir latencia bajando prioridad del nodo rx9070
Acciones: 1) Leer config  2) Modificar prioridad (10→5)  3) Reiniciar gateway

⚠️ RIESGO: MEDIUM
Razones: bash_token=systemctl, servicio afectado=ailab-gateway

🔙 ROLLBACK: SÍ — restaurar snapshot pre-ejecución

🔐 APPROVAL: runtime_write (expira en 2 min)
```

### 7. Approval Gate con tickets firmados

No depende de headers HTTP simples. Usa tickets con HMAC:

```json
{
  "approval_id": "appr-x9y8z7",
  "plan_hash": "sha256:abc123...",
  "dry_run_hash": "sha256:def456...",
  "expires_at": "2026-05-19T22:03:00Z",
  "hmac": "HMAC-SHA256(plan_hash + dry_run_hash + expires_at, secret)"
}
```

Verificación al ejecutar: ¿expirado? ¿plan modificado? ¿HMAC válido?

| Approval Type | TTL | Ejemplo |
|---------------|-----|---------|
| workspace_confirm | 5 min | modify_config, create_file |
| runtime_confirm | 2 min | restart_service |
| privileged_confirm | 1 min | install_package |

### 8. Ejecución en sandbox

Confinamiento multicapa:

| Recurso | Límite |
|---------|--------|
| Filesystem | Solo paths allowlist + chroot |
| Network | Solo localhost:1234 (LM Studio) |
| Procesos | Max 5 (`ulimit -u 5`) |
| Memoria | 256MB (`ulimit -v 262144`) |
| CPU time | 60s (`ulimit -t 60`) |
| Timeout | 30s por acción |

### 9. Verifier

Comprueba el estado **REAL** del sistema tras la ejecución:

- Checksums pre/post por archivo
- Sintaxis válida (JSON, YAML, .env)
- Service health (`systemctl is-active`)
- Port listening (`ss -tlnp`)
- Side effects no esperados
- Si falla → rollback automático

### 10. Rollback transaccional

```python
Transaction(
    state="PREPARING → EXECUTING → COMMITTED | ROLLING_BACK → ROLLED_BACK",
    snapshots={
        "/opt/ai-lab/config/file.json": FileSnapshot(checksum_pre, checksum_post, backup_path)
    },
    executed_actions=["action-1", "action-2"],
    failed_action="action-3"  # si falla
)
```

Rollback parcial: si la acción 2 de 3 falla, solo se revierten las acciones 1 y 2.

## Modelo de permisos (5 niveles)

| Nivel | Intents | Approval | Path scope |
|-------|---------|----------|------------|
| **readonly** | read_config, read_state, observe_runtime | Nunca | /opt/ai-lab/ (read) |
| **workspace_write** | + modify_config, create_file | Tras dry-run | config/, prompts/, profiles/ |
| **runtime_write** | + restart_service | Ticket firmado | + policies/, agentic/ |
| **privileged** | + install_package | Doble ticket | + .venv/ (solo pip) |
| **forbidden** | — | Siempre bloqueado | /etc/, /home/, gateway/, llm/ |

## Simulation-Only Mode (FASE 28.0)

Feature flag `AGENTIC_EXECUTION_ENABLED=false`:

- ✅ Todo el pipeline funciona normalmente (intents, planner, dry-run, governance, approval, verifier)
- ❌ Executor: no-op (devuelve SIMULATED_SUCCESS, nada se modifica)
- ✅ Métricas, replay y audit: emiten igual que en real

**Propósito:** 3-5 días de tráfico simulado para detectar planes absurdos, risk scores incorrectos, governance edge cases y approval fatigue **sin tocar el sistema real.**

## Idempotencia

> Mismo plan + mismo approval ticket = mismo resultado

- plan_id deduplication: si ya se ejecutó → 409 Conflict
- Ticket single-use: cada approval ticket solo se usa UNA vez
- Retry safe: misma acción con mismo input = mismo output
- Transaction atomicity: si una acción falla → rollback total

## Replay con plan diffing

Tres versiones del plan trazables:

```
original_plan    →  Lo que el LLM generó (intents)
normalized_plan  →  Lo que el planner produjo (acciones reales)
executed_plan    →  Lo que realmente se ejecutó
```

Nuevos endpoints:
- `GET /api/agentic/plan/{id}` — plan completo con acciones y risk scores
- `GET /api/agentic/plan/{id}/diff` — diff entre las 3 versiones
- `GET /api/agentic/workflow/{id}/timeline` — trazabilidad completa

## Observabilidad (12 métricas nuevas)

| Categoría | Métricas |
|-----------|----------|
| Planner | `ailab_agentic_plans_total`, `ailab_agentic_risk_score` |
| Approval | `ailab_agentic_approvals_requested/granted/rejected/expired` |
| Execution | `ailab_agentic_executions_total`, `ailab_agentic_actions_total`, `ailab_agentic_execution_duration_ms` |
| Rollback | `ailab_agentic_rollbacks_total` |
| Governance | `ailab_agentic_governance_blocks_total` |

4 alertas nuevas + 3 dashboards Grafana.

## Fases de implementación (10 subfases)

```
28.0 → Simulation-Only Mode           (3-5 días) 🔥 CRÍTICA - OBLIGATORIA
28.1 → Action Intent Layer + Planner  (2-3 días)
28.2 → Governance + Risk Determinista (1-2 días)
28.3 → Approval Gate + Tickets + Explainability (1-2 días)
28.4 → Replay + Plan Diffing          (1-2 días)
28.5 → Verifier (ampliado)            (1-2 días)
28.6 → Executor (readonly primero)    (2-3 días) ⚠️ PROLONGADO
28.7 → Rollback + Transactions        (1-2 días)
28.8 → Sandbox (write + hardening)    (2-3 días)
28.9 → Observabilidad + Dashboards    (1-2 días)
28.10 → Burn-in + Agent Profile Stable (3-5 días)
```

**⚠️ 28.6 executor readonly debe durar al menos 2 semanas antes de pasar a write.**

## Lo que NO se hace todavía

- Multi-agent swarm (sin orquestador maduro)
- Auto-aprobación (viola human-in-the-loop)
- Self-modifying runtime (el agente NUNCA modifica su propio código)
- Bash sin sandbox (siempre ulimit + chroot + path allowlist)
- Sub-agentes recursivos (`max_plan_depth = 1`)
- Docker obligatorio (opcional en 28.8)
- Acceso a internet desde sandbox (solo localhost:1234)

## Resultado esperado

Tras completar FASE 28:

```
✅ LLM genera intents de alto nivel, nunca tool_calls
✅ Planner normaliza intents a acciones reales con paths validados
✅ Risk scoring 100% determinista (reglas fijas)
✅ Dry-run obligatorio con diff preview
✅ Approval con tickets HMAC firmados (plan_hash + dry_run_hash)
✅ Ejecución en sandbox con ulimit + chroot + network isolation
✅ Verifier comprueba checksums, service health, side effects
✅ Rollback transaccional con snapshots pre/post
✅ Replay con diff entre original/normalized/executed plans
✅ Idempotencia garantizada (mismo plan = mismo resultado)
✅ Simulation-only mode para burn-ins seguros
✅ Perfil "agent" marcado stable=true
```
