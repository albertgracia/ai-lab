---
title: "Servicios Persistentes (systemd)"
summary: "Servicios systemd del AI-LAB y cómo gestionarlos."
order: 12
---

## Servicios Activos

| Servicio | Puerto | Descripción | Estado |
|---|---|---|---|
| \`ailab-heartbeat.service\` | — | Heartbeat persistente del cluster (30s) | ✅ Running |
| \`ailab-gateway.service\` | 8008 | Gateway OpenAI-compatible con sanitización | ✅ Running |
| \`ailab-router.service\` | 8083 | Router API cognitivo FastAPI | ✅ Running |
| \`ailab-live-state.service\` | — | Snapshots de estado del sistema cada 5s | ✅ Running |

## Gestión

\`\`\`bash
# Estado de todos los servicios
systemctl status ailab-*

# Reiniciar un servicio
sudo systemctl restart ailab-gateway.service

# Ver logs
journalctl -u ailab-gateway.service -n 50 --no-pager

# Habilitar/Deshabilitar autoarranque
sudo systemctl enable ailab-gateway.service
sudo systemctl disable ailab-gateway.service
\`\`\`

## Dependencias

\`ailab-router.service\` depende de \`ailab-gateway.service\` (After).
Todos dependen de \`network-online.target\`.

## Límites de Recursos

| Servicio | MemoryMax |
|---|---|
| ailab-gateway | 256M |
| ailab-router | 256M |
| ailab-live-state | 128M |
| ailab-heartbeat | 128M |
