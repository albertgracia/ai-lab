# AI-LAB-MCP-EXISTING-SERVER-INVENTORY-01

**Estado:** PASS
**Fecha:** 2026-06-01
**HEAD:** 70eacd8d
**Rama:** main
**Git:** ahead 4 de origin/main, working tree limpio

---

## 1. Resumen

Se localizó e inventarió el servidor MCP real de AI-LAB. El servidor activo NO está en el repo de git. Vive en `/mnt/mcp_server/` con arquitectura modular. El directorio `/opt/ai-lab/mcp/` contiene una versión anterior (monolítica, 3 tools) que NO es la que ejecuta systemd.

---

## 2. Montajes relevantes

| Filesystem | Punto | Tamaño | Uso |
|---|---|---|---|
| /dev/mapper/ubuntu--vg-ai--models | /mnt/ai-models | 79G | 1% |
| /dev/mapper/ubuntu--vg-ai--lab--data | /opt/ai-lab-data | 15G | 4% |
| systemd-1 | /mnt/opencode | autofs | OpenCode workspace |

---

## 3. Rutas MCP encontradas

### Activa (en /mnt, fuera del repo)
```
/mnt/mcp_server/
  server.py              <- entrypoint real
  config/ailab_semantic_gateway.mcp.json
  tools/
    __init__.py          <- register_all()
    client.py            <- HTTP client compartido
    status.py            -> ailab_status
    runtime_health.py    -> ailab_runtime_health
    route_preview.py     -> ailab_route_preview
    operator.py          -> ailab_operator_summary
    incidents.py         -> ailab_incidents_active
    slo.py               -> ailab_slo_status
    latency.py           -> ailab_health_latency
    memory.py            -> ailab_memory_search
```

### Stale (en /opt/ai-lab, dentro del repo)
```
/opt/ai-lab/mcp/
  servers/ailab_semantic_gateway.py   <- monolítico, 3 tools
  config/ailab_semantic_gateway.mcp.json
  config/filesystem.mcp.json
  config/git.mcp.json
  logs/semantic_gateway.log
```

### Relación /opt vs /mnt
- No hay symlinks entre ambas rutas.
- El servicio systemd apunta directamente a `/mnt/mcp_server/server.py`.
- `/opt/ai-lab/mcp/` quedó como copia obsoleta en el repo.

---

## 4. Servicio systemd

```
Nombre: ailab-mcp-semantic-gateway.service
Estado: active (running), PID 1501
Usuario: albert
WorkingDirectory: /mnt/mcp_server
ExecStart: /opt/ai-lab/.venv/bin/python /mnt/mcp_server/server.py
MemoryMax: 128M (actual: 62.9M)
Restart: always (5s)
```

**Variables de entorno:**
```
AILAB_GATEWAY_URL=http://127.0.0.1:8008
AILAB_ROUTER_URL=http://127.0.0.1:8083
AILAB_LIVE_API_URL=http://127.0.0.1:8084
AILAB_MCP_BIND=127.0.0.1
AILAB_MCP_PORT=8091
AILAB_MCP_LOG_LEVEL=INFO
```

No tiene `AILAB_MCP_TOKEN` → modo local dev, bind automático a 127.0.0.1.

---

## 5. Puerto / bind / transporte

| Atributo | Valor |
|---|---|
| Puerto | 8091 |
| Bind | 127.0.0.1 (solo local) |
| Transporte | Streamable HTTP (MCP) |
| Endpoint MCP | `http://127.0.0.1:8091/mcp` |
| Framework | FastMCP + Uvicorn |
| Auth token | No configurado (dev mode) |

---

## 6. Tools actuales (8 tools, todas read-only)

| Tool | Dependencia | Riesgo |
|---|---|---|
| `ailab_status` | Gateway + Router health | Bajo |
| `ailab_runtime_health` | Gateway /runtime/health | Bajo |
| `ailab_route_preview` | Heurística local (regex) | Bajo |
| `ailab_operator_summary` | Router /operator-summary | Bajo |
| `ailab_incidents_active` | Gateway /incidents/report | Bajo |
| `ailab_slo_status` | Gateway /slo/status + /violations | Bajo |
| `ailab_health_latency` | Gateway /latency + /score | Bajo |
| `ailab_memory_search` | Live-API /memory/search | Bajo |

**Resources:** No se encontraron.
**Prompts:** No se encontraron.
**Total tools activas: 8** (frente a 3 del servidor obsoleto en `/opt/ai-lab`).

---

## 7. Logs relevantes

- Sin errores en el último ciclo de vida.
- Un reinicio planificado a las 04:42 (11h 34min de uptime previo).
- Tools operativas con timeouts esporádicos en `runtime/health/score` (5s).
- POST `/mcp` responde 200 OK y 202 Accepted (streaming).
- GET `/health` devuelve 404 (no implementado en FastMCP).
- GET `/mcp` devuelve 406 (esperado, requiere cabeceras MCP streamable HTTP).

---

## 8. Configuración OpenCode

**Activa (`opencode.jsonc`):**
- MCP remoto configurado como `ailab` → `http://127.0.0.1:8091/mcp`
- timeout: 15000ms, enabled: true
- Provider `ailab-router` en `http://192.168.1.30:8083/v1`

**Secundaria (`opencode.json`):**
- Solo `gitnexus` MCP local

---

## 9. Compatibilidad LM Studio

**Estimación: Compatible con túnel.**

- El servidor actual usa **Streamable HTTP** → LM Studio lo soporta.
- Está bind a `127.0.0.1` → No accesible desde LM Studio remoto sin túnel.
- Sin auth token → Requiere túnel SSH o exponer a LAN con token.
- Todas las tools son **read-only** → Seguras para exponer.
- Si LM Studio corre en la misma máquina → Compatible directo.

**Riesgo:** Exponer el puerto a LAN sin token permite acceso a observables del runtime.

---

## 10. Riesgos

1. **Duplicidad /opt vs /mnt** — El repo contiene servidor obsoleto (3 tools). Clon nuevo no tendrá el MCP real.
2. **Bind local sin token** — Seguro para dev, bloquea consumo remoto directo.
3. **Sin resources ni prompts** — Faltan para búsqueda semántica y contexto.
4. **Tools no versionadas en git** — `/mnt/mcp_server` sin control de versiones.
5. **Timeout esporádico** — `runtime/health/score` timeoutea a 5s ocasionalmente.

---

## 11. Recomendaciones

1. **AI-LAB-MCP-CONTROL-PLANE-SPEC-01** — Unificar `/mnt/mcp_server/` con el repo, versionando tools y config en git.
2. **AI-LAB-MCP-TOOLS-CATALOG-VALIDATION-01** — Validar que todas las tools del directorio `tools/` están registradas y documentadas.
3. **AI-LAB-LMSTUDIO-MCP-SAFE-READONLY-INTEGRATION-01** — Evaluar integración segura con LM Studio (túnel SSH + token).

---

## 12. Confirmación

- ✅ No se modificaron archivos (salvo este informe).
- ✅ No se reiniciaron servicios.
- ✅ No se tocó runtime.
- ✅ No se tocó Docker.
- ✅ No se hizo push.
- ✅ No se creó tag.

**Commit:** `docs(audit): inventory existing mcp server`
