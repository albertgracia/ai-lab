 cat /opt/ai-lab/apps/ialab-docs/src/content/docs/architecture_phase8.md
[?2004l]3008;start=dd43b2d0-b41a-4f31-a8ee-8a1814ef0ef8;machineid=20aaf5bfa7584e8fb6c0264046eebecd;user=albert;hostname=ubuntu-ialab;bootid=1fc818c4-677f-4c57-b21b-3a4b2a5c6134;pid=00000000000000094699;type=command;cwd=/home/albert\---
title: "Phase 8 Architecture — Realtime Cognitive Mesh"
summary: "Arquitectura completa del AI-LAB tras la Fase 8 con eventos SSE, topologia viva y observabilidad en tiempo real."
order: 16
---

## Overview

La Fase 8 transforma AI-LAB en un Cognitive Mesh en tiempo real.
]3008;end=dd43b2d0-b41a-4f31-a8ee-8a1814ef0ef8;exit=success\]3008;start=083f1e15-3bae-457a-ad21-998be969a6d6;machineid=20aaf5bfa7584e8fb6c0264046eebecd;user=albert;hostname=ubuntu-ialab;bootid=1fc818c4-677f-4c57-b21b-3a4b2a5c6134;pid=00000000000000094699;type=shell;cwd=/home/albert\[?2004h]0;albert@ubuntu-ialab: ~[01;32malbert@ubuntu-ialab[00m:[01;34m~[00m

## Overview

La Fase 8 transforma AI-LAB de un runtime funcional con observabilidad clasica
a un **Cognitive Mesh** en tiempo real: una malla cognitiva donde cada componente
emite eventos, se visualiza en vivo y puede ser monitorizado con latencia sub-5s.

## Componentes

```
                         ┌──────────────┐
                         │  Open WebUI  │
                         │    :3000      │
                         └──────┬───────┘
                                │ /v1/chat/completions
                                ▼
┌──────────────────────────────────────────────────────┐
│                  ROUTER API (:8083)                   │
│  capability-aware routing  ·  stream sanitization    │
│  CORS  ·  model selection  ·  session tracking       │
└────────────────────┬─────────────────────────────────┘
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ Gateway  │ │ Gateway  │ │ Gateway  │
   │ :8008    │ │ :8008    │ │ :8008    │
   └────┬─────┘ └────┬─────┘ └────┬─────┘
        │            │            │
   ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
   │ RX9070  │  │RX7900XT │  │  NAS    │
   │ LMStudio│  │LMStudio │  │(offline)│
   └─────────┘  └─────────┘  └─────────┘
```

## Capas del Sistema

### Capa 1: Infraestructura Fisica
- Hyper-V host (NAS-N5) con 2 VMs Ubuntu Server
- 3 nodos GPU (RX9070 16GB, RX7900XT 20GB, NAS offline)
- Red 10Gb + 2.5Gb con Cloudflare Tunnel

### Capa 2: Runtime Cognitivo
- 7 servicios systemd con autoarranque
- Gateway OpenAI-compatible con failover y rate limiting
- Router API con routing capability-aware
- Live API con eventos SSE y topologia

### Capa 3: Observabilidad (Stack Central en 1.40)
- Prometheus: scraping de todas las metricas
- Grafana: 8 dashboards + 2 nuevos Fase 8
- Loki: logs centralizados
- Cloudflare Tunnel: acceso seguro

### Capa 4: Visualizacion en Tiempo Real (Fase 8)
- SSE Event Bus: eventos estructurados via streaming
- ClusterHealth: indicadores vivos GPUs/Docker/VRAM
- EventStream: timeline de eventos cognitivos
- TopologyGraph: topologia interactiva del cluster
- Cytoscape.js: grafo de red para futura migracion

## Flujo de Datos en Tiempo Real

```
GPU Nodes (9182/9183)
    │ scrape cada 30s
    ▼
Prometheus (:9090 en 1.40)
    │
    ├── Grafana dashboards (query)
    └── live_api.py (:8084 en 1.30)
            │
            ├── /api/status.json  → Polling (ClusterHealth)
            ├── /api/topology     → Polling (TopologyGraph)
            └── /api/events       → SSE push (EventStream)
```

## Metricas Tiempo Real

| Metrica | Fuente | Latencia |
|---|---|---|
| GPU temperatura | GPU API :9183 | 3s (SSE) |
| VRAM usado | windows_exporter :9182 | 30s (scrape) |
| Docker count | live_api.py | 3s (SSE) |
| Requests total | Gateway :8008/metrics | 15s (scrape) |
| Eventos SSE | live_api.py | 3s (push) |
| Topologia | live_api.py | 5s (polling) |

## Seguridad

- CORS configurado en Router API y Live API
- Rate limiting en Gateway (30 req/min)
- Cloudflare Zero Trust para acceso publico
- Sin exponer puertos entrantes (solo Tunnel)