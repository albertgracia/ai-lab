# Workspace Rules - OpenCode NAS

## Contexto Del Workspace

- Este workspace vive en un recurso SMB montado en Ubuntu como `/mnt/opencode`.
- El recurso Windows es `//192.168.1.200/opencode`.
- Para abrir OpenCode en este workspace, usar `opencode-nas`.
- La capa local de agentes está en `.agent/` y procede de `/opt/ai-lab/.agent`.
- Usar `.agent/BOOTSTRAP.md` como entrada principal de la capa de agente.

## Datos De OpenCode

- No mover ni copiar al SMB los datos globales de OpenCode.
- Mantener configuración, auth, sesiones y chats en:
  - `~/.config/opencode`
  - `~/.local/share/opencode`
  - `~/.cache/opencode`
- No guardar `auth.json`, bases SQLite de OpenCode ni historiales de chat en `/mnt/opencode` salvo petición explícita.

## Seguridad En El NAS

- Pedir confirmación antes de borrar, mover o reestructurar archivos en `/mnt/opencode`.
- Evitar operaciones destructivas o masivas sin backup o confirmación explícita.
- Mantener cambios pequeños, reversibles y verificables.

## AI-LAB Real

- El repositorio real de AI-LAB está en `/opt/ai-lab`.
- No asumir que `/mnt/opencode` es el repo productivo salvo que el usuario lo confirme.
- Para trabajos sobre AI-LAB, verificar primero si la tarea debe ejecutarse en `/opt/ai-lab` o en este workspace SMB.
- Responder en español.
- No inventar servicios, puertos, rutas, dominios ni configuración; comprobarlos en archivos o con comandos de solo lectura antes de actuar.

## Dominios Y Servicios Relevantes

- Público Astro: `https://ai-lab.labrazahome.com`
- Privado Astro local: `https://blog-ai-lab.labrazahome.com`
- Métricas live SSR: `https://metricas.labrazahome.com`
- `ailab-docs`: Astro preview en `:4322`
- `ailab-metrics`: Next.js SSR en `:3010`
- `ailab-router`: router API en `:8083`
- `ailab-live-api`: live API en `:8084`

## Regla De Publicación Astro / AI-LAB Docs

Cuando se modifique `apps/ialab-docs/` en `/opt/ai-lab`:

1. Ejecutar build antes de considerar terminado el cambio:

   ```bash
   npm run build
   ```

   desde:

   ```bash
   /opt/ai-lab/apps/ialab-docs
   ```

2. Si el cambio afecta al sitio privado local `blog-ai-lab.labrazahome.com`, reiniciar:

   ```bash
   sudo systemctl restart ailab-docs
   ```

3. Verificar localmente:

   ```bash
   curl -I http://127.0.0.1:4322/
   ```

4. Si el cambio debe llegar al público `ai-lab.labrazahome.com`, hacer commit y push en `/opt/ai-lab`.

5. Astro público: asumir siempre `GitHub -> Cloudflare Pages`; no pedir ni documentar reinicio local porque el despliegue no usa `ailab-docs`.

6. Astro privado: si el cambio toca `blog-ai-lab.labrazahome.com`, el flujo correcto es `npm run build` + `sudo systemctl restart ailab-docs` + `curl -I http://127.0.0.1:4322/`.

7. Cloudflare Pages despliega automáticamente desde GitHub tras el push.

8. No commitear `dist/`, `runtime/state`, `__pycache__`, snapshots ni datos generados salvo petición explícita.

9. Si se modifican enlaces públicos relacionados con telemetría u operaciones, preferir apuntar a `metricas.labrazahome.com`:
   - `/ops` -> `https://metricas.labrazahome.com/ops`
   - `/status` -> `https://metricas.labrazahome.com`
   - GPU telemetry -> `https://metricas.labrazahome.com/gpus`
   - Runtime telemetry -> `https://metricas.labrazahome.com/runtime`

**10. Regla de sincronización Astro → Metrics:** Cuando se actualice documentación en Astro que afecte a fases, modelos, arquitectura o estado del runtime, verificar que `https://metricas.labrazahome.com` refleje los datos correctos. Si la métrica live depende de los cambios (nuevos modelos, nuevas fases, nuevos servicios), actualizar también `/opt/ai-lab/apps/metrics-dashboard/` siguiendo la Regla de Métricas Live.

## Regla De Métricas Live

- `metricas.labrazahome.com` usa Next.js SSR local, no Cloudflare Pages ni Astro SSG.
- La app está en `/opt/ai-lab/apps/metrics-dashboard`.
- Después de cambiarla:
  1. Ejecutar `npm run build` en `/opt/ai-lab/apps/metrics-dashboard`.
  2. Reiniciar `ailab-metrics`.
  3. Verificar:
     - `https://metricas.labrazahome.com`
     - `https://metricas.labrazahome.com/ops`
     - `https://metricas.labrazahome.com/gpus`
     - `https://metricas.labrazahome.com/runtime`

## Historial de Conversación

- `ai-lab/conversation-history.md` contiene el historial completo de la sesión actual con objetivos, decisiones, FASEs implementadas, estado de servicios y next steps.
- Leer este archivo al inicio de cada sesión para recuperar contexto sin depender del historial SQLite de OpenCode.

## Capa .agent

- Priorizar las fuentes indicadas por `.agent/BOOTSTRAP.md`.
- Usar `.agent/OPENCODE_PROMPT.md` como guía de comportamiento para AI-LAB.
- Cuando se implemente algo en el runtime, separar workflows por modo/capacidad antes de mezclar contexto o prompts.
- Si la tarea es ambigua, preguntar antes de ejecutar cambios.
- Si la tarea encaja con un workflow, consultar `.agent/workflows/`.
- Si la tarea encaja con un especialista, consultar `.agent/agents/` y las skills mínimas necesarias.

## AI-LAB Onboarding Para Agentes Nuevos

- Antes de actuar, leer en este orden:
  - `conversation-history.md`
  - `.agent/BOOTSTRAP.md`
  - `.agent/OPENCODE_PROMPT.md`
  - `AGENTS.md` del workspace actual
  - workflows relevantes en `.agent/workflows/`
  - agentes/skills relevantes en `.agent/agents/`
- No asumir nada:
  - no asumir rutas
  - no asumir puertos
  - no asumir servicios
  - no asumir dominios
  - no asumir modos
  - no asumir configuraciones
  - verificar siempre con lectura sola
- AI-LAB tiene separación estricta por workflows:
  - `cognitive`
  - `operational`
  - `tool`
  - `execute`
  - no mezclar contexto entre ellos sin una razón clara
- Regla de contexto:
  - no construir `HARD_FACTS` gigante por defecto
  - usar el contexto mínimo necesario para la intención real
  - si la tarea es un saludo o small talk, responder breve y sin formato pesado
  - si la tarea es `tool_use`, priorizar tool calls estructurados y contexto mínimo
  - si la tarea es análisis operativo, usar contexto liviano y observable
  - si la tarea implica cambios, pasar por modo gobernado
- Regla de seguridad:
  - no inventar estado del sistema
  - si un dato no está verificado, marcarlo como `NO DISPONIBLE`
  - no ejecutar acciones destructivas
  - no proponer comandos peligrosos
  - no usar `sudo`, `reboot`, `rm -rf`, `shutdown`, `systemctl restart/stop` ni equivalentes salvo aprobación explícita y workflow adecuado
- Regla de validación:
  - cambios pequeños
  - cambios reversibles
  - cambios verificables
  - compilar/probar antes de dar por cerrado el cambio
  - no considerar terminado algo sin comprobar el comportamiento real
- Regla de documentación:
  - si cambia runtime, documentarlo en Astro
  - si cambia observabilidad, documentarlo en runbook y/o fase
  - mantener el contenido alineado con el comportamiento real
  - no documentar hipótesis como si fueran hechos
- Regla de respuesta:
  - responder en español
  - ser directo
  - no rellenar con explicación innecesaria
  - si falta contexto, preguntar antes de asumir
- Regla de publicación:
  - si se modifica `apps/ialab-docs/`, ejecutar build antes de cerrar
  - verificar rutas nuevas
  - reiniciar el servicio si aplica
  - no commitear artefactos generados salvo petición explícita
- Regla de operación del agente:
  - si el agente no conoce AI-LAB, debe leer este onboarding antes de tocar nada
  - si el problema encaja en un workflow existente, usar ese workflow
  - si no encaja, pedir aclaración o proponer el workflow correcto antes de actuar

## Git Discipline & Checkpoint Integrity Rule

No tag without commit. No phase closed with dirty working tree. A partir de ahora, ningún checkpoint, tag o fase se considera cerrada si el código no está commiteado.

### Regla obligatoria

1. Antes de crear cualquier tag:
   - ejecutar `git status --short`
   - ejecutar `git diff --stat`
   - confirmar que los cambios de la fase están incluidos en un commit real

2. Prohibido crear tags sobre commits antiguos si hay cambios pendientes en working tree.

3. Cada fase estable debe tener:
   - commit semántico propio
   - tag apuntando a ese commit
   - tests ejecutados
   - resumen en AGENTS.md
   - documentación o nota de fase si aplica

4. Si hay cambios de varias fases acumulados sin commit:
   - NO crear nuevo tag
   - NO seguir implementando nuevas fases
   - primero separar cambios en commits por fase siempre que sea posible

5. Antes de cualquier fase nueva ejecutar:
   ```bash
   git status --short
   git log --oneline --decorate -5
   git tag --points-at HEAD
   ```

6. Criterio de cierre de fase:

   Una fase solo está cerrada si:
   - tests PASS
   - build PASS si aplica
   - working tree revisado
   - commit creado
   - tag creado sobre el commit correcto
   - `git status --short` no contiene cambios relacionados con esa fase

7. Naming recomendado:
   - Commit: `feat(runtime): FASE XX.Y description`
   - Burn-in: `test(runtime): FASE XX.Y-B burn-in validation`
   - Fix: `fix(runtime): FASE XX.Y-Z short description`
   - Tag: `CP-XX.Y-DESCRIPTIVE-STABLE`

8. Si se detecta inconsistencia tag/commit:
   - parar implementación
   - crear backup patch: `git diff > /tmp/ailab-emergency-backup.patch`
   - reconstruir commits semánticos
   - mover o recrear tags correctamente
   - documentar la corrección en AGENTS.md

Esta regla tiene prioridad sobre velocidad de implementación. La trazabilidad Git forma parte del runtime governance.

---

# Runtime Configuration Philosophy

## Principio general

AI-LAB evoluciona desde un runtime hardcoded hacia un runtime declarativo y observable. El objetivo **no** es eliminar todo el código defensivo. Los guards de seguridad siguen siendo obligatorios. Los defaults operativos deben salir del código y pasar a perfiles declarativos. Los hardcodes de seguridad **no** son deuda técnica.

## Jerarquía oficial de configuración

```
cliente explícito
→ cognitive profile
→ config declarativa
→ defaults seguros runtime
→ guards hardcoded
```

| Capa | Significado | Ejemplo |
|------|-------------|---------|
| cliente explícito | El valor que envía OpenCode/OpenWebUI en el payload | `max_tokens: 32` |
| cognitive profile | El perfil declarativo en `runtime/profiles/*.json` | `chat_profile.json → max_tokens: 512` |
| config declarativa | `runtime/prompts/` y `manifest.json` | `chat_prompt.md` |
| defaults seguros runtime | Valores que el código inyecta si nada anterior los definió | `temperature: 0.4` |
| guards hardcoded | Protecciones que **siempre** se aplican | `pop("reasoning")` para modelos que no lo soportan |

## Distribución oficial de responsabilidades

### `.env`

Solo configuración de despliegue y entorno:

```env
AI_LAB_ENV=production
AI_LAB_DEFAULT_MODEL=qwen/qwen2.5-coder-14b-instruct
AI_LAB_LMSTUDIO_URL=http://192.168.1.50:1234/v1
AI_LAB_ENABLE_PROFILES=true
```

**NO** usar `.env` para: `max_tokens` por perfil, prompts, temperatures específicas, políticas cognitivas, tools policies.

---

### `runtime/prompts/*.md`

**Responsabilidad:** lenguaje y comportamiento textual.

Ejemplos: `chat_prompt.md`, `coding_prompt.md`, `reasoning_prompt.md`.

**NO** incluir: `max_tokens`, tools, policies, routing, modelos.

---

### `runtime/profiles/*.json`

**Responsabilidad:** policy bundles cognitivos.

Cada perfil define: prompt, modelo, inference defaults, memory policy, reasoning policy, tools policy, streaming policy, output policy.

```json
{
  "profile": "chat",
  "prompt": "chat_prompt.md",
  "model": { "default": "qwen2.5-coder-14b-instruct" },
  "inference": { "max_tokens": 512, "temperature": 0.4 },
  "tools": { "allowed": false },
  "memory": { "policy": "light" },
  "reasoning": { "policy": "disabled" }
}
```

---

### Código runtime

El código debe contener **SOLO**:

- Guards de seguridad
- Validación
- Compatibilidad
- Circuit breakers
- Fallback críticos
- Protecciones específicas de modelo

Ejemplos válidos:

- Stripping de `reasoning` no soportado por el modelo
- Fallback si modelo no cargado (`Model unloaded`)
- Clamp de `max_tokens` peligrosos (>2048)
- Sanitización de tools peligrosas
- Guardia `qwen2.5-coder-14b`: pop de `reasoning`, `tool_choice`, `tools`

> **Un hardcode de seguridad NO es deuda técnica.**

## Cómo evitar semantic leakage y runtime drift

| Problema | Causa | Solución |
|----------|-------|----------|
| **Semantic leakage** | Prompt cognitivo contamina ruta ligera | Separar prompts en `runtime/prompts/`, cargar por perfil |
| **Runtime drift** | Hardcode en gateway difiere del router | Una sola fuente de verdad: `runtime/profiles/` |
| **Tool contamination** | Tools heredadas de payload global | Perfil `tools.allowed: false` + `apply_profile()` |
| **Context inflation** | `max_tokens` global pisa valor del perfil | Jerarquía cliente > perfil > default |
| **Silent regression** | Hardcode eliminado sin observabilidad | 3 canales: stdout + audit + Prometheus |

## Objetivo arquitectónico

AI-LAB separa 7 capas independientes:

```
Prompts       → lenguaje          (runtime/prompts/)
Profiles      → comportamiento    (runtime/profiles/)
Policies      → permisos          (runtime/policies/ — FASE 22)
Memory        → contexto          (runtime/memory/ — FASE 23)
Models        → inferencia        (runtime/models/)
Routing       → decisión          (runtime/llm/ + router/)
Observability → trazabilidad      (runtime/telemetry/ + audit/)
```

## Estado actual de fases

```
FASE 20A → modelos estabilizados                        ✅
FASE 20B → wrappers legacy limpiados                    ✅
FASE 20C → prompts declarativos (runtime/prompts/)      ✅
FASE 21A → perfiles cognitivos (runtime/profiles/)      ✅
FASE 21A.1 → observabilidad de perfiles                 ✅
FASE 21B → de-hardcoding progresivo (26 eliminados)     ✅ CP-21B-STABLE
FASE 22A → tool runtime policies (3 modos)              ✅
FASE 22B → bash sanitizer + confirmation gate 428       ✅
FASE 22B.1 → fix clasificador greetings                 ✅
FASE 23A → memory architecture (3 policies)             ✅
FASE 23B → quality gate + contamination guard           ✅
FASE 23B.1 → 8 skip reasons + replay inspector          ✅
FASE 24 → cognitive traceability + audit log            ✅
FASE 25 → OpenCode production profile                   ✅
FASE 26 → OpenWebUI production profile                  ✅
FASE 26.1 → burn-in 280 reqs, 83% éxito                 ✅
FASE 26.1.1 → completion finalization                   ✅
FASE 26.1.2 → report routing (heavy/light)              ✅
FASE 26.1.3 → grounding discipline (NO DISPONIBLE)      ✅
FASE 26.2 → UX & cognitive quality                      ✅
FASE 27 → runtime stabilization                         ✅ CP-27-RUNTIME-STABILIZATION
FASE 27.1-B → baseline observability burn-in            ✅
FASE 27.3 → quality guard observacional                 ⏭
FASE 27.4 → replay studio enrichment                    ⏭
FASE 28 → governed agentic runtime                       📋 plan técnico completado (v2.1)
FASE 28.0 → simulation-only mode                        ✅
FASE 28.1 → planner runtime skeleton                     ✅ CP-28.1-PLANNER-RUNTIME-SKELETON-STABLE
FASE 28.2 → readonly executor runtime                    ✅ CP-28.2-READONLY-EXECUTOR-STABLE
FASE 28.2-B → burn-in 74/74 tests                        ✅ CP-28.2-B-READONLY-BURNIN-STABLE
FASE 28.3 → sandbox write runtime                        ✅ CP-28.3-SANDBOX-WRITE-STABLE
FASE 28.3-B → burn-in & rollback validation              ✅ CP-28.3-B-SANDBOX-WRITE-BURNIN-STABLE
FASE 29.0 → gateway hardening ✅
FASE 29.2 → real streaming ✅ CP-29.2-B-STREAMING-BURNIN-STABLE
FASE 29.3 → three-model runtime ✅ CP-29.3-THREE-MODEL-RUNTIME-STABLE
FASE 29.3.1 → routing tightening ✅
FASE 29.3.2 → SLO baseline ✅
FASE 29.4 → SLO enforcement & adaptive runtime protection ✅ CP-29.4-SLO-ENFORCEMENT-STABLE
FASE 29.4.1 → report runtime grounding fix ✅
FASE 29.4.2 → report presentation fix                     ✅ CP-29.4.2-REPORT-PRESENTATION-STABLE
FASE 29.4.3 → runtime identity grounding                  ✅ CP-29.4.3-RUNTIME-IDENTITY-GROUNDING-STABLE
FASE 29.4.4 → error taxonomy & failure attribution        ✅ CP-29.4.4-ERROR-TAXONOMY-STABLE
FASE 29.4.4-B → error taxonomy burn-in (147/148)          ✅ CP-29.4.4-B-ERROR-TAXONOMY-BURNIN-STABLE
FASE 29.4.4-C → SLO health endpoint always-on             ✅ CP-29.4.4-C-SLO-HEALTH-ENDPOINT-STABLE
FASE 29.4.4-D → parallel tool call hardening                ✅ CP-29.4.4-D-PARALLEL-TOOLCALL-HARDENING-STABLE
FASE 30A → runtime state foundation & maturity descriptors  ✅ CP-30A-RUNTIME-STATE-FOUNDATION-STABLE
FASE 30B → model state awareness (active/loaded/discoverable) ✅ CP-30B-MODEL-STATE-AWARE-STABLE
```

Tags git: 29 tags desde `CP-21B-STABLE` hasta `CP-30B-MODEL-STATE-AWARE-STABLE`.

**Deuda saldada:** FASE 29.4.4-C — `/slo/health` ahora responde 200 siempre, con payload disabled cuando enforcement=false.

## Próximo: Runtime Maturity Before Multi-GPU (Prioridad cambiada 20/05/26)

**Checkpoint actual:** "Runtime Operational Identity"
**Estado:** 🟢 Runtime estable | 🟢 Governance estable | 🟢 Taxonomy estable | 🟢 Burn-in estable | 🟢 Runtime state foundation (FASE 30A) | 🟢 Model state awareness (FASE 30B) | 🟡 Degraded mode (30C) pendiente | 🔵 Multi-GPU postergado

**Razón:** FASE 30A + 30B completadas — runtime tiene identidad operacional y estado de modelos. RULE-30B-1 a 30B-6 establecidas. `ModelStatusTracker` con TTL, alias normalization, DISABLED priority. 29 tags git.

### FASES PRIORITARIAS (próxima sesión)

1. **Runtime semantic maturity** — descriptors de estado runtime
2. **Operational reporting discipline** — reportes NOC con semántica operacional
3. **Runtime topology awareness** — rol del nodo en la topología
4. **Active vs inventory vs discoverable separation** — qué modelo está cargado, cuál activo, cuál disponible
5. **Cognitive route semantics** — semántica operacional por route-family
6. **Runtime-state descriptors** — estado explícito del runtime (fase, modo, degradación)
7. **Governance visibility refinement** — visibilidad de decisiones governance
8. **Failure-domain classification** — clasificación de dominios de fallo
9. **Single-node degraded-mode explicit state** — estado degradado explícito en nodo único

### Multi-GPU pospuesto hasta

- Runtime maturity estable
- Report consistency estable
- Cognitive topology awareness estable
- Governance semantics cerradas
- Scheduler contracts definidos

### Multi-GPU futuro (cuando se reactive)

- RX7900XT recovery
- qwen32b activation
- cognitive route placement
- scheduler v1
- warm pool
- queue arbitration
- failover chains
- VRAM-aware routing

---



## Stack de observabilidad (192.168.1.40)

### Arquitectura física

| Componente | Host | Puerto | Rol |
|------------|------|--------|-----|
| Prometheus | 192.168.1.40 | 9090 | Scraping + alertas + TSDB |
| Grafana | 192.168.1.40 | 3000 | Dashboards + provisioning |
| Prometheus config | `/home/albert/docker/monitorizacion/prometheus/` | — | `prometheus.yml`, scrape targets |
| Alert rules | `/home/albert/docker/monitorizacion/prometheus/config/rules/` | — | `ai-lab-route-family-alerts.yml` |
| Grafana provisioning | `/home/albert/docker/monitorizacion/grafana/provisioning/` | — | Dashboards JSON auto-load |

### Scrape targets AI-LAB

| Target | Endpoint | Labels |
|--------|----------|--------|
| `ai-lab-gateway` | 192.168.1.30:8008/metrics | `role=gateway` |
| `ai-lab-router` | 192.168.1.30:8083/metrics | `role=router` |
| `ai-lab-live-api` | 192.168.1.30:8084/metrics | `role=live-api` |
| `ai-lab-cadvisor` | 192.168.1.30:8081 | Container metrics |
| `ai-lab-node` | 192.168.1.30:9100 | Host metrics (node_exporter) |
| `ai-lab-gpu-rx9070` | 192.168.1.50:9182 | GPU RX9070 metrics |
| `ai-lab-gpu-metrics` | 192.168.1.50:9183 | GPU compute metrics |
| `ai-lab-gpu-rx7900xt` | 192.168.1.60:9182 | **DOWN** — nodo apagado |
| `ai-lab-gpu-metrics` | 192.168.1.60:9183 | **DOWN** — nodo apagado |
| `cloudflare-tunnel` | cloudflare-tunnel:2000 | Tunnel metrics |

### Métricas clave (100+ métricas `ailab_*`)

| Categoría | Métrica | Tipo |
|-----------|---------|------|
| Perfiles | `ailab_profile_total`, `ailab_route_family_total` | Counter |
| Latencia | `ailab_first_token_latency_ms` (TTFB), `ailab_request_total_latency_ms`, `ailab_completion_stream_duration_ms` | Histogram |
| Tools | `ailab_tool_call_total`, `ailab_tool_empty_arguments_total`, `ailab_tool_fastpath_total` | Counter |
| Memoria | `ailab_memory_recall_total`, `ailab_memory_chars_injected`, `ailab_memory_items_total`, `ailab_memory_contamination_risk`, `ailab_memory_quality_score` | Counter/Histogram |
| Calidad | `ailab_quality_score`, `ailab_hallucination_risk` | Histogram |
| Streaming | `ailab_stream_chunks_total`, `ailab_stream_stalls_total`, `ailab_stream_finish_inconsistent_total` | Counter |
| GPU | `ailab_gpu_active_requests`, `ailab_gpu_estimated_utilization_pct` | Gauge |
| Checksums | `ailab_prompt_checksum_changes_total` | Counter |
| Cold starts | `ailab_cold_start_total` | Counter |
| SLO (FASE 29.4) | `ailab_runtime_slo_state`, `ailab_runtime_degradation_level`, `ailab_runtime_timeout_rate`, `ailab_runtime_vram_pressure`, `ailab_runtime_gpu_pressure`, `ailab_runtime_priority_lane_total`, `ailab_runtime_emergency_mode_total`, `ailab_runtime_qwen_protection_total`, `ailab_runtime_llama_fastpath_forced_total`, `ailab_runtime_stream_backlog`, `ailab_circuit_breaker_state`, `ailab_slo_violations_total`, `ailab_runtime_qwen_parallel`, `ailab_runtime_concurrent_streams` | Gauge/Counter |
| Report grounding (FASE 29.4.1) | `ailab_report_grounding_total`, `ailab_report_missing_fields_total`, `ailab_report_target_ip_total`, `ailab_report_ungrounded_total` | Counter |

### Alertas (19 reglas activas)

Todas con health=ok. Cubren: regresión de rutas, fuga de tool_fastpath, explosión cognitive, errores, governance, memory fallback, contamination, budget, cold starts, dominance, context caps.

**Alarmas rojas (STOP burn-in):**
- `tool_fastpath` leakage > 0
- `governance` unexpected blocks > 0
- Empty responses sostenidos
- `HARD_FACTS` accidental
- Memory recall en minimal
- Prompt inflation runaway
- Finish inconsistency alta
- Stream stalls repetidos

### Dashboards Grafana (15 dashboards, carpeta `AI-LAB`, datasource UID `PBFA97CFB590B2093`)

TIER 1 (operación diaria): latencia, perfiles, tools, errores, GPU, tokens.
TIER 2 (troubleshooting): memory, streaming, quality, cold starts, checksums.

### Troubleshooting común de métricas

**Problema: paneles Grafana muestran "Sin datos"**

AI-LAB tiene **3 procesos Python independientes**, cada uno con su propio registry Prometheus. Solo el gateway (:8008) recibe tráfico de chat. El router (:8083) y live-api (:8084) tienen los mismos counters registrados pero nunca los incrementan.

**Diagnóstico:**
```bash
# Verificar qué endpoint tiene datos reales
curl -s http://192.168.1.30:8008/metrics | grep "ailab_route_family_total"
curl -s http://192.168.1.30:8083/metrics | grep "ailab_route_family_total"
curl -s http://192.168.1.30:8084/metrics | grep "ailab_route_family_total"
```

**Fix canónico para métricas de chat:** las métricas que solo emite el gateway NO deben ser "primeadas" (inc(0)) en router ni live-api. Esto evita que series con valor 0 contaminen las queries PromQL de Grafana.

- `runtime/llm/router_api.py` → NO llamar `prime_route_family_metrics()`
- `runtime/state/live_api.py` → NO llamar `prime_route_family_metrics()`
- `runtime/gateway/openai_gateway.py` → SÍ llamar `prime_route_family_metrics()` (único proceso con tráfico real)

---

## Arquitectura de servicios AI-LAB

### Procesos en ejecución (192.168.1.30)

| Servicio | Puerto | Proceso | Tráfico |
|----------|--------|---------|---------|
| `ailab-gateway` | 8008 | `openai_gateway.py` (HTTP simple) | **Único entrypoint de chat** |
| `ailab-router` | 8083 | `router_api.py` (FastAPI/uvicorn) | Solo API interna (/status, /profiles, /replay) |
| `ailab-live-api` | 8084 | `live_api.py` (HTTP simple) | API de estado, embeddings |
| `ailab-docs` | 4322 | Astro preview | Documentación |
| `ailab-metrics` | 3010 | Next.js SSR | Dashboard público |
| `ailab-heartbeat` | — | Heartbeat persistente | Latido de cluster |
| `ailab-live-state` | — | State snapshot | Snapshot periódico |
| `ailab-runner` | — | GitHub Actions Runner | CI/CD |
| `ailab-traefik` | 80/443 | Traefik proxy | Reverse proxy (exited, gestiona certificados) |

### Flujo de una petición de chat

```
Cliente (OpenCode/OpenWebUI)
  → ailab-gateway (:8008) → POST /v1/chat/completions
    → inject_agent_context()
      → classify_chat_route() → family + variant
      → apply_profile() → configura modelo, tokens, temp
      → SLO degradation check → forced llama / qwen protection
      → memory injection (si flag activo + política lo permite)
      → quality/hallucination scoring (post-respuesta)
    → LM Studio (192.168.1.50:1234)
    → SLO state evaluation → adaptive concurrency → circuit breaker update
    → respuesta al cliente
```

**El router (:8083) NO procesa tráfico de chat en producción.** Su endpoint `POST /v1/chat/completions` existe (legacy) pero `ailab_router_chat_requests_total = 0`.

### SLO Enforcement (FASE 29.4)

AI-LAB evoluciona de SLO pasivo a runtime auto-protegido vía `runtime/slo/`:

- **`RuntimeSLOManager`** + `SLOState` (deques sliding window para TTFB, timeouts, GPU/VRAM). Estados GREEN/YELLOW/RED.
- **`DegradationManager`**: 4 niveles (NORMAL/LIGHT/HEAVY/EMERGENCY) con anti-flapping (30s min entre transiciones) y cooldown.
  - `LEVEL 1`: forced llama routing + qwen protection + qwen parallel 2→1
  - `LEVEL 2/3`: observables pero NO auto-activos todavía
- **`AdaptiveConcurrency`**: parallel dinámico para qwen (2→1 bajo presión GPU>90%) y llama (3→2).
- **`PrioritySlotManager`**: Lane 1 (critical: greetings, lightweight) con 2 slots reservados. Lane 2/3 comparten pool.
- **`ModelCircuitBreaker`**: 3 fallos/60s → OPEN. Observable — no bloquea requests en esta fase.
- **Feature flags**: `AI_LAB_ENABLE_SLO_ENFORCEMENT=false`, `AI_LAB_SLO_DRY_RUN=true` por defecto.
- **Endpoint**: `GET /slo/health` devuelve estado SLO completo.
- **14 métricas nuevas**: `ailab_runtime_slo_state`, `ailab_runtime_degradation_level`, `ailab_runtime_timeout_rate`, `ailab_runtime_vram_pressure`, `ailab_runtime_gpu_pressure`, `ailab_runtime_priority_lane_total`, `ailab_runtime_emergency_mode_total`, `ailab_runtime_qwen_protection_total`, `ailab_runtime_llama_fastpath_forced_total`, `ailab_runtime_stream_backlog`, `ailab_circuit_breaker_state`, `ailab_slo_violations_total`, `ailab_runtime_qwen_parallel`, `ailab_runtime_concurrent_streams`.
- **Dashboard**: "AI-LAB Runtime Protection" con 14 paneles.
- **DRY RUN obligatorio primero**: enforcement real desactivado hasta validar dashboards.

### Route tightening (FASE 29.3.1)

El routing es 100% determinista. El LLM **nunca** decide qué modelo usar.

- **48 greeting markers** en `tool_request_classifier.py` detectan saludos, trivia ligera, preguntas personales simples → `llama-3.1-8b`
- **`is_lightweight_prompt()`**: heurística que mide pesos de greeting markers vs total chars; si ≥30% y <150 chars → llama-3.1-8b
- **9 `QWEN_ESCALATION_REASONS`**: coding real, arquitectura, debugging, análisis técnico profundo → `qwen2.5-coder-14b` solo si hay razón de escalado
- **Métricas**: `ailab_greeting_fastpath_total`, `ailab_qwen_escalation_total`, `ailab_llama_fastpath_total`

Regla: si no hay QWEN_ESCALATION_REASON y es lightweight → llama-3.1-8b. Si no es lightweight y hay QWEN_ESCALATION_REASON → qwen2.5-14b.

### Gateway hardening (FASE 29.0)

- **`process_guard.py`**: PID lock singleton (previene 2 instancias), rogue uvicorn killer en prebind
- **SIGTERM handler**: graceful shutdown con flush de métricas pendientes
- **Port hardening**: router_api.py `if PORT==8008: exit(1)` — el router no puede ocupar el puerto del gateway
- **Systemd**: `StartLimitBurst=6` previene fork storms si el gateway crashea repetidamente
- **15 métricas lifecycle**: startup, shutdown, health, lock contention, rogue kills

### Real streaming (FASE 29.2)

- `relay_stream()` con `requests.post(stream=True)` → relay directo de chunks SSE desde llama.cpp
- Backpressure: max 3 streams concurrentes
- Timeout 4 capas: connect=5s / chunk=20s / idle=30s / completion=300s
- TTFB ~1.5s (vs ~12s con fake SSE), ~79 chunks reales vs 2 sintéticos
- Rollback vía `AI_LAB_REAL_STREAMING=false` → fake SSE legacy

### SLO baseline (FASE 29.3.2)

45-min burn-in, 306/306 OK (100%):

| Métrica | Valor | Target |
|---------|-------|--------|
| TTFB p50 | 804ms | <1.2s |
| TTFB p95 | ~3s | <5s |
| Success rate | 99.2-100% | >99% |
| Latency p95 | ~45s | <60s |
| Gateway crashes | 0 | 0 |
| Orphan streams | 0 | 0 |

### Backend de inferencia

| Modelo | Host | VRAM | Uso |
|--------|------|------|-----|
| `llama-3.1-8b-instruct` | 192.168.1.50:1234 | RX9070 16GB | Minimal, greetings, observe, light prompts |
| `qwen2.5-coder-14b-instruct` | 192.168.1.50:1234 | RX9070 16GB | Coding, report, architecture, reasoning, creative |
| `nomic-embed-text-v1.5` | 192.168.1.50:1234 | RX9070 16GB | Embeddings, semantic recall |
| `qwen3.6-27b` | 192.168.1.50:1234 | RX9070 16GB | **DESACTIVADO** — FASE 29.3 (three-model runtime) |
| `qwen2.5-coder-32b` | 192.168.1.60:1234 | RX7900XT 20GB | **DOWN** — nodo apagado |

**Backend:** llama.cpp v2.14.0 (Windows) con Vulkan/ROCm en RX9070.
**Streaming:** Real (AI_LAB_REAL_STREAMING=true), relay directo de chunks SSE desde llama.cpp.
**Model set activo:** 3 modelos (llama-3.1-8b, qwen2.5-coder-14b, nomic-embed).
**SLO Enforcement:** FASE 29.4 activo con `AI_LAB_SLO_DRY_RUN=true` por defecto. `RuntimeSLOManager` evalúa TTFB, timeouts, GPU/VRAM. `DegradationManager` con LEVEL 1 (forced llama, qwen protection). `AdaptiveConcurrency` reduce qwen parallel 2→1 bajo presión GPU. Priority lanes (Lane 1 con 2 slots reservados). Circuit breakers observables (no bloquean). Endpoint `/slo/health`.

### Perfiles cognitivos congelados

| Perfil | Stable | Modelo | Tokens | Temperatura | Memoria |
|--------|--------|--------|--------|-------------|---------|
| `minimal` | ✅ | llama-3.1-8b | 300 cap | 0.2 | disabled |
| `report` | ✅ | qwen2.5-14b | 1024 | 0.4 | light |
| `coding` | ✅ | qwen2.5-14b | 2048 | 0.1 | light |
| `observe` | ❌ (UX) | llama-3.1-8b | 180 | 0.1 | disabled |
| `chat` | ❌ (UX) | qwen2.5-14b | 512 | 0.4 | light |
| `analysis` | ❌ (burn-in) | qwen2.5-14b | 2048 | 0.3 | full |
| `creative` | ❌ (validación) | qwen2.5-14b | 2048 | 0.7 | light |
| `agent` | ❌ (tools) | qwen2.5-14b | 2048 | 0.2 | full |

Model set activo: `29.3-three-model-runtime` (llama-3.1-8b, qwen2.5-coder-14b, nomic-embed).
qwen3.6-27b desactivado. No borrado del disco, disponible para tests manuales.

---

## Procedimientos operativos

### Verificar salud del stack

```bash
# AI-LAB
curl -s http://192.168.1.30:8008/health | jq .
curl -s http://192.168.1.30:8083/health | jq .
curl -s http://192.168.1.30:8008/metrics | grep "ailab_requests_total"

# FASE 29.4: SLO health endpoint
curl -s http://192.168.1.30:8008/slo/health | jq .

# LM Studio
curl -s http://192.168.1.50:1234/v1/models | jq ".data[].id"

# Prometheus
curl -s "http://192.168.1.40:9090/api/v1/targets" | jq ".data.activeTargets[] | {labels: .labels, health}"

# Grafana
curl -s -o /dev/null -w "%{http_code}" http://192.168.1.40:3000/api/health
```

### Reiniciar servicios (requiere sudo)

```bash
# Gateway (único entrypoint de chat — reiniciar con cuidado)
sudo systemctl restart ailab-gateway

# Router (API interna, no afecta al tráfico de chat)
sudo systemctl restart ailab-router

# Live API
sudo systemctl restart ailab-live-api

# Tras reiniciar gateway, verificar que no haya uvicorn rogue en :8008
ss -tlnp | grep 8008
# Si aparece uvicorn en :8008, matarlo (es el router arrancando en puerto incorrecto)
```

### Ejecutar burn-in

```bash
# Script de burn-in en /tmp/fase27-burnin-v3.sh
# Rota 12 tipos de mensaje cada 3s, timeout curl 120s
nohup bash /tmp/fase27-burnin-v3.sh </dev/null >/dev/null 2>&1 &
disown
tail -f /tmp/fase27-burnin-v3.log
```

### Debug de métricas flatlineadas

**Checklist cuando un panel Grafana muestra "Sin datos":**

1. Verificar que la métrica existe en el endpoint correcto:
   ```bash
   curl -s http://192.168.1.30:8008/metrics | grep "METRICA_SOSPECHOSA"
   ```
2. Si existe pero con valor 0, verificar que el code path se ejecuta (feature flags, import errors).
3. Si no existe en :8008 pero sí en :8083 o :8084, el tráfico va al proceso equivocado.
4. Si la métrica existe con datos en :8008 pero Grafana no la ve, verificar la query PromQL:
   ```bash
   curl -s "http://192.168.1.40:9090/api/v1/query?query=METRICA" | jq .
   ```
5. Las métricas `rate()` requieren ≥5min de tráfico continuo para devolver datos.
6. Métricas que dependen de feature flags: `AI_LAB_ENABLE_MEMORY_INJECTOR` (memoria), `AI_LAB_ENABLE_PROFILES` (perfiles).

### Memory injection

Controlado por feature flag `AI_LAB_ENABLE_MEMORY_INJECTOR` (default: `false`).

**Cómo activar:**
```bash
# Añadir al systemd service o setear en os.environ al inicio del gateway:
Environment=AI_LAB_ENABLE_MEMORY_INJECTOR=true
```

**Políticas de memoria** (`runtime/policies/memory/`):
- `minimal` → sin recall (SKIP_MINIMAL_GUARD)
- `light` → 1 memoria, 800 chars, solo `incidents`, min_score 0.6
- `full` → 5 memorias, 4000 chars, 3 colecciones, min_score 0.45

**Mapeo perfil → política** (`runtime/policies/memory/manifest_memory.json`):
- chat/coding → light
- analysis/agent → full
- observe → minimal

### uvicorn rogue en :8008

Síntoma: `curl http://192.168.1.30:8008/health` devuelve `"service":"ai-lab-router-api"` en vez de `"ai-lab-openai-gateway"`.

Causa: un proceso `uvicorn runtime.llm.router_api:app --port 8008` está ocupando el puerto del gateway.

Fix:
```bash
kill $(ss -tlnp | grep ':8008.*uvicorn' | grep -oP 'pid=\K\d+')
# systemd reiniciará ailab-gateway automáticamente
```

## Nota final

El objetivo **no** es maximizar flexibilidad a costa de estabilidad. AI-LAB prioriza runtime observable, reversible y seguro. Cada cambio debe ser pequeño, verificable y con rollback inmediato.

## FASE 29.4.1 — Report Runtime Grounding

**Bug corregido:** `build_minimal_report_messages()` mencionaba `OBSERVED_RUNTIME` en el system prompt pero nunca lo construía ni inyectaba. Los reportes heavy (qwen2.5-14b) respondían "no tengo información".

### Archivos nuevos

| Archivo | Propósito |
|---------|-----------|
| `runtime/context/__init__.py` | Export público del módulo context |
| `runtime/context/report_runtime_context.py` | `build_report_runtime_context()`, `format_report_runtime_context()`, `extract_target_ip()` |
| `runtime/prompts/report_prompt.md` | System prompt para reportes, versionable y externo |

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `runtime/gateway/tool_request_classifier.py` | `build_minimal_report_messages()` acepta `observed_runtime`; carga prompt desde archivo |
| `runtime/gateway/openai_gateway.py` | Inyecta OBSERVED_RUNTIME en reportes, flag `_report_grounded=true`, elimina doble system prompt en heavy report |
| `runtime/telemetry/prometheus_metrics.py` | +4 métricas: `ailab_report_grounding_total`, `ailab_report_missing_fields_total`, `ailab_report_target_ip_total`, `ailab_report_ungrounded_total` |
| `runtime/prompts/manifest.json` | `report → report_prompt.md` |

### OBSERVED_RUNTIME

- Datos de: `runtime_state`, `topology`, `health_score`, `inference_nodes`, `profile_manifest`
- `extract_target_ip()` soporta IPs, dominios multi-nivel, URLs con puerto
- Snapshot JSON ≤12,000 chars con `observed_fields` / `missing_fields`
- Grounding discipline: solo módulos locales, NO memory recall, NO tools, NO HARD_FACTS

### Próximo

- FASE 28.4 (tool contracts, cross-plan GC) — pendiente
