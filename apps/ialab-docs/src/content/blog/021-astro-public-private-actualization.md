---
title: "Astro público y privado: actualización de superficies visibles"
date: "2026-07-06"
summary: "AI-LAB completa la actualización de todas las superficies visibles del portal Astro: home, arquitectura, blog y roadmap ahora reflejan el estado real del ecosistema."
tags:
  - ai-lab
  - astro
  - documentation
  - public
  - private
---

## El problema

El portal Astro de AI-LAB tiene dos builds:

- **Público** (`ai-lab.labrazahome.com`) — Cloudflare Pages, sin IPs internas, sin secretos
- **Privado** (`blog-ai-lab.labrazahome.com`) — Traefik local, contenido completo con runbooks e incidentes

Aunque la documentación interna (Starlight docs) se había actualizado en fases anteriores, las **superficies visibles principales** — la home, la página de arquitectura y el blog — seguían mostrando contenido desactualizado.

## Causa raíz

El sitio Astro tiene **dos render paths independientes**:

1. **Custom pages** (`src/pages/`): home, architecture, blog, skills, services, projects
2. **Starlight docs** (`src/content/docs/`): documentación estructurada

El refresh anterior (`CP-AI-LAB-ASTRO-DOCS-REFRESH-01`) actualizó las Starlight docs, pero **no tocó las custom pages**. La home pública y la arquitectura seguían siendo las originales, con referencias obsoletas e IPs internas.

## Lo que cambió

### Home pública (`/`)

- Contenido actualizado para reflejar Hermes Enterprise Core, AnythingLLM Enterprise, Marketplace Digital Twin y GitNexus
- Sección de blog con las 4 últimas entradas
- Enlaces a documentación Starlight
- **Eliminadas todas las IPs internas**
- Sección de ecosistema con cuadros de métricas clave (185 tests, 1304 vectores, 3 modelos, 100+ métricas)

### Página de arquitectura (`/architecture/`)

- 9 capas definidas: desde el Public Edge hasta GitNexus
- Sección de modelos activos con los 3 modelos del runtime
- Checkpoints clave con tags de referencia
- Enlaces a documentación completa y roadmap

### Blog

- 4 entradas nuevas: Hermes Enterprise Core, AnythingLLM Enterprise, Marketplace Digital Twin y esta misma entrada
- Home ahora muestra las últimas 4 entradas del blog

## Validación

- Build público: 140+ páginas, 0 errores
- Build privado: 277 páginas, 0 errores
- 0 IPs internas en build público
- URLs públicas verificadas

## Despliegue

- **Público**: push a Cloudflare Pages
- **Privado**: pull + rebuild en preview local

Checkpoint: `CP-AI-LAB-ASTRO-PUBLIC-PRIVATE-ACTUALIZATION-02`.
