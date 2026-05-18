## Pre-commit hook — Astro build check

Antes de cualquier commit que toque `apps/ialab-docs/`, ejecuta `npm run build` automáticamente. Si el build falla, el commit se bloquea.

### Setup (una vez por clon)

```bash
ln -sf ../../scripts/pre-commit.sh .git/hooks/pre-commit
```

### Bypass

```bash
git commit --no-verify
```

## Regla: despliegue de documentación Astro

Cada vez que crees o modifiques documentación en `apps/ialab-docs/src/content/docs/`:

1. **Espera al pre-commit hook** — ya hace build + restart automáticamente
2. Si haces build manual (sin commit), ejecuta también:
   ```bash
   echo 19682507 | sudo -S systemctl restart ailab-docs
   ```
3. Verifica con `curl http://localhost:4322/docs/<slug>/` (debe dar 200)
4. El público (`ai-lab.labrazahome.com`) se despliega solo desde GitHub

El pre-commit hook ya lo hace automático en cada commit que toque docs.

## Servicios activos

| Servicio | Puerto | URL |
|---|---|---|
| `ailab-docs` | 4322 | blog-ai-lab.labrazahome.com (privado) |
| `ailab-metrics` | 3010 | metricas.labrazahome.com (privado, Next.js SSR) |
| `ailab-router` | 8083 | API router |
| `ailab-live-api` | 8084 | API datos en vivo |

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

## Estado actual

```
FASE 20A → modelos estabilizados          ✅
FASE 20B → wrappers legacy limpiados      ✅
FASE 20C → prompts declarativos           ✅
FASE 21A → perfiles cognitivos            ✅
FASE 21A.1 → observabilidad de perfiles   ✅
FASE 21B → de-hardcoding progresivo       ✅ CP-21B-STABLE
FASE 22A → tool runtime policies          ⏭
```

## Nota final

El objetivo **no** es maximizar flexibilidad a costa de estabilidad. AI-LAB prioriza runtime observable, reversible y seguro. Cada cambio debe ser pequeño, verificable y con rollback inmediato.
