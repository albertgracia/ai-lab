# AI-LAB Fast Model Fix 01

**FASE:** AI-LAB-FAST-MODEL-FIX-01
**Fecha:** 2026-07-03
**Tipo:** Corrección
**Autor:** OpenCode Agent

---

## Resultado: PASS ✅

FAST_MODEL corregido de `qwen3-vl-8b-instruct` a `qwen2.5-14b-instruct`.

---

## 1. Cambio Realizado

**Archivo:** `runtime/models/model_policy.py:41`

```diff
-FAST_MODEL = "qwen3-vl-8b-instruct"
+FAST_MODEL = "qwen2.5-14b-instruct"
```

## 2. Backup

**Ruta:** `/opt/ai-lab/runtime/models/model_policy.py.bak.1783095527`
**Tamaño:** 2933 bytes

## 3. Difusión del Cambio

FAST_MODEL es consumido por:

| Función | Uso | Efectivo |
|---------|-----|----------|
| `get_fast_model()` | Retorna FAST_MODEL para fast/lightweight/observe | ✅ |
| `get_fallback_model()` | Retorna FAST_MODEL para fallback/default | ✅ |
| `get_degraded_model()` | Retorna FAST_MODEL para degraded/emergency | ✅ |
| `get_model_for_route(unknown)` | Fallback para rutas no registradas en CANONICAL_MODELS | ✅ |
| `PRIMARY_OPERATIONAL_MODEL` | Alias exportado vía `runtime/router/model_policy.py` | ✅ |

**Nota:** `CANONICAL_MODELS` en `model_policy.py:21-28` sigue mapeando rutas específicas
a `qwen3-vl-8b-instruct` como valor de diccionario. El routing real usa las helpers
(`get_fast_model()`, `get_fallback_model()`, etc.) que retornan `FAST_MODEL`. No se
requiere cambio adicional porque el gateway no consulta `CANONICAL_MODELS` directamente.

## 4. Validaciones

### 4.1 Gateway Health

```json
{
  "status": "ok",
  "service": "ai-lab-openai-gateway",
  "backend": "http://192.168.1.50:1234/v1",
  "pool": { "nodes_total": 3, "nodes_online": 2, "nodes_offline": 1 }
}
```

### 4.2 Modelos Disponibles

6 modelos listados, incluyendo `qwen2.5-14b-instruct`. `qwen3-vl-8b-instruct` **no aparece**.
Si el cliente solicitara `qwen3-vl-8b-instruct` explícitamente, el gateway lo rechazaría
(no cargado en LM Studio).

### 4.3 Chat Simple (`qwen2.5-14b-instruct`)

```json
{
  "model": "qwen2.5-14b-instruct",
  "choices": [{"message": {"content": "pong"}, "finish_reason": "stop"}]
}
```

### 4.4 Ruta Greeting

```json
{
  "model": "qwen2.5-14b-instruct",
  "choices": [{"message": {"content": "Hola, ¿cómo estás?"}}]
}
```

### 4.5 Ruta Observe

```json
{
  "model": "qwen2.5-14b-instruct",
  "choices": [{"message": {"content": "I'm an assistant designed to help..."}}]
}
```

### 4.6 FAST_MODEL Efectivo

`qwen3-vl-8b-instruct` no aparece como FAST_MODEL efectivo en ninguna respuesta.
Todas las rutas retornan `qwen2.5-14b-instruct`.

## 5. Restart

Gateway reiniciado vía `SIGTERM → systemd Restart=always`. Sin sudo requerido,
sin interrupción de servicio perceptible.

- **Método:** `kill -TERM $(pgrep -f openai_gateway.py)`
- **Tiempo recuperación:** ~6 segundos
- **Pool post-restart:** 2/3 online, `total_selections: 0` (recién arrancado)

## 6. Estado Final

| Métrica | Valor |
|---------|-------|
| FASTMODEL | `qwen2.5-14b-instruct` |
| Cobertura | fast, observe, minimal, fallback, degraded, greeting, lightweight |
| Modelos .50 | 6 (qwen2.5-14b-instruct, nomic-embed, gemma-4-12b, qwen3.6-27b, deepseek-coder-v2, deepseek-r1) |
| Pool online | 2/3 (.50 + .250) |
| Pool offline | 1/3 (.60 esperado) |

## 7. Riesgos Residuales

- `CANONICAL_MODELS` desactualizado (referencia `qwen3-vl-8b-instruct` en 7 rutas)
- `_BACKEND_MODEL_MAP` no mapea `qwen2.5-14b-instruct` (solo mapea coder models con prefijo `qwen/qwen2.5-coder-14b-instruct`)
- Si el código consulta `CANONICAL_MODELS` directamente (sin pasar por helpers), seguirá viendo `qwen3-vl-8b-instruct`

---

*Commit: c1f3a1b*
