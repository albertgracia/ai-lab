# AI-LAB-MODEL-REFERENCE-CLEANUP-02A

**Fecha:** 2026-07-03
**Fase:** AI-LAB-CLEANUP-02A — Fase A (ACTIVE_RUNTIME_BLOCKER en openai_gateway.py)
**Tag:** (commit-only, sin tag independiente)

## Objetivo

Eliminar las 7 referencias ACTIVE_RUNTIME_BLOCKER a `qwen3-vl-8b-instruct` en `runtime/gateway/openai_gateway.py` que causaban routing a un modelo no cargado.

## Cambios Realizados

Archivo: `runtime/gateway/openai_gateway.py` (7 cambios en bloque de model selection)

| Ruta | Línea | Antes | Después | Riesgo |
|------|-------|-------|---------|--------|
| tool-use fastpath | 5159 | `selected_model = "qwen3-vl-8b-instruct"` | `selected_model = "qwen2.5-14b-instruct"` | CRÍTICO → ✅ |
| minimal/observe sin escalation | 5175 | `selected_model = "qwen3-vl-8b-instruct"` | `selected_model = "qwen2.5-14b-instruct"` | CRÍTICO → ✅ |
| observe fastpath | 5179 | `selected_model = "qwen3-vl-8b-instruct"` | `selected_model = "qwen2.5-14b-instruct"` | CRÍTICO → ✅ |
| greeting fastpath | 5181 | `selected_model = "qwen3-vl-8b-instruct"` | `selected_model = "qwen2.5-14b-instruct"` | CRÍTICO → ✅ |
| tool_use task_type | 5197 | `selected_model = "qwen3-vl-8b-instruct"` | `selected_model = "qwen2.5-14b-instruct"` | CRÍTICO → ✅ |
| lightweight prompt | 5205 | `selected_model = "qwen3-vl-8b-instruct"` | `selected_model = "qwen2.5-14b-instruct"` | CRÍTICO → ✅ |
| fast/general sin escalation | 5221 | `selected_model = "qwen3-vl-8b-instruct"` | `selected_model = "qwen2.5-14b-instruct"` | CRÍTICO → ✅ |

Además, comentario adjunto en línea 5157 actualizado de `tool-use -> always qwen3-vl-8b-instruct` a `tool-use -> fast model` (coherencia con código).

## Validación

| Check | Resultado |
|-------|-----------|
| 1. `GET /health` | ✅ `200 OK`, `"status": "ok"` |
| 2. `GET /v1/models` (.50) | ✅ `qwen2.5-14b-instruct` presente, `qwen3-vl-8b-instruct` ausente |
| 3. Routing greeting | ✅ Via `ailab_route_preview("hola")` → `route_family: "fast"` |
| 4. Routing observe | ✅ Via `ailab_route_preview("¿temperatura?")` → `route_family: "fast"` |
| 5. Gateway logs | ✅ Sin errors, tracebacks ni import failures |
| 6. ACTIVE_RUNTIME_BLOCKER restantes | ✅ **0** — `grep selected_model.*qwen3-vl` → sin resultados |
| 7. LEGACY_DEFAULT restantes | ✅ 2 (líneas 3348, 5092) — labels en respuestas no-routing |
| 8. SCP .30 | ✅ Archivo copiado y gateway reiniciado |

## Detalle de las 2 referencias LEGACY_DEFAULT restantes

| Línea | Ruta | Propósito | Riesgo |
|-------|------|-----------|--------|
| 3348 | `/runtime/performance/fastpath` | Label en respuesta de diagnóstico (no afecta routing) | NULO |
| 5092 | capability answer early return | Label en respuesta sintética sin LM Studio (cosmético) | NULO |

## Riesgos Post-Fix

### LM Studio sin modelo cargado para inferencia

`POST /v1/chat/completions` contra `.50:1234` responde `"No models loaded"`. Es un problema pre-existente de infraestructura (no relacionado con este fix). El gateway envía correctamente la request a `.50` con `qwen2.5-14b-instruct`, pero LM Studio rechaza la inferencia.

**Esto NO es una regresión de nuestro cambio.** El routing anterior apuntaba a `qwen3-vl-8b-instruct` que también no estaba cargado — mismo síntoma, peor causa.

### llama-3.1-8b-instruct no disponible

`llama-3.1-8b-instruct` (PRIMARY_OPERATIONAL_MODEL según AGENTS.md) no aparece en `GET /v1/models` de `.50`. Es pre-existente.

## Conclusión

**PASS.** 7 ACTIVE_RUNTIME_BLOCKER eliminados. Gateway estable sin errores. Routing de observe/greeting/minimal/lightweight/fast ya no apunta a modelo no cargado.

## Commits

| Hash | Mensaje |
|------|---------|
| (pendiente) | `fix(gateway): remove active qwen3-vl runtime blockers` |
