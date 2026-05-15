---
title: "Implementing a Real-Time Runtime Analytics Engine for Local AI Infrastructure"
description: "Como implemente un motor de analiticas en tiempo real para el AI-LAB con health score, metricas de gateway y visualizacion en Astro. Incluye solucion a problemas de routing con Traefik."
date: "2026-05-15"
tags:
  - analytics
  - python
  - astro
  - traefik
  - sse
  - observability
---

# Implementing a Real-Time Runtime Analytics Engine for Local AI Infrastructure

## El Problema

Tras construir el AI-LAB con gateway, router API, event bus y monitorizacion GPU,
me di cuenta de que faltaba una capa crucial: **analiticas en tiempo real**.

Sabia cuantas requests habia recibido el gateway en total (gracias a Prometheus),
pero no podia ver en un solo sitio:

- Health score del cluster
- Requests por minuto
- Sesiones activas
- Latencia media
- Nodos online/offline
- Errores recientes
- Decisiones de routing

## La Solucion

Cree un motor de analiticas en Python con 4 modulos:

### 1. runtime_analytics.py
Lee las metricas del gateway via HTTP (`:8008/metrics`) y el estado del cluster
desde `cluster_state.json`. Retorna datos agregados en tiempo real.

### 2. health_score.py
Algoritmo que evalua 6 factores y devuelve un score 0-100:

- GPUs online (hasta 2, -30 por offline)
- Gateway responde (-15)
- Router responde (-10)
- Prometheus responde (-10)
- Docker corriendo (-5 si <5 contenedores)
- Latencia aceptable (-20 si >30s)

### 3. session_metrics.py
Sesiones activas, totales y duracion media.

### 4. routing_metrics.py
Rutas por tarea, failovers y historial de rutas.

## El Problema con Traefik

Al integrar el endpoint `/api/analytics` en el portal Astro, me encontre con que
las peticiones desde el blog no llegaban al backend. El problema era que Traefik
tiene rutas definidas en un archivo YAML dinamico, y la ruta del API necesitaba
`priority: 100` para ganar a la ruta principal de docs:

```yaml
ai-lab-docs-api:
  rule: "Host(`blog-ai-lab.labrazahome.com`) && PathPrefix(`/api/`)"
  service: ai-lab-docs-api
  priority: 100  # <-- clave
```

Sin `priority: 100`, Traefik devolvia 404 porque la ruta principal
(sin PathPrefix) coincidia primero.

## Resultado Final

El AI Operations Center (`/ops`) muestra ahora en tiempo real:

- Health Score con codigo de colores
- 8 metricas clave
- Stream de eventos
- Factores de salud detallados
- Ultimos errores

Todo servido desde un solo endpoint `/api/analytics` con datos agregados
cada 8 segundos.
