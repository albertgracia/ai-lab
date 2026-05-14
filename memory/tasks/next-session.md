# AI-LAB — Próxima Sesión: Fase 8

## Prioridad 1 — Stack de Visualización en Tiempo Real

### Backend (Python — live_api.py :8084)
- [ ] Endpoint SSE `/api/events` — stream de métricas GPU, cluster, Docker cada 5s
- [ ] Endpoint `/api/topology` — topología del cluster (nodos, conexiones, estado)
- [ ] Endpoint `/api/history` — datos históricos (temperatura, VRAM, load últimas 24h)

### Frontend (Astro + React)
- [ ] Componente `TopologyGraph.astro` con **Cytoscape.js** — topología interactiva del cluster
  - Nodos: VMs, GPUs, servicios core
  - Aristas: conexiones de red
  - Color: verde (online) / rojo (offline)
  - Hover: métricas en tooltip
- [ ] Página `/status/topology` → topología pública
- [ ] Página `/ops/topology` → topología privada con más detalle
- [ ] Componente `GpuLiveChart.tsx` con **uPlot** — tiempo real de temperatura, VRAM, load
  - Streaming via SSE (no polling)
  - 60s de ventana deslizante
- [ ] Página `/ops/gpu-detail` → dashboard detallado por GPU con uPlot

### Mejoras a componentes existentes
- [ ] `LiveStatus.astro` — migrar de polling a SSE
- [ ] `HomeLiveStats.astro` — conectar a datos en vivo (GPUs, LLM, Docker, VRAM)

## Prioridad 2 — Documentación
- [ ] Actualizar `src/content/docs/observabilidad-y-estado-vivo.md` con:
  - GPU Metrics API (9183)
  - Live API (8084)
  - Endpoint SSE
  - Topología interactiva
- [ ] Nuevo artículo blog: "Fase 7 — Production Stabilization"
- [ ] Nuevo artículo blog: "Monitorización GPU en tiempo real con PowerShell + LibreHWMonitor"

## Prioridad 3 — Limpieza y Hardening
- [ ] Revisar y eliminar páginas/componentes obsoletos
- [ ] Configurar SSL en Traefik (acme.json)
- [ ] Dashboard de logs en Grafana (Loki datasource)
- [ ] Alertas en Grafana: temperatura GPU > 85°C, nodo offline > 5min

## Dependencias a instalar
```bash
cd /opt/ai-lab/apps/ialab-docs
npm install cytoscape uplot
```

## Notas
- El `TopologyGraph.astro` ya existe pero es ASCII art estático → reemplazar con Cytoscape
- uPlot es 10x más rápido que Recharts para datos en vivo
- SSE evita el polling cada 5s → menos carga en backend y frontend
- La API SSE se servirá en `/api/events` con `text/event-stream`
