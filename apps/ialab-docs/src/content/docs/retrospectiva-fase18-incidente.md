---
title: "Retrospectiva — FASE 18 y el Incidente Model Unloaded"
summary: "Documento completo del despliegue de FASE 18, el incidente de streaming con OpenCode, la restauracion del router y el estado final del proyecto tras la sesion del 17/18 de mayo 2026."
order: 38
---

## Cronología

| Hora (UTC) | Evento |
|---|---|
| 21:00 | Despliegue FASE 18.1 — Control Plane (6 endpoints `/api/control/*`) |
| 21:15 | FASE 18.2 — Health Scoring (`model_health.py` + `model_router.py`) |
| 21:20 | FASE 18.3/18.4/18.5/18.7 — Tool Metrics, Memory Usefulness, Governance Audit v2, Recovery Manager |
| 21:25 | FASE 18.8 — Dashboard `/ops/control` en metrics-dashboard |
| 21:30 | Commit `c48014f6` — FASE 18 completa, 49 archivos, 3152 líneas |
| 22:00 | Test de estabilidad: 0 errores, 0 crashes, 0 degradación hot path |
| 22:06 | Reinicio de `ailab-router` (servicio) |
| 22:15 | **INCIDENTE**: OpenCode y OpenWebUI devuelven `"Model unloaded."` |
| 22:30 | Diagnóstico: LM Studio TTL descarga el modelo tras cada respuesta |
| 22:45 | Fix en router + gateway: retry en `"Model unloaded."` + fallback `.50:1234` |
| 23:00 | Commit `35ed8a20` — fix de resiliencia |
| 23:10 | **INCIDENTE SSE**: OpenCode no renderiza respuestas streaming |
| 23:15 | Experimentos fallidos: wrapper SSE, peek de chunks, formatos incompatibles |
| 23:40 | Revertido a `35ed8a20` |
| 23:45 | OpenCode config restaurada a original (`auto`/`fast`/`coding`/`reasoning`) |
| 00:00 | **FIX FINAL**: SSE nativo passthrough — el router deja pasar el SSE de LM Studio sin modificar |
| 00:35 | Commit `38aa46ab` — router simplificado (29 líneas añadidas, 73 borradas) |
| 00:45 | OpenCode, OpenWebUI, curl: todo funcionando |

## Causa raíz del incidente

**No fue FASE 18.** El reinicio del router rompió la conexión mantenida con LM Studio. LM Studio, al no recibir tráfico durante el reinicio, aplicó su TTL y descargó el modelo. Cada petición posterior requería recarga del modelo (~2s). Y el streaming nativo de LM Studio mete errores dentro del SSE con HTTP 200, invisibles para el router.

## Qué se rompió

1. **Streaming SSE**: el router intentaba wrappear, peekear, reformatear. Cada intento rompía la compatibilidad con OpenCode.
2. **OpenCode config**: los modelos cambiaron de `auto`/`fast` a `ailab-router/auto` — OpenCode no los reconocía.
3. **3 horas de debugging**: por no seguir la regla de "cambios pequeños, reversibles y verificables".

## Qué funciona ahora

### Router (`runtime/llm/router_api.py`)
- SSE nativo: pasa el stream de LM Studio sin tocar (formato OpenAI completo)
- Retry: si LM Studio responde HTTP 400 con `"unloaded"` o `"invalid model identifier"`, reintenta con fallback a `192.168.1.50:1234`
- No-streaming: igual que antes, con todo el pipeline HARD_FACTS + governance

### Gateway (`runtime/gateway/openai_gateway.py`)
- No-streaming a LM Studio
- Retry en `"Model unloaded."`

### OpenCode
- Config original: `auto`, `fast`, `coding`, `reasoning`
- baseURL: `http://192.168.1.30:8083/v1`
- Streaming: nativo SSE de LM Studio, token a token

### OpenWebUI
- `OPENAI_API_BASE_URL=http://host.docker.internal:8083/v1`
- Funcionando con `ailab-router/auto`, `ailab-router/fast`, etc.

### FASE 18 (todo intacto)
- Control Plane: 10 endpoints `/api/control/*` en `:8084`
- Health Scoring: per-model en `model_router.py`
- Tool Metrics: contadores `prometheus_client`
- Memory Usefulness: `memory_usefulness.py`
- Governance Audit v2: hooks en router + recall
- Recovery Manager: snapshots + restore
- Dashboard: `/ops/control` en metrics-dashboard
- Grafana: `AI-LAB · Panel de Gobernanza`
- Prometheus: scrape `ai-lab-router` + `ai-lab-gateway`

## Commits de la sesión

| Commit | Descripción |
|---|---|
| `c48014f6` | feat: FASE 18 — Professional Operations Runtime |
| `35ed8a20` | fix: router + gateway resiliencia ante Model unloaded |
| `a04d3ba4` | docs: runbook y doc del fix |
| `38aa46ab` | fix: native SSE passthrough |

## Lecciones aprendidas

1. **No tocar streaming sin tests end-to-end con el cliente real.**
2. **No cambiar config de cliente sin su confirmación.**
3. **El SSE de LM Studio funciona — no envolverlo.**
4. **Un reinicio del router rompe la conexión con LM Studio.**
5. **FASE 18 no causó el incidente — el reinicio del servicio sí.**

## Estado del proyecto

**AI-LAB v1 — Professional Operations Runtime**: estable y operativo.

```bash
# Verificación rápida
curl -s http://192.168.1.30:8083/health
# {"status":"ok","service":"ai-lab-router-api"}

curl -s http://192.168.1.30:8084/api/control/runtime
# {"mode":"plan","health":"good","nodes_online":2,"governance":"NORMAL"}
```
