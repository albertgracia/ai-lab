---
title: "Servicios Persistentes (systemd)"
summary: "Servicios systemd del AI-LAB y gestión de arranque (core runtime + docs + métricas)."
order: 12
---

## Servicios Activos

| Servicio | Puerto | Descripción | Estado |
|---|---|---|---|
| `ailab-gateway.service` | 8008 | Gateway OpenAI-compatible con sanitización | ✅ Enabled |
| `ailab-router.service` | 8083 | Router API (API interna) | ✅ Enabled |
| `ailab-live-state.service` | — | Snapshots de estado del sistema | ✅ Enabled |
| `ailab-heartbeat.service` | — | Heartbeat persistente del cluster | ✅ Enabled |
| `ailab-live-api.service` | 8084 | Live API (estado vivo, embeddings) | ✅ Enabled |
| `ailab-docs.service` | 4322 | Portal de documentación Astro (privado) | ✅ Enabled |
| `ailab-metrics.service` | 3010 | Dashboard SSR (público) | ✅ Enabled |

Nota: stacks externos (p.ej. reverse proxy) pueden existir, pero no forman parte del core runtime salvo que estén en el flujo de autoridad/evidencia.

## Gestión

```bash
# Estado de todos los servicios
systemctl status ailab-*

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
Todos los servicios core dependen de `network-online.target`.

## Límites de Recursos

| Servicio | MemoryMax |
|---|---|
| ailab-gateway | 256M |
| ailab-router | 256M |
| ailab-live-state | 128M |
| ailab-heartbeat | 128M |
| ailab-live-api | 128M |
| ailab-docs | 512M |
| (stacks externos) | N/A |

## Recuperación Post-Reboot

Todos los servicios systemd arrancan automáticamente al iniciar el sistema.
Adicionalmente, el script `scripts/startup.sh` se ejecuta via cron `@reboot`
para verificar que los componentes externos necesarios también estén operativos:

```bash
# Verificar último arranque
cat /opt/ai-lab/logs/startup.log

# Ejecutar manualmente
/opt/ai-lab/scripts/startup.sh
```

Para más detalles, consultar el runbook de post-reboot y el incidente registrado.
