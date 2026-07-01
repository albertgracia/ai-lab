---
title: "Runtime Analytics - Diagnostico y Correccion de Metricas"
summary: "Diagnostico y solucion de los 3 bugs que impedian la correcta visualizacion de metricas en el AI-LAB Command Center: health score, nodos online y gateway health check."
order: 25
---

# Runtime Analytics — Diagnostico y Correccion de Metricas

## Resumen

El AI-LAB Command Center (`/ops/`) mostraba metricas incorrectas:
- Health Score en **20/critical** en vez de ~70/good
- **0/2 GPUs** y **0/2 nodos online** cuando ambos nodos GPU estaban operativos
- **"Gateway down"** y **"High latency"** como razones del health score

## Bug 1: health_score.py leia nodos incorrectos

### Causa

El fichero `cluster_state.json` contiene **dos listas distintas** de nodos:

- `nodes[]` — usada por el heartbeat/exponential backoff. Los nodos se marcan como `online: false` y `status: "backoff_skip"` tras fallos consecutivos, incluso cuando ya estan operativos de nuevo.
- `discovered_nodes[]` — generada por el descubrimiento periodico. Contiene el **estado real** de cada nodo con latencia, modelos y capacidades.

`health_score.py` y `runtime_analytics.py` leian de `nodes[]`, obteniendo siempre 0 nodos online.

### Solucion

Ambos modulos ahora leen de `discovered_nodes[]` con fallback a `nodes[]`:

```python
discovered = state.get("discovered_nodes", [])
nodes = discovered if discovered else state.get("nodes", [])
```

### Impacto

| Antes | Despues |
|-------|---------|
| 0/2 GPUs online | 2/2 GPUs online |
| -60 penalty | 0 penalty |

## Bug 2: Gateway health check endpoint incorrecto

### Causa

`health_score.py` verificaba el gateway con:

```python
curl http://localhost:8008/health  # -> HTTP 404
```

El gateway OpenAI-compatible **no tiene endpoint `/health`**. La raiz `/` tambien devuelve 404. El chequeo fallaba siempre, restando -15 puntos con la razon "Gateway down".

### Solucion

Cambiado a `/metrics` que es un endpoint real del gateway:

```python
curl http://localhost:8008/metrics  # -> HTTP 200
```

### Impacto

| Antes | Despues |
|-------|---------|
| "Gateway down" (-15) | Sin penalizacion |

## Bug 3: runtime_analytics.py nodos siempre 0

### Causa

El `get_aggregated()` en `runtime_analytics.py` usaba `state.get("nodes", [])` (mismo problema que Bug 1), por lo que el dashboard mostraba "Nodos Online: 0" y "Total: 0".

### Solucion

Misma correccion que Bug 1: usar `discovered_nodes` prioritariamente.

### Impacto

| Antes | Despues |
|-------|---------|
| Nodos Online: 0 | Nodos Online: 2 |
| Total: 0 | Total: 3 |

## Archivos Modificados

- `runtime/analytics/health_score.py` — corregido acceso a nodos + endpoint health check
- `runtime/analytics/runtime_analytics.py` — corregido acceso a nodos
- `runtime/state/live_api.py` — anadido handler CORS `do_OPTIONS` para peticiones cross-origin

## Resultado Final

Health Score: **70/good** (antes 20/critical)
GPUs online: **2/2**
Nodos online: **2/3** (1 nodo 1.250 offline por configuracion)
Razones: **ninguna**
