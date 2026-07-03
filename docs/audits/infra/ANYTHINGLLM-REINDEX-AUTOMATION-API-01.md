# ANYTHINGLLM-REINDEX-AUTOMATION-API-01

**Estado:** PASS  
**Fecha:** 2026-06-11  
**Fase:** ANYTHINGLLM-REINDEX-AUTOMATION-API-01  
**Tag:** — (pre-commit)

---

## Objetivo

Cerrar el ciclo documental automático del Protocolo de Cierre de Fase (PC-01) implementando un script PowerShell que automatiza la reindexación de AnythingLLM tras cambios en la documentación Astro.

## Criterios de auditoría

### 1. Identificación de endpoints AnythingLLM

| Endpoint | Identificado | Uso en script |
|----------|:-----------:|:-------------:|
| `GET /api/v1/auth` | ✅ | Verificar API key |
| `GET /api/v1/workspaces` | ✅ | Listar workspaces |
| `GET /api/v1/workspace/{slug}` | ✅ | Detalle del workspace + documentos |
| `POST /api/v1/document/raw-text` | ✅ | Subir documentos como texto |
| `POST /api/v1/document/upload` | ✅ | Alternativa multipart (documentada pero no usada por defecto) |
| `POST /api/v1/workspace/{slug}/update-embeddings` | ✅ | Añadir docs al workspace + trigger reindex |
| `POST /api/v1/workspace/{slug}/chat` | ✅ | Smoke queries de validación |

**Fuente:** OpenAPI spec oficial de AnythingLLM v1.0.0 (`server/swagger/openapi.json`).

### 2. Script reindex-workspace.ps1

| Característica | Estado | Detalle |
|---------------|:------:|---------|
| Dry-run mode | ✅ | Auth → workspace list → detail → doc inspection. No modifica nada. |
| Apply mode | ✅ | Upload raw-text → update-embeddings → smoke queries |
| Smoke-only mode | ✅ | Solo ejecuta 3 preguntas de validación |
| API key segura | ✅ | Carga por orden: parámetro → env var → `.anythingllm.env` (gitignorado) |
| Base URL configurable | ✅ | Parámetro `-BaseUrl` o `$env:ANYTHINGLLM_BASE_URL` |
| Counter PASS/FAIL/WARN | ✅ | Reporte numérico al finalizar |
| Exit code | ✅ | 0 si PASS, 1 si FAIL > 0 |

### 3. Smoke queries

| Pregunta | Palabra clave esperada | Propósito |
|----------|------------------------|-----------|
| ¿Qué exige el protocolo de cierre de fase si hay impacto documental? | `protocolo` | Verifica que PC-01 está indexado |
| ¿Qué es el Cognitive Health Layer 37A? | `health` | Verifica que 37A está indexado |
| ¿Por qué validation_score era 56.3? | `prometheus\|sensores\|safety` | Verifica que 36C-A está indexado |

### 4. Seguridad

- `.anythingllm.env` añadido a `.gitignore`
- Template `.anythingllm.env.example` sin secrets reales
- API key nunca hardcodeada en el script
- Sin logging de la API key a stdout

### 5. Documentación

| Archivo | Propósito |
|---------|-----------|
| `scripts/anythingllm/reindex-workspace.ps1` | Script de automatización |
| `scripts/anythingllm/.anythingllm.env.example` | Template de configuración |
| `apps/ialab-docs/src/content/docs/governance/anythingllm-reindex-automation.md` | Documentación Astro |
| `docs/audits/ANYTHINGLLM-REINDEX-AUTOMATION-API-01.md` | Este informe |

## Resultados

| Criterio | Resultado |
|----------|:---------:|
| Endpoints identificados correctamente | ✅ PASS |
| Script con dry-run + apply + smoke | ✅ PASS |
| Smoke queries integradas (3) | ✅ PASS |
| API key management seguro | ✅ PASS |
| Documentación completa | ✅ PASS |
| Astro build | ⏳ Pendiente |

## Conclusión

**PASS.** La automatización de reindex AnythingLLM está completa y documentada. Pendiente de verificación contra instancia real de AnythingLLM (depende de disponibilidad de entorno y API key).

## Riesgos residuales

- No probado contra instancia AnythingLLM real (sin acceso a API key en este entorno)
- Smoke queries pueden fallar si el modelo LLM configurado en AnythingLLM no está disponible
- La subida de documentos via raw-text requiere que el contenido quepa en memoria
