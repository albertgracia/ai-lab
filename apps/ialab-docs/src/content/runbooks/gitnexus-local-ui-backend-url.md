---
title: "GitNexus UI Stuck on Waiting (Backend URL)"
summary: "Runbook: la UI de GitNexus puede quedarse en 'Waiting for server to start' desde un PC remoto por default backend URL = http://localhost:4747. Fix via localStorage o SSH tunnel."
severity: "low"
---

# GitNexus UI Stuck on “Waiting for server to start” (Backend URL)

## Síntoma

- La UI carga en `http://192.168.1.30:4747` pero se queda en **“Waiting for server to start”**.
- El backend responde:
  - `http://192.168.1.30:4747/api/health` → `{"status":"ok"}`
- `http://192.168.1.30:4747/api` puede devolver **`Cannot GET /api`** y eso es normal.
- `http://192.168.1.30:4747/socket.io/` **no** es el endpoint relevante para el bootstrap (la UI usa polling a `/api/health`).

## Root Cause

El frontend de GitNexus resuelve el backend URL así:

1. Lee `localStorage['gitnexus-backend-url']`
2. Si no existe, usa el default:
   - `http://localhost:4747`

Desde un PC remoto, `localhost` apunta al **PC del usuario**, no al servidor AI-LAB (`192.168.1.30`). Resultado: la UI nunca llega a `.../api/health` del servidor y se queda esperando.

## Fix Recomendado (DevTools)

En el navegador donde está “Waiting…”:

1. Abrir DevTools → Console y ejecutar:

```js
localStorage.setItem('gitnexus-backend-url', 'http://192.168.1.30:4747')
location.reload()
```

## Validación

En DevTools → Network, filtrar por `health`:

- Antes (falla): `http://localhost:4747/api/health`
- Después (OK): `http://192.168.1.30:4747/api/health` (HTTP 200)

## Workaround Alternativo (SSH Tunnel)

Si no quieres tocar `localStorage`, fuerza que `localhost:4747` apunte al servidor:

```bash
ssh -L 4747:127.0.0.1:4747 albert@192.168.1.30
```

Luego abrir en el PC del usuario:

- `http://127.0.0.1:4747`

## Estado Servidor Esperado

En el host `192.168.1.30`:

- `gitnexus serve --host 0.0.0.0 --port 4747`
- Puerto escuchando en `0.0.0.0:4747`
- `curl -s http://127.0.0.1:4747/api/health` → OK
- `curl -s http://192.168.1.30:4747/api/health` → OK

## Seguridad / Límites

- No tocar runtime AI-LAB.
- No reiniciar `ailab-gateway`.
- No reiniciar Prometheus/Grafana.
- GitNexus = **codebase structural truth**.
- Prometheus = **runtime authority**.
- OperationalTruth = **semantic runtime truth**.
