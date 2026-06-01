# AI-LAB MCP LAN Endpoint Read-Only — Implementación

**Fase:** `AI-LAB-MCP-LAN-ENDPOINT-READONLY-IMPLEMENTATION-01`

---

## Resumen

Implementación del wrapper/runner LAN separado (Opción B del diseño previo) para el endpoint MCP read-only en puerto `8092` con token obligatorio. El endpoint original `127.0.0.1:8091/mcp` usado por OpenCode queda intacto.

---

## Archivos creados

### Fuera del repo

| Ruta | Propósito |
|---|---|
| `/mnt/mcp_server/lan_server.py` | Wrapper MCP con auth middleware (ASGI), 8 tools read-only |
| `/etc/ai-lab/mcp-lan.env` | Variables de entorno: host, port, token, require_token |
| `/etc/systemd/system/ailab-mcp-lan-gateway.service` | Unidad systemd del nuevo servicio |

### En el repo

| Ruta | Propósito |
|---|---|
| `docs/mcp/AI-LAB-MCP-LAN-ENDPOINT-READONLY-IMPLEMENTATION-01.md` | Documento técnico (este) |
| `docs/audits/AI-LAB-MCP-LAN-ENDPOINT-READONLY-IMPLEMENTATION-01.md` | Informe de auditoría |

---

## Configuración

### `/etc/ai-lab/mcp-lan.env`

```
AILAB_MCP_HOST=127.0.0.1
AILAB_MCP_PORT=8092
AILAB_MCP_REQUIRE_TOKEN=true
AILAB_MCP_TOKEN=<64-char hex token>
```

- `600` permisos, root owner
- Token generado con `openssl rand -hex 32`
- Host inicial `127.0.0.1` — **no expuesto a LAN aún**

### `/etc/systemd/system/ailab-mcp-lan-gateway.service`

- Type=simple, User=albert
- WorkingDirectory=/mnt/mcp_server
- EnvironmentFile=/etc/ai-lab/mcp-lan.env
- Environment adicionales: `AILAB_GATEWAY_URL`, `AILAB_ROUTER_URL`, `AILAB_LIVE_API_URL`
- ExecStart: `/opt/ai-lab/.venv/bin/python /mnt/mcp_server/lan_server.py`
- Restart=on-failure, RestartSec=5
- NoNewPrivileges=true, PrivateTmp=true, ProtectSystem=full

### `/mnt/mcp_server/lan_server.py`

- Copia controlada de `server.py` con cambios mínimos
- **Auth middleware** ASGI que verifica `Authorization: Bearer <token>` o `X-AILAB-MCP-TOKEN: <token>`
- Si `AILAB_MCP_REQUIRE_TOKEN=true` y token no configurado: aborta con `sys.exit(1)`
- Nunca loggea el token
- Las 8 tools read-only idénticas al servidor original

---

## Estado actual

### Puerto 8091 (OpenCode)

- Servicio: `ailab-mcp-semantic-gateway.service` → `active (running)`
- Endpoint: `127.0.0.1:8091/mcp`
- Intacto, no modificado

### Puerto 8092 (LAN Gateway)

- Servicio: `ailab-mcp-lan-gateway.service` → `active (running)`, **disabled**
- Endpoint: `127.0.0.1:8092/mcp`
- Token obligatorio
- Sin firewall — bind local-only `127.0.0.1`

---

## Pruebas de autenticación

| Escenario | Header | Resultado |
|---|---|---|
| Sin token | — | `401 Unauthorized` |
| `X-AILAB-MCP-TOKEN: <token>` | Custom | Pasa auth, `404` o `406` por GET HTTP puro (esperado) |
| `Authorization: Bearer <token>` | Standard | Pasa auth, `404` o `406` por GET HTTP puro (esperado) |

> Las respuestas `404` en `/health` y `406` en `/mcp` son normales — el endpoint MCP espera POST con sesión Streamable HTTP.

---

## Backup

```
BACKUP_DIR=/home/albert/backups/ai-lab/mcp-lan-endpoint/20260601-132210
```

Contenido:
- `mcp_server.before/` — copia completa de `/mnt/mcp_server` antes de cambios
- `ailab-mcp-semantic-gateway.service.before.txt` — unit original

---

## Rollback

```bash
# Ejecutar script de rollback (fuera del repo)
sudo bash /tmp/rollback-mcp-lan-endpoint.sh
```

Pasos manuales si es necesario:

1. `sudo systemctl stop ailab-mcp-lan-gateway.service`
2. `sudo systemctl disable ailab-mcp-lan-gateway.service`
3. `sudo rm /etc/systemd/system/ailab-mcp-lan-gateway.service`
4. `sudo systemctl daemon-reload`
5. `rm /mnt/mcp_server/lan_server.py`
6. `sudo rm /etc/ai-lab/mcp-lan.env` (opcional)
7. Verificar: `systemctl status ailab-mcp-semantic-gateway.service`

---

## Pendiente para fases siguientes

| Fase | Acción |
|---|---|
| `AI-LAB-MCP-FIREWALL-ALLOWLIST-01` | Cambiar host a `0.0.0.0`, aplicar reglas UFW allowlist |
| `AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01` | Probar LM Studio contra 8092 con token |

---

## Notas de seguridad

- Token generado con `openssl rand -hex 32` (256 bits de entropía)
- Token guardado exclusivamente en `/etc/ai-lab/mcp-lan.env` (600, root)
- No se ha mostrado el token completo en logs, informes ni commits
- Auth middleware verifica dos headers: `Authorization: Bearer` y `X-AILAB-MCP-TOKEN`
- El token puede rotarse regenerando el env file y reiniciando el servicio
- Sin firewall todavía — bind seguro a localhost hasta fase de firewall allowlist

---

## Comandos útiles

```bash
# Estado
systemctl status ailab-mcp-lan-gateway.service

# Logs
journalctl -u ailab-mcp-lan-gateway.service -n 50 -f

# Probar auth sin token
curl -I http://127.0.0.1:8092/health

# Probar auth con token
TOKEN=$(sudo cat /etc/ai-lab/mcp-lan.env | grep AILAB_MCP_TOKEN | cut -d= -f2-)
curl -I -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8092/health
```
