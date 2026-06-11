---
title: "AnythingLLM Reindex Automation"
summary: "Automatización del reindexado incremental de AnythingLLM tras cambios documentales. Procesamiento por lotes, exclusiones automáticas, modo incremental y smoke queries para cerrar el ciclo documental del protocolo PC-01."
order: 9
---

## Propósito

Automatiza el paso 4 del [Protocolo de Cierre de Fase (PC-01)](./phase-closure-protocol.md): la reindexación de AnythingLLM después de cambios en la documentación Astro.

```
Cambio en docs/ → Astro build → upload por lotes → update-embeddings → smoke validation
```

## Endpoints de la API AnythingLLM

| Endpoint | Método | Propósito |
|----------|--------|-----------|
| `/api/v1/auth` | GET | Verificar API key |
| `/api/v1/workspaces` | GET | Listar workspaces |
| `/api/v1/workspace/{slug}` | GET | Detalle del workspace (documentos incrustados) |
| `/api/v1/document/raw-text` | POST | Subir documento como texto plano |
| `/api/v1/workspace/{slug}/update-embeddings` | POST | Añadir documentos al workspace + reindexar |
| `/api/v1/workspace/{slug}/chat` | POST | Ejecutar consulta RAG (smoke test) |

## Script: `reindex-workspace.ps1`

### Modos de operación

| Modo | Parámetro | Acción |
|------|-----------|--------|
| **DryRun** | `-Mode DryRun` | Valida conexión, auth, workspace, muestra lotes sin cambios |
| **Apply** | `-Mode Apply` | Sube documentos en lotes, actualiza embeddings, smoke queries |
| **SmokeOnly** | `-Mode SmokeOnly` | Solo ejecuta preguntas de validación |

### Parámetros principales

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `-Mode` | `DryRun` | DryRun, Apply o SmokeOnly |
| `-BaseUrl` | `$env:ANYTHINGLLM_BASE_URL` | URL base de AnythingLLM |
| `-WorkspaceSlug` | `$env:ANYTHINGLLM_WORKSPACE_SLUG` o `ai-lab-core` | Slug del workspace objetivo |
| `-ApiKey` | `$env:ANYTHINGLLM_API_KEY` | API key |
| `-DocFolder` | — | Carpeta local con documentos (usar solo para carpetas pequeñas) |
| `-ChangedFilesPath` | — | Archivo de texto con rutas relativas (modo incremental) |
| `-BatchSize` | `10` | Documentos por lote de embedding |
| `-BatchDelaySeconds` | `5` | Espera entre lotes |
| `-MaxFiles` | `20` | Máximo de archivos sin `-AllowLargeBatch` |
| `-AllowLargeBatch` | — | Omite el guard de MaxFiles |
| `-IncludeAudits` | — | Incluye `docs/audits/` (excluido por defecto) |
| `-AllowLargeFiles` | — | Incluye archivos > 500KB |
| `-MaxFileSizeKB` | `500` | Umbral de tamaño de archivo |

### Exclusiones automáticas

| Exclusión | Condición | Override |
|-----------|-----------|----------|
| `docs/archive/**` | Siempre | — |
| `docs/quarantine/**` | Siempre | — |
| `docs/audits/**` | Por defecto | `-IncludeAudits` |
| Archivos > 500KB | Por defecto | `-AllowLargeFiles` |

### Flujo de Apply

```
1. Auth → workspace lookup → detalles
2. Colección de archivos (DocFolder o ChangedFilesPath)
3. Filtrado por extensión (.md, .txt, .json, .yaml, .yml, .html)
4. Exclusiones automáticas
5. Guard MaxFiles (a menos que AllowLargeBatch)
6. Bucle por lotes de BatchSize:
   a. Subir lote a /v1/document/raw-text
   b. Llamar update-embeddings con adds del lote
   c. Confirmar que los documentos quedaron en el workspace
   d. Esperar BatchDelaySeconds
7. Smoke queries (3 preguntas)
```

### Smoke queries

3 preguntas de validación contra el workspace RAG:

1. ¿Qué exige el protocolo de cierre de fase si hay impacto documental?
2. ¿Qué es el Cognitive Health Layer 37A?
3. ¿Por qué validation_score era 56.3?

Cada respuesta debe incluir contenido relevante (match con palabra clave esperada). El script distingue respuestas con fuentes citadas vs. conocimiento general del LLM.

## Integración OpenCode → Astro → AnythingLLM

```
OpenCode (agente)
  │
  ├── 1. Modifica docs en apps/ialab-docs/
  │
  ├── 2. npm run build (Astro)
  │      └── 0 errores
  │
  ├── 3. scripts/anythingllm/reindex-workspace.ps1 -Mode Apply
  │      ├── Lote 1/N: upload 10 docs → update-embeddings → confirmar
  │      ├── Lote 2/N: upload 10 docs → update-embeddings → confirmar
  │      ├── ...
  │      └── Smoke queries → PASS/FAIL
  │
  └── 4. Resultado registrado en el cierre de fase
```

### Seguridad

- API key **nunca** hardcodeada
- Fuentes: variable de entorno, `.anythingllm.env` (gitignorado) o `-ApiKey`
- `.anythingllm.env` en `.gitignore`

## Uso típico

```powershell
# Validar conectividad
.\scripts\anythingllm\reindex-workspace.ps1 -Mode DryRun

# Reindexar cambios incrementales (lista de archivos)
.\scripts\anythingllm\reindex-workspace.ps1 -Mode Apply -ChangedFilesPath ./changed.txt -BatchSize 5

# Subir carpeta pequeña (máx 20 archivos)
.\scripts\anythingllm\reindex-workspace.ps1 -Mode Apply -DocFolder ./new-docs -MaxFiles 5

# Reindexar lote grande (con override)
.\scripts\anythingllm\reindex-workspace.ps1 -Mode Apply -DocFolder ./docs -AllowLargeBatch -BatchSize 20

# Solo smoke queries
.\scripts\anythingllm\reindex-workspace.ps1 -Mode SmokeOnly
```

## Referencias

- [Phase Closure Protocol (PC-01)](./phase-closure-protocol.md)
- [scripts/anythingllm/reindex-workspace.ps1](https://github.com/anomalyco/ai-lab/blob/main/scripts/anythingllm/reindex-workspace.ps1)
- [AnythingLLM Developer API](https://docs.anythingllm.com/features/api)
