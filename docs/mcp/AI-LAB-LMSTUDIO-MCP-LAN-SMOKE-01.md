# AI-LAB LM Studio MCP LAN Smoke ? Documento T?cnico

**Fase:** `AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01`
**Resultado:** PASS

---

## Objetivo

Validar el endpoint MCP LAN `8092` desde clientes reales de la red interna con token obligatorio, sin romper `8091` local.

---

## Servidor AI-LAB

| Componente | Valor |
|---|---|
| Host | `192.168.1.30` |
| MCP LAN endpoint | `http://192.168.1.30:8092/mcp` |
| MCP local (OpenCode) | `127.0.0.1:8091/mcp` |
| Token | Obligatorio |
| Token fingerprint | `ff4f2df5ea199879` |
| UFW | `inactive` (no modificado) |
| Servicio LAN | `disabled`, `active (running)` |

---

## Pruebas servidor local

| Escenario | Resultado |
|---|---|
| 8092 sin token | `401 Unauthorized` |
| 8092 con token (localhost) | `404` / `406` (auth OK) |
| 8092 con token (LAN IP) | `404` / `406` (auth OK) |
| 8091 intacto | ? Activo, 5h28m uptime |

---

## Prueba desde 192.168.1.50 (X870EAORUSPRO / Administrador)

### LM Studio

| Escenario | Resultado |
|---|---|
| MCP Server URL: `http://192.168.1.30:8092/mcp` | ? Conectado |
| Authorization: Bearer `<token>` | ? Autenticado |
| **Conclusi?n** | ? LM Studio operativo contra MCP LAN |

### OpenCode Desktop

| Escenario | Resultado |
|---|---|
| Tools listadas con prefijo `ailab-runtime-mcp_*` | ? 8 tools visibles |
| `ailab-runtime-mcp_ailab_status` | ? Gateway `:8008` OK `200`, Router `:8083` OK `200` |
| `ailab-runtime-mcp_ailab_runtime_health` | ? Health Score `89.6`, Status `healthy`, 2/3 nodes online |
| **Conclusi?n** | ? OpenCode Desktop operativo contra MCP LAN |

> **Nota:** OpenCode `.50` puede mostrar una referencia heredada a `ailab-semantic-gateway 127.0.0.1:8091`. Esto es contexto del agente de fases previas; no afecta la conectividad funcional. Las tools `ailab-runtime-mcp_*` se ejecutan correctamente contra `8092`.

---

## Prueba desde 192.168.1.250 (NAS-N5 / LM Studio)

### LM Studio

| Escenario | Resultado |
|---|---|
| MCP Server URL: `http://192.168.1.30:8092/mcp` | ? Conectado |
| Authorization: Bearer `<token>` | ? Autenticado |
| **Conclusi?n** | ? LM Studio operativo contra MCP LAN |

### OpenCode Desktop

| Escenario | Resultado |
|---|---|
| Tools listadas `ailab_*` | ? 8 tools visibles |
| `ailab_status` | ? Gateway `:8008` OK `200`, Router `:8083` OK `200` |
| **Conclusi?n** | ? OpenCode Desktop operativo contra MCP LAN |

---

## Tools AI-LAB Runtime validadas

| Tool | Estado |
|---|---|
| `ailab_status` | ? Respuesta OK (`.50`, `.250`) |
| `ailab_runtime_health` | ? Health Score 89.6, 2/3 nodes online |
| `ailab_health_latency` | ? Visible |
| `ailab_slo_status` | ? Visible |
| `ailab_operator_summary` | ? Visible (cautela) |
| `ailab_incidents_active` | ? Visible (cautela) |
| `ailab_route_preview` | ? Visible |
| `ailab_memory_search` | ? Visible (cautela) |

---

## Limitaciones y riesgos aceptados

- La red LAN puede alcanzar `8092` ? el token obligatorio protege el uso MCP
- UFW permanece `inactive` ? no se modific? en esta fase
- La referencia heredada en `.50` a `ailab-semantic-gateway 127.0.0.1:8091` no es un fallo funcional
- No hay firewall de red ? la ?nica protecci?n es el token MCP

---

## Rollback

Restaurar host a local-only:

```bash
sudo bash /tmp/rollback-mcp-lan-bind-token-only.sh
```

---

## Siguientes fases

1. `AI-LAB-MCP-LAN-SMOKE-PASS-PUSH-01` ? push de commits documentales
2. `AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-01`

