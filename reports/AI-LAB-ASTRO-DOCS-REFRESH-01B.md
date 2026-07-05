# AI-LAB-ASTRO-DOCS-REFRESH-01B — Refresh documental con separación público/privado

**Fecha:** 2026-07-05
**Estado:** ✅ PASS

## Resumen

Refresh de documentación Astro de AI-LAB respetando la separación público/privado implementada en `CP-ASTRO-PUBLIC-PRIVATE-SEPARATION-01`.

## Cambios realizados

### Sanitización de IPs públicas (seguridad)

| Página | Antes | Después |
|--------|-------|---------|
| `docs/architecture/anythingllm-enterprise.md` | IPs `192.168.1.50:3001/1234` en tabla | "Red privada" |
| `docs/architecture/anythingllm-role.md` | 3 referencias IP `192.168.1.50:3001/1234` | "Red privada" |
| `docs/runtime-ai-lab.md` | Tabla de componentes con puertos internos | Tabla sin puertos; mermaid sin puertos |
| `docs/roadmap/index.md` | Observabilidad table con IPs + modelos table con IPs | Tablas sin IPs; Grafana nota genérica |
| `docs/roadmap/index.md` (Marketplace) | `192.168.1.150:8080` | "Go + Fiber v2 en red privada" |
| `docs/roadmap/index.md` (Multi-GPU) | `192.168.1.60` | "Nodo apagado" sin IP |

### Marketplace Digital Twin → PRIVATE_ONLY

`docs/architecture/marketplace-digital-twin.md` movido a filtro privado (demasiadas IPs dispersas). Sidebar condicional `isPublicBuild` añadido.

| Cambio | Archivo |
|--------|---------|
| Añadido a filter | `scripts/private-content-filter.json` |
| Sidebar conditional | `astro.config.mjs` — solo muestra en privado |

### Contenido actualizado

| Página | Cambio |
|--------|--------|
| `docs/index.md` | Nuevos checkpoints: `CP-AI-LAB-ASTRO-DOCS-REFRESH-01`, `CP-ASTRO-PUBLIC-PRIVATE-SEPARATION-01`. Nuevo next step |
| `docs/roadmap/index.md` | Nueva sección "Astro Docs — Public/Private Separation". Checkpoints actualizados. Prioridades actualizadas |
| `docs/arquitectura-publico-privado.md` | Nueva sección "Separación de documentación Astro (Julio 2026)" con arquitectura, mecanismo, métricas y pipeline CI/CD |

### Builds

| Build | Páginas | IPs | Tiempo | Estado |
|-------|---------|-----|--------|--------|
| Público (`npm run build:public`) | **170** | **0** | 12.93s | ✅ PASS |
| Privado (`npm run build:private`) | **277** | — | 13.90s | ✅ PASS |

> Nota: 170 páginas públicas (vs 171 anterior) por exclusión de `marketplace-digital-twin.md`.

### Validación de seguridad

```powershell
# Búsqueda de IPs internas en dist público
Get-ChildItem -Path dist -Recurse -File | Select-String -Pattern "192\.168\." -SimpleMatch
# Resultado: 0 matches
```

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `docs/index.md` | Nuevos checkpoints + next steps |
| `docs/architecture/anythingllm-enterprise.md` | IP → "Red privada" |
| `docs/architecture/anythingllm-role.md` | IP → "Red privada" |
| `docs/runtime-ai-lab.md` | Tabla sin puertos, mermaid sanitizado |
| `docs/roadmap/index.md` | IPs sanitizadas, nueva sección Docs Separation |
| `docs/arquitectura-publico-privado.md` | Nueva sección Docs Separation |
| `scripts/private-content-filter.json` | +1 entry: marketplace-digital-twin.md |
| `astro.config.mjs` | Sidebar conditional para Marketplace |

## Tags

- `CP-AI-LAB-ASTRO-DOCS-REFRESH-01B`

## Validación

- [x] Build público (170 pages, 0 IPs)
- [x] Build privado (277 pages)
- [x] 0 internal IPs en dist/ público
- [x] Marketplace sidebar conditional funciona
- [x] Contenido actualizado refleja estado real
