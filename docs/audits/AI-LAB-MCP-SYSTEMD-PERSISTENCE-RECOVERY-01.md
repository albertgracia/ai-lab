# AI-LAB-MCP-SYSTEMD-PERSISTENCE-RECOVERY-01

## Resultado: PASS ✅

### Resumen
Se recuperó la persistencia operativa de ambos servidores MCP de AI-LAB en `192.168.1.30`, dejando ambos servicios gestionados por systemd y persistentes tras reinicio.

| Servicio | Puerto | Estado final |
|---|---|---|
| `ailab-mcp-semantic-gateway.service` | `127.0.0.1:8091` | ✅ active, enabled |
| `ailab-mcp-lan-gateway.service` | `0.0.0.0:8092` | ✅ active, enabled |

---

### HEAD
`f881a7da` — `docs(audit): record mcp control plane closure push`

### Base
`origin/main` — sin commits ahead/behind

### Estado inicial

#### 8091 — Semantic Gateway
- **PID**: `1541` — `/opt/ai-lab/.venv/bin/python /mnt/mcp_server/server.py`
- **Systemd**: `active (running)` — **enabled**
- **Puerto**: `127.0.0.1:8091` — LISTEN
- **Gestionado por systemd?** ✅ Sí (MainPID=1541 coincide con el PID del puerto)

#### 8092 — LAN Gateway
- **PID**: Ninguno (proceso `lan_server.py` no corriendo)
- **Systemd**: `inactive (dead)` — **disabled**
- **Puerto**: `0.0.0.0:8092` — NO LISTEN
- **Gestionado por systemd?** ❌ No (service disabled, no process)

### Acción realizada para 8091
**Caso A** — Ya gestionado por systemd:
- MainPID (1541) coincide con el listener del puerto 8091
- No se requirió intervención
- `systemctl enable` ya estaba configurado
- Se confirmó estado sin cambios

### Acción realizada para 8092
1. `systemctl daemon-reload`
2. `systemctl start ailab-mcp-lan-gateway.service` → **activo** (PID 448266)
3. `systemctl enable ailab-mcp-lan-gateway.service` → symlink creado en `multi-user.target.wants/`

### Estado final

#### `ailab-mcp-semantic-gateway.service`
- **Active**: `active (running)` desde Tue 2026-06-02 10:37:06 CEST
- **Enabled**: `enabled`
- **MainPID**: `1541` (python)
- **Puerto**: `127.0.0.1:8091` — LISTEN
- **Memory**: 64.1M (peak: 64.5M, max: 128M)
- **CPU**: 1min 26s

#### `ailab-mcp-lan-gateway.service`
- **Active**: `active (running)` desde Tue 2026-06-02 22:49:03 CEST
- **Enabled**: `enabled`
- **MainPID**: `448266` (python)
- **Puerto**: `0.0.0.0:8092` — LISTEN
- **Memory**: 46.1M (peak: 46.1M)
- **CPU**: 344ms

### Validación endpoints

| Endpoint | Resultado |
|---|---|
| `8091/` (GET sin auth) | HTTP 404 (esperado — sin ruta raíz) |
| `8091/mcp` (POST sin headers MCP) | Error MCP `-32600` (esperado — requiere headers) |
| `8092/mcp` (GET sin token) | HTTP **401 Unauthorized** ✅ (esperado) |
| `8092/mcp` (GET con token) | HTTP 406 + MCP initialize exitoso ✅ |
| `8092/mcp` (MCP initialize con token) | ✅ ServerInfo completo: `ailab-mcp-lan-gateway v1.27.1`, 8 tools |

### UFW
No se tocó UFW/firewall. Estado no modificado.

### Token
- Fingerprint actual: `01896ebfed567192` (cambiado desde el fingerprint previo `ff4f2df5ea199879` documentado en contexto anterior)
- **No mostrado** en pantalla ni logs
- **No modificado**
- No se encontró el valor real del token en los logs de systemd

### Rollback
Script disponible en: `/tmp/rollback-mcp-systemd-persistence.sh`
```bash
# Desactiva y detiene LAN gateway
sudo systemctl disable ailab-mcp-lan-gateway.service
sudo systemctl stop ailab-mcp-lan-gateway.service
# Reactiva semantic gateway
sudo systemctl start ailab-mcp-semantic-gateway.service
sudo systemctl enable ailab-mcp-semantic-gateway.service
```

### Confirmaciones de seguridad

| Prohibición | Estado |
|---|---|
| Código MCP modificado (`server.py`/`lan_server.py`) | ❌ No modificado |
| Token modificado | ❌ No modificado |
| Token mostrado | ❌ No mostrado |
| UFW/firewall tocado | ❌ No tocado |
| Runtime Gateway/Router tocado | ❌ No tocado |
| OpenCode/LM Studio tocado | ❌ No tocado |
| Docker/Astro tocado | ❌ No tocado |
| `mcp/runtime-mcp/` modificado | ❌ No modificado |
| Sync repo → `/mnt` | ❌ No realizado |
| Reboot ejecutado | ❌ No realizado |
| Push creado | ❌ No realizado |
| Tag creado | ❌ No realizado |

### Backup
- Ruta: `/home/albert/backups/ai-lab/mcp-systemd-persistence/20260602-224842/`
- Archivos:
  - `semantic.status.before.txt` / `lan.status.before.txt`
  - `semantic.unit.txt` / `lan.unit.txt`
  - `ports.before.txt`
  - `processes.before.txt`
  - `ps_aux.before.txt`

### Recomendación
- Fase opcional siguiente: `AI-LAB-MCP-PERSISTENCE-REBOOT-SMOKE-01` para validar que ambos servicios arrancan automáticamente tras reinicio del sistema
- Si no se desea reboot, la persistencia systemd queda validada y operativa
- Monitorear `8092` desde cliente `.50`/`.250` para confirmar conectividad LAN remota
