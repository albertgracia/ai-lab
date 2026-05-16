---
title: "Research: FASE 10 — JSON HARD FACTS + Qdrant Cognitive Layer"
summary: "Diseño y plan de implementación para HARD FACTS estructurado en JSON y memoria operacional cognitiva con Qdrant."
order: 18
---

## 1. Motivación

El bloque HARD FACTS actual es texto plano. El modelo lo parsea línea por línea
y tiende a alucinar campos que no existen (`routing_confidence`, `context_budget_used`, etc.).
Con JSON estructurado el modelo consulta por clave → valor directamente,
eliminando la interpolación semántica.

Además, la memoria operacional actual vive en RAM y muere al reiniciar.
Qdrant ya está corriendo en el cluster (`:6333`) y `nomic-embed-text-v1.5`
está cargado en RX9070. No hace falta instalar nada nuevo.

## 2. Decisión arquitectónica

**Opción C — Híbrido JSON + Qdrant en paralelo:**

| Componente | Enfoque |
|---|---|
| HARD FACTS | Bloque JSON al inicio + texto detallado debajo (híbrido) |
| Memoria persistente | Qdrant con 6 colecciones, hooks no-invasivos `try/except` |
| Embedding | `nomic-embed-text-v1.5` vía LM Studio API, **asíncrono** (cola background) |
| Routing histórico | Seed desde `routing_history.jsonl` (107 eventos) + `cognitive_history.jsonl` (106) |

### Por qué híbrido y no solo JSON

| Capa | Función |
|---|---|
| **JSON** | Parsing rápido y preciso del LLM. Consulta por clave → valor. |
| **Texto** | Redundancia humana + contexto narrativo. Respaldo si el JSON falla. |

Esto reduce drásticamente la *hallucination by interpolation*: el modelo recibe
datos precisos con delimitadores explícitos, no texto abierto a interpretación.

## 3. Schema JSON del HARD FACTS

```json
[HARD_FACTS_BEGIN]
=== AI-LAB RUNTIME (HARD FACTS) ===

{
  "schema_version": "1.0",
  "runtime": {
    "mode": "plan",
    "version": "1.1.0",
    "timestamp": "2026-05-16T18:00:00Z",
    "uptime_hours": 2.2
  },
  "gpu_nodes": [
    {
      "name": "rx9070-node",
      "host": "192.168.1.50",
      "friendly_name": "RX9070",
      "online": true,
      "vram_gb": 16,
      "latency_ms": 2,
      "models": [
        {
          "id": "qwen2.5-coder-14b-instruct",
          "ctx": 32768,
          "skills": ["coding", "debugging", "refactor", "testing"]
        },
        {
          "id": "llama-3.1-8b-instruct",
          "ctx": 128000,
          "skills": ["fast", "general", "chat", "summarisation"]
        },
        {
          "id": "text-embedding-nomic-embed-text-v1.5",
          "ctx": 8192,
          "skills": ["embeddings", "semantic-search", "rag"]
        }
      ]
    },
    {
      "name": "rx7900xt-node",
      "host": "192.168.1.60",
      "friendly_name": "RX7900XT",
      "online": false,
      "vram_gb": 20,
      "latency_ms": null,
      "models": []
    }
  ],
  "system": {
    "hostname": "ubuntu-ialab",
    "ram": {"total_gib": 7.2, "used_gib": 2.5, "available_gib": 4.7},
    "disk": {"total_g": 97, "used_g": 70, "pct": 76},
    "docker_containers": 16,
    "load": [0.28, 0.39, 0.43],
    "uptime_hours": 2.2
  },
  "services": [
    {"name": "ailab-router", "active": true, "running": true},
    {"name": "ailab-docs", "active": true, "running": true},
    {"name": "ailab-gateway", "active": true, "running": true},
    {"name": "ailab-heartbeat", "active": true, "running": true},
    {"name": "ailab-live-api", "active": true, "running": true},
    {"name": "ailab-live-state", "active": true, "running": true},
    {"name": "ailab-runner", "active": true, "running": true},
    {"name": "ailab-traefik", "active": true, "running": false}
  ],
  "docker": {
    "total": 16,
    "main": [
      "traefik", "open-webui", "ollama", "qdrant",
      "cadvisor", "node-exporter", "promtail", "portainer"
    ],
    "nginx_sites": [
      "musquera-web", "agithome", "albertskills",
      "agitservices", "albertskills-amd-multi"
    ]
  },
  "routing": {
    "total_events": 107,
    "cognitive_snapshots": 106,
    "model_performance": {
      "qwen2.5-coder-14b-instruct": {
        "requests": 7,
        "success_rate": 1.0,
        "performance_index": 97,
        "failover_rate": 0.0
      }
    }
  },
  "health": {
    "watchdog": {"ok": 6, "total": 6, "status": "healthy"},
    "active_sessions": 1
  },
  "pending_implementations": [
    "routing_confidence",
    "latency_per_request",
    "puppet_ansible",
    "gateway_api_write",
    "rx7900xt_diagnosis",
    "ci_cd_automation",
    "auto_scaling"
  ],
  "sites": [
    {"url": "ai-lab.labrazahome.com", "access": "public", "tech": "Cloudflare Pages + Astro"},
    {"url": "blog-ai-lab.labrazahome.com", "access": "private", "tech": "Cloudflare Tunnel + Traefik"}
  ]
}

[HARD_FACTS_END]

=== DETALLE (texto) ===
GPU NODES:
  🟢 rx9070-node → 192.168.1.50 (ONLINE, 16GB VRAM, 2ms)
     Models:
       · qwen2.5-coder-14b-instruct (32768 ctx, coding/debugging)
       · llama-3.1-8b-instruct (128000 ctx, fast/general)
       · text-embedding-nomic-embed-text-v1.5 (8192 ctx, embeddings)
  🔴 rx7900xt-node → 192.168.1.60 (OFFLINE, 20GB VRAM)
     No models available (node offline)
SYSTEM RESOURCES:
  · RAM: 7,2Gi total / 2,5Gi used / 4,7Gi available
  · Disk: 97G total / 70G used (76%)
  · Uptime: 2 hours, 12 minutes
  · Load: 0.28, 0.39, 0.43
  · Docker: 16 containers running
...
```

### Reglas del JSON

- `routing_confidence`, `avg_latency_ms` **NO existen** en el JSON
- Solo aparecen en `pending_implementations` como funcionalidades pendientes
- `latency_ms: null` en nodos offline (null ≠ 0, el modelo no debe interpretarlo como dato real)
- `model_performance` solo incluye modelos con datos reales en el histórico

## 4. Colecciones Qdrant

Las seis colecciones, cada una con `schema_version` y `event_type` explícitos.

### 4.1 `routing_history`

| Campo | Tipo | Fuente |
|---|---|---|
| `schema_version` | string | `"1.0"` |
| `event_type` | string | `routing_success`, `routing_failover`, `routing_error` |
| `id` | UUID | Generado |
| `timestamp` | ISO datetime | `routing_history.jsonl` |
| `task_type` | string | routing_history.jsonl |
| `model` | string | routing_history.jsonl |
| `node` | string | routing_history.jsonl |
| `host` | string | routing_history.jsonl |
| `latency_ms` | int | routing_history.jsonl |
| `success` | bool | routing_history.jsonl |
| `stream` | bool | routing_history.jsonl |
| `failover` | bool | routing_history.jsonl |
| `error` | string? | routing_history.jsonl |
| `embedding` | float[768] | nomic-embed-text-v1.5 |

### 4.2 `cognitive_history`

| Campo | Tipo | Fuente |
|---|---|---|
| `schema_version` | string | `"1.0"` |
| `event_type` | string | `context_shaping`, `budget_truncation`, `memory_digest` |
| `id` | UUID | Generado |
| `timestamp` | ISO datetime | `cognitive_history.jsonl` |
| `task_type` | string | cognitive_history.jsonl |
| `model` | string | cognitive_history.jsonl |
| `context_size` | int | cognitive_history.jsonl |
| `budget_used` | float | cognitive_history.jsonl |
| `shaping_latency_ms` | int | cognitive_history.jsonl |
| `files_used` | int | cognitive_history.jsonl |
| `files_used_names` | string[] | cognitive_history.jsonl |
| `working_memory_used` | bool | cognitive_history.jsonl |
| `embedding` | float[768] | nomic-embed-text-v1.5 |

### 4.3 `optimizer_history`

| Campo | Tipo | Fuente |
|---|---|---|
| `schema_version` | string | `"1.0"` |
| `event_type` | string | `weight_adjustment`, `policy_change`, `snapshot_restore` |
| ... | ... | `optimizer_history.jsonl` |
| `embedding` | float[768] | nomic-embed-text-v1.5 |

### 4.4 `incidents`

| Campo | Tipo | Fuente |
|---|---|---|
| `schema_version` | string | `"1.0"` |
| `event_type` | string | `watchdog_failure`, `502_upstream_error`, `node_offline` |
| `id` | UUID | Generado |
| `timestamp` | ISO datetime | watchdog / router errors |
| `severity` | string | `low`, `medium`, `high`, `critical` |
| `message` | string | Descripción del incidente |
| `node` | string? | Nodo afectado |
| `resolved` | bool | Estado actual del incidente |
| `embedding` | float[768] | nomic-embed-text-v1.5 |

### 4.5 `runtime_snapshots`

Snapshot periódico del JSON HARD FACTS completo. `event_type`: `periodic_snapshot`, `pre_action_snapshot`.

### 4.6 `working_memory`

Persistencia entre reinicios del session working memory. `event_type`: `session_start`, `session_turn`, `session_end`.

## 5. Retention policy

| Colección | Retención | Motivo |
|---|---|---|
| `routing_history` | 90 días | Patrones de routing estacionales |
| `cognitive_history` | 90 días | Context decay natural |
| `optimizer_history` | 180 días | Decisiones valiosas a largo plazo |
| `incidents` | Ilimitado | Fallos pasados siempre relevantes |
| `runtime_snapshots` | 30 días | Solo recall reciente |
| `working_memory` | 7 días | Solo sesiones activas |

Implementado como `retention_days` en config de cada colección + cron semanal.

## 6. Pipeline de embedding asíncrono

**NO** se embebe inline en el request path del router.

```
Request → router → LM Studio → response
                          ↓
                   jsonl append (síncrono, inmediato)
                          ↓
                   Background embedder (cola asíncrona)
                          ↓
                   qdrant upsert (batch cada 10s o 20 eventos)
```

### Detalles del embedder

- **Modelo**: `nomic-embed-text-v1.5` (dim 768, ya cargado en RX9070)
- **Batch**: máximo 10 eventos por request a LM Studio
- **Timeout**: 5s por batch
- **Daemon**: hilo background dentro del proceso router, o script independiente
- **Fallback**: si el embedder falla, los JSONL siguen acumulándose — no se pierde nada

## 7. Hooks no-invasivos

Todos siguen el patrón `try/except ImportError`:

```python
try:
    from runtime.memory.qdrant_store import store_embedding
    store_embedding(collection="routing_history", payload=data, embedding=emb)
except ImportError:
    pass
```

### Puntos de inyección

| Archivo | Evento | Colección |
|---|---|---|
| `runtime/routing/routing_history.py` | Nuevo evento de ruteo | `routing_history` |
| `runtime/cognitive/cognitive_history.py` | Nuevo snapshot cognitivo | `cognitive_history` |
| `runtime/autonomous/optimizer_history.py` | Nueva acción del optimizador | `optimizer_history` |
| `runtime/state/system_state.py` | Actualización de estado | `runtime_snapshots` |
| `runtime/llm/router_api.py` | Error 502 upstream | `incidents` |
| `runtime/watchdog/runtime_watchdog.py` | Fallo de watchdog | `incidents` |
| `runtime/agent/context_shaper.py` | Context shaping completado | `working_memory` |

## 8. API endpoints nuevos

### `GET /api/memory/search`

```json
{
  "query": "¿Qué pasó la última vez que RX7900XT falló?",
  "collection": "incidents",
  "limit": 5,
  "threshold": 0.75
}
```

Respuesta:
```json
{
  "results": [
    {
      "score": 0.89,
      "payload": {
        "schema_version": "1.0",
        "event_type": "watchdog_failure",
        "timestamp": "2026-05-14T12:30:00Z",
        "severity": "high",
        "message": "RX7900XT timeout en health check",
        "node": "rx7900xt-node",
        "resolved": false
      }
    }
  ]
}
```

### `GET /api/incidents/search`

Búsqueda semántica específica en la colección `incidents`, con filtro por `event_type` y `severity`.

### `GET /api/runtime/recall`

Cruza `routing_history`, `cognitive_history`, `incidents` para recall general. El endpoint más potente conceptualmente: ya no busca documentos, **recuerda experiencias operacionales similares**.

## 9. Astro UI: `/ops/memory`

Tres secciones:

1. **Episodios Recientes** — feed con últimos eventos de routing + cognitivos
2. **Incidentes Similares** — búsqueda semántica de fallos pasados
3. **Decisiones Repetidas** — patrones de routing detectados por similitud de embedding

```
┌─────────────────────────────────────┐
│  🧠 Memoria Operacional Cognitiva   │
├─────────────────────────────────────┤
│ 🔍 [Buscar en memoria...        ]  │
├─────────────────────────────────────┤
│ ┌─ Episodios Recientes ───────────┐│
│ │ 🟢 12:30 - routing: qwen2.5... ││
│ │ 🟢 12:28 - cognitive snapshot  ││
│ │ 🔴 12:00 - watchdog check pass ││
│ └──────────────────────────────────┘│
│ ┌─ Incidentes Similares ──────────┐│
│ │ 📌 Score: 0.89                  ││
│ │ "RX7900XT timeout en health..." ││
│ │ 📌 Score: 0.76                  ││
│ │ "Failover a llama3.1 tras..."   ││
│ └──────────────────────────────────┘│
└─────────────────────────────────────┘
```

## 10. Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Embedding lento satura LM Studio | Baja | Batch max 10, timeout 5s, cola asíncrona |
| Qdrant sin memoria (container reinicia) | Media | JSONL files = source of truth, Qdrant = cache semántico |
| Modelo ignora JSON y usa texto | Media | System prompt: "JSON es autoritativo, texto es respaldo" |
| `nomic-embed` no disponible | Baja | `try/except`: sin embedding = sin Qdrant, runtime no se rompe |
| Crecimiento ilimitado de Qdrant | Media | Retention policy por colección + cron semanal de poda |

## 11. Orden de implementación (3 días)

| Día | Mañana | Tarde |
|---|---|---|
| **1** | `context_shaper.py` → JSON híbrido | `qdrant_store.py` + `qdrant_collections.py` |
| **2** | Embedding pipeline (LM Studio API) | Routing hook + seed script desde JSONL |
| **3** | API endpoints (`/api/memory/search`, etc.) | Astro `/ops/memory` + state snapshot hook |
