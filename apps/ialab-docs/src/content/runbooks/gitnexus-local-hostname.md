---
title: "GitNexus Local Hostname (LAN)"
summary: "Acceso estable a GitNexus en LAN vía gitnexus.ai-lab.local (sin Cloudflare)."
---


## Objetivo

Acceder a GitNexus desde cualquier PC de la LAN con un nombre estable:

- Hostname: `gitnexus.ai-lab.local`
- Server: `ubuntu-ialab` (`192.168.1.30`)
- Puerto: `4747`
- Repo monitorizado: `/opt/ai-lab`

## URL final

- UI: `http://gitnexus.ai-lab.local:4747/`
- UI (explicit server):
  - `http://gitnexus.ai-lab.local:4747/?project=ai-lab&server=http%3A%2F%2Fgitnexus.ai-lab.local%3A4747`

## Método recomendado (UniFi DNS)

Crear un DNS record local:

- Name: `gitnexus.ai-lab.local`
- IP: `192.168.1.30`

Después validar desde otro PC:

```bash
ping -c 1 gitnexus.ai-lab.local
curl -s http://gitnexus.ai-lab.local:4747/api/health
```

Debe devolver:

```json
{"status":"ok"}
```

## Fallback (hosts file)

Si no tienes DNS local, añade en el cliente:

`192.168.1.30 gitnexus.ai-lab.local`

Linux/macOS: `/etc/hosts`

Windows: `C:\\Windows\\System32\\drivers\\etc\\hosts`

## Validación en el servidor

```bash
systemctl status gitnexus --no-pager -l
ss -tulpn | grep 4747
curl -s http://127.0.0.1:4747/api/health
curl -s http://127.0.0.1:4747/api/repos
```

## Troubleshooting

### UI muestra “Waiting for server to start”

Checklist:

1. API responde:
   - `curl -s http://gitnexus.ai-lab.local:4747/api/health`
2. Puerto escuchando:
   - `ss -tulpn | grep 4747`
3. Servicio activo:
   - `systemctl is-active gitnexus`
4. Logs:
   - `journalctl -u gitnexus -n 200 --no-pager`

### Diferencia entre localhost, IP y hostname

- `127.0.0.1`: solo desde el propio servidor.
- `192.168.1.30`: accesible desde la LAN, pero cambia si se reasigna IP.
- `gitnexus.ai-lab.local`: nombre estable recomendado (vía DNS local o hosts).
