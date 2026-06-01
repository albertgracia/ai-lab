# AI-LAB MCP LAN Endpoint Read-Only Design

**Estado:** DESIGN / READ-ONLY
**Fecha:** 2026-06-01
**HEAD:** 997b4160
**Rama:** main (sincronizada con origin)

---

## 1. Objetivo

Diseñar un endpoint MCP LAN read-only separado para AI-LAB, manteniendo intacto el endpoint local `127.0.0.1:8091/mcp` usado por OpenCode.

---

## 2. Estado actual

| Aspecto | Valor |
|---|---|
| Endpoint local (OpenCode) | `127.0.0.1:8091/mcp` — intacto |
| Servicio local | `ailab-mcp-semantic-gateway.service` (PID 1501, running) |
| MCP activo | `/mnt/mcp_server/server.py` |
| Framework | FastMCP + Uvicorn + Streamable HTTP |
| Token | `AILAB_MCP_TOKEN` en source, sin validación real |
| Bind | Controlado por `AILAB_MCP_BIND` + `AILAB_MCP_PORT` (env) |
| Tools | 8 read-only (catalogadas en `AI-LAB-MCP-TOOLS-CATALOG-01.md`) |
| Puerto `8092` | **Libre** (no escucha ningún proceso) |

---

## 3. Decisión de diseño

**No tocar `127.0.0.1:8091/mcp`.** OpenCode sigue apuntando ahí sin cambios.

Crear nuevo endpoint LAN en **`0.0.0.0:8092/mcp`** mediante **Opción B: wrapper/runner separado**.

---

## 4. Opciones técnicas evaluadas

### Opción A — Reutilizar `server.py` con variables de entorno

| Aspecto | Detalle |
|---|---|
| Descripción | Modificar `server.py` para aceptar `AILAB_MCP_PROFILE=local\|lan` y adaptar bind+token según perfil. Una segunda unidad systemd ejecuta el mismo server con perfil LAN. |
| Ventaja | Un solo punto de mantenimiento. |
| Riesgo | **Alto.** Tocar el server actual puede romper OpenCode si la lógica de perfiles falla. |
| **Veredicto** | **No recomendada.** Riesgo innecesario para OpenCode. |

### Opción B — Wrapper/runner LAN separado (recomendada)

| Aspecto | Detalle |
|---|---|
| Descripción | Crear un nuevo script independiente que importe/use las tools existentes desde `tools/`, añada middleware de autenticación y arranque en 8092. El server original no se modifica. |
| Ventaja | **Cero riesgo para OpenCode.** Rollback inmediato. Fácil de aislar. |
| Riesgo | Duplicidad mínima de lógica de arranque (solo el main loop, las tools se reutilizan). |
| **Veredicto** | **Recomendada.** |

### Opción C — Copiar MCP al repo y desplegar desde repo

| Aspecto | Detalle |
|---|---|
| Descripción | Unificar `/mnt/mcp_server` dentro de `/opt/ai-lab/mcp` para versionado y despliegue controlado. |
| Ventaja | Reproducibilidad total. |
| Riesgo | Fase más grande. No conviene mezclar con token/firewall. |
| **Veredicto** | **Dejar para fase posterior:** `AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-01`. |

---

## 5. Arquitectura propuesta

```
127.0.0.1:8091/mcp         →  ailab-mcp-semantic-gateway.service  (sin cambios)
  OpenCode (actual)               Proceso: /mnt/mcp_server/server.py
                                   Sin token, bind localhost

0.0.0.0:8092/mcp           →  ailab-mcp-lan-gateway.service  (nuevo)
  LM Studio + LAN autorizada       Proceso: /mnt/mcp_server/lan_server.py (nuevo)
                                   Token obligatorio: AILAB_MCP_TOKEN
                                   Firewall: UFW allowlist
                                   Tools: solo read-only
```

Ambos servicios coexisten en la misma máquina. Comparten `tools/` y `client.py`.

---

## 6. Diseño del wrapper LAN (`lan_server.py`)

### Ubicación

`/mnt/mcp_server/lan_server.py` (futura implementación)

### Estructura

```python
"""
AI-LAB MCP LAN Gateway — read-only endpoint for authorized LAN clients.
Uses same tools/ package as the local server, with token auth middleware.
"""

import os
import sys
import logging
from tools.client import logger as _logger
from tools import register_all

BIND_HOST = os.environ.get("AILAB_LAN_HOST", "0.0.0.0")
BIND_PORT = int(os.environ.get("AILAB_LAN_PORT", "8092"))
TOKEN = os.environ.get("AILAB_MCP_TOKEN", "")

if not TOKEN:
    _logger.error("AILAB_MCP_TOKEN is required for LAN gateway — refusing to start")
    sys.exit(1)

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "ailab-mcp-lan-gateway",
    instructions="""Read-only MCP LAN Gateway for AI-LAB.
Authorized LAN clients only. Token required.
""",
)

register_all(mcp)

# Token validation middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class TokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        auth = request.headers.get("authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        if token != TOKEN:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)

def main():
    import uvicorn
    app = mcp.streamable_http_app()
    app.add_middleware(TokenMiddleware)
    _logger.info("Starting LAN MCP gateway on %s:%s", BIND_HOST, BIND_PORT)
    uvicorn.run(app, host=BIND_HOST, port=BIND_PORT, log_level="INFO")

if __name__ == "__main__":
    main()
```

### Notas de diseño

- Tools se reutilizan directamente importando `tools/__init__.py` existente.
- El middleware valida `Authorization: Bearer <token>` en todas las rutas.
- Sin token → servicio no arranca (fail-fast).
- Logging específico para auditoría LAN (prefijo `ailab-mcp-lan-gateway`).

---

## 7. Unidad systemd propuesta

**Archivo:** `/etc/systemd/system/ailab-mcp-lan-gateway.service`

**No crear ahora.** Solo diseño.

```ini
[Unit]
Description=AI-LAB MCP LAN Gateway (read-only, token required)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=albert
WorkingDirectory=/mnt/mcp_server
Environment=AILAB_LAN_HOST=0.0.0.0
Environment=AILAB_LAN_PORT=8092
Environment=AILAB_MCP_LOG_LEVEL=INFO
EnvironmentFile=/etc/ai-lab/mcp-lan.env
ExecStart=/opt/ai-lab/.venv/bin/python /mnt/mcp_server/lan_server.py
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=false

[Install]
WantedBy=multi-user.target
```

### Notas

- `EnvironmentFile` = `/etc/ai-lab/mcp-lan.env` (contiene `AILAB_MCP_TOKEN=<real_token>`, **nunca en repo**).
- Ruta Python: `/opt/ai-lab/.venv/bin/python` (mismo venv que el servidor local).
- `ProtectHome=false` permite acceso a `/home/albert` si el server necesita leer configs (revisar en implementación).

---

## 8. Token auth

### Header

- **Recomendado:** `Authorization: Bearer <AILAB_MCP_TOKEN>`
- **Alternativa opcional:** `X-AILAB-MCP-TOKEN: <token>`

### Storage

- Archivo: `/etc/ai-lab/mcp-lan.env`
- Contenido: `AILAB_MCP_TOKEN=<token_generado>`
- Permisos: `600`, propietario `root:root` o `albert:albert`

### Reglas

- Token generado fuera del repo (ej: `openssl rand -hex 32`).
- Nunca loggear el token.
- Nunca devolver el token en respuestas.
- Validación en middleware ASGI (cubre todas las rutas, incluyendo `/mcp`).

---

## 9. Firewall allowlist

**No aplicar ahora.** Diseño de reglas UFW:

```bash
# Permitir IPs autorizadas
sudo ufw allow from 192.168.1.50 to any port 8092 proto tcp comment 'MCP LAN X870EAORUSPRO'
sudo ufw allow from 192.168.1.60 to any port 8092 proto tcp comment 'MCP LAN X870AORUSELITE'
sudo ufw allow from 192.168.1.250 to any port 8092 proto tcp comment 'MCP LAN NAS-N5 LM Studio'

# Bloquear todo lo demás al puerto 8092
sudo ufw deny 8092/tcp comment 'Block other MCP LAN access'
```

### Validación futura

```bash
# Verificar reglas
sudo ufw status | grep 8092

# Probar desde IP autorizada
curl -i -H "Authorization: Bearer <token>" http://192.168.1.30:8092/mcp

# Probar desde IP no autorizada (debe fallar timeout o conexión rechazada)
curl -i -m 5 http://192.168.1.30:8092/mcp
```

---

## 10. Tools permitidas

### Sin restricciones (5 tools)

| Tool | Descripción |
|---|---|
| `ailab_status` | Health de Gateway + Router |
| `ailab_runtime_health` | Runtime health summary |
| `ailab_route_preview` | Heurístico local (regex) |
| `ailab_slo_status` | SLO health + violations |
| `ailab_health_latency` | Latencia + health score |

### Con cautela (3 tools)

| Tool | Riesgo | Acción |
|---|---|---|
| `ailab_operator_summary` | Expone estado del cluster | Permitir pero loguear uso |
| `ailab_incidents_active` | Expone fallos activos | Permitir pero loguear uso |
| `ailab_memory_search` | Expone historial Qdrant | Limitar a `limit=5` (ya implementado). Loguear queries |

Todas las tools son **read-only**. Ninguna tool mutable se expone en el endpoint LAN.

---

## 11. Plan de validación futura

### Local (en AI-LAB VM)

```bash
# Sin token → 401
curl -i http://127.0.0.1:8092/mcp

# Con token válido → respuesta MCP
curl -i -H "Authorization: Bearer $AILAB_MCP_TOKEN" http://127.0.0.1:8092/mcp

# Con token inválido → 401
curl -i -H "Authorization: Bearer invalid" http://127.0.0.1:8092/mcp
```

### Desde IP autorizada (192.168.1.50, .60, .250)

```bash
curl -i -H "Authorization: Bearer <token>" http://192.168.1.30:8092/mcp
```

### Desde IP no autorizada

Debe fallar por firewall (timeout o conexión rechazada).

---

## 12. Rollback

```bash
# 1. Detener y deshabilitar unidad LAN
sudo systemctl stop ailab-mcp-lan-gateway.service
sudo systemctl disable ailab-mcp-lan-gateway.service

# 2. Eliminar reglas firewall
sudo ufw delete deny 8092/tcp
sudo ufw delete allow from 192.168.1.50 to any port 8092
sudo ufw delete allow from 192.168.1.60 to any port 8092
sudo ufw delete allow from 192.168.1.250 to any port 8092

# 3. Verificar que el local sigue vivo
systemctl status ailab-mcp-semantic-gateway.service --no-pager

# 4. Probar OpenCode en 8091
curl -i http://127.0.0.1:8091/mcp
```

**Rollback completo en < 30 segundos. No afecta a 8091.**

---

## 13. Próximas fases

1. `AI-LAB-MCP-LAN-ENDPOINT-READONLY-IMPLEMENTATION-01` — Crear `lan_server.py` + unidad systemd
2. `AI-LAB-MCP-FIREWALL-ALLOWLIST-01` — Aplicar reglas UFW
3. `AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01` — Probar LM Studio contra 8092
4. `AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-01` — Unificar MCP en el repo (fase futura)

---

## 14. Riesgos documentados

| Riesgo | Severidad | Mitigación |
|---|---|---|
| Token mal configurado → servicio LAN no arranca | Baja | Fail-fast: servicio no arranca sin token. No afecta 8091. |
| Firewall allowlist incompleta → IP autorizada no conecta | Media | Validar reglas antes de habilitar el servicio. |
| LM Studio no soporta Bearer token en MCP HTTP | Media | Probar en smoke phase. Alternativa: header `X-AILAB-MCP-TOKEN`. |
| Wrapper LAN duplica lógica de arranque | Baja | Aceptable. Tools se reutilizan. |
| Repo unification pendiente | Media | Fase separada después de LAN smoke. |
