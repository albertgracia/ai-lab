# AI-LAB-ASTRO-PRIVATE-DOCS-SYNC-01

**Estado:** PASS  
**Fecha:** 2026-06-11  
**Fase:** AI-LAB-ASTRO-PRIVATE-DOCS-SYNC-01  
**Tag:** — (controlled deploy)

---

## Resumen

Sincronización de `/opt/ai-lab` en `192.168.1.30` con `origin/main` (`f4f37c44`), build Astro y restart de `ailab-docs` para que `blog-ai-lab.labrazahome.com` refleje los cambios documentales.

## Pre-requisitos

| Check | Resultado |
|-------|-----------|
| SSH access a 192.168.1.30 | ✅ albert@ |
| `git status` | ✅ Clean — no cambios inesperados |
| HEAD local | `8bf31182` (atrás de origin/main) |
| `git remote -v` | ✅ `origin git@github.com:albertgracia/ai-lab.git` |
| Rama | ✅ `main` |

## Ejecución

### 1. Backup

| Paso | Resultado |
|------|-----------|
| `cp -a dist dist.rollback-*` | ✅ Backup creado |

### 2. Pull

| Paso | Resultado |
|------|-----------|
| `git pull --ff-only origin main` | ✅ `8bf31182..f4f37c44` fast-forward |
| Nuevo HEAD | `f4f37c44` — `chore: add .vs/ to .gitignore` |
| Archivos actualizados | 23 files, 2069 inserciones |

### 3. Build

| Paso | Resultado |
|------|-----------|
| `npm run build` | **PASS** — 264 pages, 0 errors |
| Página nueva | `/blog/017-anythingllm-memoria-documental/index.html` ✅ |
| Página nueva | `/docs/architecture/anythingllm-role/index.html` ✅ |
| Página nueva | `/docs/governance/anythingllm-reindex-automation/index.html` ✅ |
| Página nueva | `/docs/governance/phase-closure-protocol/index.html` ✅ |

### 4. Restart

| Paso | Resultado |
|------|-----------|
| `sudo systemctl restart ailab-docs` | ✅ Active (running), PID 1195438, port 4322 |

### 5. Validación (curl localhost:4322)

| URL | HTTP | Title |
|-----|------|-------|
| `/blog/017-anythingllm-memoria-documental/` | **200** ✅ | `AnythingLLM como memoria documental de AI-LAB` |
| `/docs/architecture/anythingllm-role/` | **200** ✅ | `AnythingLLM — Memoria Documental de AI-LAB` |
| `/docs/governance/anythingllm-reindex-automation/` | **200** ✅ | `AnythingLLM Reindex Automation` |
| `/docs/governance/phase-closure-protocol/` | **200** ✅ | `AI-LAB Phase Protocol 01` |
| `/` (homepage) | **200** ✅ | — |

## Rollback procedure

Si hubiera sido necesario revertir:

```bash
# Restaurar dist/ anterior
cd /opt/ai-lab/apps/ialab-docs
rm -rf dist
mv dist.rollback-* dist
sudo systemctl restart ailab-docs
```

## Conclusión

**PASS** — `blog-ai-lab.labrazahome.com` sirve el contenido actualizado. Las 4 URLs nuevas responden 200 con títulos correctos. Build de 264 páginas sin errores. Servicio activo.
