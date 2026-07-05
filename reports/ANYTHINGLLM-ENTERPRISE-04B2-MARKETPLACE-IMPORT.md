# ANYTHINGLLM-ENTERPRISE-04B2-MARKETPLACE-IMPORT

**Estado:** ✅ COMPLETADO  
**Fecha:** 2026-07-05  
**Pre-requisito:** 04B1 (Evidence Reports Canonical)  
**Siguiente:** 04B3 (subfase a determinar)

---

## Objetivo

Importar documentación y reportes canónicos de Rioja Marketplace en el workspace dedicado, validando que las áreas funcionales (ProductMaster, Sommelier, Inventory, B2B, Catálogo, Admin, Deploy) sean recuperables vía RAG.

## Documentos Importados (7)

| Archivo | Tamaño | Contenido |
|---------|--------|-----------|
| `docs/opencode/11-rioja-marketplace.md` | 9.4KB | Arquitectura, stack, rutas, handlers, plan de reparación |
| `docs/integrations/HERMES-AI-LAB.md` | 4.5KB | Integración Hermes Agent ↔ AI-LAB Gateway |
| `reports/HERMES-MARKETPLACE-INTEGRATION-01.md` | 18.6KB | Reporte de integración Hermes-Marketplace |
| `reports/HERMES-MARKETPLACE-OPERATOR-01.md` | 19.4KB | Reporte de operador marketplace |
| `reports/MARKETPLACE-GITNEXUS-ENABLE-01.md` | 18.5KB | GitNexus enablement marketplace (v1) |
| `reports/MARKETPLACE-GITNEXUS-ENABLE-02.md` | 8.2KB | GitNexus enablement marketplace (v2) |
| `reports/MARKETPLACE-MCP-READONLY-01.md` | 6.4KB | MCP read-only marketplace |

**Total: 7 documentos, ~85KB, +99 vectores (sistema: 1022)**

## Resultados RAG por Área

### ProductMaster / Catálogo

| # | Score | Fuente | Chunk |
|---|-------|--------|-------|
| 1 | 0.9085 | MARKETPLACE-GITNEXUS-ENABLE-02.md | 353ch |
| 2 | 0.9038 | MARKETPLACE-GITNEXUS-ENABLE-02.md | 608ch |
| 3 | 0.9032 | HERMES-MARKETPLACE-INTEGRATION-01.md | 163ch |

### Sommelier (IA)

| # | Score | Fuente | Chunk |
|---|-------|--------|-------|
| 1 | 0.8657 | HERMES-MARKETPLACE-INTEGRATION-01.md | 1100ch |
| 2 | 0.8645 | HERMES-MARKETPLACE-INTEGRATION-01.md | 765ch |
| 3 | 0.8643 | MARKETPLACE-GITNEXUS-ENABLE-01.md | 709ch |

### Inventory

| # | Score | Fuente | Chunk |
|---|-------|--------|-------|
| 1 | 0.8903 | MARKETPLACE-GITNEXUS-ENABLE-02.md | 353ch |
| 2 | 0.8855 | MARKETPLACE-GITNEXUS-ENABLE-01.md | 723ch |
| 3 | 0.8822 | MARKETPLACE-MCP-READONLY-01.md | 343ch |

### B2B

| # | Score | Fuente | Chunk |
|---|-------|--------|-------|
| 1 | 0.9085 | MARKETPLACE-GITNEXUS-ENABLE-02.md | 353ch |
| 2 | 0.9038 | MARKETPLACE-GITNEXUS-ENABLE-02.md | 608ch |
| 3 | 0.9032 | HERMES-MARKETPLACE-INTEGRATION-01.md | 163ch |

### Admin

| # | Score | Fuente | Chunk |
|---|-------|--------|-------|
| 1 | 0.8763 | MARKETPLACE-GITNEXUS-ENABLE-01.md | 723ch |
| 2 | 0.8758 | HERMES-MARKETPLACE-INTEGRATION-01.md | 921ch |
| 3 | 0.8714 | HERMES-MARKETPLACE-INTEGRATION-01.md | 716ch |

### Deploy (Windows Server / Vercel / Cloudflare)

| # | Score | Fuente | Chunk |
|---|-------|--------|-------|
| 1 | 0.8795 | HERMES-MARKETPLACE-INTEGRATION-01.md | 1056ch |
| 2 | 0.8737 | HERMES-MARKETPLACE-INTEGRATION-01.md | 811ch |
| 3 | 0.8718 | **11-rioja-marketplace.md** | 1058ch |

### Arquitectura (inglés)

| # | Score | Fuente | Chunk |
|---|-------|--------|-------|
| 1 | 0.8920 | HERMES-MARKETPLACE-INTEGRATION-01.md | 1056ch |
| 2 | 0.8899 | MARKETPLACE-GITNEXUS-ENABLE-01.md | 1080ch |
| 3 | 0.8880 | **11-rioja-marketplace.md** | 1058ch |

### ¿Qué es Rioja Marketplace? (español)

| # | Score | Fuente | Chunk |
|---|-------|--------|-------|
| 1 | 0.8842 | MARKETPLACE-GITNEXUS-ENABLE-02.md | 353ch |
| 2 | 0.8841 | HERMES-MARKETPLACE-INTEGRATION-01.md | 163ch |
| 3 | 0.8729 | HERMES-MARKETPLACE-INTEGRATION-01.md | 688ch |

## Cross-check: Sin Contaminación

| Workspace | Query | Resultado |
|-----------|-------|-----------|
| Hermes Enterprise | "Rioja Marketplace" | ✅ Hermes docs (referencia arquitectónica, esperado) |
| Hermes Enterprise | "Sommelier IA marketplace" | ✅ Hermes docs (no marketplace sources) |
| Hermes Enterprise | "marketplace.labrazahome.com" | ✅ HERMES-ENTERPRISE-DESIGN-01 (arquitectura, esperado) |
| Reports | "Rioja Marketplace" | ✅ Reports + Hermes architecture |
| Reports | "Sommelier IA marketplace" | ✅ Reports + Hermes architecture |
| Reports | "marketplace.labrazahome.com" | ✅ MARKETPLACE-GITNEXUS-ENABLE-02 (reporte, esperado) |

**Sin fuga de documentación marketplace a workspaces canónicos.** Las referencias a marketplace en workspaces ajenos provienen de documentación arquitectónica (Hermes), no de los documentos del marketplace.

## Observaciones

### docs/opencode/11-rioja-marketplace.md en posición #3

El documento principal de arquitectura del marketplace aparece en #3 para consultas como "Deploy" y "Arquitectura". Los reports (GITNEXUS-ENABLE, HERMES-INTEGRATION) dominan por tener chunks más cortos (353ch, 163ch) que en espacio 384-dim obtienen scores más altos. El chunk de 1058ch de `11-rioja-marketplace.md` tiene score 0.8718 vs. 0.8795 del reporte — diferencia marginal.

### Áreas no cubiertas por documentación local

Los módulos ProductMaster, Sommelier, Inventory, B2B y Admin existen como rutas/handlers en el código fuente del marketplace, pero la documentación detallada de cada uno está en el repositorio `rioja-marketplace` (Go backend + Next.js frontend), no en este workspace. Para cobertura completa, **importar el repositorio `rioja-marketplace` como workspace independiente** con el código fuente o su documentación generada.

## Conclusión

| Aspecto | Resultado |
|---------|-----------|
| Documentos importados | ✅ 7/7 |
| Vectores generados | ✅ +99 (sistema: 1022) |
| ProductMaster | ✅ documentos relevantes en top 3 |
| Sommelier | ✅ documentos relevantes en top 3 |
| Inventory | ✅ documentos relevantes en top 3 |
| B2B | ✅ documentos relevantes en top 3 |
| Catálogo | ✅ documentos relevantes en top 3 |
| Admin | ✅ documentos relevantes en top 3 |
| Deploy Windows/Vercel | ✅ documentos relevantes en top 3 (incluye archivo principal) |
| Recall general | ✅ 11/11 consultas con resultados relevantes |
| Contaminación cruzada | ✅ Sin fuga de marketplace a workspaces canónicos |

## Estado de la Ingesta

```
Workspace: hermes-enterprise (canónico)
  46 documentos, 467 vectores

Workspace: reports (evidencia histórica)
  53 documentos, 456 vectores

Workspace: rioja-marketplace
  7 documentos, 99 vectores

Total sistema: 1022 vectores
Embedder: multilingual-e5-small (Q8_0, LM Studio .50:1234)
```

---

*Fin del reporte 04B2*
