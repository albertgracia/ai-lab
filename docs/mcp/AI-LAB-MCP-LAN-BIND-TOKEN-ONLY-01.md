# AI-LAB MCP LAN Bind Token-Only — Documento Técnico

**Fase:** `AI-LAB-MCP-LAN-BIND-TOKEN-ONLY-01`
**Resultado:** PASS

---

## Objetivo

Exponer el endpoint MCP LAN `8092` en la red local usando `0.0.0.0:8092` con token obligatorio, sin activar UFW ni aplicar firewall allowlist.

---

## Decisión operativa

UFW está `inactive` y activarlo sin reglas base (SSH, SMB, servicios existentes) podría romper accesos remotos. La red local es de confianza. Se decide exponer `8092` con **token obligatorio** como única protección de capa de aplicación.

Riesgo aceptado: equipos de la LAN pueden alcanzar el puerto 8092, pero no pueden usar MCP sin el token.

---

## Cambios realizados

### 1. Host bind

| Antes | Después |
|---|---|
| `AILAB_MCP_HOST=127.0.0.1` | `AILAB_MCP_HOST=0.0.0.0` |

Archivo: `/etc/ai-lab/mcp-lan.env`

### 2. Transport security

Se añadió `TransportSecuritySettings` a `lan_server.py` para permitir conexiones vía IP LAN:

```python
from mcp.server.transport_security import TransportSecuritySettings

mcp = FastMCP(
    ...,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
        allowed_hosts=["*"],
    ),
)
```

Sin esto, MCP rechazaba peticiones con `421 Misdirected Request` por Host header no válido.

---

## Estado final

| Componente | Estado |
|---|---|
| 8091 (OpenCode) | `127.0.0.1:8091`, intacto |
| 8092 (LAN Gateway) | `0.0.0.0:8092`, accesible desde LAN |
| Token | Obligatorio |
| Servicio LAN | `disabled`, `active (running)` |
| UFW | `inactive` (no modificado) |
| Boot enable | `disabled` |

---

## Pruebas

| Escenario | Resultado |
|---|---|
| 8092 sin token | `401 Unauthorized` |
| 8092 con token (localhost) | `404` / `406` (pasa auth) |
| 8092 vía LAN IP con token | `404` / `406` (pasa auth) |
| 8091 intacto | ✅ Activo, responde |

---

## Token

- Fingerprint: `ff4f2df5ea199879`
- Almacenamiento: `/etc/ai-lab/mcp-lan.env` (600, root)

---

## Backup

```
/home/albert/backups/ai-lab/mcp-lan-bind-token-only/20260601-134207/
├── mcp-lan.env.before
├── mcp-lan.env.before-host-change
├── ailab-mcp-lan-gateway.service.before.txt
├── ports.before.txt
└── ufw-status.before.txt
```

---

## Rollback

```bash
sudo bash /tmp/rollback-mcp-lan-bind-token-only.sh
```

O manual:

1. `sudo sed -i 's/^AILAB_MCP_HOST=.*/AILAB_MCP_HOST=127.0.0.1/' /etc/ai-lab/mcp-lan.env`
2. `sudo systemctl restart ailab-mcp-lan-gateway.service`
3. Verificar: `ss -ltnp | grep 8092` debe mostrar `127.0.0.1:8092`

---

## Limitaciones

- No hay firewall — cualquier equipo en LAN puede alcanzar el puerto 8092
- La protección es exclusivamente por token MCP
- No se probó desde `192.168.1.250` (NAS-N5 / LM Studio) — pendiente para `AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01`

---

## Siguiente fase

`AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01` — Probar LM Studio contra `192.168.1.30:8092` con token
