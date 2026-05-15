---
title: "Runtime Analytics Engine — Documentacion Tecnica"
summary: "Motor de analiticas en tiempo real del AI-LAB: health score, metricas agregadas, sesiones, routing y event bus."
order: 24
---

# Runtime Analytics Engine — Documentacion Tecnica

## Arquitectura

```
Gateway (:8008/metrics)
    |
    +-- Prometheus scrape (15s)
    |
    +-- runtime/analytics/runtime_analytics.py
            |                       |
            |  +-- health_score.py  |  (lee gateway metrics + cluster state)
            |  +-- session_metrics  |  (sesiones activas)
            |  +-- routing_metrics  |  (rutas por modelo)
            |
            v
    Live API (:8084/api/analytics)
            |
            +-- /api/analytics (JSON)
            |
            v
    Astro Portal
    +-- /ops (Command Center)
    +-- /status/history
```

## Componentes

### runtime/analytics/runtime_analytics.py
- Lee metricas del gateway via `:8008/metrics`
- Lee estado del cluster via `cluster_state.json`
- Retorna metricas agregadas: requests, streams, errores, routing, latencia, nodos

### runtime/analytics/health_score.py
- Score 0-100 evaluando 6 factores
- Penalizaciones: GPUs offline (-30), Gateway (-15), Router (-10), Prometheus (-10), Docker (-5), Latencia (-20)
- Niveles: perfect (90+), good (70+), degraded (50+), poor (30+), critical (<30)

### runtime/analytics/session_metrics.py
- Sesiones activas, totales, duracion media

### runtime/analytics/routing_metrics.py
- Rutas por tarea, failovers, ultimas 20 rutas

## API Endpoint

```
GET /api/analytics

Response:
{
  "health": {"score": 85, "level": "good", "reasons": ["1 GPU(s) offline"]},
  "metrics": {"requests_total": 18, "events_per_minute": 0, ...},
  "sessions": {"total_sessions": 0, "active_sessions": 0, ...},
  "routing": {"total_routes": 0, "failovers": 0, ...},
  "event_bus": {"total_events": 0, "active_listeners": 0, ...},
  "timestamp": 1747336800.0
}
```

## Integracion con Traefik

El endpoint `/api/analytics` se sirve a traves de Traefik para el blog privado:

```yaml
ai-lab-docs-api:
  rule: "Host(`blog-ai-lab.labrazahome.com`) && PathPrefix(`/api/`)"
  service: ai-lab-docs-api
  priority: 100
```

El `priority: 100` es necesario para que esta ruta tenga prioridad sobre la ruta principal de docs.

## Persistencia post-reboot

Todos los componentes necesarios arrancan automaticamente:

```bash
# Servicios verificados
systemctl is-active ailab-live-api   # Live API con analytics endpoint
systemctl is-active ailab-docs        # Astro portal
systemctl is-active ailab-gateway     # Gateway con metricas
systemctl is-active ailab-router      # Router API
systemctl is-active ailab-traefik     # Proxy inverso (via systemd)
systemctl is-active ailab-runner      # GitHub Actions runner
```

Ademas, `cron @reboot` ejecuta `scripts/startup.sh` para verificar stacks Docker.

---

### Correccion de Metricas (2026-05-15)

Ver [Runtime Analytics — Correccion](/docs/runtime-analytics-correccion/) para el diagnostico de los bugs de health score, nodos online y gateway health check.
