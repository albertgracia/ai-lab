# AI-LAB ASTRO DEPLOYMENT GOVERNANCE

**Estado:** CANONICO
**Ultima actualizacion:** 2026-05-31
**Autoridad:** Operador AI-LAB

---

## OBJETIVO

Este documento define la arquitectura oficial de documentacion Astro, Metrics Dashboard
y despliegue dentro de AI-LAB.

Todo agente debe leer este documento ANTES de modificar:

- `apps/ialab-docs` (Astro)
- `apps/metrics-dashboard` (Next.js)
- Cloudflare Pages (ai-lab.labrazahome.com)
- Operations Center / Status Pages
- Runbooks / Blog tecnico / Navegacion / Documentacion publica
- systemd: `ailab-docs`, `ailab-metrics`

---

## VISION GENERAL

AI-LAB utiliza TRES superficies web independientes:

| Superficie | URL | Stack | Tipo |
|------------|-----|-------|------|
| Documentacion privada | `blog-ai-lab.labrazahome.com` | Astro + systemd + Traefik | Privado |
| Documentacion publica | `ai-lab.labrazahome.com` | Astro + Cloudflare Pages | Publico |
| Metricas live | `metricas.labrazahome.com` | Next.js SSR + systemd + Traefik | Privado |

NO deben tratarse como un unico sistema.

---

## ENTORNO 1: PRIVADO (CANONICO)

**Estado:** PRODUCCION INTERNA

### Localizacion

```
/opt/ai-lab/apps/ialab-docs
```

### Servicio systemd

```ini
[Unit]
Description=AI-LAB Astro Documentation Portal (Preview)
After=network-online.target

[Service]
Type=simple
User=albert
WorkingDirectory=/opt/ai-lab/apps/ialab-docs
ExecStart=/usr/bin/npx astro preview --host 0.0.0.0 --port 4322
Restart=always
RestartSec=5
MemoryMax=512M
Environment=NODE_ENV=production
```

- **Unidad:** `ailab-docs.service`
- **Puerto:** 4322 (localhost)
- **Comando:** `astro preview` (Sirve el build estatico pre-generado)
- **Usuario:** albert
- **Memoria maxima:** 512 MB

### Stack tecnologico

- Framework: **Astro** v6.3.1
- UI: **Starlight**, **React**, **Tailwind CSS v4**
- Diagramas: **Mermaid**, **Cytoscape**
- Graficos: **Recharts**

### Configuracion Astro

```js
// astro.config.mjs
site: "https://ai-lab.labrazahome.com",
server: {
  host: true,
  allowedHosts: ["blog-ai-lab.labrazahome.com"],
}
```

### Proposito

- Documentacion operativa real
- Runbooks, Arquitectura, Observabilidad
- Operations Center, Estado vivo, Snapshots
- Gobierno tecnico, Procedimientos internos, Auditorias
- Blog tecnico interno

### Acceso

**Privado** solo red interna.

Este entorno es la **fuente de verdad** de la documentacion Astro.

---

## ENTORNO 2: PUBLICO (CLOUDFLARE PAGES)

**Estado:** PUBLICACION CONTROLADA

### Datos del proyecto

| Atributo | Valor |
|----------|-------|
| Repositorio | `https://github.com/albertgracia/ai-lab` |
| Proyecto Cloudflare | `ai-lab` |
| Root directory | `apps/ialab-docs` |
| Build command | `npm run build` |
| Output directory | `dist` |
| Framework preset | Astro |
| Dominio publico | `https://ai-lab.labrazahome.com` |

### Flujo de despliegue

```
Git push (main)
  → GitHub webhook
    → Cloudflare Pages build (npm run build)
      → output en dist/
        → publicado en ai-lab.labrazahome.com
```

### Proposito

- Blog tecnico, Articulos, Documentacion publica
- Divulgacion, Casos de estudio, Arquitectura compartible

### Restriccion

Este entorno **NO es la fuente de verdad**. Es una publicacion derivada.
El contenido publico puede diferir del privado.

---

## METRICS DASHBOARD (Next.js SSR)

**Estado:** PRODUCCION INTERNA

### Localizacion

```
/opt/ai-lab/apps/metrics-dashboard
```

### Servicio systemd

```ini
[Unit]
Description=AI-LAB Metrics Dashboard (Next.js SSR)
After=network.target ailab-live-api.service

[Service]
Type=exec
User=albert
WorkingDirectory=/opt/ai-lab/apps/metrics-dashboard
ExecStart=/opt/ai-lab/apps/metrics-dashboard/node_modules/.bin/next start --port 3010
Restart=always
RestartSec=5
TimeoutStopSec=10
```

- **Unidad:** `ailab-metrics.service`
- **Puerto:** 3010 (localhost)
- **Comando:** `next start` (SSR, no estatico)
- **Depende de:** `ailab-live-api.service` (consume datos del runtime)
- **Usuario:** albert

### Stack tecnologico

- Framework: **Next.js** (SSR)
- UI: **React**, **shadcn/ui**, **Tailwind CSS**
- Datos: consume `ailab-live-api` local para metricas en tiempo real

### Proposito

- Dashboard de metricas operativas live
- `/ops` → estado operacional
- `/gpus` → telemetria GPUs
- `/runtime` → telemetria runtime

### Acceso

**Privado** via `metricas.labrazahome.com` (Traefik reverse proxy).

Nunca exponer metricas reales en el sitio publico.

---

## FLUJO DE RED (TRAEFIK)

Traefik actua como reverse proxy para todos los servicios web internos.

### Configuracion

```
/opt/ai-lab/stacks/traefik/docker-compose.yml
/opt/ai-lab/data/traefik/acme.json    ← certificados SSL
/opt/ai-lab/data/traefik/dynamic/     ← configuracion dinamica
```

### Puertos expuestos

| Puerto | Uso |
|--------|-----|
| 80 | HTTP (redirecciona a 443) |
| 443 | HTTPS |
| 8080 | Dashboard Traefik (interno) |

### Routing conocido

| Dominio | Backend | Puerto |
|---------|---------|--------|
| `blog-ai-lab.labrazahome.com` | `ailab-docs` (Astro preview) | 4322 |
| `metricas.labrazahome.com` | `ailab-metrics` (Next.js SSR) | 3010 |
| `ai-lab.labrazahome.com` | Cloudflare Pages (externo) | — |

### Volumen de configuracion dinamica

```
/opt/ai-lab/data/traefik/dynamic/ → montado en /dynamic en el contenedor
```

Traefik usa **file provider** para rutas que no pueden definirse via Docker labels.

---

## SERVICIOS SYSTEMD AI-LAB

El servidor 192.168.1.30 ejecuta los siguientes servicios systemd:

| Unidad | Puerto | Proposito |
|--------|--------|-----------|
| `ailab-docs.service` | 4322 | Astro docs privado |
| `ailab-metrics.service` | 3010 | Next.js metrics dashboard |
| `ailab-gateway.service` | 8008 | OpenAI-compatible gateway |
| `ailab-router.service` | 8083 | Model router API |
| `ailab-live-api.service` | 8084 | Live runtime API |
| `ailab-live-state.service` | — | Live state sync |
| `ailab-heartbeat.service` | — | Heartbeat monitor |
| `ailab-mcp-semantic-gateway.service` | — | MCP semantic gateway |
| `ailab-runner.service` | — | Actions runner |
| `ailab-traefik.service` | — | Traefik Docker (via compose) |

---

## FLUJO COMPLETO DE DESPLIEGUE

### Flujo privado (blog-ai-lab.labrazahome.com)

```
1. npm run build           ← genera dist/ en /opt/ai-lab/apps/ialab-docs
2. sudo systemctl restart ailab-docs  ← sirve dist/ via astro preview :4322
3. curl -I http://127.0.0.1:4322/    ← verificar que responde
4. Traefik recibe blog-ai-lab...:443 → proxy reverse → localhost:4322
```

### Flujo publico (ai-lab.labrazahome.com)

```
1. git add / git commit / git push  ← sube cambios a GitHub
2. Cloudflare Pages detecta push    ← automatico
3. npm run build en Cloudflare      ← genera dist/
4. Cloudflare publica dist/         ← en ai-lab.labrazahome.com
```

### Flujo metricas (metricas.labrazahome.com)

```
1. npm run build          ← genera .next/ en /opt/ai-lab/apps/metrics-dashboard
2. sudo systemctl restart ailab-metrics  ← next start :3010
3. Traefik recibe metricas...:443 → proxy reverse → localhost:3010
4. Next.js SSR consulta ailab-live-api para datos en tiempo real
```

---

## REGLA FUNDAMENTAL

**PRIVADO** = SISTEMA MAESTRO

**PUBLICO** = PUBLICACION CONTROLADA

Nunca asumir que ambos deben contener exactamente el mismo contenido.

---

## RESTRICCIONES DE PUBLICACION

### Prohibido en sitio publico

- IPs privadas (192.168.x.x, 10.x.x.x)
- Hosts internos, nombres de servicios internos
- Endpoints privados
- Metricas sensibles, health scores en tiempo real
- Datos de observabilidad interna

### Metrics Dashboard

- Las metricas reales **viven fuera de Astro**
- No deben copiarse, duplicarse ni publicarse en Astro
- Solo accesibles via `metricas.labrazahome.com`

### Operations Center / Status Pages (Privado)

Puede mostrar: estado real, dashboards, metricas, alertas, info operativa.

### Operations Center / Status Pages (Publico)

Solo snapshots seguros. Nunca informacion operacional sensible.

---

## ERRORES CONOCIDOS

### Error historico: snapshot_unavailable

**Causa raiz:**

Cloudflare Pages ejecutaba `fetch()` contra `http://127.0.0.1:8008/metrics` durante
el build estatico de Astro. En el entorno de Cloudflare (sin acceso a la red interna),
el fetch fallaba con `TypeError: fetch failed`.

**Impacto:**

- Build publico roto
- Status page publica mostraba "snapshot_unavailable"
- Bloqueaba despliegues de Cloudflare Pages

**Sintoma:**

```
TypeError: fetch failed
  at fetch (node:internal/digest/...)
  at getMetricsSnapshot
```

**Solucion aplicada:**

1. Separar la generacion de snapshots del build de Astro
2. Generar snapshots estaticos anticipadamente (no durante el build)
3. Astro publico solo consume archivos JSON pre-generados en `public/`
4. Ningun fetch a localhost, 127.0.0.1 ni 192.168.x.x durante build estatico

**Leccion:**

Nunca depender de servicios locales (localhost, 127.0.0.1, IPs internas) durante
el build de Cloudflare Pages. El entorno de build no tiene acceso a la red privada.

---

## VALIDACION OBLIGATORIA (PRE-COMMIT)

Antes de cualquier Pull Request o Commit que modifique Astro:

### Validación técnica

1. `npm run build` en `/opt/ai-lab/apps/ialab-docs`
2. Revisar rutas Astro (ningun enlace roto)
3. Verificar generacion de archivos estaticos:
   - `/api/status.json`
   - `/api/history.json`
4. Verificar que NO existan fetch a:
   - `localhost`
   - `127.0.0.1`
   - `192.168.x.x`
   durante build estatico
5. Verificar que Cloudflare Pages pueda construir sin dependencias externas

### Validación funcional (ASTRO-VALIDATION-RULE)

Build PASS + Deploy PASS no es suficiente. Debe verificarse el contenido visible:

1. **Home** — refleja los cambios solicitados
2. **Architecture** — representa el estado actual
3. **Documentation landing** — nuevas secciones visibles
4. **Roadmap** — solo Implementado / En progreso / Planificado
5. **Blog** — entrada nueva si el estado del laboratorio cambió
6. **Producción real** — verificar `ai-lab.labrazahome.com` y `blog-ai-lab.labrazahome.com`
7. **Public/Private** — confirmar separación correcta

Si cualquiera falla → **FAIL**. No aceptar PASS.

Documento completo: `docs/governance/ASTRO-VALIDATION-RULE.md`

---

## REGLAS PARA AGENTES

Antes de modificar Astro o Metrics Dashboard:

1. **Leer este documento** obligatoriamente
2. Determinar que superficies afecta el cambio:
   - Privado (blog-ai-lab.labrazahome.com)
   - Publico (ai-lab.labrazahome.com)
   - Metricas (metricas.labrazahome.com)
   - Varias
3. Explicar explicitamente el impacto
4. Validar build local (`npm run build`)
5. Si el cambio toca metricas live: verificar `metricas.labrazahome.com`

### Cambios prohibidos (sin autorizacion explicita)

- DNS
- Cloudflare Tunnel / Access / Pages Settings
- Dominios, Certificados
- Metricas reales, Endpoints internos

### Cambios permitidos

- Runbooks, Blog tecnico, Documentacion
- Navegacion, UX, Contenido editorial
- Snapshots seguros (estaticos, pre-generados)

---

## SOURCE OF TRUTH

Orden de autoridad:

1. **Operador humano**
2. **Este documento**
3. Arquitectura AI-LAB
4. Resto de documentacion

En caso de duda:

**NO IMPLEMENTAR.** Solicitar aclaracion al operador.

---

## ULTIMA LECCION APRENDIDA

**Incidente:** Cloudflare Pages build failure por dependencia de endpoint local
(`fetch(http://127.0.0.1:8008/metrics)` durante build).

**Impacto:** Status publico roto, snapshot_unavailable, despliegues bloqueados.

**Correccion:** Snapshots estaticos, separacion publico/privado, este documento.

**Esta leccion NO debe repetirse.**
