---
title: "Capability-Aware Distributed Routing"
summary: "Sistema inteligente de selección de nodos y modelos basado en capacidades, contexto y tamaño de prompt."
status: "stable"
category: "distributed-runtime"
tags:
  - routing
  - distributed-ai
  - orchestration
  - failover
  - token-aware
date: "2026-05-14"
---

# Capability-Aware Distributed Routing

## Objetivo

AI-LAB implementa un sistema de routing distribuido capaz de:

- detectar nodos disponibles
- seleccionar modelos adecuados según capacidad
- validar contexto máximo soportado
- evitar overflows
- reroutear automáticamente workflows degradados
- operar incluso con cluster parcial

---

# Componentes Integrados

## Heartbeat Runtime

Servicio persistente:

```bash
systemctl status ailab-heartbeat.service
