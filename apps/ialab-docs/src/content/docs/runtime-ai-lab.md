---
title: "Runtime AI-LAB"
summary: "Arquitectura runtime y flujo operativo del laboratorio."
order: 5
---

# Runtime AI-LAB

El runtime constituye el núcleo operativo del laboratorio.

Gestiona:

- inferencia distribuida
- snapshots vivos
- observabilidad
- routing cognitivo
- monitorización GPU
- estado del sistema

---

# Componentes principales

| Componente | Función |
|---|---|
| router_api.py | API OpenAI-compatible |
| live_state.py | Observabilidad viva |
| system_state.py | Generación de snapshots |
| system_snapshot.json | Estado persistente |
| GPU nodes | Inferencia remota |
| Astro Portal | Visualización operativa |

---

# Flujo operativo

```mermaid
graph TD

A[Usuario] --> B[Router API]

B --> C[Routing Cognitivo]

C --> D[GPU RX9070XT]
C --> E[GPU RX7900XT]

D --> F[Inferencia]
E --> F

F --> G[Snapshot Runtime]

G --> H[Dashboard Astro]
