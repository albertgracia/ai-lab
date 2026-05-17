---
title: "Implementacion — Astro + Cloudflare Pages + GitHub"
summary: "Arquitectura de despliegue del portal AI-LAB con dos blogs (publico y privado), sincronizacion automatica via GitHub y Cloudflare Pages."
order: 22
---

# Implementacion — Astro + Cloudflare Pages + GitHub

## Arquitectura General

El portal AI-LAB utiliza dos canales de publicacion independientes que comparten
el mismo codigo fuente.

```
                            ┌─────────────────┐
                            │  GitHub Repo    │
                            │ albertgracia/   │
                            │ ai-lab          │
                            └────────┬────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
          ┌─────────────────┐ ┌────────────┐ ┌──────────────┐
          │ Cloudflare Pages│ │ Cloudflare │ │ Servidor    │
          │ (Build automatico│ │ Tunnel     │ │ 192.168.1.30 │
          │  desde GitHub)  │ │            │ │             │
          └────────┬────────┘ └─────┬──────┘ └──────┬───────┘
                   │                │                │
                   ▼                ▼                ▼
          ┌─────────────────┐ ┌────────────┐ ┌──────────────┐
          │ Blog Publico    │ │ Traefik    │ │ Astro Preview│
          │ ai-lab.labrazah │ │ Reverse    │ │ :4322        │
          │ ome.com         │ │ Proxy      │ │              │
          └─────────────────┘ └────────────┘ └──────────────┘
                                        │
                                        ▼
                               ┌─────────────────┐
                               │ Blog Privado    │
                               │ blog-ai-lab.labr│
                               │ azahome.com     │
                               └─────────────────┘
```

## Componentes

### 1. GitHub Repository
- **Repo:** `github.com/albertgracia/ai-lab`
- **Rama:** `main`
- **Contenido:** Codigo fuente Astro en `apps/ialab-docs/`
- **Trigger:** Cada push a `main` activa Cloudflare Pages

### 2. Cloudflare Pages (Blog Publico)
- **URL:** `https://ai-lab.labrazahome.com`
- **Build:** Automatico desde GitHub (push a main)
- **Comando:** `npm run build` en `apps/ialab-docs/`
- **Directorio publicacion:** `apps/ialab-docs/dist/`
- **SSL:** Automatico (Cloudflare)
- **Cache:** Purga manual via Cloudflare Dashboard

### 3. Cloudflare Tunnel + Traefik (Blog Privado)
- **URL:** `https://blog-ai-lab.labrazahome.com`
- **Tunnel:** Cloudflare Tunnel (docker en 192.168.1.40)
- **Proxy:** Traefik (docker en 192.168.1.30)
- **Backend:** Astro preview en `:4322`
- **Servicio:** `ailab-docs.service` (systemd)
- **API:** `/api/*` disponible via Traefik → `:8084`

### 4. Servidor Local (192.168.1.30)
- **Servicio:** `ailab-docs.service` (systemd, autoarranque)
- **Comando:** `astro preview --host 0.0.0.0 --port 4322`
- **Build:** Manual via `npm run build`
- **Contenido:** Mismo `dist/` que Cloudflare Pages

## Flujo de Publicacion

### Para actualizar contenido:
```bash
# 1. Crear o modificar documento en:
#    apps/ialab-docs/src/content/
# 2. Construir localmente
cd /opt/ai-lab/apps/ialab-docs && npm run build

# 3. Commit y push a GitHub
cd /opt/ai-lab
git add apps/ialab-docs/
git commit -m "docs: descripcion del cambio"
git push origin main
```

### Efectos del push:
| Sitio | Efecto | Tiempo |
|---|---|---|
| Blog Publico | Cloudflare Pages rebuild automatico | ~1-2 min |
| Blog Privado | GitHub Actions runner rebuild + restart automatico | ~20-30 s |

### Para forzar el blog privado manualmente, si hace falta:
```bash
cd /opt/ai-lab/apps/ialab-docs && npm run build
echo 19682507 | sudo -S systemctl restart ailab-docs.service
```

## Configuracion Clave

### Cloudflare Pages (Dashboard)
```
Build command:     npm run build
Build directory:   apps/ialab-docs
Output directory:  dist
Root directory:    apps/ialab-docs
Node version:      22 (por defecto)
```

### Traefik (blog privado)
```yaml
# /opt/ai-lab/data/traefik/dynamic/ai-lab-docs.yml
http:
  routers:
    ai-lab-docs:
      rule: "Host(`blog-ai-lab.labrazahome.com`)"
      service: ai-lab-docs
    ai-lab-docs-api:
      rule: "Host(`blog-ai-lab.labrazahome.com`) && PathPrefix(`/api/`)"
      service: ai-lab-docs-api
      priority: 10
  services:
    ai-lab-docs:
      loadBalancer:
        servers:
          - url: "http://host.docker.internal:4322"
    ai-lab-docs-api:
      loadBalancer:
        servers:
          - url: "http://host.docker.internal:8084"
```

### Cloudflare DNS
```
ai-lab.labrazahome.com       → Cloudflare Pages (CNAME)
blog-ai-lab.labrazahome.com  → Cloudflare Tunnel (CNAME)
```

## Diferencia entre ambos blogs

| Aspecto | Publico | Privado |
|---|---|---|
| URL | ai-lab.labrazahome.com | blog-ai-lab.labrazahome.com |
| Autenticacion | No | Cloudflare Access (opcional) |
| Build | Automatico (Cloudflare) | Manual (local) |
| API | No disponible | Disponible (`/api/*`) |
| Actualizacion | Push a GitHub | Rebuild + restart servicio |
| Latencia | ~2 min desde push | 0s (local) |

## Verificacion post-despliegue

```bash
# Verificar build local
cd /opt/ai-lab/apps/ialab-docs && npm run build 2>&1 | tail -5
# Debe mostrar: "64 page(s) built" sin errores

# Verificar servicio
echo 19682507 | sudo -S systemctl is-active ailab-docs.service

# Verificar sitio privado
curl -s http://localhost:4322/ | head -1

# Verificar sitio publico (externa)
curl -s https://ai-lab.labrazahome.com/ | head -1
```
