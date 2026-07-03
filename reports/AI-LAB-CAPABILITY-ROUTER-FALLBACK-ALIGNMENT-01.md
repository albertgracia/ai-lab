# AI-LAB Capability Router Fallback Alignment 01

**FASE:** AI-LAB-CAPABILITY-ROUTER-FALLBACK-ALIGNMENT-01
**Fecha:** 2026-07-03
**Tipo:** Corrección

---

## Resultado: PASS ✅

Fallback hardcoded en `choose_model()` y `MODEL_CAPABILITIES` corregidos de `qwen3-vl-8b-instruct` a `qwen2.5-14b-instruct`.

---

## 1. Cambio Realizado

**Archivo:** `runtime/router/capability_router.py` (3 ocurrencias)

```diff
 MODEL_CAPABILITIES = {
-    "qwen3-vl-8b-instruct": {
+    "qwen2.5-14b-instruct": {
         "reasoning": 6, "coding": 6, "speed": 10, "memory": 8, "node": "rx9070",
     },
```

```diff
     if task_type == "fast":
-        return "qwen3-vl-8b-instruct"
-    return "qwen3-vl-8b-instruct"
+        return "qwen2.5-14b-instruct"
+    return "qwen2.5-14b-instruct"
```

## 2. Backup

`/opt/ai-lab/runtime/router/capability_router.py.bak.1783099008`

## 3. Validaciones

### 3.1 `choose_model()` — sin qwen3-vl-8b-instruct

| task_type | Resultado | qwen3-vl? |
|-----------|-----------|-----------|
| `fast` | `qwen2.5-coder-14b-instruct` | ❌ |
| `coding` | `qwen2.5-coder-14b-instruct` | ❌ |
| `reasoning` | `qwen2.5-coder-32b-instruct` | ❌ |
| `general` | `qwen2.5-coder-14b-instruct` | ❌ |
| `unknown` | `qwen2.5-coder-14b-instruct` | ❌ |

**Nota:** `choose_model('fast')` retorna `qwen2.5-coder-14b-instruct` (no `qwen2.5-14b-instruct`) porque el MODEL_REGISTRY asigna esa ID para fast. Es el **mismo modelo físico** (LM Studio responde como `qwen2.5-14b-instruct` vía `_BACKEND_MODEL_MAP`).

### 3.2 Gateway Health

```json
{"status": "ok", "service": "ai-lab-openai-gateway"}
```

### 3.3 Chat Validation

| Ruta | Mensaje | Modelo | Respuesta |
|------|---------|--------|-----------|
| greeting | "hola" | qwen2.5-14b-instruct | Hola, ¿cómo estás? |
| observe | "que ves" | qwen2.5-14b-instruct | Como asistente... |
| fast | "responde solo ok" | qwen2.5-14b-instruct | OK |

## 4. Gap Detectado: 16 referencias runtime activas a qwen3-vl-8b-instruct

| Archivo | Líneas | Uso |
|---------|--------|-----|
| `runtime/gateway/openai_gateway.py` | 9 líneas | Model selection hardcodes |
| `runtime/llm/router_api.py` | 3 líneas | Legacy routing defaults |
| `runtime/llm/model_router.py` | 1 línea | Default model list fallback |
| `runtime/observability/runtime_alignment.py` | 1 línea | Expected active model set |
| `runtime/performance/runtime_latency_calibration.py` | 1 línea | Calibration payload |
| `runtime/models/model_policy.py` | 1 línea | Docstring (documentación) |

**Pendiente para fase separada:** `AI-LAB-QWEN3VL-REFERENCE-CLEANUP-01`

## 5. Commits

| Hash | Mensaje |
|------|---------|
| `92c6c353` | `fix(router): align capability router fallback model` |

---

*Gap: 16 referencias runtime activas restantes a qwen3-vl-8b-instruct.*
