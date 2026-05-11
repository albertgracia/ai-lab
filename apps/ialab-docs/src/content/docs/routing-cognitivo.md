---
title: "Routing Cognitivo"
summary: "Sistema de decisión inteligente del AI-LAB."
order: 6
---

El Routing Cognitivo es el sistema de decisión central del AI-LAB.

Su función es determinar:

- qué modelo usar
- qué GPU utilizar
- cómo distribuir inferencia
- qué contexto recuperar
- cuándo usar grounding
- cómo optimizar recursos

---

# Objetivos

## Optimización de inferencia

Seleccionar automáticamente:

- nodo menos cargado
- GPU óptima
- modelo adecuado
- tamaño de contexto correcto

---

# Flujo conceptual

```mermaid
graph TD

A[Usuario] --> B[Router API]

B --> C[Analizador de intención]

C --> D[Consulta simple]
C --> E[Reasoning complejo]
C --> F[Embeddings]
C --> G[Grounding]

D --> H[Modelo pequeño]
E --> I[Modelo reasoning]
F --> J[Embedding model]
G --> K[Qdrant]

H --> L[Respuesta]
I --> L
J --> L
K --> L
