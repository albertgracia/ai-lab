---
title: "GitNexus UI: Fix para 'Waiting for server to start' desde un PC remoto"
date: "2026-05-23"
summary: "Root cause y fix: la UI usa por defecto localStorage['gitnexus-backend-url'] = http://localhost:4747; desde un PC remoto, localhost no es el servidor."
tags:
  - gitnexus
  - ai-lab
  - runbook
  - operations
---

# GitNexus UI: Fix para “Waiting for server to start” desde un PC remoto

Este es un fallo típico de UIs locales: el backend está vivo, pero el frontend mira al host equivocado.

## Síntoma

- Abres `http://192.168.1.30:4747` y ves **“Waiting for server to start”**.
- Pero:
  - `http://192.168.1.30:4747/api/health` → `{"status":"ok"}`
- `http://192.168.1.30:4747/api` puede responder `Cannot GET /api` (normal).
- `/socket.io/` no es el endpoint relevante para el bootstrap.

## Root Cause

El frontend de GitNexus resuelve el backend URL con esta regla:

- `localStorage['gitnexus-backend-url']`
- si no existe, default: `http://localhost:4747`

Desde un PC remoto, `localhost` apunta al PC del navegador. Por tanto, la UI intenta llegar a `http://localhost:4747/api/health` y se queda esperando, aunque el backend real esté en `192.168.1.30`.

## Fix Recomendado

En el navegador remoto:

```js
localStorage.setItem('gitnexus-backend-url', 'http://192.168.1.30:4747')
location.reload()
```

## Validación

DevTools → Network (filtrar `health`):

- Antes: `http://localhost:4747/api/health` (fail)
- Después: `http://192.168.1.30:4747/api/health` (200 OK)

## Workaround Alternativo (SSH Tunnel)

Si quieres mantener el default `localhost:4747`:

```bash
ssh -L 4747:127.0.0.1:4747 albert@192.168.1.30
```

Y abrir `http://127.0.0.1:4747`.

## Estado Servidor Esperado

- `npx gitnexus@latest serve --host 0.0.0.0 --port 4747`
- `:4747` escuchando en `0.0.0.0`
- `/api/health` OK por `127.0.0.1` y por `192.168.1.30`

## Seguridad / límites

- GitNexus = codebase structural truth.
- Prometheus = runtime authority.
- OperationalTruth = semantic runtime truth.
- Este fix no toca runtime AI-LAB ni reinicia servicios.
