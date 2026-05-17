---
title: "Arquitectura Publico-Privado de Metricas"
summary: "Split de metricas: sitio privado con datos reales via Service Token, sitio publico con JSON estatico."
order: 26
---

# Arquitectura Publico-Privado de Metricas

## Problema

El AI-LAB tiene dos sitios web:
- **Publico** (`ai-lab.labrazahome.com`) — Cloudflare Pages (estatico)
- **Privado** (`blog-ai-lab.labrazahome.com`) — Cloudflare Tunnel + Traefik + Astro preview

El sitio privado esta protegido por **Cloudflare Access (Zero Trust)**, lo que impedía que el sitio publico hiciera fetch de datos de la API desde el dominio privado.

## Solucion: Hostname Detection

Se implemento deteccion de hostname en el JavaScript para usar diferentes fuentes de datos segun el dominio:

```javascript
const isPublic = window.location.hostname === "ai-lab.labrazahome.com" 
  || window.location.hostname.includes("pages.dev");
const apiUrl = isPublic ? "/api/analytics.json" : "https://blog-ai-lab.labrazahome.com/api/analytics";
const res = await fetch(apiUrl, {
  cache: "no-store",
});
```

## Sitio Privado: Service Token + Cloudflare Access

- Las peticiones se hacen al mismo origen del blog privado: `/api/analytics`
- El browser no envía tokens de acceso manuales
- Cloudflare Access protege el sitio, no el JS del cliente
- Traefik enruta `/api/*` a `localhost:8084` (Live API)
- Datos en **tiempo real**

## Sitio Publico: JSON Estatico

- Se sirven ficheros JSON estaticos desde `public/api/analytics.json` y `public/api/status.json`
- Mismo dominio → sin CORS, sin Access, sin preflight
- Los datos son ficticios pero realistas (requests, health score, GPUs, etc.)
- Se actualizan manualmente en cada build de Cloudflare Pages

## Paginas Afectadas

| Pagina | Privado | Publico |
|--------|---------|---------|
| `/ops/` | API real + Service Token | `analytics.json` estatico |
| `/status/history/` | API real + Service Token | `analytics.json` estatico |
| `/status/gpus/` | API real via Traefik | `status.json` estatico |

## Archivos Clave

- `runtime/analytics/health_score.py` — usa `discovered_nodes` en vez de `nodes`
- `runtime/analytics/runtime_analytics.py` — usa `discovered_nodes` en vez de `nodes`
- `runtime/state/live_api.py` — handler `do_OPTIONS` para CORS preflight
- `apps/ialab-docs/src/pages/ops/index.astro` — hostname detection
- `apps/ialab-docs/src/pages/status/history/index.astro` — hostname detection + fix variable bug
- `apps/ialab-docs/src/pages/status/gpus/index.astro` — hostname detection
- `apps/ialab-docs/public/api/analytics.json` — datos dummy publicos
- `apps/ialab-docs/public/api/status.json` — datos dummy publicos

## Bugs Corregidos

1. **health_score.py**: leia `nodes[]` en vez de `discovered_nodes[]`
2. **runtime_analytics.py**: mismo error, nodos siempre 0
3. **live_api.py**: faltaba handler `do_OPTIONS` para CORS
4. **history page**: variable `r` undefined (debia ser `res`)
5. **gpus page**: fetch a `/api/analytics` en vez de `/api/status.json`
6. **Backups**: ficheros `.bak` con contaminacion de ANSI escape sequences
