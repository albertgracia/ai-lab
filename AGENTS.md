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

## Astro Governance

Antes de modificar cualquiera de los siguientes elementos:

- `apps/ialab-docs` (Astro)
- Cloudflare Pages (`ai-lab.labrazahome.com`)
- `blog-ai-lab.labrazahome.com`
- `ai-lab.labrazahome.com`
- `metricas.labrazahome.com`

leer obligatoriamente:

`docs/architecture/ASTRO-DEPLOYMENT-GOVERNANCE.md`

Ese documento es la ***source of truth*** canónica sobre superficies web, flujos de despliegue, restricciones de publicación y el incidente histórico `snapshot_unavailable`. Ningún agente debe modificar Astro, Cloudflare Pages o Metrics Dashboard sin haberlo leído primero.

11. **ASTRO-VALIDATION-RULE (permanente):** Build PASS + Deploy PASS no es suficiente. Toda modificación Astro debe validar funcionalmente Home, Architecture, Documentation Landing, Roadmap, Blog y separación Public/Private en producción real. Documento completo en `docs/governance/ASTRO-VALIDATION-RULE.md`.

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

---

## Federated Runtime Agent Constitution

Este documento ya no es una guía informal: es doctrina operacional de runtime governance.

### Authority Precedence

Orden de precedencia (si hay conflicto, gana el nivel superior):

1. Safety hard rules (no destructive ops sin aprobación explícita, no inventar estado, no saltarse gates)
2. Operational truth (solo hechos verificables; lo no verificado es `NO DISPONIBLE`)
3. Contracts-first (respetar contratos de entrada/salida entre dominios; no acoplar por conveniencia)
4. Domain ownership (cada bounded context es owner de su semántica y de sus invariantes)
5. UX/capabilities (preferencias, estilo, tooling), solo si no contradice lo anterior

### Allowed Coupling (bounded contexts)

Regla general: el core orquesta; los dominios razonan localmente. Evitar “god agents”.

1. El core puede llamar dominios vía contracts (`runtime/contracts/*`, `runtime/federation/*`).
2. Los dominios pueden depender de `contracts`, `domain_registry`, y tipos compartidos explícitos.
3. La dependencia cruzada dominio→dominio requiere justificación y debe quedar declarada en el domain registry.

### Forbidden Dependencies

Estas dependencias están prohibidas por diseño (rompen aislamiento y causan singularidad):

1. Observability MUST NOT importar lógica de orquestación del gateway/core.
2. Authority MUST NOT depender de routing heuristics del core (la autoridad no decide placement).
3. Operator intent MUST NOT ejecutar remediation (solo clasificación/razonamiento; ejecución es otro dominio).
4. Structural cognition (GitNexus) MUST NOT modificar runtime state ni inventar topología.
5. Memory MUST NOT contaminar rutas `minimal` ni inflar el core por defecto.

### Operational Semantics (vocabulario obligatorio)

Las respuestas operacionales deben etiquetar explícitamente el tipo de verdad:

1. `authority-backed`: proviene de una fuente con autoridad (health endpoints, métricas, logs auditables, contracts)
2. `operational`: refleja el estado operativo real observado (no intención, no deseos)
3. `discoverable-only`: solo inventario/descubrimiento (LM Studio listings, scans), no implica activo
4. `stale`: dato fuera de ventana o potencialmente desactualizado
5. `degraded`: el runtime está operando con protecciones o reducción de capacidad
6. `confidence`: alto/medio/bajo, con motivo (evidencia, frescura, cobertura)
7. `remediation-safe`: propuesta que NO requiere acciones destructivas ni privilegios sin aprobación

### Context Budget Discipline

1. El core NO arrastra contexto global por defecto.
2. Solo inyectar lo mínimo para decidir y ejecutar el siguiente paso seguro.
3. Si algo requiere contexto amplio (p. ej. análisis estructural), delegar al dominio correspondiente y traer un summary contract.
4. `runtime/state/*` es estado vivo: NO se versiona, NO se usa como “source of truth” documental.

## Phase Closure — Documental Impact Rule

Toda fase debe evaluar impacto documental antes de declararse PASS.

Si hay impacto documental:
- La documentación canónica en `apps/ialab-docs/` debe actualizarse
- `npm run build` debe ejecutarse y pasar en `apps/ialab-docs/`
- AnythingLLM debe reindexar el workspace AI-LAB
- La recuperación documental debe validarse con preguntas representativas

Si no es posible reindexar (entorno no disponible), el cierre puede ser PARTIAL documentando la razón.

El protocolo completo está en `apps/ialab-docs/src/content/docs/governance/phase-closure-protocol.md`.

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

## Storage Hardening Rules

- `RULE-STORAGE-1`: Nunca generar backups dentro de rutas ya archivables.
- `RULE-STORAGE-2`: Todo backup debe usar `.backup-excludes`.
- `RULE-STORAGE-3`: `/opt/ai-lab/backups` queda deprecated.
- `RULE-STORAGE-4`: Archives completos solo en `/mnt/opencode/ai-lab-archives`.
- `RULE-STORAGE-5`: Snapshots no pueden contener `backups`, `.venv`, `node_modules`, `.git`, caches ni artifacts temporales.
- `RULE-STORAGE-6`: Todo archive debe generar manifest JSON.
- `RULE-STORAGE-7`: Detect recursion BEFORE copy, not after.

---

## Runtime Maturity Rules

1. Loaded ≠ Active ≠ Discoverable ≠ Disabled
Un modelo listado por LM Studio no se considera activo. ACTIVE solo significa que ha recibido tráfico real reciente dentro de ACTIVE_WINDOW_SECONDS.

2. Disabled wins always
Si un modelo está desactivado por runtime/config, debe aparecer siempre como DISABLED aunque LM Studio lo liste.

3. Control-plane ≠ inference backend
192.168.1.30 = primary-control-plane (gateway, router, live-api).
192.168.1.50 = inference backend RX9070 (LM Studio principal).
192.168.1.60 = inventory/offline RX7900XT hasta que se reactive explícitamente.
192.168.1.250 = storage + LM Studio secundario (NAS-N5, disponible para failover).

4. No Multi-GPU before semantic readiness (todas las dependencias cerradas en FASE 30A-31B)
No implementar scheduler Multi-GPU hasta cerrar:
- 30H evidence enforcement
- 30I sensor fusion
- 30I-G deterministic runtime grounding
- OBS-31A observability alignment
- 31B runtime semantic maturity & degraded mode governance
Todas las anteriores están ✅ cerradas desde CP-31B.

5. Reports must be operational, not generic
Los informes deben usar tono NOC/operacional.
Prohibido recomendar Kubernetes, Docker Swarm, Spark, Dask o herramientas genéricas salvo que el runtime real las use o el usuario las pida.

6. Active route semantics
Cada route-family debe tener estado explícito:
active, degraded, throttled, blocked, unused.
No inferir salud de una ruta solo por existir en código.

7. External AI reports are advisory only
Informes de Google IA, DeepSeek u otros agentes deben tratarse como señales externas no verificadas. Antes de actuar, validar contra:
- código
- métricas
- endpoints
- logs
- runtime_state

8. Health endpoints must be always-on
Endpoints como /health, /slo/health, /runtime/maturity y futuros /runtime/* deben responder siempre 200 con estado disabled/passive si la feature está apagada.

9. No phase closed without operational proof
Además de tests/build/tag, cada fase runtime debe incluir al menos una validación real:
curl endpoint, métrica Prometheus, dashboard, JSONL audit o burn-in corto.

10. Failure domain must be explicit per node
Cada nodo en la topología debe tener un failure_domain explícito que determine el impacto de su caída.
- control-plane failure → bloquea todo el routing cognitivo
- inference-gpu failure → solo bloquea requests que requieren ese GPU
- observability failure → no afecta al plano cognitivo, solo a métricas
- network failure → afecta a nodos aguas abajo
- storage failure → afecta solo a memoria episódica y replay

11. Topology must be observable without inference backend
El endpoint /runtime/topology debe responder 200 aunque el backend de inferencia esté offline.
La topología separa rol (qué hace) de failure_domain (qué pasa si falla).

12. Governance visibility must be always-on
El endpoint /runtime/governance debe responder 200 siempre, incluso si control_plane no está disponible.
El payload debe incluir source (control_plane | fallback) para distinguir datos reales de fallback.

13. Governance level must be dynamic, not hardcoded
El governance_level en el descriptor de madurez debe resolverse desde control_plane.get_governance_state():
- NORMAL   → ENFORCED
- ELEVATED → ENFORCED
- DEGRADED → DEGRADED
- LOCKDOWN → LOCKDOWN
Prohibido hardcodear "enforced" en builder.py.

14. Route existence ≠ route health
La existencia de una route-family en código NO implica que esté operativa.
El estado de ruta debe derivarse de métricas observadas (total_requests, error_count, blocked_count)
y/o señales runtime explícitas (SLO, governance override).

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
FASE 30B.1 → completion truncation + multi-gpu triggers       ✅ CP-30B.1-COMPLETION-METADATA-STABLE
FASE 30C → single-node explicit degraded mode                ✅ CP-30C-DEGRADED-MODE-EXPLICIT-STABLE
FASE 30D → topology role & failure domain taxonomy            ✅ CP-30D-TOPOLOGY-FAILURE-DOMAIN-STABLE
FASE 30E → governance visibility refinement                   ✅ CP-30E-GOVERNANCE-VISIBILITY-STABLE
FASE 30F → cognitive route semantics                           ✅ CP-30F-ROUTE-SEMANTICS-STABLE
FASE 30G → operational reporting discipline                     ✅ CP-30G-OPERATIONAL-REPORTING-STABLE
FASE 30Z → runtime maturity consolidation snapshot               ✅ CP-30Z-RUNTIME-MATURITY-CONSOLIDATED
FASE 30H → runtime evidence enforcement                         ✅ CP-30H-RUNTIME-EVIDENCE-ENFORCEMENT-STABLE
FASE 30H.1 → universal evidence guard                            ✅ CP-30H.1-UNIVERSAL-EVIDENCE-GUARD-STABLE
FASE 30H.2 → runtime context injection                           ✅ CP-30H.2-RUNTIME-CONTEXT-INJECTION-STABLE
FASE 30I → runtime sensor fusion                                 ✅ CP-30I-RUNTIME-SENSOR-FUSION-STABLE
FASE 30I-B → sensor fusion hardening                             ✅ CP-30I-B-SENSOR-FUSION-HARDENED-STABLE
FASE 30I-C → sensor summary exposure                              ✅ CP-30I-C-SENSOR-SUMMARY-EXPOSURE-STABLE
FASE 30I-D → sensor semantics normalization                       ✅ CP-30I-D-SENSOR-SEMANTICS-NORMALIZED-STABLE
FASE 30I-E → operational response formatting                      ✅ CP-30I-E-OPERATIONAL-RESPONSE-FORMATTING-STABLE
FASE 30I-F → runtime cognitive compression                        ✅ CP-30I-F-RUNTIME-COGNITIVE-COMPRESSION-STABLE
FASE 30I-F0 → runtime model routing cleanup                       ✅ CP-30I-F0-RUNTIME-MODEL-ROUTING-CLEANUP-STABLE
FASE 30I-G → deterministic runtime grounding                      ✅ CP-30I-G-RUNTIME-GROUNDING-STABLE
FASE OBS-31A → observability source-of-truth audit               ✅ CP-OBS-31A-OBSERVABILITY-SOURCE-OF-TRUTH-STABLE
FASE OBS-31A.1 → Prometheus authority audit                       ✅ CP-OBS-31A.1-PROMETHEUS-AUTHORITY-AUDIT-STABLE
FASE OBS-31A.2 → Grafana drift audit                              ✅ CP-OBS-31A.2-GRAFANA-DRIFT-AUDIT-STABLE
FASE OBS-31A.3 → runtime-observability alignment                  ✅ CP-OBS-31A.3-RUNTIME-OBSERVABILITY-ALIGNMENT-STABLE
FASE OBS-31A.4 → observability remediation plan                   ✅ CP-OBS-31A.4-OBSERVABILITY-REMEDIATION-PLAN-STABLE
FASE OBS-31A.5 → safe quick wins execution                        ✅ CP-OBS-31A.5-EXECUTOR-STABLE
FASE 31B → runtime semantic maturity & degraded mode governance    ✅ CP-31B-RUNTIME-SEMANTIC-MATURITY-STABLE
FASE 31B-HF1 → OpenCode runtime context alignment                   ✅ CP-31B-HF1-OPENCODE-CONTEXT-ALIGNMENT-STABLE
FASE 31C → operational reporting discipline                          ✅ CP-31C-OPERATIONAL-REPORTING-DISCIPLINE-STABLE
FASE 35C → live authority-backed cognition                            ✅ CP-35C-LIVE-AUTHORITY-BACKED-COGNITION-STABLE
FASE 35D → operational fast-path                                       ✅ CP-35D-OPERATIONAL-FAST-PATH-STABLE
FASE 36A → operational incident intelligence                           ✅ CP-36A-OPERATIONAL-INCIDENT-INTELLIGENCE-STABLE
FASE DEV-36X → codebase memory integration                              ✅ CP-DEV-36X-CODEBASE-MEMORY-INTEGRATION-STABLE
FASE DOC-36X → GitNexus structural cognition documentation               ✅ CP-DOC-36X-GITNEXUS-STRUCTURAL-COGNITION-STABLE
FASE DOC-36X → Spanish localization                                      ✅ CP-DOC-36X-SPANISH-LOCALIZATION-STABLE
FASE 35D-HF1 → fastpath routing priority fix                             ✅ CP-35D-HF1-FASTPATH-ROUTING-PRIORITY-STABLE
FASE 36B → runtime precision mode                                        ✅ CP-36B-RUNTIME-PRECISION-MODE-STABLE
FASE 36C-A → validation score 56.3 investigation (READ-ONLY)             ✅ docs audit
FASE 37A → cognitive health layer documentation                          ✅ docs audit
FASE PC-01 → phase closure protocol                                      ✅ docs audit
FASE 36C → operator intent reasoning                                    ✅
FASE 36D → autonomous observability triage                              ✅
FASE FEDERATION → domain registry, contracts, doctrine, budgets         ✅
FASE CANONICAL-MODEL-REGISTRY → canonical model registry, aliases       ✅
FASE COGNITIVE-SLO → bounded cognitive SLO framework                    ✅
FASE ARCHITECTURE-GOVERNANCE → architecture governance framework        ✅
FASE 37A → cognitive health layer documentation                         ✅
FASE 37B → graph-runtime correlation                                    ✅
FASE 37C → critical path analysis                                       ✅
FASE 37D → graph hotspot history                                        ✅
FASE 37E → governance drift detection                                   ✅
FASE 38A → runtime deep audit                                           ✅
FASE 38B → gateway shutdown graceful                                    ✅
FASE 38C → GitNexus NAPI error triage                                   ✅
FASE 38D → runtime stability snapshot                                   ✅
FASE 39A → OpenCode gateway contract hardening                          ✅
FASE 39B → runtime observability alerts                                 ✅
FASE 39C → cognitive health followup                                    ✅
FASE 39E → runtime stabilization release close                          ✅
FASE 40A → post-release SLO drift watch                                 ✅
SLO-ENFORCEMENT-01 → SLO enforcement read-only (13 SLOs, 26/26 tests)  ✅ CP-SLO-ENFORCEMENT-01
VALIDATION-AUTHORITY-01 → validation authority read-only (57/57)        ✅ CP-VALIDATION-AUTHORITY-01
AUTONOMOUS-OBSERVABILITY-TRIAGE-01 → triage read-only (34/34)           ✅ CP-AUTONOMOUS-OBSERVABILITY-TRIAGE-01
OPERATOR-INTENT-REASONING-01 → operator intent (25/25)                  ✅ CP-OPERATOR-INTENT-REASONING-01
MULTIGPU-READINESS-01 → readiness assessment (37/100)                   ✅ CP-MULTIGPU-READINESS-01
```

Tags git: desde `CP-21B-STABLE` hasta `CP-MULTIGPU-READINESS-01` (114 tags).

**Documentation hierarchy:** `docs/DOCUMENTATION-HIERARCHY.md` — Level 1: AGENTS.md, Level 2: ARCHITECTURE.md, Level 3: ROADMAP-2026.md, Level 4: conversation-history.md + audits/archive.

## Current Runtime Truth

**Checkpoint actual:** `CP-MULTIGPU-READINESS-01`

**Runtime state source of truth:** `/runtime/maturity` (build_runtime_descriptor)

**Operational model routing policy:**
- `llama-3.1-8b-instruct` = PRIMARY_OPERATIONAL_MODEL (minimal, greetings, observe, light prompts)
- `qwen/qwen2.5-coder-14b-instruct` = PRIMARY_CODING_MODEL (coding, report, architecture, reasoning, creative)
- `nomic-embed-text-v1.5` = embedding model (semantic recall)
- `lmstudio-community/qwen2.5-coder-14b-instruct` = DEPRECATED / NON_ROUTABLE
- `qwen3.6-27b` = DESACTIVADO (disponible para tests manuales)
- `qwen2.5-coder-32b` = DOWN (nodo RX7900XT apagado)

**Active GPU:**
- RX9070 / 192.168.1.50 / active_inference_backend

**Inventory offline:**
- RX7900XT / 192.168.1.60 / expected_offline (nodo apagado)

**Observability authority:**
- Prometheus = source of truth → 192.168.1.40:9090
- Grafana = visualization layer only → 192.168.1.40:3000
- Loki = log layer
- Grafana is NOT source of truth

**Storage:**
- runtime: `/opt/ai-lab`
- runtime data: `/opt/ai-lab-data`
- models: `/mnt/ai-models`
- archives: `/mnt/opencode/ai-lab-archives`

**Próxima fase:** FASE 37B — Validation Authority Recovery (restaurar Prometheus scrape targets)

### Roadmap actual

```
37B — Validation Authority Recovery (restaurar Prometheus scrape targets)
Multi-GPU scheduling (post-node-reactivation + pre-requisites: 7-10d)
Pilot técnico (post-authority)
Pilot operador (post-pilot técnico)
```

### Roadmap completado (Blocks 37-40)

```
Block 37 — Cognitive Health & Graph Analysis (37A-37E)
Block 38 — Runtime Stability (38A-38D: deep audit, graceful shutdown, error triage, snapshot)
Block 39 — Release Hardening (39A-39E: gateway contracts, observability alerts, followup, close)
Block 40 — Post-Release SLO Drift Watch (40A)
```



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

- FASE 36C — Operator Intent Reasoning
- FASE 36D — Autonomous Observability Triage

## FASE 36B — Runtime Precision Mode

**Objetivo:** precisión operacional extrema sin sobreafirmaciones: manejar evidencia parcial/ambigua, authority conflictiva, confidence degradada y señales contradictorias con disciplina de grounding (Unknown > hallucination).

**Componentes añadidos:**
- `runtime/precision/` (engine + contracts): evidence classification, conflict/partial handling, confidence aggregation (operational/authority/observability/routing/incidents/codebase).
- FastPath operacional: summary confidence-aware y compacto, evita ruido low-confidence.

**Garantías:**
- No `lmstudio-community` leakage en payloads operacionales.
- Discoverable != routable (discoverables visibles como discoverable, NO active/NO routable/NO operational).
- Partial evidence reduce confidence; conflicts degradan certainty (no fake certainty).

**APIs (always-on 200):**
- `/runtime/precision`
- `/runtime/precision/confidence`
- `/runtime/precision/evidence`
- `/runtime/precision/conflicts`
- `/runtime/precision/partial`
- `/runtime/precision/discoverable`
- `/runtime/precision/score`

**Validation invariants (36B):**
- `INVARIANT-PRECISION-CONFIDENCE`
- `INVARIANT-NO-OVERASSERTION`
- `INVARIANT-NO-DISCOVERY-LEAKAGE`
- `INVARIANT-CONFIDENCE-DETERMINISM`
- `INVARIANT-NO-LMSTUDIO-LEAKAGE`

**Métricas Prometheus (36B):**
- `ailab_operational_precision_score`
- `ailab_confidence_integrity_score`
- `ailab_authority_conflicts_total`
- `ailab_partial_state_total`
- `ailab_discovery_leakage_total`
- `ailab_stale_evidence_total`
- `ailab_precision_degraded_responses_total`
- `ailab_confidence_downgrade_total`

**Checkpoint:** commit `ac322c3b`, tag `CP-36B-RUNTIME-PRECISION-MODE-STABLE`.

---

## GITNEXUS-FIRST — Política Oficial de Consulta Pre-Cambio

**Vigencia:** Activa desde CP-GITNEXUS-FIRST-ACTIVATION-01

### Alcance

Antes de modificar **cualquiera** de los siguientes componentes, es **obligatorio** consultar GitNexus:

| Componente | Rutas |
|------------|-------|
| Router | `runtime/router/` |
| Gateway | `runtime/gateway/` |
| Runtime core | `runtime/*.py`, `runtime/**/*.py` |
| Scheduler | `runtime/nodes/scheduler.py` |
| Elastic Pool | `runtime/router/elastic_pool.py` |
| Marketplace Backend | `apps/marketplace/` (backend) |
| Marketplace Frontend | `apps/marketplace/` (frontend) |
| IDS | `runtime/intrusion/` |
| Hermes | `apps/hermes/` |

### Consultas obligatorias

Ejecutar **antes** de escribir cualquier cambio:

1. **`gitnexus_impact({target, direction: "upstream"})`** — qué depende de lo que vas a cambiar
2. **`gitnexus_impact({target, direction: "downstream"})`** — de qué depende lo que vas a cambiar
3. **`gitnexus_context({name})`** — referencias completas del símbolo
4. **`gitnexus_detect_changes()`** — antes de commitear, verificar que solo se afectan los símbolos esperados
5. **`gitnexus_route_map()`** (si aplica a rutas API) — consumidores de endpoints
6. **`gitnexus_shape_check()`** (si aplica a rutas API) — drift de contratos

### Flujo

```
1. Identificar componente/símbolo a modificar
2. Ejecutar impact() + context() obligatorios
3. Reportar blast radius al usuario (callers, procesos afectados, riesgo)
4. Si risk=HIGH/CRITICAL → obtener aprobación explícita
5. Implementar cambio
6. Ejecutar detect_changes() pre-commit
7. Solo entonces commitear
```

### Excepciones

- Cambios puramente cosméticos (comentarios, whitespace, formatting)
- Archivos de configuración (`*.json`, `*.yaml`, `*.env`)
- Tests (`tests/`) — no requieren consulta pre-cambio
- Documentación (`docs/`, `reports/`, `*.md`) — no requieren consulta

### Incumplimiento

Si un cambio se realiza sin la consulta GitNexus correspondiente y produce una regresión:
1. Reversión inmediata del cambio
2. Ejecución retrospectiva del análisis omitido
3. Documentación del incidente en `reports/`

---

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **ai-lab** (20327 symbols, 32455 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/ai-lab/context` | Codebase overview, check index freshness |
| `gitnexus://repo/ai-lab/clusters` | All functional areas |
| `gitnexus://repo/ai-lab/processes` | All execution flows |
| `gitnexus://repo/ai-lab/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

<!-- ANCHORED SUMMARY -->
## Goal
Actualizar superficies visibles Astro público y privado (home, architecture, blog, docs) para reflejar el estado real del ecosistema AI-LAB.

## Constraints & Preferences
- Público: PUBLIC_SAFE únicamente, sin IPs internas, sin secretos.
- Privado: puede contener detalle operativo completo.
- No tocar runtime AI-LAB, Hermes runtime, Marketplace productivo, Prometheus/Grafana.
- No desplegar sin validar builds.
- Criterio PASS: home/architecture/blog/roadmap cambian en ambos builds.

## Progress
### Done
- **HERMES-E02C-OPERATOR-REGISTRY-VALIDATOR**: 12 validaciones profundas de operadores. 17 tests nuevos. Commit `5f72dc5`, tag `CP-E02C-OPERATOR-REGISTRY-VALIDATOR-STABLE`.
- **HERMES-E06-DYNAMIC-GOVERNANCE**: Sistema completo ADR-006. 4 modos, GovernanceResolver, anti-flapping, capability-governance matrix. Commit `beca850`, tag `CP-E06-DYNAMIC-GOVERNANCE-STABLE`.
- **CP-HERMES-ENTERPRISE-CORE-01**: Checkpoint formal cierre Core. 113 tests PASS. Commit `c80781f`.
- **HERMES-E07-ENTERPRISE-RUNTIME-STATUS-ENDPOINT**: `GET /hermes/status` en `:8095`. 72 tests. Commit `df84882`, tag `CP-E07-ENTERPRISE-RUNTIME-STATUS-ENDPOINT-STABLE`.
- **HERMES-DOCS-ASTRO-ENTERPRISE-UPDATE-01**: 10 páginas Astro Hermes. 275 págs, 0 errores. Tag `CP-HERMES-DOCS-ASTRO-ENTERPRISE-01`.
- **ANYTHINGLLM-ENTERPRISE-01 a 03**: Diseño workspaces, provider check, creación 10 workspaces vía API.
- **ANYTHINGLLM-ENTERPRISE-04-COMPLETE**: KB Enterprise. 1304 vectores, 7 workspaces. RAG 100%. Tag `CP-ANYTHINGLLM-ENTERPRISE-04-COMPLETE`.
- **AI-LAB-ASTRO-DOCS-REFRESH-01**: Actualización masiva Astro. 277 págs, 0 errores. Tag `CP-AI-LAB-ASTRO-DOCS-REFRESH-01`.
- **AI-LAB-ASTRO-PUBLIC-PRIVATE-ACTUALIZATION-02**: Actualización pública+privada de superficies visibles. **Causa raíz identificada**: `src/pages/` (custom pages) no se actualizó en refresh anterior — solo Starlight docs. Home, arquitectura reescritos. 4 nuevos blog posts (018-021). IPs limpiadas de 7 posts legacy. Build público: 144 págs, 0 IPs, 0 errores. Build privado: 281 págs, 0 errores. Commit `4483722`, tag `CP-AI-LAB-ASTRO-PUBLIC-PRIVATE-ACTUALIZATION-02`.

### Blocked
- (none)

## Key Decisions
- El sitio Astro tiene dos render paths: `src/pages/` (custom, independiente) y `src/content/docs/` (Starlight). Ambos deben actualizarse por separado.
- `build-public-wrapper.mjs` filtra contenido PRIVATE_ONLY antes del build público.
- Reemplazar IPs internas por descriptores semánticos en contenido público.

## Next Steps
1. **ANYTHINGLLM-ENTERPRISE-05**: Cuando exista necesidad funcional real
2. **HERMES-E08-HOOK-INTEGRATION**: Activar primer lifecycle hook real
3. **HERMES-E09-GOVERNANCE-ENFORCEMENT**: Conectar resolver a runtime para bloqueo activo

## Critical Context
- HEAD: `4483722` (origin/main). Tags: 14 tags CP-Hermes + CP-ANYTHINGLLM-ENTERPRISE-04-COMPLETE + CP-AI-LAB-ASTRO-DOCS-REFRESH-01 + CP-AI-LAB-ASTRO-PUBLIC-PRIVATE-ACTUALIZATION-02.
- Tests: **185 PASS**.
- Status endpoint vivo: `GET /hermes/status → :8095`.
- Build público: 144 páginas, 0 IPs, 0 errores.
- Build privado: 281 páginas, 0 errores.
- AnythingLLM: `.50:3001`, 1304 vectores, 7 workspaces activos.
- **Causa raíz documentada**: `src/pages/` (custom pages) no Starlight — explicación en `reports/AI-LAB-ASTRO-PUBLIC-PRIVATE-ACTUALIZATION-02.md`.
- **Nota:** `192.168.1.30:3001` es Grafana v12.0.2, NO AnythingLLM.


*\.bak

