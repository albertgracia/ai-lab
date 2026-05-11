---
title: "Observabilidad y Estado Vivo"
summary: "Sistema de monitorización y snapshots vivos del AI-LAB."
order: 9
---

El AI-LAB mantiene un sistema de observabilidad continua para conocer en tiempo real:

- estado GPU
- modelos activos
- salud de nodos
- servicios Docker
- runtime IA
- snapshots operativos

---

# Objetivos

## Observabilidad continua

Permitir:

- monitorización viva
- failover automático
- detección de errores
- dashboards realtime
- reasoning contextual

---

# Componentes principales

| Componente | Función |
|---|---|
| live_state.py | Actualización runtime |
| system_state.py | Recolección estado |
| system_snapshot.json | Snapshot persistente |
| Astro Dashboard | Visualización |
| Router API | Estado IA |
| GPU monitor | Telemetría GPU |

---

# Flujo operativo

```mermaid
graph TD

A[GPU Nodes]

A --> B[live_state.py]

B --> C[system_state.py]

C --> D[system_snapshot.json]

D --> E[Astro Dashboard]

D --> F[Router Cognitivo]

F --> G[Inferencia]
