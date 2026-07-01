# AI-LAB-MCP-LAN-BIND-TOKEN-ONLY-01 — Auditoría

**Resultado:** PASS
**HEAD base:** d30fd653
**HEAD final:** <pendiente commit>
**Rama:** main
**Fecha:** 2026-06-01

---

## 1. Resumen

Endpoint MCP LAN `8092` expuesto en `0.0.0.0:8092` con token obligatorio. Sin firewall. `8091` intacto. Transport security configurado para aceptar conexiones vía IP LAN.

---

## 2. Cambios fuera de repo

| Archivo | Cambio |
|---|---|
| `/etc/ai-lab/mcp-lan.env` | `AILAB_MCP_HOST=127.0.0.1` → `0.0.0.0` |
| `/mnt/mcp_server/lan_server.py` | Añadido `TransportSecuritySettings(allowed_hosts=["*"])` |

---

## 3. Servicios

| Puerto | Servicio | Estado | Bind |
|---|---|---|---|
| 8091 | `ailab-mcp-semantic-gateway` | `active (running)`, enabled | `127.0.0.1:8091` |
| 8092 | `ailab-mcp-lan-gateway` | `active (running)`, **disabled** | `0.0.0.0:8092` |

---

## 4. Validaciones

| Validación | Resultado |
|---|---|
| 8091 intacto | ✅ |
| 8092 bind `0.0.0.0:8092` | ✅ |
| Sin token → 401 | ✅ |
| Con token (localhost) → pasa auth | ✅ |
| Con token (LAN IP) → pasa auth | ✅ (404/406 esperados) |
| UFW no modificado | ✅ (inactive) |
| OpenCode no modificado | ✅ |
| Runtime/servicios no tocados | ✅ |

---

## 5. Token

- **Creado previamente:** Sí
- **Fingerprint:** `ff4f2df5ea199879`
- **Expuesto en informe/commit/logs:** No

---

## 6. Backups

```
/home/albert/backups/ai-lab/mcp-lan-bind-token-only/20260601-134207/
```

---

## 7. Rollback

Script: `/tmp/rollback-mcp-lan-bind-token-only.sh`

---

## 8. Cambios en repo

- `docs/mcp/AI-LAB-MCP-LAN-BIND-TOKEN-ONLY-01.md` (creado)
- `docs/audits/AI-LAB-MCP-LAN-BIND-TOKEN-ONLY-01.md` (creado)

**Commit local:** Sí
**Push:** No
**Tag:** No

---

## 9. Riesgo aceptado

LAN puede alcanzar puerto 8092. Token obligatorio protege uso MCP. Sin firewall.

---

## 10. Siguiente fase

`AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01`
