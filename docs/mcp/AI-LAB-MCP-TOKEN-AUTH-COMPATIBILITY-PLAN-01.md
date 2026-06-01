# AI-LAB MCP Token Auth Compatibility Plan

**Estado:** PLAN / READ-ONLY
**Fecha:** 2026-06-01
**HEAD:** 6786415a
**Rama:** main (sincronizada con origin)

---

## 1. Estado actual

### MCP activo

- Ruta: `/mnt/mcp_server/server.py`
- Servicio: `ailab-mcp-semantic-gateway.service` (PID 1501, running)
- Bind: `127.0.0.1:8091`
- Transporte: Streamable HTTP → endpoint `/mcp`
- Token: `AILAB_MCP_TOKEN` definido en source pero **sin implementación de validación real** (solo controla bind local vs LAN)
- Sin middleware de auth

### OpenCode (Ubuntu AI-LAB)

- Config: `/home/albert/.config/opencode/opencode.jsonc`
- Conexión MCP:
  ```json
  "mcp": {
    "ailab": {
      "type": "remote",
      "url": "http://127.0.0.1:8091/mcp",
      "enabled": true,
      "timeout": 15000
    }
  }
  ```
- **No tiene headers, ni token, ni autorización.**
- Solo `type`, `url`, `enabled`, `timeout`.
- No se pudo confirmar si OpenCode soporta headers en su `remote` MCP type (schema no accesible localmente).

---

## 2. Cómo funciona la conexión actual

1. OpenCode envía peticiones MCP streamable HTTP a `http://127.0.0.1:8091/mcp`
2. El servidor FastMCP procesa las peticiones (`POST /mcp` con body JSON-RPC)
3. No hay verificación de headers ni token
4. Todo funciona porque el bind es localhost (solo procesos locales pueden alcanzarlo)

---

## 3. Opciones de compatibilidad

### Opción A — Token obligatorio para todo

| Aspecto | Detalle |
|---|---|
| Descripción | Añadir middleware de validación de token en el endpoint `/mcp`. OpenCode y cualquier cliente deben mandar `Authorization: Bearer <token>` |
| Impacto OpenCode | **Riesgo alto de ruptura.** Si OpenCode no soporta headers en `remote` MCP type, dejaría de funcionar. Requiere verificar primero. |
| Impacto LM Studio | LM Studio soporta headers/token en config MCP, pero habría que configurarlo manualmente. |
| Complejidad | Baja (solo middleware + env var) |
| Rollback | Sencillo (quitar middleware) |
| **Veredicto** | **No recomendada como primer paso.** Riesgo de romper OpenCode actual. |

### Opción B — Localhost sin token + LAN con token (única app)

| Aspecto | Detalle |
|---|---|
| Descripción | Modificar `server.py` para distinguir origen: si `request.client.host == "127.0.0.1"`, omitir token; si es LAN, requerir token. |
| Impacto OpenCode | **Seguro.** Localhost sigue funcionando sin cambios. |
| Impacto LM Studio | LM Studio desde LAN necesitaría configurar token. |
| Complejidad | Media. Requiere modificar el servidor para inspeccionar origen y bifurcar lógica. |
| Riesgo | Que un atacante LAN pueda falsificar origen (limitado por bind+firewall). Si se usa `0.0.0.0`, el origen puede ser falsificado. |
| Rollback | Revertir cambios en `server.py`. |
| **Veredicto** | **Posible pero con limitaciones.** Depende de que el cliente real no pueda falsear origen. |

### Opción C — Segundo endpoint/puerto LAN con token (recomendada)

| Aspecto | Detalle |
|---|---|
| Descripción | Mantener `127.0.0.1:8091/mcp` intacto (sin cambios, sin token). Crear un segundo proceso/unidad systemd para LAN: `0.0.0.0:8092/mcp` con `AILAB_MCP_TOKEN` obligatorio + firewall allowlist. |
| Impacto OpenCode | **Cero riesgo.** OpenCode sigue apuntando a `127.0.0.1:8091/mcp` como hasta ahora. |
| Impacto LM Studio | LM Studio se configura con token contra `192.168.1.30:8092/mcp`. |
| Complejidad | Media. Nueva unidad systemd + nueva app runner en `/mnt/mcp_server/` (reutilizando tools/). |
| Riesgo | Mínimo. El puerto 8092 solo se abre con token + firewall. Rollback: detener unidad y cerrar puerto. |
| Rollback | `systemctl stop ailab-mcp-lan-gateway.service && ufw delete allow 8092` |
| **Veredicto** | **Recomendada.** Máxima compatibilidad, mínimo riesgo. |

---

## 4. Decisión recomendada

**Opción C: Segundo endpoint/puerto LAN con token.**

### Arquitectura propuesta

```
127.0.0.1:8091/mcp  →  ailab-mcp-semantic-gateway.service  (sin cambios)
                          Solo localhost
                          Sin token
                          OpenCode actual sigue igual

0.0.0.0:8092/mcp    →  ailab-mcp-lan-gateway.service       (nuevo)
                          Con AILAB_MCP_TOKEN obligatorio
                          Firewall allowlist (192.168.1.50, .60, .250)
                          Reutiliza tools/ del servidor actual
                          Logging específico LAN
```

### Requisitos para implementación

- Nueva unidad systemd: `ailab-mcp-lan-gateway.service`
- Puerto: `8092`
- Bind: `0.0.0.0` o IP LAN del servidor `192.168.1.30`
- Token: `AILAB_MCP_TOKEN` obligatorio vía Environment o drop-in
- Firewall: UFW allowlist
- App runner: script nuevo que importe tools/ existentes y añada middleware de token
- Logging dedicado para auditoría LAN

---

## 5. Implementación de token en el servidor

El token debe validarse mediante middleware ASGI en Uvicorn o en el wrapper FastMCP:

```python
from starlette.middleware.base import BaseHTTPMiddleware

class TokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        if token != os.environ.get("AILAB_MCP_TOKEN", ""):
            from starlette.responses import JSONResponse
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)
```

Esto aplica a todas las rutas, incluido `/mcp` y `/health`.

---

## 6. Impacto sobre OpenCode actual

- **Ninguno.** El endpoint `127.0.0.1:8091/mcp` no se modifica.
- OpenCode sigue conectando como ahora sin headers, sin token.

---

## 7. Impacto sobre LM Studio

- LM Studio se configura contra el endpoint LAN `192.168.1.30:8092/mcp`
- Necesita token en la configuración MCP de LM Studio
- Compatible si LM Studio soporta `Authorization: Bearer <token>` en sus requests MCP
- Las tools read-only actuales son seguras para LM Studio

---

## 8. Rollback

```bash
# Detener y deshabilitar unidad LAN
systemctl stop ailab-mcp-lan-gateway.service
systemctl disable ailab-mcp-lan-gateway.service

# Cerrar puerto firewall
ufw delete allow 8092/tcp

# La unidad original (8091) no se toca nunca
# Rollback completo en < 30 segundos
```

---

## 9. Fases siguientes

1. `AI-LAB-MCP-LAN-ENDPOINT-READONLY-DESIGN-01` — Diseñar la nueva unidad systemd + app runner
2. `AI-LAB-MCP-FIREWALL-ALLOWLIST-01` — Aplicar reglas UFW
3. `AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01` — Probar conexión LM Studio contra 8092

---

## 10. Riesgos documentados

- **Riesgo 0:** OpenCode no se toca, no hay riesgo de ruptura.
- **Riesgo menor:** Token mal configurado en unidad LAN → servicio LAN no arranca (no afecta 8091).
- **Riesgo menor:** Firewall allowlist mal escrita → IPs autorizadas no pueden conectar.
- **Riesgo a futuro:** Si se decide unificar a un solo endpoint, requeriría migración coordinada de OpenCode.

---

## 11. Pendiente

- Confirmar si OpenCode `remote` MCP type soporta headers (para futura migración a endpoint único)
- Si LM Studio soporta Bearer token en MCP HTTP (asumido, pendiente verificación)
