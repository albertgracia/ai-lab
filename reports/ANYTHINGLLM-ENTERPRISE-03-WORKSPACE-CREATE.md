# ANYTHINGLLM-ENTERPRISE-03: Workspace Creation

**Estado:** ✅ PASS
**Fecha:** 2026-07-04
**HEAD:** d92cc92
**Ejecutado desde:** NAS-N5 → LAN `192.168.1.50:3001` (AnythingLLM Desktop)

---

## 0. Resumen

Creación automática vía API REST de los 10 workspaces Enterprise de AnythingLLM.

| Resultado | Valor |
|-----------|-------|
| Workspaces creados | **10/10** |
| Pre-existentes (defaults) | 2 (intocados) |
| API endpoint | `POST /api/v1/workspace/new` |
| Auth | Bearer token |
| Documentos cargados | **0** |
| Indexación iniciada | **0** |

---

## 1. Workspaces Creados

### Nivel 1 — Canónico

| # | Workspace | Slug | simThreshold | topN | temp | Prompt |
|:--:|-----------|------|:-----------:|:----:|:----:|:------:|
| 1 | **Hermes Enterprise** | `hermes-enterprise` | 0.70 | 5 | 0.2 | 829ch |
| 2 | **ADRs** | `adrs` | 0.75 | 5 | 0.2 | 381ch |

### Nivel 2 — Operativo

| # | Workspace | Slug | simThreshold | topN | temp | Prompt |
|:--:|-----------|------|:-----------:|:----:|:----:|:------:|
| 3 | **AI-LAB Runtime** | `ai-lab-runtime` | 0.65 | 5 | 0.2 | 409ch |
| 4 | **Rioja Marketplace** | `rioja-marketplace` | 0.60 | 5 | 0.2 | 277ch |
| 5 | **Observabilidad** | `observabilidad` | 0.65 | 5 | 0.2 | 271ch |
| 6 | **MCP y A2A** | `mcp-y-a2a` | 0.60 | 5 | 0.2 | 311ch |
| 7 | **Stack-2026** | `stack-2026` | 0.60 | 5 | 0.2 | 237ch |
| 8 | **IDS** | `ids` | 0.65 | 5 | 0.2 | 266ch |
| 9 | **Runbooks** | `runbooks` | 0.70 | 5 | 0.2 | 317ch |

### Nivel 3 — Evidencia

| # | Workspace | Slug | simThreshold | topN | temp | Prompt |
|:--:|-----------|------|:-----------:|:----:|:----:|:------:|
| 10 | **Reports** | `reports` | 0.55 | 5 | 0.2 | 363ch |

---

## 2. System Prompts

Cada workspace tiene su system prompt específico en español, incluyendo:

- Regla de **OBSERVADO / INFERIDO / SUPUESTO**
- **Prohibición de inventar facts**
- **Jerarquía documental:** Reports no sustituyen a fuentes canónicas
- Prohibición de ejecutar acciones
- Redirección a Observabilidad/Grafana/GitNexus según el tipo de consulta
- Formato Markdown CLI

---

## 3. Configuración RAG Aplicada

| Parámetro | Valor |
|-----------|-------|
| Chunk size | No configurable vía API (default del sistema) |
| Overlap | 128 (por defecto del sistema) |
| **topN** | **5** (seteado vía API) |
| **Temperature** | **0.2** (seteado vía API) |
| **SimilarityThreshold** | **0.55-0.75 según workspace** |

---

## 4. Detalles Técnicos

### API utilizada

| Endpoint | Método | Propósito |
|----------|--------|-----------|
| `/api/v1/workspace/new` | POST | Crear workspace |
| `/api/v1/workspace/{slug}/update` | POST | Configurar prompt y RAG |
| `/api/v1/workspace/{slug}` | DELETE | Limpiar duplicados |
| `/api/workspaces` | GET | Listar y validar |

### API Key

`YHNYABM-TVVM8Y3-HKHFD2S-SZVZVH2` (válida, desde conversación previa)

### Nota técnica

Workspace slugs se generan automáticamente desde el nombre (no son configurables vía API). Todos los slugs esperados se obtuvieron correctamente.

---

## 5. Validación

| Check | Resultado |
|-------|:---------:|
| 10 workspaces enterprise existentes | ✅ 10/10 |
| Slugs correctos | ✅ |
| System prompts aplicados | ✅ (237-829ch cada uno) |
| SimilarityThreshold configurado | ✅ (0.55-0.75) |
| topN=5 | ✅ |
| temperature=0.2 | ✅ |
| Cero documentos cargados | ✅ |
| Cero indexaciones iniciadas | ✅ |
| Defaults pre-existentes intactos | ✅ (Mi espacio de trabajo, Assistant Chats) |

---

## 6. Riesgos y Observaciones

| Observación | Detalle |
|-------------|---------|
| **API key** | La del archivo `.anythingllm.env` (`QG7JW4A-...`) no funcionó. Se usó la key de la sesión previa |
| **Desktop vs Server** | AnythingLLM Desktop NO expone el v1 API en el `app` raíz — solo bajo `/api/` vía `apiRouter`. Esto difiere de la documentación oficial que muestra rutas sin prefijo `/api` |
| **Slug no configurable** | `slug` no es writable vía API. Se genera automáticamente del `name`. No hubo conflictos |
| **System prompt durante creación** | `Workspace.new()` sobreescribe `openAiPrompt` con el default del sistema. Hubo que setearlo vía `update` post-creación |
| **Chunk/overlap** | No configurables vía API REST. Solo desde UI |

---

## 7. Próxima Fase

**ANYTHINGLLM-ENTERPRISE-04-DOCUMENT-IMPORT-FOUNDATION**

Cargar documentación canónica en los workspaces de Nivel 1 (Hermes Enterprise + ADRs) usando el script de carga (`scripts/anythingllm/reindex-workspace.ps1` adaptado).

No iniciar indexación hasta tener todos los documentos del Nivel 1 cargados.
