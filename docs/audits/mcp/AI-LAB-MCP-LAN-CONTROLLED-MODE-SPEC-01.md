# AI-LAB-MCP-LAN-CONTROLLED-MODE-SPEC-01

**Estado:** PASS
**Fecha:** 2026-06-01
**HEAD:** 5901ca72
**Rama:** main
**Git:** ahead 5 de origin/main, working tree limpio desde el commit de inventario previo

---

## 1. Resumen

Se definió la especificación operativa y de seguridad para exponer el servidor MCP actual de AI-LAB a equipos autorizados de la red interna. No se implementó ningún cambio de bind, firewall, token, systemd ni código.

---

## 2. Estado MCP actual (verificado)

- Servicio activo: `ailab-mcp-semantic-gateway.service` (PID 1501)
- Ruta activa: `/mnt/mcp_server/server.py`
- Bind: `127.0.0.1:8091`
- Transporte: Streamable HTTP
- Token: no configurado
- Tools: 8 read-only
- Resources: no
- Prompts: no

---

## 3. Documentos creados

| Documento | Ruta |
|---|---|
| Spec LAN Controlled Mode | `docs/mcp/AI-LAB-MCP-LAN-CONTROLLED-MODE-SPEC-01.md` |
| Auditoría | `docs/audits/AI-LAB-MCP-LAN-CONTROLLED-MODE-SPEC-01.md` |

---

## 4. Allowlist definida

### Activas iniciales

| IP | Host | Uso |
|---|---|---|
| `192.168.1.50` | `X870EAORUSPRO` | Equipo Administrador |
| `192.168.1.60` | `X870AORUSELITE` | Equipo Albert |
| `192.168.1.250` | `NAS-N5` | LM Studio |

### Reserva/futuro

`192.168.1.40`, `192.168.1.200`, `192.168.1.100`, `192.168.1.150`

---

## 5. Decisión de seguridad

**No exponer MCP a LAN hasta completar fases previas:**
1. Token read-only (`AILAB_MCP_TOKEN`)
2. Firewall allowlist con las IPs activas
3. Solo tools read-only
4. Sin Internet, sin Cloudflare/NPM

---

## 6. Fases posteriores

1. `AI-LAB-MCP-TOOLS-CATALOG-VALIDATION-01`
2. `AI-LAB-MCP-TOKEN-AUTH-READONLY-01`
3. `AI-LAB-MCP-FIREWALL-ALLOWLIST-01`
4. `AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01`
5. `AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-01`

---

## 7. Riesgos documentados

- MCP activo fuera del repo en `/mnt/mcp_server/` (sin versionado)
- Sin token actual
- Bind LAN sin firewall sería inseguro
- Duplicidad `/opt/ai-lab/mcp` vs `/mnt/mcp_server`
- LM Studio podría invocar tools automáticamente si se permite

---

## 8. Confirmación

- No se modificó `/mnt/mcp_server/server.py`
- No se modificó `/opt/ai-lab/mcp/`
- No se modificó systemd
- No se modificó firewall
- No se modificó bind address
- No se expuso puerto 8091 a LAN
- No se creó token real
- No se tocó runtime
- No se tocó Gateway
- No se tocó Router
- No se tocó Docker
- No se hizo push
- No se creó tag

**Commit:** `docs(mcp): specify lan controlled mode`
