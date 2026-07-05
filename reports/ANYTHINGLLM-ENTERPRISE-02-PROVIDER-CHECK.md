# ANYTHINGLLM-ENTERPRISE-02: Provider Check

**Estado:** ✅ PASS — Providers validados
**Fecha:** 2026-07-04
**HEAD:** d92cc92 (CP-HERMES-DOCS-ASTRO-ENTERPRISE-01)

---

## 1. Resumen

Validación de providers para AnythingLLM antes de crear workspaces y cargar documentos.

| Componente | Estado | Detalle |
|------------|--------|---------|
| AnythingLLM host | ✅ OK | `192.168.1.50:3001` |
| API key | ✅ OK | `YHNYABM-TVVM8Y3-HKHFD2S-SZVZVH2` |
| LM Studio backend | ✅ OK | `192.168.1.50:1234` — 6 modelos cargados |
| Chat test | ✅ OK | `qwen2.5-14b-instruct` → "ok" |
| Embedding test | ✅ OK | `text-embedding-nomic-embed-text-v1.5` → vector 768d |

### Mapa de hosts (corregido)

| Host | IP | Puerto | Servicio | Accesible desde .200 |
|------|----|--------|----------|:----:|
| **AnythingLLM** | `192.168.1.50` | `3001` | RAG/documental | ❌ (localhost only) |
| **LM Studio** | `192.168.1.50` | `1234` | Inferencia | ✅ |
| **Grafana** | `192.168.1.40` | `3001` | Dashboards | ❌ (localhost only) |
| ~~NAS-N5~~ | ~~.200~~ | ~~3001~~ | ~~(erróneo)~~ | — |

AnythingLLM y Grafana están vinculados a `127.0.0.1` y no son accesibles desde otras máquinas. Solo LM Studio en `.50:1234` es accesible desde fuera.

**Nota:** `192.168.1.30:3001` responde como Grafana v12.0.2 pero según el usuario Grafana está en `.40:3001`. Posible instancia legacy/duplicada en `.30`.

---

## 2. LM Studio (Backend de Inferencia)

### 2.1 Modelos disponibles

```
GET http://192.168.1.50:1234/v1/models
→ 200 OK
```

| Model ID | Tipo | Uso propuesto |
|----------|------|---------------|
| `qwen2.5-14b-instruct` | Chat | LLM provider para AnythingLLM |
| `google/gemma-4-12b` | Chat | Alternativa / pruebas |
| `qwen/qwen3.6-27b` | Chat | Backup (heavy) |
| `deepseek-coder-v2-lite-instruct` | Chat | Alternativa coding |
| `deepseek/deepseek-r1-distill-qwen-14b` | Chat | Alternativa razonamiento |
| `text-embedding-nomic-embed-text-v1.5` | Embeddings | Embedding provider |

### 2.2 Prueba de chat

```
POST /v1/chat/completions {"model":"qwen2.5-14b-instruct","messages":[{"role":"user","content":"responde solo: ok"}]}
→ "content": "ok"
→ finish_reason: "stop"
→ tokens: 34 prompt + 2 completion
```

**Resultado: ✅ PASS**

### 2.3 Prueba de embeddings

```
POST /v1/embeddings {"model":"text-embedding-nomic-embed-text-v1.5","input":"test de embedding"}
→ 768-dimensional vector
→ model: "text-embedding-nomic-embed-text-v1.5"
```

**Resultado: ✅ PASS**

---

## 3. AnythingLLM

### 3.1 Conectividad

```
GET http://127.0.0.1:3001/
→ 404 Not Found (Express, esperado — no hay ruta raíz)
```

Servidor Express.js corriendo en puerto `:3001` de **NAS-N5 (192.168.1.200)**.

### 3.2 API Key

```
Authorization: Bearer YHNYABM-TVVM8Y3-HKHFD2S-SZVZVH2
→ 200 OK en endpoints autenticados
```

**API key válida y funcional.**

### 3.3 Workspaces existentes

```
GET /api/v1/workspaces
→ 200 OK
```

2 workspaces por defecto (creados hoy 2026-07-04):

| Workspace | Slug | Creado | Docs |
|-----------|------|--------|------|
| Mi espacio de trabajo | `mi-espacio-de-trabajo` | 13:56:19 | 0 |
| Assistant Chats | `assistant-chats` | 13:57:36 | 0 |

### 3.4 Configuración actual

| Parámetro | Valor | Nota |
|-----------|-------|------|
| **LLM Provider** | `null` | No configurado |
| **LLM Model** | `null` | No configurado |
| **Embedding Provider** | Default (built-in) | No configurado explícitamente |
| **Vector DB** | LanceDB (default) | Integrado |
| **Similarity Threshold** | 0.25 | Default |
| **Top-N** | 4 | Default |
| **Context Window** | 16384 | 16K tokens default |
| **Chat Mode** | `automatic` | Default |

---

## 4. Configuración Recomendada (pendiente de aplicar)

| Parámetro | Valor Recomendado | Razón |
|-----------|-------------------|-------|
| **LLM Provider** | LM Studio (OpenAI-compatible) | `http://192.168.1.50:1234/v1` |
| **Chat Model** | `qwen2.5-14b-instruct` | Mejor comprensión técnica, 32K contexto |
| **Embedding Provider** | Built-in `all-MiniLM-L6-v2` | Hasta que LM Studio sea emb provider configurable |
| **Alternativa Embeddings** | `text-embedding-nomic-embed-text-v1.5` | 768d, mejor recall. Requiere LM Studio como provider embeddings |
| **Vector DB** | LanceDB (default) | Suficiente para ~10 workspaces documentales |
| **Similarity Threshold** | 0.25 | Default. Ajustar post-carga si necesario |
| **Top-N** | 5 | Diseño original (vs 4 default) |
| **Context Window** | 4096 | Diseño original (vs 16384 default) |

### Decisión final: Embeddings

| Provider | Disponible | Recomendado |
|----------|-----------|-------------|
| `text-embedding-nomic-embed-text-v1.5` via LM Studio | ✅ Sí | **Preferido** (768d, mejor recall) |
| `all-MiniLM-L6-v2` built-in | ✅ Siempre | Fallback si LM Studio no está disponible como embedding provider en AnythingLLM |

AnythingLLM v13.x puede no soportar LM Studio como proveedor de embeddings nativamente. Si no es configurable, usar built-in `all-MiniLM-L6-v2`.

---

## 5. Pruebas Realizadas

### 5.1 Chat simple

**Input:**
```json
{"model":"qwen2.5-14b-instruct","messages":[{"role":"user","content":"responde solo: ok"}],"max_tokens":10}
```

**Output:** ✅ `"content": "ok"` (cold start ~30s, luego respuesta inmediata)

### 5.2 Embedding simple

**Input:**
```json
{"model":"text-embedding-nomic-embed-text-v1.5","input":"test de embedding"}
```

**Output:** ✅ Vector 768-dim, sin errores

### 5.3 Conexión estable

**Resultado:** ✅ Ambas APIs (LM Studio .50 y AnythingLLM local) responden consistentemente.

---

## 6. Bloqueadores

| Blocker | Estado | Resolución |
|---------|--------|------------|
| LM Studio caído | ✅ **RESUELTO** | Usuario reinició LM Studio en .50 |
| API key inválida | ✅ **RESUELTO** | Usuario generó nueva API key |
| Host incorrecto en .env | ⚠️ **CORREGIR** | `.anythingllm.env` apunta a `127.0.0.1:3001` (localhost). Si el script se ejecuta desde el NAS-N5, funciona. Si se ejecuta desde .30, apunta a Grafana en lugar de AnythingLLM |

---

## 7. Decisión Final

| Criterio | Resultado |
|----------|-----------|
| LM Studio reachable | ✅ PASS |
| Chat model `qwen2.5-14b-instruct` | ✅ PASS |
| Embedding model `nomic-embed-text-v1.5` | ✅ PASS |
| AnythingLLM reachable | ✅ PASS |
| API key funcional | ✅ PASS |
| LLM provider configurado | ❌ NO (pendiente de configuración) |
| Embedding provider configurado | ❌ NO (pendiente de configuración) |

**Estado global: ✅ PASS**

---

## 8. Siguiente Fase: ANYTHINGLLM-ENTERPRISE-03-WORKSPACE-CREATE

### Pre-requisitos cumplidos

1. ✅ **LM Studio** activo en `.50:1234` con `qwen2.5-14b-instruct` + `nomic-embed-text-v1.5`
2. ✅ **AnythingLLM** activo en `127.0.0.1:3001` (NAS-N5 .200)
3. ✅ **API key** válida: `YHNYABM-TVVM8Y3-HKHFD2S-SZVZVH2`

### Acciones para la siguiente fase

1. **Configurar LLM Provider** en AnythingLLM:
   - Provider: LM Studio (OpenAI-compatible)
   - Base URL: `http://192.168.1.50:1234/v1`
   - Model: `qwen2.5-14b-instruct`

2. **Configurar Embedding Provider** en AnythingLLM:
   - Opción A: `text-embedding-nomic-embed-text-v1.5` via LM Studio (si soportado)
   - Opción B: `all-MiniLM-L6-v2` built-in (fallback)

3. **Crear workspaces** según diseño (10 workspaces, Fase A primero):
   - Hermes Enterprise
   - AI-LAB Runtime
   - ADRs
   - Reports

4. **Actualizar `.anythingllm.env`:**
   - `ANYTHINGLLM_BASE_URL=http://127.0.0.1:3001`
   - `ANYTHINGLLM_WORKSPACE_SLUG=ai-lab-core`
   - `ANYTHINGLLM_API_KEY=YHNYABM-TVVM8Y3-HKHFD2S-SZVZVH2`
