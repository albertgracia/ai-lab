# MCP-SEMANTIC-GATEWAY-01 — AI-LAB MCP Semantic Gateway (Read-Only PoC)

## Objetivo

Crear un primer MCP Semantic Gateway en el servidor Ubuntu AI-LAB para que OpenCode
pueda consumir capacidades gobernadas de AI-LAB mediante MCP remoto (Streamable HTTP).

No es un proxy directo a LM Studio. Es una fachada read-only hacia los endpoints
de AI-LAB Gateway / Router / Health.

## Arquitectura

```
OpenCode (Windows)
  → MCP remoto (Streamable HTTP)
  → ai-lab (192.168.1.30:8091/mcp)
  → ailab-mcp-semantic-gateway (Python + FastMCP SDK)
    → ailab-gateway (127.0.0.1:8008)
    → ailab-router (127.0.0.1:8083)
```

## Tools Expuestas (3, read-only)

| Tool | Descripción | Endpoint interno |
|---|---|---|
| `ailab_status` | Estado resumido gateway + router | `:8008/health`, `:8083/health` |
| `ailab_runtime_health` | Salud cognitiva/runtime detallada | `:8008/runtime/health` |
| `ailab_route_preview` | Clasificación heurística de ruta (sin LLM) | Local, sin HTTP |

## Endpoints Internos Usados

| Servicio | URL | Puerto | Propósito |
|---|---|---|---|
| ailab-gateway | `http://127.0.0.1:8008` | 8008 | Health + Runtime health |
| ailab-router | `http://127.0.0.1:8083` | 8083 | Health check |

## Puertos

- **MCP Semantic Gateway**: `8091` (Streamable HTTP transport)
- **Endpoint MCP**: `http://127.0.0.1:8091/mcp`

## Systemd Unit (pendiente de instalación por operador)

Archivo: `/etc/systemd/system/ailab-mcp-semantic-gateway.service`

```
[Unit]
Description=AI-LAB MCP Semantic Gateway (Read-Only PoC)
After=network-online.target ailab-gateway.service ailab-router.service
Wants=network-online.target

[Service]
Type=simple
User=albert
WorkingDirectory=/opt/ai-lab/mcp/servers
ExecStart=/opt/ai-lab/.venv/bin/python /opt/ai-lab/mcp/servers/ailab_semantic_gateway.py
Restart=always
RestartSec=5
MemoryMax=128M

Environment=AILAB_GATEWAY_URL=http://127.0.0.1:8008
Environment=AILAB_ROUTER_URL=http://127.0.0.1:8083
Environment=AILAB_MCP_BIND=127.0.0.1
Environment=AILAB_MCP_PORT=8091
Environment=AILAB_MCP_LOG_LEVEL=INFO

[Install]
WantedBy=multi-user.target
```

**Comandos para activar** (como root o con sudo):

```bash
sudo mv /tmp/ailab-mcp-semantic-gateway.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ailab-mcp-semantic-gateway
systemctl status ailab-mcp-semantic-gateway --no-pager
journalctl -u ailab-mcp-semantic-gateway -n 50 --no-pager
```

## Seguridad / Auth

- Si `AILAB_MCP_TOKEN` no está definida: el gateway se bindea solo a `127.0.0.1` (modo local/dev).
- Si `AILAB_MCP_TOKEN` está definida: se puede bindear a `0.0.0.0` y el token se valida
  como Bearer token en los headers MCP.
- No hay tokens hardcodeados.
- No se imprimen tokens en logs.

## Storage Audit Unidad 80 GB

### Resultado

| Campo | Valor |
|---|---|
| Dispositivo | `/dev/mapper/ubuntu--vg-ai--models` |
| Tamaño | 80 GB (79G mostrados) |
| Filesystem | ext4 |
| UUID | `e43c331f-fb63-4cbb-a027-31aa7eaf2b8c` |
| Mountpoint actual | `/mnt/ai-models` |
| Estado | Montado, contenido: solo `lost+found` (2.1M usado / 75G disponible) |
| Riesgo de uso | Bajo — disco vacío y dedicado a almacenamiento auxiliar |

### Recomendación para /srv/ai-lab-data

El plan original mencionaba una unidad de "~100 GB". El candidato real es el LV
`ubuntu--vg-ai--models` de 80 GB, actualmente montado en `/mnt/ai-models` y vacío.

**Propuesta**: Usar `/mnt/ai-models` (ya montado) como punto de almacenamiento auxiliar
con la siguiente estructura:

```
/mnt/ai-models/mcp/logs
/mnt/ai-models/mcp/cache
/mnt/ai-models/mcp/runtime
/mnt/ai-models/backups
/mnt/ai-models/staging
```

Variables de entorno recomendadas:

```bash
AILAB_MCP_DATA_DIR=/mnt/ai-models/mcp
AILAB_MCP_LOG_DIR=/mnt/ai-models/mcp/logs
AILAB_MCP_CACHE_DIR=/mnt/ai-models/mcp/cache
```

**NO se ha formateado, montado, movido ni modificado fstab.**
**NO se ha movido /opt/ai-lab.**
**NO se ha tocado Qdrant ni modelos.**

## Archivos del Proyecto

| Archivo | Ruta |
|---|---|
| Código principal | `/opt/ai-lab/mcp/servers/ailab_semantic_gateway.py` |
| Config MCP | `/opt/ai-lab/mcp/config/ailab_semantic_gateway.mcp.json` |
| Systemd unit | `/tmp/ailab-mcp-semantic-gateway.service` (pendiente de instalar) |
| Tests | `/opt/ai-lab/tests/test_mcp_semantic_gateway_01.py` |
| Documentación | `docs/runtime/mcp-semantic-gateway-01.md` |

## Limitaciones

1. **Systemd no instalado** — el gateway arranca manualmente. Pendiente de sudo.
2. **Bind a 127.0.0.1** — solo accesible desde el propio Ubuntu. Para OpenCode Windows
   se necesita bind a `0.0.0.0` con `AILAB_MCP_TOKEN`.
3. **Sin auth** en modo local — si se expone a LAN, debe configurarse `AILAB_MCP_TOKEN`.
4. **Streamable HTTP** — usa el transporte estándar MCP v1.27.1.

## Validación Realizada

- ✅ `py_compile` pasa sin errores
- ✅ 13 tests pytest pasan en 0.38s
- ✅ gateway sigue OK (`:8008/health` → `{"status":"ok"}`)
- ✅ router sigue OK (`:8083/health` → `{"status":"ok"}`)
- ✅ MCP gateway arranca manualmente y responde en `:8091/mcp`
- ✅ `ailab_status` devuelve ok
- ✅ `ailab_runtime_health` devuelve runtime health (2 nodos online)
- ✅ `ailab_route_preview` clasifica sin inferencia real
- ✅ No se guardan prompts completos (truncados a 120 chars en logs)
- ✅ No hay secrets en logs
- ✅ No se ha tocado gateway/router existentes
- ✅ No se ha modificado /etc/fstab
- ✅ No se ha formateado ni montado la unidad

## Rollback

Si es necesario deshacer todo:

```bash
# Si systemd está instalado:
sudo systemctl disable --now ailab-mcp-semantic-gateway || true
sudo rm -f /etc/systemd/system/ailab-mcp-semantic-gateway.service
sudo systemctl daemon-reload

# Archivos del proyecto:
rm -f /opt/ai-lab/mcp/servers/ailab_semantic_gateway.py
rm -f /opt/ai-lab/mcp/config/ailab_semantic_gateway.mcp.json
rm -f /opt/ai-lab/tests/test_mcp_semantic_gateway_01.py
rm -f /opt/ai-lab/docs/runtime/mcp-semantic-gateway-01.md

# Matar proceso manual si corre:
kill $(lsof -ti:8091) 2>/dev/null || true
```

## Próximos Pasos (fuera de esta fase)

1. Activar systemd unit (sudo)
2. Configurar OpenCode Windows → MCP remoto a `192.168.1.30:8091/mcp`
3. Implementar tools semánticas: `sommelier`, `analyze_label`, `price_estimate`
4. Integración con Rioja Marketplace
