# AI-LAB-MCP-LAN-ENDPOINT-READONLY-DESIGN-01

**Estado:** PASS
**Fecha:** 2026-06-01
**HEAD:** 997b4160
**Rama:** main (sincronizada con origin/main)

---

## 1. Resumen

Se diseñó el futuro endpoint MCP LAN read-only en puerto `8092` para AI-LAB. El endpoint local `127.0.0.1:8091/mcp` queda intacto. No se implementó nada. Puerto `8092` verificado como libre.

---

## 2. Estado MCP actual

- **Servicio:** `ailab-mcp-semantic-gateway.service` (PID 1501, running)
- **Endpoint:** `127.0.0.1:8091/mcp` — sin cambios, sin token
- **Uso actual:** OpenCode en Ubuntu AI-LAB
- **Puerto 8092:** Libre (no escucha ningún proceso)

---

## 3. Diseño producido

| Aspecto | Decisión |
|---|---|
| Opción técnica | **B — Wrapper/runner LAN separado** (`lan_server.py`) |
| Puerto LAN | `0.0.0.0:8092/mcp` |
| Servicio nuevo | `ailab-mcp-lan-gateway.service` |
| Token | `AILAB_MCP_TOKEN` vía `EnvironmentFile` |
| Auth header | `Authorization: Bearer <token>` |
| Middleware | ASGI (Starlette) sobre FastMCP streamable HTTP |
| Firewall | UFW allowlist (192.168.1.50, .60, .250) |
| Tools | 8 read-only (5 sin restricciones, 3 con cautela) |
| Rollback | < 30s, no afecta 8091 |

---

## 4. Impactos

| Sistema | Impacto |
|---|---|
| OpenCode (Ubuntu AI-LAB) | **Ninguno.** Sigue usando `127.0.0.1:8091/mcp` sin cambios |
| MCP local (`ailab-mcp-semantic-gateway.service`) | **No se modifica** |
| LM Studio | Se configura contra `192.168.1.30:8092/mcp` con token Bearer |
| Firewall | Reglas UFW diseñadas, no aplicadas |
| Systemd | Unidad diseñada, no creada |

---

## 5. Confirmación

- No se modificó `/mnt/mcp_server/server.py`
- No se modificó `/opt/ai-lab/mcp/`
- No se modificó OpenCode
- No se creó unidad systemd
- No se modificó firewall
- No se creó token real
- No se abrió puerto 8092
- No se tocó runtime/Gateway/Router/Docker
- No se hizo push
- No se creó tag

---

## 6. Siguientes fases

1. `AI-LAB-MCP-LAN-ENDPOINT-READONLY-IMPLEMENTATION-01` — Crear `lan_server.py` + unidad systemd
2. `AI-LAB-MCP-FIREWALL-ALLOWLIST-01` — Aplicar reglas UFW
3. `AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01` — Probar LM Studio contra 8092
4. `AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-01` — Unificar MCP en el repo
