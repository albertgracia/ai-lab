---
title: "Arquitectura Publico-Privado de Metricas"
summary: "Split de metricas: sitio privado con datos reales via Service Token, sitio publico con JSON estatico."
order: 26
---


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

---

## Separación de documentación Astro (Julio 2026)

AI-LAB Docs también implementa separación público/privado para su documentación técnica en Astro/Starlight.

### Arquitectura

Contenido público (`ai-lab.labrazahome.com`) y privado (`blog-ai-lab.labrazahome.com`) comparten el mismo codebase en `apps/ialab-docs/src/content/docs/`. La separación se logra mediante un **build filter** que elimina paths PRIVATE_ONLY antes del build público.

### Mecanismo

1. **Clasificación:** Cada página se etiqueta como `PUBLIC_SAFE` o `PRIVATE_ONLY` según su sensibilidad (IPs internas, puertos, runbooks, secretos).
2. **Build filter:** `scripts/private-content-filter.json` define 33+ paths PRIVATE_ONLY que se eliminan temporalmente antes del build público vía `scripts/build-public-wrapper.mjs`.
3. **Restauración:** Tras el build público, los archivos se restauran automáticamente con `git checkout`.
4. **Sidebar condicional:** La variable `AILAB_PUBLIC_BUILD` oculta secciones privadas (Runbooks, Incidents, Historical) en el sidebar de Starlight.
5. **Redirects edge:** `public/_redirects` bloquea rutas privadas en Cloudflare Pages.

### Cobertura

| Métrica | Público | Privado |
|---------|---------|---------|
| Páginas | 171 (filtradas) | 277 (completas) |
| IPs internas | 0 (validado con grep) | Presentes donde aplica |
| Sidebar | Sin Runbooks/Incidents/Historical | Completo |

### Scripts

- `scripts/build-public-wrapper.mjs` — wrapper que filtra y restaura automáticamente
- `scripts/private-content-filter.json` — catálogo de 33+ paths PRIVATE_ONLY
- `scripts/build-public-filter.mjs` — filter standalone (deprecated)
- `package.json`: `build:public` y `build:private`

### Pipeline CI/CD

- `scripts/phase-closure/publish-astro-public.ps1` — build público + deploy Cloudflare
- `scripts/phase-closure/publish-astro-private.ps1` — build privado + deploy local

---

## Archivos Clave

- `runtime/analytics/health_score.py` — usa `discovered_nodes` en vez de `nodes`
- `runtime/analytics/runtime_analytics.py` — usa `discovered_nodes` en vez de `nodes`
- `runtime/state/live_api.py` — handler `do_OPTIONS` para CORS preflight
- `apps/ialab-docs/src/pages/ops/index.astro` — hostname detection
- `apps/ialab-docs/src/pages/status/history/index.astro` — hostname detection + fix variable bug
- `apps/ialab-docs/src/pages/status/gpus/index.astro` — hostname detection
- `apps/ialab-docs/public/api/analytics.json` — datos dummy publicos
- `apps/ialab-docs/public/api/status.json` — datos dummy publicos
- `apps/ialab-docs/scripts/build-public-wrapper.mjs` — build filter wrapper
- `apps/ialab-docs/scripts/private-content-filter.json` — 33+ entries PRIVATE_ONLY
- `apps/ialab-docs/astro.config.mjs` — sidebar condicional via AILAB_PUBLIC_BUILD
- `apps/ialab-docs/public/_redirects` — bloqueo de rutas privadas en edge

## Bugs Corregidos

1. **health_score.py**: leia `nodes[]` en vez de `discovered_nodes[]`
2. **runtime_analytics.py**: mismo error, nodos siempre 0
3. **live_api.py**: faltaba handler `do_OPTIONS` para CORS
4. **history page**: variable `r` undefined (debia ser `res`)
5. **gpus page**: fetch a `/api/analytics` en vez de `/api/status.json`
6. **Backups**: ficheros `.bak` con contaminacion de ANSI escape sequences
