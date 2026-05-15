---
title: "Building a Realtime AI Operations Platform with Astro, Grafana and SSE"
description: "Como construi el centro de operaciones en tiempo real del AI-LAB usando Astro, Server-Sent Events, Prometheus y Grafana para monitorizar un cluster de inferencia distribuido con GPUs AMD."
summary: "Centro de operaciones en tiempo real con Astro, SSE, Prometheus y Grafana."
date: "2026-05-15"
tags:
  - astro
  - observability
  - sse
  - grafana
  - prometheus
  - realtime
---

# Building a Realtime AI Operations Platform with Astro, Grafana and SSE

## El Problema

Cuando construyes un cluster de inferencia local con GPUs AMD y LM Studio,
necesitas saber en todo momento que esta pasando: que modelo se esta usando,
que temperatura tiene la GPU, cuanta VRAM queda libre, si el gateway responde.

Los dashboards de Grafana son excelentes para metricas historicas, pero no
para monitorizacion operativa en tiempo real tipo NOC/SOC.

## La Solucion

Construir una capa de observabilidad en tiempo real sobre el portal Astro
existente, usando:

- **Server-Sent Events (SSE)** para streaming de datos cada 3s
- **Event Bus** en Python con 9 tipos de eventos cognitivos
- **Runtime Analytics Engine** con health score 0-100
- **Prometheus** para metricas de gateway y GPU
- **Grafana** para dashboards historicos

## Arquitectura

```
GPU Nodes (Windows)
    | (windows_exporter + PowerShell API)
    v
Prometheus (:9090)
    |
    +-- Grafana dashboards (:3000)
    |
    +-- Live API (:8084)
            |
            +-- /api/status.json  (polling)
            +-- /api/topology     (polling)
            +-- /api/events       (SSE streaming)
            +-- /api/analytics    (health + metrics)
                    |
                    v
            Astro Portal
            +-- /ops (Command Center)
            +-- /status/live
            +-- /status/gpus
            +-- /status/history
```

## Componentes Clave

### 1. SSE Event Bus

El corazon del sistema es un bus de eventos en Python con soporte para
conexiones multiples concurrentes via ThreadingHTTPServer:

```python
from runtime.event_bus import emit, get_history

# Emitir evento cuando se selecciona un modelo
emit("model_selected", {"model": "qwen2.5-coder-14b", "node": "RX9070", "latency_ms": 2450})

# Obtener estadisticas del bus
stats = get_stats()
# {"total_events": 150, "active_listeners": 2, "event_types": {...}}
```

### 2. Health Score

Algoritmo de puntuacion de salud 0-100 que evalua 6 factores:

| Factor | Penalizacion | Descripcion |
|---|---|---|
| GPUs online | -30 por GPU offline | Hasta 2 GPUs |
| Gateway | -15 si no responde | Health check :8008 |
| Router API | -10 si no responde | Health check :8083 |
| Prometheus | -10 si no responde | Health check 1.40:9090 |
| Docker | -5 si <5 contenedores | Contenedores activos |
| Latencia | -20 si >30s | Latencia de inferencia |

### 3. Portal en Tiempo Real

El portal Astro consume los datos via:
- **SSE** para el EventStream (conexion persistente)
- **Polling** cada 8s para el Command Center (/ops)
- **Polling** cada 10s para GPU Telemetry (/status/gpus)

## Resultados

El AI Operations Center muestra en tiempo real:

- Health Score con codigo de colores
- 8 metricas clave (GPUs, requests, sesiones, latencia, routing, streams, errores)
- Stream de eventos en vivo
- Factores de salud detallados
- Ultimos errores del sistema

## Stack Tecnologico

| Componente | Tecnologia |
|---|---|
| Frontend | Astro 6 + Starlight + Tailwind 4 |
| Tiempo real | SSE + ThreadingHTTPServer |
| Metricas | Prometheus + Grafana 13 |
| Backend | Python 3.14 + FastAPI |
| GPUs | LM Studio + windows_exporter |
| Infra | Docker + Traefik + systemd |

## Proximos Pasos

1. Experiments Lab con benchmarks GPU y comparativas de modelos
2. Blog tecnico con arquitectura detallada
3. Pagina de proyectos con 8 proyectos activos
4. Historical telemetry con evolucion 24h/7d

*Articulo escrito el 15 de Mayo de 2026 como parte de la documentacion del proyecto AI-LAB.*
