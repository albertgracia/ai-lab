# AI-LAB Canonical Models Fast Alignment 01

**FASE:** AI-LAB-CANONICAL-MODELS-FAST-ALIGNMENT-01
**Fecha:** 2026-07-03
**Tipo:** Corrección

---

## Resultado: PASS ✅

CANONICAL_MODELS alineado con FAST_MODEL. Todas las rutas fast apuntan a `qwen2.5-14b-instruct`.

---

## 1. Cambio Realizado

**Archivo:** `runtime/models/model_policy.py` (CANONICAL_MODELS dict)

```diff
-CANONICAL_MODELS = {
-    "fast": "qwen3-vl-8b-instruct",
-    "observe": "qwen3-vl-8b-instruct",
-    "minimal": "qwen3-vl-8b-instruct",
-    "fallback": "qwen3-vl-8b-instruct",
-    "degraded": "qwen3-vl-8b-instruct",
-    "greeting": "qwen3-vl-8b-instruct",
-    "lightweight": "qwen3-vl-8b-instruct",
+CANONICAL_MODELS = {
+    "fast": "qwen2.5-14b-instruct",
+    "observe": "qwen2.5-14b-instruct",
+    "minimal": "qwen2.5-14b-instruct",
+    "fallback": "qwen2.5-14b-instruct",
+    "degraded": "qwen2.5-14b-instruct",
+    "greeting": "qwen2.5-14b-instruct",
+    "lightweight": "qwen2.5-14b-instruct",
```

## 2. Backup

`/opt/ai-lab/runtime/models/model_policy.py.bak.canonical.1783098302`

## 3. Validaciones

### 3.1 Python Validation

```python
fast: qwen2.5-14b-instruct
observe: qwen2.5-14b-instruct
minimal: qwen2.5-14b-instruct
fallback: qwen2.5-14b-instruct
degraded: qwen2.5-14b-instruct
greeting: qwen2.5-14b-instruct
lightweight: qwen2.5-14b-instruct
FAST_MODEL: qwen2.5-14b-instruct
get_model_for_route(fast): qwen2.5-14b-instruct
get_model_for_route(unknown): qwen2.5-14b-instruct
ALL CANONICAL ROUTES CLEAN: no qwen3-vl-8b-instruct references
```

### 3.2 Gateway Health

```json
{"status": "ok", "service": "ai-lab-openai-gateway"}
```

### 3.3 Chat Validation

| Ruta | Mensaje | Modelo | Respuesta (primeros 60 chars) |
|------|---------|--------|-------------------------------|
| greeting | "hola" | qwen2.5-14b-instruct | Hola, ¿cómo estás? |
| observe | "que ves" | qwen2.5-14b-instruct | Como asistente de inteligencia artificial, no tengo la capac |
| fast | "responde solo ok" | qwen2.5-14b-instruct | OK |
| lightweight | "si" | qwen2.5-14b-instruct | ¿Si, qué quieres saber? |

## 4. Incidente: Gateway Crash por Conflictos Heredados

Durante el reinicio del gateway tras aplicar el cambio, el proceso falló con:

```
File "/opt/ai-lab/runtime/gateway/openai_gateway.py", line 1
    <<<<<<< Updated upstream
SyntaxError: invalid syntax
```

**Causa raíz:** El stash pop del paso de sincronización (HERMES-AI-LAB-SYNC-AND-VERIFY-01) dejó marcadores de conflicto en 7 archivos runtime (`openai_gateway.py`, `control_plane.py`, `tool_request_classifier.py`, `operational_fastpath.py`, `operator_intent_reasoning.py`, `routing_history.py`, `live_api.py`, `test_operator_intent_reasoning_36c.py` y `AGENTS.md`).

**Resolución:** Todos los archivos runtime fueron restaurados desde la versión local sincronizada vía SCP y los conflictos git resueltos con `git checkout --theirs` + commit.

## 5. Gap Detectado: capability_router.py

`runtime/router/capability_router.py` (archivo nuevo de los 11 commits locales) contiene en `choose_model()` fallbacks hardcoded a `qwen3-vl-8b-instruct`:

```python
# ── fallback (original behaviour) ─────────────────────────────────
if task_type == "fast":
    return "qwen3-vl-8b-instruct"
return "qwen3-vl-8b-instruct"
```

Además, `MODEL_CAPABILITIES` en el mismo archivo referencia `"qwen3-vl-8b-instruct"`.

**No se tocó.** Pendiente para fase separada: `AI-LAB-CAPABILITY-ROUTER-FALLBACK-ALIGNMENT-01`.

## 6. Commits

| Commit | Mensaje |
|--------|---------|
| `17e01642` | `fix(runtime): align canonical fast routes with available model` |
| `fc75656a` | `merge: resolve AGENTS.md and openai_gateway.py conflicts with origin` |

---

*Informe generado post-fix y post-resolución de conflictos heredados.*
