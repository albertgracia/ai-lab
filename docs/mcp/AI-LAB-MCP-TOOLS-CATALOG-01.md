# AI-LAB MCP Tools Catalog

**Estado:** Read-only catalog
**Fecha:** 2026-06-01
**HEAD:** 345bcb6d
**Servidor activo:** `/mnt/mcp_server/server.py`
**Transporte:** Streamable HTTP → `127.0.0.1:8091/mcp`
**Framework:** FastMCP + Uvicorn

---

## Tabla de herramientas

| # | Tool | Entrada | Salida | Fuente interna | Read-only | Riesgo | OpenCode | LM Studio |
|---|---|---|---|---|---|---|---|---|
| 1 | `ailab_status` | — | Gateway + Router health map | Gateway `:8008/health`, Router `:8083/health` | Sí | Bajo | Apta | Apta |
| 2 | `ailab_runtime_health` | — | Runtime health summary (nodes, scores, watchdog) | Gateway `:8008/runtime/health` | Sí | Bajo | Apta | Apta |
| 3 | `ailab_route_preview` | `prompt: str` | Heuristic route classification, no LLM | Local (regex) | Sí | Bajo | Apta | Apta |
| 4 | `ailab_operator_summary` | — | NOC-ready summary (services, nodes, GPU, watchdog) | Router `:8083/runtime/reporting/operator-summary` | Sí | Medio* | Apta con cautela | Apta con cautela |
| 5 | `ailab_incidents_active` | — | Incident intelligence report (failures, offline nodes) | Gateway `:8008/runtime/incidents/report` | Sí | Medio* | Apta con cautela | Apta con cautela |
| 6 | `ailab_slo_status` | — | SLO health + degradation + violations | Gateway `:8008/runtime/slo/status` + `/violations` | Sí | Bajo | Apta | Apta |
| 7 | `ailab_health_latency` | — | Latency stats (p50/p95/max) + health score | Gateway `:8008/runtime/health/latency` + `/score` | Sí | Bajo | Apta | Apta |
| 8 | `ailab_memory_search` | `query: str`, `limit: int=5` | Semantic search across Qdrant collections | Live-API `:8084/api/memory/search` | Sí | Medio* | Apta con cautela | Apta con cautela |

\* **Riesgo Medio:** Puede exponer información sensible del runtime si no se controla acceso. Ver notas abajo.

---

## Contratos detallados

### 1. `ailab_status`

- **Entrada:** ninguna
- **Salida:** `{"status": "ok|degraded|unavailable", "gateway": {"url", "ok", "status_code"}, "router": {"url", "ok", "status_code"}}`
- **Dependencia:** Gateway `:8008/health`, Router `:8083/health`
- **Mutable:** No. Solo `GET`.
- **Timeout:** 5s

### 2. `ailab_runtime_health`

- **Entrada:** ninguna
- **Salida:** `{"status": "ok|unavailable", "source": url, "data": {...}}`
- **Dependencia:** Gateway `:8008/runtime/health`
- **Mutable:** No. Solo `GET`.
- **Timeout:** 5s

### 3. `ailab_route_preview`

- **Entrada:** `prompt: str` (obligatorio)
- **Salida:** `{"status": "ok|error", "executed_model_call": false, "preview_type": "heuristic_preview", "route_family": "coding|reasoning|tool_use|fast|unknown", "confidence": 0.0-1.0, "reason": string}`
- **Dependencia:** Ninguna (heurística local con regex)
- **Mutable:** No. Sin llamada externa.
- **Log:** Prompt truncado a 120 chars en logs.

### 4. `ailab_operator_summary`

- **Entrada:** ninguna
- **Salida:** `{"status": "ok|unavailable", "data": {...}}`
- **Dependencia:** Router `:8083/runtime/reporting/operator-summary`
- **Mutable:** No. Solo `GET`.
- **Riesgo:** Puede exponer estado interno del cluster (GPU, nodos, watchdog). Controlar por IP/token.

### 5. `ailab_incidents_active`

- **Entrada:** ninguna
- **Salida:** `{"status": "ok|unavailable", "data": {...}}`
- **Dependencia:** Gateway `:8008/runtime/incidents/report`
- **Mutable:** No. Solo `GET`.
- **Riesgo:** Puede exponer fallos activos del sistema. Controlar por IP/token.

### 6. `ailab_slo_status`

- **Entrada:** ninguna
- **Salida:** `{"status": "ok", "slo_state": {...}, "violations": [...]}`
- **Dependencia:** Gateway `:8008/runtime/slo/status` + `/violations`
- **Mutable:** No. Solo `GET`.

### 7. `ailab_health_latency`

- **Entrada:** ninguna
- **Salida:** `{"status": "ok", "latency": {...}, "health_score": {...}}`
- **Dependencia:** Gateway `:8008/runtime/health/latency` + `/score`
- **Mutable:** No. Solo `GET`.
- **Observación:** `/score` puede timeout a 5s ocasionalmente.

### 8. `ailab_memory_search`

- **Entrada:** `query: str` (obligatorio), `limit: int` (opcional, default 5, max 20)
- **Salida:** `{"status": "ok|unavailable|error", "data": {...}}`
- **Dependencia:** Live-API `:8084/api/memory/search`
- **Mutable:** No. Solo `GET`.
- **Riesgo:** Puede exponer contenido del historial de routing, incidentes o memoria cognitiva. Limitar por token/IP/query scope.

---

## Recursos y Prompts

- **Resources:** No definidos.
- **Prompts:** No definidos.

---

## Resultados de validación

- **Tools detectadas:** 8/8 (coinciden con `register_all()` en `tools/__init__.py`)
- **Tools mutables:** 0
- **Shell/subprocess:** 0
- **Filesystem write:** 0
- **HTTP mutante (POST/PUT/DELETE):** 0
- **Secrets en source:** No
- **Timeout problemático:** `health_latency` → `/score` ocasionalmente timeoutea a 5s

---

## Compatibilidad OpenCode

| Tool | Apta | Notas |
|---|---|---|
| `ailab_status` | Sí | — |
| `ailab_runtime_health` | Sí | — |
| `ailab_route_preview` | Sí | Aclarar que es heurístico, no llama al router real |
| `ailab_operator_summary` | Sí con cautela | Puede exponer estado del cluster |
| `ailab_incidents_active` | Sí con cautela | Puede exponer fallos activos |
| `ailab_slo_status` | Sí | — |
| `ailab_health_latency` | Sí | — |
| `ailab_memory_search` | Sí con cautela | Limitar resultados, controlar queries |

---

## Compatibilidad LM Studio

| Tool | Apta | Notas |
|---|---|---|
| `ailab_status` | Sí | — |
| `ailab_runtime_health` | Sí | — |
| `ailab_route_preview` | Sí | — |
| `ailab_operator_summary` | Sí con cautela | Exponer solo con token + allowlist |
| `ailab_incidents_active` | Sí con cautela | Exponer solo con token + allowlist |
| `ailab_slo_status` | Sí | — |
| `ailab_health_latency` | Sí | — |
| `ailab_memory_search` | Sí con cautela | Limitar a `limit=5`, controlar acceso a Qdrant |

**Recomendación general:** LM Studio solo con token + LAN allowlist + solo tools read-only.

---

## Próximas mejoras

1. Schemas formales de entrada/salida (JSON Schema)
2. Recursos MCP (`resource://ailab/...`)
3. Prompts MCP (`prompt://ailab/...`)
4. Token auth (`AILAB_MCP_TOKEN`)
5. Repo unification (`/mnt/mcp_server` → repo)
6. Timeout ajustable para `/score`
