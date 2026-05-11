---
title: "Inferencia Distribuida"
summary: "Arquitectura multinodo GPU del AI-LAB."
order: 8
---

El AI-LAB está diseñado para soportar inferencia distribuida entre múltiples nodos GPU.

Objetivos:

- escalar capacidad
- distribuir carga
- optimizar VRAM
- mejorar reasoning
- aumentar resiliencia

---

# Nodos actuales

| Nodo | GPU | Función |
|---|---|---|
| 192.168.1.30 | Radeon 780M | Nodo principal |
| 192.168.1.50 | RX9070XT | Inferencia remota |
| 192.168.1.60 | RX7900XT | Inferencia remota |

---

# Arquitectura

```mermaid
graph TD

A[Usuario]

A --> B[Router API]

B --> C[Routing Cognitivo]

C --> D[RX9070XT]
C --> E[RX7900XT]
C --> F[Radeon 780M]

D --> G[Inferencia]
E --> G
F --> G

G --> H[Respuesta]
