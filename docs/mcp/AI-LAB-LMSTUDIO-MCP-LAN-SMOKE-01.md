# AI-LAB LM Studio MCP LAN Smoke — Documento Técnico

**Fase:** `AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01`
**Resultado:** PARTIAL

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
| 8091 intacto | ✅ Activo, 3h19m uptime |

---

## Prueba desde 192.168.1.50 (X870EAORUSPRO / Administrador)

| Escenario | Resultado |
|---|---|
| Sin token | `401 Unauthorized` |
| Con token (Authorization Bearer) | `404` / `406` (auth OK) |
| **Conclusión** | ✅ Acceso LAN validado |

---

## Prueba desde 192.168.1.250 (NAS-N5 / LM Studio)

| Escenario | Resultado |
|---|---|
| SSH | ❌ No accesible (timeout, puerto 22 y 2222) |
| Prueba curl | ❌ Pendiente para operador |
| **Conclusión** | ⏳ Pendiente — no se pudo probar remotamente |

### Configuración LM Studio pendiente

```
MCP Server URL: http://192.168.1.30:8092/mcp
Header:        Authorization: Bearer <AILAB_MCP_TOKEN>
```

Tools recomendadas para probar primero:
- `ailab_status`
- `ailab_runtime_health`
- `ailab_route_preview`
- `ailab_slo_status`
- `ailab_health_latency`

Tools con cautela (no forzar):
- `ailab_operator_summary`
- `ailab_incidents_active`
- `ailab_memory_search`

---

## OpenCode local

Tools AI-LAB Runtime esperadas (8):
`ailab_status`, `ailab_runtime_health`, `ailab_route_preview`, `ailab_operator_summary`, `ailab_incidents_active`, `ailab_slo_status`, `ailab_health_latency`, `ailab_memory_search`

Tools GitNexus esperadas (14):
`gitnexus_list_repos`, `gitnexus_query`, `gitnexus_context`, `gitnexus_impact`, `gitnexus_cypher`, `gitnexus_analyze`, `gitnexus_detect_changes`, `gitnexus_rename`, `gitnexus_route_map`, `gitnexus_tool_map`, `gitnexus_shape_check`, `gitnexus_api_impact`, `gitnexus_group_list`, `gitnexus_group_sync`

---

## Limitaciones

- No se pudo probar desde `192.168.1.250` (NAS-N5) — requiere acceso físico o configuración SSH adicional
- Smoke desde LM Studio queda pendiente para el operador
- No hay firewall — cualquier equipo LAN puede alcanzar el puerto 8092
- La única protección es el token MCP

---

## Rollback

Restaurar host a local-only:

```bash
sudo bash /tmp/rollback-mcp-lan-bind-token-only.sh
```

---

## Siguientes fases

1. `AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01` (reintento) — operador prueba LM Studio contra 8092
2. `AI-LAB-MCP-LAN-SMOKE-PUSH-01` — push de commits documentales
3. `AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-01`
