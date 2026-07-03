# AI-LAB-MCP-FIREWALL-ALLOWLIST-01 — Auditoría

**Resultado:** PARTIAL
**HEAD base:** f2e09065
**HEAD final:** f2e09065 (sin cambios en repo aún)
**Rama:** main
**Fecha:** 2026-06-01

---

## 1. Resumen

Fase detenida en PARTIAL porque UFW está `inactive` sin reglas preconfiguradas. No se ha expuesto `8092` a LAN. No se ha cambiado `AILAB_MCP_HOST`. `8091` intacto.

---

## 2. Causa del PARTIAL

| Condición | Resultado |
|---|---|
| UFW activo | ❌ `inactive` |
| Reglas preconfiguradas SSH | ❌ ninguna |
| Riesgo de bloqueo remoto | ⚠️ Activar UFW sin allow SSH cortaría la conexión |

---

## 3. Estado actual

| Componente | Estado |
|---|---|
| 8091 | `127.0.0.1:8091`, intacto |
| 8092 | `127.0.0.1:8092`, local-only, token required |
| AILAB_MCP_HOST | `127.0.0.1` (no cambiado) |
| Servicio LAN | `disabled`, `active (running)` |
| Token fingerprint | `ff4f2df5ea199879` |
| UFW | `inactive` |

---

## 4. Backups

```
/home/albert/backups/ai-lab/mcp-firewall-allowlist/20260601-133323/
├── mcp-lan.env.before
├── ailab-mcp-lan-gateway.service.before.txt
├── ufw-status-numbered.before.txt
└── ports.before.txt
```

---

## 5. Lo que NO se hizo (intencionadamente)

- ❌ No se aplicaron reglas UFW
- ❌ No se cambió `AILAB_MCP_HOST` a `0.0.0.0`
- ❌ No se reinició el servicio LAN
- ❌ No se expuso `8092` a LAN
- ❌ No se habilitó el servicio en boot
- ❌ No se activó UFW
- ✅ `8091` intacto
- ✅ Sin push, sin tag

---

## 6. Reglas UFW diseñadas (pendientes)

```bash
sudo ufw allow from 192.168.1.50  to any port 8092 proto tcp
sudo ufw allow from 192.168.1.60  to any port 8092 proto tcp
sudo ufw allow from 192.168.1.250 to any port 8092 proto tcp
sudo ufw deny  8092/tcp
```

---

## 7. Prerrequisito para completar

Crear fase `AI-LAB-MCP-FIREWALL-BASE-ACTIVATION-01`:

1. `sudo ufw allow 22/tcp comment "SSH"`
2. `sudo ufw enable`
3. Verificar conectividad SSH persistente
4. Re-ejecutar `AI-LAB-MCP-FIREWALL-ALLOWLIST-01`

---

## 8. Siguientes fases

1. `AI-LAB-MCP-FIREWALL-BASE-ACTIVATION-01` — Activar UFW con SSH allow
2. `AI-LAB-MCP-FIREWALL-ALLOWLIST-01` (reintento) — Aplicar allowlist 8092
3. `AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01` — Probar LM Studio contra 8092
