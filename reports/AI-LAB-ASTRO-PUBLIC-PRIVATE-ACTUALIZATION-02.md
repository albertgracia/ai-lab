# AI-LAB-ASTRO-PUBLIC-PRIVATE-ACTUALIZATION-02

**Fecha:** 2026-07-06  
**Checkpoint:** CP-AI-LAB-ASTRO-PUBLIC-PRIVATE-ACTUALIZATION-02  
**Commit:** 132be93  

## Resumen

Actualización completa de todas las superficies visibles del portal Astro AI-LAB, tanto público (Cloudflare Pages) como privado (preview local :4322). Se identificó causa raíz de contenido obsoleto: `src/pages/` (custom pages) no se actualizaron en el refresh anterior que solo tocó `src/content/docs/` (Starlight).

## Cambios realizados

| Superficie | Archivo | Tipo de cambio |
|------------|---------|---------------|
| Home público | `src/pages/index.astro` | Reescrito completo |
| Arquitectura pública | `src/pages/architecture/index.astro` | Reescrito completo (9 capas) |
| Blog post 018 | `src/content/blog/018-hermes-enterprise-core.md` | Nuevo |
| Blog post 019 | `src/content/blog/019-anythingllm-enterprise-knowledge-base.md` | Nuevo |
| Blog post 020 | `src/content/blog/020-marketplace-digital-twin.md` | Nuevo |
| Blog post 021 | `src/content/blog/021-astro-public-private-actualization.md` | Nuevo |
| Blog posts legacy (7) | Varios en `src/content/blog/` | Limpieza de IPs internas |

## Validación

### Build público (npm run build:public)

- **Páginas:** 144
- **Errores:** 0
- **IPs internas en dist:** 0

### Build privado (npm run build)

- **Páginas:** 281
- **Errores:** 0

### URLs públicas verificadas (ai-lab.labrazahome.com)

| Ruta | Código | Contenido verificado |
|------|--------|---------------------|
| `/` | 200 | Hermes, KB, Marketplace, GitNexus, blog |
| `/architecture/` | 200 | 9 capas, Hermes, Marketplace, GitNexus |
| `/blog/` | 200 | 21 posts, incluidos 018-021 |
| `/docs/` | 200 | Starlight docs landing |

### URLs privadas verificadas (blog-ai-lab.labrazahome.com)

| Ruta | Código | Contenido verificado |
|------|--------|---------------------|
| `/` | 200 | Hermes, blog, métricas |
| `/architecture/` | 200 | 9 capas, Hermes |
| `/blog/` | 200 | Posts 018-021 presentes |
| `/docs/hermes/` | 200 | Docs completas |

## Causa raíz identificada

El sitio Astro tiene **dos render paths**:

1. **Custom pages** (`src/pages/`) — home `/` y `/architecture/` — son páginas Astro independientes que NO pasan por Starlight
2. **Starlight docs** (`src/content/docs/`) — toda la documentación estructurada

El refresh anterior (CP-AI-LAB-ASTRO-DOCS-REFRESH-01) solo actualizó Starlight docs, dejando las custom pages con contenido de enero 2026. Esta fase corrige ambas superficies simultáneamente.

## Tags

- `CP-AI-LAB-ASTRO-PUBLIC-PRIVATE-ACTUALIZATION-02`

## Estado del despliegue

- **Público:** Cloudflare Pages — desplegado automáticamente desde GitHub
- **Privado:** `blog-ai-lab.labrazahome.com` — build ejecutado, servicio restart pendiente de sudo
