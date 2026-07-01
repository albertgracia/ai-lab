---
title: "Phase 8 Architecture — Realtime Cognitive Mesh"
summary: "Arquitectura completa del AI-LAB tras la Fase 8: runtime cognitivo con eventos SSE, topologia viva y observabilidad en tiempo real."
order: 16
---

## Overview

La Fase 8 transforma AI-LAB de un runtime funcional con observabilidad clasica a un **Cognitive Mesh** en tiempo real.

## Capas del Sistema

### Capa 3: Observabilidad operativa en 1.40
- Prometheus: `192.168.1.40:9090`
- Grafana: `192.168.1.40:3000`
- Loki: `192.168.1.40:3100`
- Promtail: `192.168.1.30:1514/tcp` para `unifi-ids`
- Dashboards y logs ya conectados al stack vivo

### Capa 4: Visualizacion en Tiempo Real
- SSE Event Bus
- ClusterHealth
- EventStream
- TopologyGraph

## Estado

- Observabilidad viva y operativa.
- Grafana consolidado en `192.168.1.40:3000`.
- El Grafana antiguo ya no es referencia.
