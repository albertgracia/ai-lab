# AI-LAB-MCP-TOKEN-AUTH-COMPATIBILITY-PLAN-01

**Estado:** PASS
**Fecha:** 2026-06-01
**HEAD:** 6786415a
**Rama:** main (sincronizada con origin/main)

---

## 1. Resumen

Se inspeccionó cómo OpenCode se conecta al MCP actual, se evaluó el soporte de token/headers en OpenCode y el source del servidor MCP. Se diseñó un plan de compatibilidad para añadir autenticación por token sin romper el OpenCode actual.

---

## 2. Conexión actual OpenCode → MCP

- **Config:** `/home/albert/.config/opencode/opencode.jsonc`
- **Tipo:** `remote`
- **URL:** `http://127.0.0.1:8091/mcp`
- **Headers/token:** No configurado
- **Soporte de headers en OpenCode:** No confirmado (schema no accesible localmente)

**Conclusión:** OpenCode actual no envía token ni headers. Cualquier cambio que exija token en el endpoint actual rompería OpenCode.

---

## 3. Source MCP — Puntos de auth

- **`AILAB_MCP_TOKEN`:** Definido en `server.py` pero solo usado para decidir bind (local vs LAN), **no implementa validación real**.
- **Middleware de auth:** No existe
- **FastMCP `streamable_http_app()`:** No incluye verificación de token
- **Framework:** Uvicorn + Starlette (soporta middleware ASGI)

---

## 4. Opciones evaluadas

| Opción | Descripción | Riesgo para OpenCode | Verdicto |
|---|---|---|---|
| A | Token obligatorio para todo (único endpoint) | Alto — rompe OpenCode | No recomendada |
| B | Localhost sin token + LAN con token (misma app, inspección de origen) | Medio — riesgo de falsificación de origen | Posible pero limitada |
| C | **Segundo endpoint/puerto LAN con token** (8091 intacto + 8092 con token) | **Nulo** — OpenCode no se toca | **Recomendada** |

---

## 5. Decisión

**Opción C: Segundo endpoint/puerto LAN con token.**

- Mantener `127.0.0.1:8091/mcp` sin cambios (OpenCode sigue igual)
- Crear `ailab-mcp-lan-gateway.service` en `0.0.0.0:8092/mcp` con:
  - `AILAB_MCP_TOKEN` obligatorio
  - Middleware de validación Bearer token
  - Firewall allowlist (`192.168.1.50`, `192.168.1.60`, `192.168.1.250`)
  - Reutiliza `tools/` del servidor actual

---

## 6. Impactos

| Sistema | Impacto |
|---|---|
| OpenCode (Ubuntu AI-LAB) | **Ninguno.** Sigue apuntando a `127.0.0.1:8091/mcp` sin cambios |
| LM Studio | Se configura contra `192.168.1.30:8092/mcp` con token Bearer |
| Servicio MCP actual | **No se modifica.** `ailab-mcp-semantic-gateway.service` intacto |
| Seguridad LAN | Token + firewall allowlist antes de exponer |

---

## 7. Rollback

Detener y deshabilitar la unidad LAN, cerrar puerto 8092 en firewall. La unidad original 8091 nunca se toca.

---

## 8. Confirmación

- No se modificó `/mnt/mcp_server/server.py`
- No se modificó `/opt/ai-lab/mcp/`
- No se modificó OpenCode
- No se modificó systemd
- No se modificó firewall
- No se creó token real
- No se tocó runtime
- No se tocó Gateway/Router/Docker
- No se hizo push
- No se creó tag

---

## 9. Siguientes fases

1. `AI-LAB-MCP-LAN-ENDPOINT-READONLY-DESIGN-01` — Diseñar unidad systemd LAN + app runner
2. `AI-LAB-MCP-FIREWALL-ALLOWLIST-01` — Aplicar reglas UFW
3. `AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01` — Probar LM Studio vs 8092
