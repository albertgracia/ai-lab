---
title: "FASE 11 — Cognitive Recall & Supervised Execution"
summary: "Controlled semantic recall with policy engine, persistent mode state, command proposal pipeline, and EXECUTE v1 security sandbox."
order: 25
---

FASE 11 transforma el AI-LAB de "homelab con LLMs" a **cognitive operations runtime**. Introduce memoria semántica controlada por política, modo operativo persistente, pipeline de comandos supervisados y una capa de seguridad EXECUTE v1.

## 11.0 — Controlled Cognitive Recall

`runtime/memory/recall_policy.py`

El recall ya no es "Auto-RAG mágico" sino una **decisión cognitiva**:

```
query → should_recall() → search sources (ordered) → quality gate → advisory block
```

### should_recall(task_type, query)

Decide si merece la pena buscar. Retorna `False` si:
- Query vacía o menor de 10 caracteres
- Query es trivial (saludo, "ok", "gracias")
- El perfil no tiene fuentes configuradas

### Retrieval budget por perfil

| Profile | Max memories | Max chars | Score mínimo | Fuentes |
|---|---|---|---|---|
| **fast** | 1 | 500 | 0.65 | incidents |
| **coding** | 3 | 1500 | 0.55 | incidents, routing_history |
| **reasoning** | 5 | 3000 | 0.45 | incidents, routing_history, cognitive_history |
| **general** | 2 | 1000 | 0.50 | incidents, routing_history |

### Strict source ordering

1. **incidents** — prioridad máxima (eventos operacionales)
2. **routing_history** — histórico de inferencias
3. **cognitive_history** — snapshots cognitivos
4. ~~working_memory~~ — reservado para futuro

Esto prioriza **relevancia operacional** sobre similitud vectorial pura.

### Recall Quality Gate (11.0.6)

Antes de inyectar el bloque de recall, se ejecuta `assess_query()` sobre los hits. Si `contamination_risk > 0.2`, se descarta el recall completamente.

Esto protege contra:
- Drift semántico en embeddings
- Prompt inflation por resultados irrelevantes
- Contaminación por low-score hits

### Advisory format

El bloque inyectado usa tono **advisory**, no autoritario:

```
[SEMANTIC_RECALL_BEGIN]
Experiencias pasadas relevantes (advisory, no verificadas):
  • (incidents) service down rl7900xt ...
  • (routing_history) failover rx9070 ...
[/SEMANTIC_RECALL_END]
```

El LLM trata el recall como **pista**, no como **hecho**.

### Stats en HARD FACTS

```json
"semantic_recall": {
  "enabled": true,
  "collections_used": ["incidents", "routing_history"],
  "matches": 3,
  "avg_score": 0.72,
  "chars_injected": 420
}
```

## 10.1 — Memory Recall API

Endpoints READ-ONLY en Live API (`:8084`):

- `GET /api/memory/search?q=&collection=&limit=` — búsqueda semántica en cualquier colección
- `GET /api/runtime/recall?q=&limit=` — recall cruzado multi-colección
- `GET /api/incidents/search?q=&severity=&limit=` — búsqueda filtrada de incidentes

Backfill inicial: 14 incidents desde `cluster_state` + `routing_history`.

Watchdog hook: `watchdog_incident_hook.py` registra `service_down`, `degraded`, `recovered` automáticamente en cada ciclo.

## 10.2 — Incident Intelligence

- `GET /api/incidents/analytics?days=` — agregación por tipo, severidad, nodo, timeline
- `GET /api/incidents/timeline?days=&bucket=` — series temporales (bucket=day/hour)

Hooks automáticos:
- `routing_history.py`: failures/failovers → incident
- `cognitive_history.py`: budget > 90% → `context_overflow`

## 10.3 — Semantic Search Quality

`runtime/memory/quality_assessment.py`

- `GET /api/memory/quality?q=&collection=&limit=` — precision, noise, contamination_risk
- `GET /api/memory/quality/batch?collection=&limit=` — 10 test queries automáticos por colección

Resultados batch (incidents): `avg_precision=0.78`, `noise=0.0`.

Threshold suggestion: analiza score distribution gaps para encontrar cutoff points naturales.

## 10.4 — Pattern Learning

`runtime/memory/pattern_learner.py`

Detección de patrones en incidents:
- Fallos repetidos en mismo nodo
- Horas pico de incidentes
- Tendencias de latencia (empeorando/mejorando/estable)

## 11.1 — Persistent Mode State

`runtime/modes/mode_manager.py` + `runtime/state/current_mode.json`

Separa **runtime cognition** de **runtime authority**:

- `read_mode()`, `write_mode()`, `can_transition()`, `requires_reason()`
- Transiciones válidas: `readonly → plan → build → execute`
- `plan → execute` permitido directamente (con `reason`)
- `GET /api/mode`, `POST /api/mode/switch?mode=&reason=`

System prompt dinámico: `router_api.py::build_system_context()` lee `current_mode.json` y ajusta el prompt. `context_shaper.py` inyecta el modo actual en HARD FACTS.

## 11.2 — Command Proposal Pipeline

Pipeline completo de comandos supervisados:

1. **Proponer**: `POST /api/commands/propose` — command + reason + risk
2. **Listar pendientes**: `GET /api/commands/pending`
3. **Aprobar**: `POST /api/commands/approve?id=` — ejecuta vía `sandbox_runner`
4. **Rechazar**: `POST /api/commands/reject?id=`

Proposals almacenadas en `runtime/state/command_proposals.jsonl`.

Audit dual: Qdrant incidents + `governance_audit.jsonl`.

## 11.6 — EXECUTE v1 Security Policy

`runtime/execution/execute_v1_policy.py`

EXECUTE v1 SOLO permite:
- Archivos temporales (`/tmp/ai-lab/`)
- Scripts sandbox
- Dry-run
- Comandos readonly
- Análisis y validación
- Generación de planes

**PROHIBIDO:**
- ❌ Docker
- ❌ systemctl (except status)
- ❌ Network (curl solo localhost/health)
- ❌ Filesystem fuera de `/tmp/ai-lab/` y `/opt/ai-lab/`
- ❌ Hyper-V, UniFi, Cloudflare
- ❌ sudo, chmod, mount, dd, iptables, virsh
- ❌ git push/commit, ssh, scp, kill, apt, pip/npm install
- ❌ `shell=True` (nunca)

**Whitelist:** `ls`, `cat`, `echo`, `head`, `tail`, `wc`, `grep`, `find`, `pwd`, `date`, `whoami`, `id`, `df -h`, `free -h`, `ps aux`, `uname`, `uptime`, `env`. `python3` solo en dry-run.

Validación en dos capas: `sandbox_runner.py` y `live_api.py` approve handler.

## Arquitectura General

```
FASE 11: Cognitive Operations Runtime

  LLM ──→ router_api.py
              │
              ├── build_system_context() → mode dinámico
              │
              └── context_shaper.py
                      │
                      ├── HARD FACTS (JSON + texto)
                      │     └── semantic_recall stats
                      │
                      └── execute_recall() ← recall_policy.py
                              ├── should_recall() gate
                              ├── search sources (ordered)
                              ├── quality gate (contamination)
                              └── advisory block

  Live API (:8084)
      ├── /api/mode/switch        ← mode_manager.py
      ├── /api/commands/propose   ← JSONL pipeline
      ├── /api/commands/approve   ← sandbox_runner.py
      │                              └── execute_v1_policy.py
      └── /api/commands/reject

  Seguridad:
      ├── execute_v1_policy.py    (global whitelist)
      ├── capability_guard.py     (mode check)
      └── profile loader          (per-user allow_shell)
```

## Archivos creados

| Archivo | Propósito |
|---|---|
| `runtime/memory/recall_policy.py` | Controlled recall engine (policy, budgets, quality gate) |
| `runtime/memory/quality_assessment.py` | Precision, noise, contamination_risk metrics |
| `runtime/memory/backfill_incidents.py` | Seed incidents from cluster_state + routing_history |
| `runtime/memory/watchdog_incident_hook.py` | Auto-record incidents from watchdog checks |
| `runtime/memory/pattern_learner.py` | Pattern detection (repeated failures, peak hours, trends) |
| `runtime/modes/mode_manager.py` | Persistent mode state with transition validation |
| `runtime/execution/execute_v1_policy.py` | EXECUTE v1 whitelist, blocked commands, dry-run rules |

## Tools — Pre-commit Hook (Astro build check)

`scripts/pre-commit.sh`

Para evitar errores tontos (como romper el template HTML de una página Astro), cada commit que toque `apps/ialab-docs/` ejecuta automáticamente `npm run build`. Si el build falla, el commit se bloquea.

```bash
# Instalación (una vez por clon):
ln -sf ../../scripts/pre-commit.sh .git/hooks/pre-commit

# Bypass (emergencia):
git commit --no-verify
```

El hook está versionado en `scripts/pre-commit.sh` y documentado en `AGENTS.md`.

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `runtime/memory/qdrant_store.py` | search, recall, store_embedding, search_collection |
| `runtime/state/live_api.py` | Mode switch + command proposal/approve/reject endpoints |
| `runtime/llm/router_api.py` | Dynamic system prompt via build_system_context() |
| `runtime/agent/context_shaper.py` | HARD FACTS mode key + semantic_recall stats injection |
| `runtime/execution/sandbox_runner.py` | EXECUTE v1 policy validation |
| `runtime/cognitive/cognitive_history.py` | Hook: budget > 90% → incident |
| `runtime/routing/routing_history.py` | Hook: failures/failovers → incident |
