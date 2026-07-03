# AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01 ? Auditor?a

**Resultado:** PASS
**HEAD base:** 0a609cd1
**HEAD final:** <pendiente commit>
**Rama:** main
**Fecha:** 2026-06-01

---

## 1. Resumen

Smoke tests del endpoint LAN `8092` completados desde servidor local y ambos clientes LAN (`192.168.1.50` y `192.168.1.250`). LM Studio y OpenCode Desktop en ambas estaciones validados contra MCP LAN. `8091` intacto.

---

## 2. Estado

| Componente | Estado |
|---|---|
| 8091 | `active (running)`, `127.0.0.1:8091`, enabled |
| 8092 | `active (running)`, `0.0.0.0:8092`, disabled |
| UFW | `inactive` (no modificado) |
| Token fingerprint | `ff4f2df5ea199879` |

---

## 3. Pruebas

| Origen | Sin token | Con token | Resultado |
|---|---|---|---|
| Servidor local (127.0.0.1) | 401 ? | 404/406 ? | PASS |
| Servidor LAN (192.168.1.30) | ? | 404/406 ? | PASS |
| 192.168.1.50 (X870EAORUSPRO) ? LM Studio | 401 ? | Conexi?n OK ? | PASS |
| 192.168.1.50 (X870EAORUSPRO) ? OpenCode Desktop | ? | tools OK ? | PASS |
| 192.168.1.250 (NAS-N5) ? LM Studio | ? | Conexi?n OK ? | PASS |
| 192.168.1.250 (NAS-N5) ? OpenCode Desktop | ? | tools OK ? | PASS |

---

## 4. Tools validadas

| Tool | .50 | .250 |
|---|---|---|
| `ailab_status` | ? Gateway/Router OK | ? Gateway/Router OK |
| `ailab_runtime_health` | ? Score 89.6, 2/3 nodes | ? |
| `ailab_health_latency` | ? Visible | ? Visible |
| `ailab_slo_status` | ? Visible | ? Visible |
| `ailab_operator_summary` | ? Visible (cautela) | ? Visible (cautela) |
| `ailab_incidents_active` | ? Visible (cautela) | ? Visible (cautela) |
| `ailab_route_preview` | ? Visible | ? Visible |
| `ailab_memory_search` | ? Visible (cautela) | ? Visible (cautela) |

---

## 5. Cambios respecto a PARTIAL

| Aspecto | PARTIAL | PASS |
|---|---|---|
| Acceso `.250` | ? No accesible SSH | ? Operador confirm? LM Studio y OpenCode OK |
| Resultado `.250` | ? Pendiente | ? PASS |
| Evidencia OpenCode Desktop | No documentada | ? Documentada para `.50` y `.250` |
| Health Score | No documentado | ? 89.6 healthy, 2/3 nodes online |

---

## 6. Detalle de evidencia

### 192.168.1.50 ? LM Studio
- Conexi?n a `http://192.168.1.30:8092/mcp` con token exitosa
- Sin errores de autenticaci?n

### 192.168.1.50 ? OpenCode Desktop
- 8 tools `ailab-runtime-mcp_*` listadas
- `ailab-runtime-mcp_ailab_status`: Gateway `:8008` OK 200, Router `:8083` OK 200
- `ailab-runtime-mcp_ailab_runtime_health`: Health Score 89.6, 2/3 nodes online (`.250`, `.50`)
- Referencia heredada a `ailab-semantic-gateway 127.0.0.1:8091` considerada contexto de agente, no fallo funcional

### 192.168.1.250 ? LM Studio
- Conexi?n a `http://192.168.1.30:8092/mcp` con token exitosa
- Sin errores de autenticaci?n

### 192.168.1.250 ? OpenCode Desktop
- 8 tools `ailab_*` listadas
- `ailab_status`: Gateway `:8008` OK 200, Router `:8083` OK 200
- Sin incidencias

---

## 7. Cambios en repo

- `docs/mcp/AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01.md` (actualizado)
- `docs/audits/AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01.md` (actualizado)

**Commit local:** S?
**Push:** No
**Tag:** No

---

## 8. Confirmaciones

| Confirmaci?n | S?/No |
|---|---|
| 8091 intacto | ? |
| OpenCode no modificado | ? |
| Runtime no tocado | ? |
| UFW no modificado | ? |
| Token no filtrado | ? |
| Sin push | ? |
| Sin tag | ? |
| Sin modificaci?n de servicios | ? |
| Sin modificaci?n de LM Studio | ? |

---

## 9. Siguientes fases

1. `AI-LAB-MCP-LAN-SMOKE-PASS-PUSH-01` ? push de commits documentales
2. `AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-01`

