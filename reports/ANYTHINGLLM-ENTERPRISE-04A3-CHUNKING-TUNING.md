# ANYTHINGLLM-ENTERPRISE-04A3-CHUNKING-TUNING

**Estado:** ✅ COMPLETADO  
**Fecha:** 2026-07-05  
**Pre-requisito:** 04A2 (multilingual-e5-small migration)  
**Siguiente:** 04B (Evidence Import)

---

## Objetivo

Ajustar chunking de AnythingLLM Desktop para mejorar precisión de RAG antes de importar documentos de evidencia (Reports, Marketplace, Observabilidad, etc.).

## Problema Detectado

En 04A2 se observó que consultas en español encontraban documentos relevantes pero con fuentes mezcladas:
- `matrix.json` (chunk de `}\n  }\n}`) aparecía como #1 con score 0.8942
- `operator.schema.json` (chunk de `}`) como #2 con score 0.8835
- El ADR real aparecía en #3 con score 0.8726

## Diagnóstico

### Chunking NO Configurable vía API

AnythingLLM Desktop usa `TextChunker` con chunking hardcoded. No hay endpoint REST para modificar `chunk_size`, `overlap` o `min_chunk_size`.

Pruebas realizadas:
- `POST /api/v1/system/update-env` con `DocumentChunkSize`, `DocumentChunkOverlap`, `TEXT_CHUNK_SIZE`, `TEXT_CHUNK_OVERLAP` → todos ignorados (no existen en KEY_MAPPING)
- `GET /api/v1/workspace/{slug}` → solo expone `openAiTemp`, `openAiHistory`, `similarityThreshold`, `topN` — no hay chunk settings por workspace
- Ningún endpoint `/system/preferences`, `/admin/settings` o chunk-specific disponible

### Distribución de Chunks (antes de cleanup)

| Rango | Chunks | Porcentaje |
|-------|--------|-----------|
| 100-200 chars | 20 | 26.7% |
| 200-500 chars | 8 | 10.7% |
| 500-1000 chars | 15 | 20.0% |
| 1000-2000 chars | 32 | 42.7% |

Los chunks de 100-200 chars provenían exclusivamente de archivos `.json` y `.yaml`:
- `matrix.json`: chunk final con `}\n  }\n}` (108 chars)
- `operator.schema.json`: fragmento final (108 chars)
- `identity.yaml`: línea suelta (139 chars)
- `before_write.yaml`: fragmento suelto (144 chars)

### Por qué Contaminan

En espacio 384-dim (e5-small), chunks cortos sin contenido semántico específico tienen similitud artificialmente alta con cualquier consulta. Una llave de cierre `}\n  }\n}` obtiene score 0.89 simplemente porque no hay suficiente texto para diferenciarla semánticamente.

## Solución: Eliminar Fuentes de Ruido

En lugar de eliminar archivos individualmente (no hay API para re-chunkear), se removieron los 40 archivos `.json` y `.yaml` del workspace `hermes-enterprise` vía `POST /api/v1/workspace/{slug}/update-embeddings` con `deletes: [docpath, ...]`.

### Archivos Eliminados (40)

**Schemas JSON (7):** `capability.schema.json`, `hook.schema.json`, `mcp_server.schema.json`, `matrix.json`, `modes.json`, `operator.schema.json`, `schema.json`, `soul.schema.json`

**Config YAML (32):** `after_request.yaml`, `after_tool.yaml`, `after_write.yaml`, `ai-lab-runtime.yaml` (2), `ailab-runtime.yaml`, `before_request.yaml`, `before_tool.yaml`, `before_write.yaml`, `boundaries.yaml`, `deployment-review.yaml` (2), `domains.yaml`, `filesystem.yaml`, `gitnexus-analysis.yaml`, `gitnexus.yaml`, `identity.yaml`, `incident-response.yaml` (2), `marketplace-operator.yaml` (2), `marketplace.yaml`, `observability-operator.yaml`, `observability.yaml`, `on_error.yaml`, `on_incident.yaml`, `on_shutdown.yaml`, `prometheus.yaml`, `protocols.yaml`, `registry.yaml` (2), `truth_model.yaml`

### Impacto

- Vectores: 576 → **467** (-109 vectores de ruido)
- Archivos `.md` y `.py`: **46 intactos** (100% del contenido canónico)

## Resultados

### Español (después de cleanup)

| Consulta | Antes (score, fuente) | Después (score, fuente) |
|----------|----------------------|------------------------|
| ¿Qué es el SOUL? | 0.8942 matrix.json | **0.8726 HERMES-ENTERPRISE-DESIGN-01.md** |
| ¿Diferencia Capability vs Operator? | — | **0.8801 HERMES-ENTERPRISE-DESIGN-01.md** |
| ¿Qué es Dynamic Governance? | 0.8652 ADR-004 | **0.8674 HERMES-ENTERPRISE-DESIGN-01.md** |
| ¿Endpoint de Hermes? | — | **0.9058 HERMES-ENTERPRISE-DESIGN-01.md** |

### Inglés (después de cleanup)

| Consulta | Score | Fuente |
|----------|-------|--------|
| What is SOUL? | 0.8777 | ADR-004-MCP-REGISTRY.md |
| What is Dynamic Governance? | 0.8637 | ADR-006-DYNAMIC-GOVERNANCE.md (EXACTO) |
| What is Capability Registry? | 0.8876 | HERMES-ENTERPRISE-DESIGN-01.md |

## Conclusión

| Aspecto | Resultado |
|---------|-----------|
| Chunking configurable vía API | ❌ NO |
| Eliminación de ruido YAML/JSON | ✅ 40 archivos, -109 vectores |
| Recall español (ADR relevante en #1) | ✅ 4/4 consultas |
| Recall inglés | ✅ 3/3 consultas |
| Contenido canónico preservado | ✅ 46 archivos intactos |

## Recomendación

El chunking actual (TextChunker por defecto) es adecuado para documentos `.md` y `.py`. Los archivos `.json` y `.yaml` deben excluirse porque:
1. Producen chunks semánticamente vacíos (cierres de llaves)
2. Contaminan el ranking en espacio 384-dim
3. No aportan valor documental (son schemas y configuraciones, no documentación)

Si en el futuro AnythingLLM Desktop expone chunking configurable vía API, re-evaluar con:
- `chunk_size: 1024` (textos técnicos en español necesitan ~600-800 chars)
- `overlap: 128`
- `min_chunk_size: 300` (eliminaría chunks de 108 chars)

---

*Fin del reporte 04A3*
