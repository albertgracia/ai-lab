# AI-LAB MCP Firewall Allowlist — Documento Técnico

**Fase:** `AI-LAB-MCP-FIREWALL-ALLOWLIST-01`
**Resultado:** PARTIAL

---

## Objetivo

Exponer el endpoint MCP LAN `8092` con firewall allowlist para las IPs autorizadas. **No completado** porque UFW está `inactive` en el servidor.

---

## Estado actual

| Componente | Estado |
|---|---|
| UFW | `inactive` |
| 8091 (OpenCode) | `127.0.0.1:8091`, intacto |
| 8092 (LAN Gateway) | `127.0.0.1:8092`, local-only, token obligatorio |
| AILAB_MCP_HOST | `127.0.0.1` (no cambiado) |
| Servicio LAN | `disabled`, `active (running)` |
| Token | Configurado, fingerprint: `ff4f2df5ea199879` |

---

## Motivo de PARTIAL

UFW está `inactive`. Según las reglas de la fase:

> Si UFW está inactive, NO activar UFW automáticamente en esta fase. Parar con PARTIAL y documentar que se necesita fase de firewall base.

No se ha cambiado `AILAB_MCP_HOST` a `0.0.0.0`. 8092 permanece en `127.0.0.1`.

---

## Reglas UFW diseñadas (pendientes de aplicar)

Ejecutar tras activar UFW:

```bash
# Allowlist autorizada
sudo ufw allow from 192.168.1.50 to any port 8092 proto tcp comment 'AI-LAB MCP LAN X870EAORUSPRO'
sudo ufw allow from 192.168.1.60 to any port 8092 proto tcp comment 'AI-LAB MCP LAN X870AORUSELITE'
sudo ufw allow from 192.168.1.250 to any port 8092 proto tcp comment 'AI-LAB MCP LAN NAS-N5 LM Studio'

# Deny general
sudo ufw deny 8092/tcp comment 'AI-LAB MCP LAN deny other clients'
```

Orden esperado:
```
[ X] 192.168.1.50 ALLOW 8092
[ X] 192.168.1.60 ALLOW 8092
[ X] 192.168.1.250 ALLOW 8092
[ X] 8092/tcp DENY
```

---

## Pasos restantes para exponer LAN

1. Activar UFW con allowlist base (SSH + servicios existentes)
2. Aplicar reglas allowlist 8092
3. Cambiar `AILAB_MCP_HOST=0.0.0.0` en `/etc/ai-lab/mcp-lan.env`
4. Reiniciar `ailab-mcp-lan-gateway.service`
5. Validar bind `0.0.0.0:8092`
6. Validar auth local y vía LAN IP
7. Probar desde `192.168.1.250` (LM Studio)

---

## Backup

```
/home/albert/backups/ai-lab/mcp-firewall-allowlist/20260601-133323/
├── mcp-lan.env.before
├── ailab-mcp-lan-gateway.service.before.txt
├── ufw-status-numbered.before.txt
└── ports.before.txt
```

---

## Rollback

No se aplicaron cambios, por lo que no se requiere rollback.
Si en el futuro se aplican las reglas y se cambia el host:

```bash
sudo sed -i 's/^AILAB_MCP_HOST=.*/AILAB_MCP_HOST=127.0.0.1/' /etc/ai-lab/mcp-lan.env
sudo systemctl restart ailab-mcp-lan-gateway.service
sudo ufw delete <rule_numbers>
```

---

## Siguiente fase

`AI-LAB-MCP-FIREWALL-BASE-ACTIVATION-01` (nueva) — activar UFW con SSH allowlist para desbloquear esta fase.
