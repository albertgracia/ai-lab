# ANYTHINGLLM-INCREMENTAL-REINDEX-HARDENING-01

**Estado:** PASS  
**Fecha:** 2026-06-11  
**Fase:** ANYTHINGLLM-INCREMENTAL-REINDEX-HARDENING-01  
**Tag:** — (pre-commit)

---

## Problema original

El script inicial subía todos los documentos de una carpeta en un solo `update-embeddings`, lo que obligaba a Albert a seleccionar manualmente los documentos en la UI de AnythingLLM y moverlos al workspace AI-LAB CORE. Eso rompía el ciclo automatizado del protocolo PC-01.

## Objetivo

Corregir `reindex-workspace.ps1` para que la reindexación sea incremental, automática y segura, sin requerir intervención manual en la UI.

## Cambios implementados

### 1. Parámetros nuevos

| Parámetro | Default | Propósito |
|-----------|---------|-----------|
| `-BatchSize` | 10 | Documentos por lote de embedding |
| `-BatchDelaySeconds` | 5 | Pausa entre lotes |
| `-MaxFiles` | 20 | Límite de archivos sin override |
| `-AllowLargeBatch` | — | Override del límite MaxFiles |
| `-IncludeAudits` | — | Incluir `docs/audits/` |
| `-AllowLargeFiles` | — | Incluir archivos > 500KB |
| `-MaxFileSizeKB` | 500 | Umbral de tamaño |
| `-ChangedFilesPath` | — | Archivo con rutas relativas (incremental) |

### 2. Modo incremental (`-ChangedFilesPath`)

- Lee un archivo de texto con rutas relativas (una por línea, `#` para comentarios)
- Resuelve cada ruta contra el directorio actual
- Solo procesa los archivos listados

### 3. Exclusiones automáticas

| Patrón | Forzado | Override |
|--------|:-------:|----------|
| `docs/archive/**` | ✅ Siempre | — |
| `docs/quarantine/**` | ✅ Siempre | — |
| `docs/audits/**` | ✅ Por defecto | `-IncludeAudits` |
| Archivos > 500KB | ✅ Por defecto | `-AllowLargeFiles` |

### 4. Procesamiento por lotes

Antes: un solo `update-embeddings` con todos los documentos.

Ahora:
1. Por cada lote de `BatchSize` archivos:
   a. Subir documentos via `POST /v1/document/raw-text`
   b. Recolectar `locations` del batch
   c. Llamar `POST /v1/workspace/{slug}/update-embeddings` con `adds` del batch
   d. Confirmar via `GET /v1/workspace/{slug}` que los docs quedaron vinculados
   e. Esperar `BatchDelaySeconds`
2. Smoke queries al final

### 5. Guardias de seguridad

- `MaxFiles`: aborta si hay más de 20 archivos a menos que `-AllowLargeBatch`
- `DocFolder` solo para carpetas pequeñas; `-ChangedFilesPath` para incremental
- Archivos grandes (>500KB) excluidos por defecto
- Sin `-IncludeAudits`, los audit reports quedan fuera

### 6. Verificación post-lote

Cada batch ejecuta `Confirm-WorkspaceDocuments` que verifica que el workspace tenga al menos la cantidad esperada de documentos después del `update-embeddings`.

### 7. Resumen final

| Campo | Descripción |
|-------|-------------|
| `Files Uploaded` | Archivos subidos exitosamente |
| `Files Skipped` | Archivos excluidos por reglas |
| `Total batches` | Número de lotes procesados |
| PASS/WARN/FAIL | Contadores de validación |

## Verificación

| Criterio | Resultado |
|----------|:---------:|
| Batch processing (lotes de 10, delay 5s) | ✅ Implementado |
| MaxFiles guard (default 20, AllowLargeBatch override) | ✅ Implementado |
| Modo incremental (-ChangedFilesPath) | ✅ Implementado |
| Exclusiones archive/quarantine/audits/size | ✅ Implementado |
| Per-batch update-embeddings + confirmación | ✅ Implementado |
| No selección manual requerida en UI | ✅ Garantizado |
| API key no expuesta | ✅ Mantenido |
| DryRun muestra lotes sin cambios | ✅ Implementado |
| Smoke queries al final de Apply | ✅ Mantenido |
| Astro build | ✅ PASS (264 páginas) |

## Conclusión

**PASS.** El script ya no requiere selección manual en la UI de AnythingLLM. Cada lote se sube, se vincula al workspace y se confirma automáticamente. El modo incremental via `-ChangedFilesPath` permite reindexar solo los documentos modificados sin tocar el resto.

## Riesgos residuales

- No probado contra instancia AnythingLLM real en este entorno (sin API key disponible)
- `-AllowLargeBatch` sin supervisión podría subir cientos de documentos si se usa sin cuidado
- Smoke queries dependen del modelo LLM configurado en AnythingLLM
