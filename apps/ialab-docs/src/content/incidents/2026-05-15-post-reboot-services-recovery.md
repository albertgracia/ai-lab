---
title: "Post-reboot services recovery: Traefik and Prometheus down after host restart"
date: "2026-05-15"
severity: "low"
status: "resolved"
tags:
  - docker
  - traefik
  - prometheus
  - reboot
  - operations
---

# Summary

Tras la sesión de la Fase 7 (production stabilization) del 14 de Mayo de 2026, se apagó el Hyper-V host
completo durante la noche. Al reiniciar las VMs al día siguiente, dos servicios Docker no arrancaron
automáticamente:

- **Traefik** (1.30) — Contenedor en estado `Exited (0)`.
- **Prometheus** (1.40) — Contenedor no presente entre los servicios activos.

El resto de la infraestructura arrancó correctamente: 6 servicios systemd, 15 contenedores Docker
y todos los nodos GPU se recuperaron sin intervención.

# Issues Detected

## 1. Traefik no arrancó en ubuntu-ialab (1.30)

**Síntoma:** El contenedor `traefik` aparecía como `Exited (0) 8 hours ago` mientras el resto de
contenedores estaban `Up 14 minutes`.

**Causa:** El stack de Traefik se gestiona con `docker compose` dentro de `/opt/ai-lab/stacks/traefik/`.
Al no usarse `docker compose up -d` de forma explícita tras el arranque del sistema, el contenedor
no se recuperó automáticamente.

**Solución:**
```bash
cd /opt/ai-lab/stacks/traefik
docker compose up -d
```

**Prevención:** Añadir script de arranque o systemd unit para garantizar que el stack de Traefik
se levante con el sistema.

## 2. Prometheus no arrancó en ubuntu-server (1.40)

**Síntoma:** Prometheus no estaba en la lista de contenedores activos en 1.40.

**Causa:** El contenedor se gestiona mediante `docker run` / `docker compose` en el directorio
`/home/albert/docker/monitorizacion/`. Al igual que Traefik, no se recuperó automáticamente.

**Solución:**
```bash
docker start prometheus
```

**Prevención:** Verificar que el stack de monitorización tenga `restart: unless-stopped` en su
docker-compose.yml.

# Healthy Services (no afectados)

| Componente | Ubicación | Estado |
|---|---|---|
| ailab-gateway.service | 1.30 | ✅ Activo |
| ailab-router.service | 1.30 | ✅ Activo |
| ailab-live-state.service | 1.30 | ✅ Activo |
| ailab-heartbeat.service | 1.30 | ✅ Activo |
| ailab-live-api.service | 1.30 | ✅ Activo |
| ailab-docs.service | 1.30 | ✅ Activo |
| Open WebUI | 1.30 | ✅ Up (healthy) |
| Ollama | 1.30 | ✅ Up |
| Qdrant | 1.30 | ✅ Up |
| Grafana | 1.40 | ✅ Up |
| Loki | 1.40 | ✅ Up |
| Cloudflare Tunnel | 1.40 | ✅ Up |

# Timeline

| Hora (UTC+2) | Evento |
|---|---|
| ~23:00 14/05 | Fin de la sesión Fase 7 |
| ~01:00 15/05 | Apagado del Hyper-V host |
| 10:05 15/05 | Encendido del Hyper-V host |
| 10:19 15/05 | Detección de Traefik y Prometheus caídos |
| 10:20 15/05 | Restauración de ambos servicios |

# Actions Taken

- ✅ `docker compose up -d` en `/opt/ai-lab/stacks/traefik/`
- ✅ `docker start prometheus` en 1.40
- ✅ Verificación de todos los endpoints API
- ✅ Verificación de targets Prometheus
- ✅ Verificación de dashboards Grafana

# Recommendations

1. Añadir un script `scripts/startup.sh` que verifique y arranque todos los stacks Docker
   críticos al inicio del sistema.
2. Considerar mover Traefik a systemd para garantizar su arranque.
3. Documentar procedimiento de post-reboot en runbooks.
