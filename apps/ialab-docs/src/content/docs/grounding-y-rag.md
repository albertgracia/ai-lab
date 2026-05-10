---
title: "Grounding y RAG"
summary: "Arquitectura de grounding contextual y recuperación semántica."
order: 7
---

# Grounding y RAG

El AI-LAB implementa una arquitectura basada en:

- grounding contextual
- embeddings
- recuperación semántica
- memoria persistente
- RAG interno

---

# Objetivo principal

Reducir:

- alucinaciones
- respuestas incorrectas
- pérdida de contexto

y mejorar:

- precisión
- coherencia
- trazabilidad
- reasoning contextual

---

# Componentes principales

| Componente | Función |
|---|---|
| Qdrant | Base vectorial |
| Embedding model | Generación embeddings |
| Router Cognitivo | Orquestación |
| Context Manager | Contexto persistente |
| Runtime snapshots | Estado operativo |
| Docs Astro | Fuente documental |

---

# Flujo RAG

```mermaid
graph TD

A[Usuario] --> B[Router API]

B --> C[Embedding Prompt]

C --> D[Qdrant Search]

D --> E[Documentos relevantes]

E --> F[Augment Prompt]

F --> G[LLM]

G --> H[Respuesta grounded]
