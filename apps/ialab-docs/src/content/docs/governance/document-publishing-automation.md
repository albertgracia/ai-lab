---
title: "Document Publishing Automation"
summary: "Pipeline automatizado de publicación documental: Astro público (Cloudflare Pages), Astro privado (ailab-docs local), reindex AnythingLLM y smoke queries. Orquestador invoke-phase-closure con flags DryRun/Skip/SudoPassword."
order: 6
---

## Visión general

El pipeline de Document Publishing Automation cierra el ciclo documental de AI-LAB. Cuando una fase modifica documentación en `apps/ialab-docs/`, el pipeline ejecuta en orden:

1. **Public Astro** — build, secret scan, commit, push a GitHub, espera despliegue de Cloudflare Pages, valida URLs clave
2. **Private Astro** — SSH a `192.168.1.30`, git pull, npm install, npm run build, sudo systemctl restart ailab-docs, valida URLs vía localhost:4322
3. **AnythingLLM Reindex** — reindexa el workspace `ai-lab-core` vía API con batch controlado, exclusiones y modo incremental
4. **AnythingLLM Smoke Queries** — 2-3 preguntas representativas validadas contra AnythingLLM

Cada etapa es independiente y puede saltarse con flags. Cualquier fallo detiene el pipeline y genera un audit report en `docs/audits/`.

## Arquitectura

```
Fase cierra cambios en apps/ialab-docs/
  → invoke-phase-closure.ps1
    ├── publish-astro-public.ps1    (commit + push → Cloudflare)
    ├── publish-astro-private.ps1   (SSH → build → restart → validate)
    ├── reindex-workspace.ps1       (AnythingLLM API → batch reindex)
    └── smoke-queries.ps1           (preguntas → validación)
```

### Superficies web

| Superficie | URL | Método de despliegue |
|---|---|---|
| Público | `https://ai-lab.labrazahome.com` | GitHub push → Cloudflare Pages (auto) |
| Privado | `https://blog-ai-lab.labrazahome.com` | SSH → systemd ailab-docs en 192.168.1.30:4322 |
| Métricas | `https://metricas.labrazahome.com` | Next.js SSR (NO incluido en este pipeline) |

## Scripts

### `invoke-phase-closure.ps1` — Orquestador

```
Usage: .\scripts\phase-closure\invoke-phase-closure.ps1 -PhaseName "NOMBRE" [flags]

Flags:
  -PhaseName <string>        Nombre obligatorio de la fase (se usa en commit y audit)
  -DryRun                    Valida prerequisitos sin hacer cambios
  -SkipPublic                Salta publicación Astro público
  -SkipPrivate               Salta publicación Astro privado
  -SkipReindex               Salta reindex AnythingLLM y smoke queries
  -BuildOnly                 Solo build privado (sin restart ailab-docs)
  -SudoPassword <string>     Password sudo para restart en .30 (o $env:AILAB_SUDO_PASSWORD)
  -AnythingLLMApiKey <string> API key (o $env:ANYTHINGLLM_API_KEY)
```

Ejemplo DryRun:
```
.\scripts\phase-closure\invoke-phase-closure.ps1 -PhaseName "FASE-XX" -DryRun
```

Ejemplo Apply completo:
```
$env:AILAB_SUDO_PASSWORD = "mipassword"
$env:ANYTHINGLLM_API_KEY = "sk-..."
.\scripts\phase-closure\invoke-phase-closure.ps1 -PhaseName "FASE-XX"
```

### `publish-astro-public.ps1` — Astro público (Cloudflare)

```
Flags: -NoPush (build local sin commit/push), -PushOnly (solo commit/push sin build local)
```

Pasos:
1. `npm run build` en `apps/ialab-docs/`
2. Secret scan en `dist/` (busca claves API)
3. `git status` para verificar cambios
4. `git add -A && git commit -m "feat(docs): ..."`
5. `git push origin main`
6. Espera hasta 300s a que Cloudflare Pages despliegue (poll cada 15s)
7. Valida 4 URLs públicas (200 OK)

### `publish-astro-private.ps1` — Astro privado (ailab-docs)

```
Flags: -BuildOnly (SSH + build sin restart), -SudoPassword
```

Pasos:
1. SSH a `albert@192.168.1.30` (requiere key SSH configurada)
2. `git status` en `/opt/ai-lab`
3. `git pull --ff-only`
4. `npm install` en `apps/ialab-docs`
5. `npm run build` (264 páginas, ~12s)
6. `sudo systemctl restart ailab-docs` (requiere password sudo o NOPASSWD)
7. Valida 4 URLs vía `localhost:4322`

## Criterios de cierre

| Resultado | Condición |
|---|---|
| **PASS** | Todas las etapas completadas sin error. URLs 200, build OK, reindex OK, smoke queries OK |
| **WARN** | Alguna etapa saltada o con advertencias (API key no configurada, sudo password no disponible) |
| **FAIL** | Cualquier etapa falla (build broken, push rechazado, URLs no responden 200, reindex falla) |

El pipeline es secuencial: si public Astro falla, no continúa a private ni reindex. Cada etapa reporta PASS/FAIL/WARN independientemente. El audit report se genera siempre, incluso en FAIL.

## Configuración

Toda la configuración compartida está en `scripts/phase-closure/config.ps1`:

| Variable | Default | Descripción |
|---|---|---|
| AILAB_SSH_HOST | 192.168.1.30 | Host privado Astro |
| AILAB_SSH_USER | albert | Usuario SSH |
| AILAB_REMOTE_REPO | /opt/ai-lab | Ruta del repo en .30 |
| PUBLIC_ASTRO_URL | https://ai-lab.labrazahome.com | URL pública |
| PRIVATE_ASTRO_LOCAL_URL | http://127.0.0.1:4322 | URL privada local |
| CLOUDFLARE_DEPLOY_TIMEOUT_SECONDS | 300 | Timeout espera Cloudflare |
| ANYTHINGLLM_BASE_URL | http://192.168.1.50:3001 | URL AnythingLLM |
| ANYTHINGLLM_WORKSPACE | ai-lab-core | Workspace AnythingLLM |

## Validaciones

El pipeline valida 4 URLs representativas tanto en público como en privado tras cada despliegue:

| Ruta | Contenido |
|---|---|
| `/docs/governance/phase-closure-protocol/` | Protocolo de cierre de fase |
| `/docs/governance/anythingllm-reindex-automation/` | Automatización reindex |
| `/docs/architecture/anythingllm-role/` | Rol de AnythingLLM |
| `/blog/017-anythingllm-memoria-documental/` | Blog sobre memoria documental |

Todas deben responder HTTP 200. Si alguna falla, la etapa se marca como FAIL y el pipeline se detiene.

## Prerequisitos

- Git repo local con `origin` configurado (push a GitHub)
- SSH key configurada para `albert@192.168.1.30` (sin contraseña interactiva)
- Sudo NOPASSWD en .30 para `systemctl restart ailab-docs`, o password vía `$env:AILAB_SUDO_PASSWORD`
- `$env:ANYTHINGLLM_API_KEY` para reindex AnythingLLM
- Astro `npm run build` funcional en ambos entornos
- Cloudflare Pages conectado al repo GitHub

## Relación con otros documentos

| Documento | Relación |
|---|---|
| `phase-closure-protocol.md` | Define cuándo y cómo cerrar una fase. Este pipeline automatiza pasos 3-5 del protocolo. |
| `anythingllm-reindex-automation.md` | Documenta el script de reindex AnythingLLM usado por este pipeline. |
| `ASTRO-DEPLOYMENT-GOVERNANCE.md` | Define las superficies web y reglas de despliegue que este pipeline ejecuta. |

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 01 | 2026-06-11 | Versión inicial del pipeline de automatización documental |
