# AI-LAB-MCP-PERSISTENCE-REBOOT-SMOKE-01

## Resultado

PASS ✅

## Objetivo

Validar tras reinicio de la VM `192.168.1.30` que los servicios MCP arrancan automáticamente bajo systemd y quedan operativos.

## HEAD / Base

- **HEAD local**: `40884299` (`main`)
- **Sincronizado con `origin/main`**: sí
- **Working tree**: limpio

## Uptime / Boot

- **Boot detectado**: sí — `uptime` = 1h 42min
- **Hora de arranque**: 09:53:49 CEST (2026-06-03)
- **Servicios arrancados por systemd**: `09:53:49` (marca en journal)

## Estado final tras reboot

### `ailab-mcp-semantic-gateway.service` (`127.0.0.1:8091`)

| Atributo | Valor |
|---|---|
| Active | `active (running)` |
| Enabled | `enabled` |
| MainPID | `1522` |
| Inicio | Wed 2026-06-03 09:53:49 CEST |
| Memory | 56.3M (peak 56.5M, max 128M) |
| CPU | 6.918s |
| Puerto | `127.0.0.1:8091` LISTEN |

### `ailab-mcp-lan-gateway.service` (`0.0.0.0:8092`)

| Atributo | Valor |
|---|---|
| Active | `active (running)` |
| Enabled | `enabled` |
| MainPID | `1518` |
| Inicio | Wed 2026-06-03 09:53:49 CEST |
| Memory | 54.1M (peak 54.7M) |
| CPU | 6.935s |
| Puerto | `0.0.0.0:8092` LISTEN |

## UFW

- **Estado**: `inactive`
- **No modificado** en esta fase

## Token

- **Fingerprint**: `ff4f2df5ea199879` (original — se restauró tras el reboot)
- **Fingerprint previo documentado**: `01896ebfed567192` (transitorio durante fase de recuperación)
- **No mostrado** en pantalla ni logs
- **No modificado**

## Validación endpoints

### 8091 (localhost, sin token)
| Prueba | Resultado |
|---|---|
| `GET /` | HTTP 404 (`Not Found`) — esperado, sin ruta raíz |
| `GET /mcp` | HTTP 406 + session ID — protocolo MCP |
| MCP initialize | ✅ ServerInfo `ailab-mcp-semantic-gateway v1.27.1`, 8 tools |

### 8092 (sin token)
| Prueba | Resultado |
|---|---|
| `GET /mcp` | **HTTP 401 Unauthorized** ✅ (esperado — token requerido) |

### 8092 (con token)
| Prueba | Resultado |
|---|---|
| `127.0.0.1:8092/mcp` (GET con Bearer) | HTTP 406 + session ID — protocolo MCP |
| `192.168.1.30:8092/mcp` (GET con Bearer) | HTTP 406 + session ID — **LAN accesible** ✅ |
| MCP initialize con token | ✅ ServerInfo `ailab-mcp-lan-gateway v1.27.1`, 8 tools |

## Logs post-reboot

### Semantic Gateway
- Arranque limpio a las `09:53:50`
- Sin tracebacks ni crashloop
- Activo desde el boot sin interrupciones

### LAN Gateway
- Arranque limpio a las `09:53:50`
- Cliente `192.168.1.50` (`.50`) ya conectado y operativo:
  - ListToolsRequest, ListPromptsRequest desde `11:31:03`
  - Múltiples sesiones MCP activas desde `.50`
  - Sin errores
- Sin token real en logs

## Tests

| Suite | Resultado |
|---|---|
| `tests/test_mcp_runtime_snapshot_01.py` | **5/5 PASS** ✅ |

## Secret scan

- Solo referencias a nombres de variables (AILAB_MCP_TOKEN, Authorization: Bearer)
- Sin valores reales de tokens/secrets
- **Limpio** ✅

## Confirmaciones

| Prohibición | Estado |
|---|---|
| Servicios reiniciados manualmente durante la fase | ❌ No (arranque automático vía systemd) |
| Configuración modificada | ❌ No |
| Token modificado | ❌ No |
| Token mostrado | ❌ No |
| `/mnt/mcp_server` modificado | ❌ No |
| UFW/firewall tocado | ❌ No |
| Runtime/Gateway/Router tocado | ❌ No |
| OpenCode/LM Studio tocado | ❌ No |
| Docker/Astro tocado | ❌ No |
| Push creado | ❌ No |
| Tag creado | ❌ No |

## Siguiente fase

`AI-LAB-MCP-PERSISTENCE-REBOOT-SMOKE-PUSH-01` — publicar el informe de validación post-reboot.
