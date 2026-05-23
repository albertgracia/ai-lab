---
title: "GitNexus UI Local Access (Backend URL Fix)"
summary: "Por qué GitNexus UI puede quedarse en 'Waiting for server to start' cuando se accede remotamente y cómo fijar el backend URL (localStorage) o usar SSH tunnel."
order: 55
---

# GitNexus UI: Acceso Local vs Remoto (Backend URL Fix)

## Problema

Puedes abrir la UI en `http://192.168.1.30:4747`, pero aun así ver:

- **Waiting for server to start**

Mientras tanto el backend está bien:

- `GET /api/health` devuelve `{"status":"ok"}`.

Notas:

- `GET /api` devolviendo `Cannot GET /api` es normal.
- `/socket.io/` no es la señal de salud relevante para el bootstrap.

## Root Cause (localhost)

La UI de GitNexus toma el backend base URL desde:

- `localStorage['gitnexus-backend-url']`

Si esa clave no existe, usa:

- `http://localhost:4747`

Desde un PC remoto, `localhost` apunta al PC del usuario. Por eso la UI intenta `http://localhost:4747/api/health` y falla, aunque `http://192.168.1.30:4747/api/health` funcione.

## Fix Recomendado

En el navegador remoto:

```js
localStorage.setItem('gitnexus-backend-url', 'http://192.168.1.30:4747')
location.reload()
```

## Validación

DevTools → Network:

- Antes: request a `http://localhost:4747/api/health` (fail)
- Después: request a `http://192.168.1.30:4747/api/health` (200 OK)

## Workaround: SSH Tunnel

Si necesitas mantener el default `localhost:4747`:

```bash
ssh -L 4747:127.0.0.1:4747 albert@192.168.1.30
```

Abrir:

- `http://127.0.0.1:4747`

## Estado Servidor Esperado

En el host AI-LAB:

- `npx gitnexus@latest serve --host 0.0.0.0 --port 4747`
- `ss -tlnp | grep 4747` muestra `0.0.0.0:4747`
- `/api/health` OK por `127.0.0.1` y por `192.168.1.30`

## Límites

- GitNexus es **codebase structural truth**.
- Prometheus sigue siendo **runtime authority**.
- Este fix es UI/cliente, no cambia el runtime.
