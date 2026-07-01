# AI-LAB-MCP-TOOLS-CATALOG-VALIDATION-01

**Estado:** PASS
**Fecha:** 2026-06-01
**HEAD:** 345bcb6d
**Rama:** main
**Git:** ahead 6 de origin/main

---

## 1. Resumen

Se validó formalmente el catálogo de 8 tools expuestas por el servidor MCP activo en `/mnt/mcp_server/server.py`. Se confirmaron contratos de entrada/salida, comportamiento read-only, riesgos, compatibilidad con OpenCode y con LM Studio.

---

## 2. Servicio MCP activo

- **Servicio:** `ailab-mcp-semantic-gateway.service`
- **PID:** 1501
- **Estado:** active (running)
- **Ruta:** `/mnt/mcp_server/server.py`
- **Bind:** `127.0.0.1:8091`
- **Transporte:** Streamable HTTP → endpoint `/mcp` (406 sin headers MCP)

---

## 3. Tools detectadas y validadas

| # | Tool | Mutable | Shell | Filesystem write | HTTP mutante | Riesgo |
|---|---|---|---|---|---|---|
| 1 | `ailab_status` | No | No | No | No | Bajo |
| 2 | `ailab_runtime_health` | No | No | No | No | Bajo |
| 3 | `ailab_route_preview` | No | No | No | No | Bajo |
| 4 | `ailab_operator_summary` | No | No | No | No | Medio* |
| 5 | `ailab_incidents_active` | No | No | No | No | Medio* |
| 6 | `ailab_slo_status` | No | No | No | No | Bajo |
| 7 | `ailab_health_latency` | No | No | No | No | Bajo |
| 8 | `ailab_memory_search` | No | No | No | No | Medio* |

\* **Riesgo Medio:** Pueden exponer información interna del runtime (estado de nodos, fallos activos, memoria Qdrant). Mitigable con token + allowlist.

**Todas las tools son read-only.** 0 operaciones mutables, 0 shell, 0 filesystem write, 0 HTTP POST/PUT/DELETE.

---

## 4. Pruebas realizadas

- **Endpoint probe:** `/health` → 404, `/` → 404, `/mcp` → 406 (esperado para MCP streamable HTTP sin headers de protocolo)
- **Test existente:** `test_mcp_semantic_gateway_01.py` → cubre el servidor obsoleto (`/opt/ai-lab/mcp/servers/`), no el activo. No se ejecutó por no aplicar.
- **Sin cliente MCP local disponible para probar tools vía protocolo sin modificar el servidor.**

---

## 5. Recursos y Prompts

- **Resources:** 0
- **Prompts:** 0
- **Gap:** No hay resources ni prompts definidos en el servidor activo.

---

## 6. Compatibilidad

### OpenCode
- Todas las 8 tools son aptas para OpenCode.
- `operator_summary`, `incidents_active`, `memory_search` requieren cautela (información interna).
- `route_preview` debe documentarse como heurístico local.

### LM Studio
- `status`, `runtime_health`, `route_preview`, `slo_status`, `health_latency` → aptas directamente.
- `operator_summary`, `incidents_active`, `memory_search` → aptas con token + allowlist.
- Ninguna tool mutable → seguras para LM Studio en modo read-only.

---

## 7. Riesgos

| Riesgo | Severidad | Mitigación |
|---|---|---|
| MCP activo fuera del repo (`/mnt/mcp_server/`) | Alta | Repo unification |
| Sin token de autenticación | Alta | Añadir `AILAB_MCP_TOKEN` |
| `operator_summary` expone estado del cluster | Media | Token + allowlist |
| `incidents_active` expone fallos del sistema | Media | Token + allowlist |
| `memory_search` expone historial Qdrant | Media | Limitar por token/query scope |
| `health_latency` timeout en `/score` (5s) | Baja | Timeout ajustable |
| Sin resources ni prompts | Baja | Fase futura |
| Duplicidad `/opt/ai-lab/mcp` vs `/mnt/mcp_server` | Media | Repo unification |

---

## 8. Próximas fases

1. `AI-LAB-MCP-TOKEN-AUTH-READONLY-01`
2. `AI-LAB-MCP-FIREWALL-ALLOWLIST-01`
3. `AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01`
4. `AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-01`

---

## 9. Confirmación

- No se modificó `/mnt/mcp_server/server.py`
- No se modificó `/opt/ai-lab/mcp/`
- No se modificó systemd
- No se modificó firewall
- No se modificó bind address
- No se creó token real
- No se tocó runtime
- No se tocó Gateway/Router
- No se tocó Docker
- No se tocó Astro
- No se hizo push
- No se creó tag

**Commit:** `docs(mcp): validate tools catalog`
