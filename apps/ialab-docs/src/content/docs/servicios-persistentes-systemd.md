---
title: "Servicios Persistentes (systemd)"
summary: "Servicios systemd del AI-LAB y gestiÃ³n de arranque."
order: 12
---

## Servicios Activos

| Servicio | Puerto | DescripciÃ³n | Estado |
|---|---|---|---|
| `ailab-traefik.service` | 80/443 | Proxy inverso Traefik (Docker compose wrapper) | âœ… Enabled |
| `ailab-gateway.service` | 8008 | Gateway OpenAI-compatible con sanitizaciÃ³n | âœ… Enabled |
| `ailab-router.service` | 8083 | Router API cognitivo FastAPI | âœ… Enabled |
| `ailab-live-state.service` | â€” | Snapshots de estado del sistema cada 5s | âœ… Enabled |
| `ailab-heartbeat.service` | â€” | Heartbeat persistente del cluster (30s) | âœ… Enabled |
| `ailab-live-api.service` | 8084 | Live API (status.json, topology, SSE) | âœ… Enabled |
| `ailab-docs.service` | 4322 | Portal de documentaciÃ³n Astro | âœ… Enabled |

## GestiÃ³n

```bash
# Estado de todos los servicios
echo '19682507' | sudo -S systemctl status ailab-*

# Reiniciar un servicio
sudo systemctl restart ailab-gateway.service

# Ver logs
journalctl -u ailab-gateway.service -n 50 --no-pager

# Habilitar/Deshabilitar autoarranque
sudo systemctl enable ailab-gateway.service
sudo systemctl disable ailab-gateway.service
```

## Dependencias

`ailab-router.service` depende de `ailab-gateway.service` (After).
`ailab-traefik.service` depende de `docker.service` y `network-online.target`.
Todos dependen de `network-online.target`.

## LÃ­mites de Recursos

| Servicio | MemoryMax |
|---|---|
| ailab-gateway | 256M |
| ailab-router | 256M |
| ailab-live-state | 128M |
| ailab-heartbeat | 128M |
| ailab-live-api | 128M |
| ailab-docs | 512M |
| ailab-traefik | Sin lÃ­mite (Docker) |

## RecuperaciÃ³n Post-Reboot

Todos los servicios systemd arrancan automÃ¡ticamente al iniciar el sistema.
Adicionalmente, el script `scripts/startup.sh` se ejecuta via cron `@reboot`
para verificar que todos los stacks Docker (Traefik, Prometheus) tambiÃ©n
estÃ©n operativos:

```bash
# Verificar Ãºltimo arranque
cat /opt/ai-lab/logs/startup.log

# Ejecutar manualmente
/opt/ai-lab/scripts/startup.sh
```

Para mÃ¡s detalles, consultar el runbook de post-reboot y el incidente registrado.
