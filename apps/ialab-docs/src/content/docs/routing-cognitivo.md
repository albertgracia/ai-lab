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

A[Usuario] --> B[Router API / Gateway]

B --> C[Classifier: greeting/casual/report/observe/tool/general]

C --> D[minimal/casual/greet/observe]
C --> E[fast/general/chat]
C --> F[coding]
C --> G[reasoning]
C --> H[tool_use/tool_fastpath]

D --> I[observe_profile → llama-3.1-8b]
E --> J[chat_profile → qwen2.5-14b]
F --> K[coding_profile → qwen2.5-14b]
G --> L[analysis_profile → qwen2.5-32b]
H --> M[agent_profile → qwen3.6-27b]

I --> N[disabled_policy → sin tools]
J --> N
K --> O[readonly_policy → tools limitadas]
L --> N
M --> P[agent_policy → tools completas + 428 gate]

N --> Q[minimal_policy → sin memoria]
O --> Q
P --> R[full_policy → memoria completa]

Q --> S[LM Studio RX9070]
R --> S
S --> T[Respuesta]
```

## Perfiles por ruta

| Ruta | Perfil | Modelo | Tools | Memoria |
|------|--------|--------|-------|---------|
| minimal/casual/greeting/observe | observe | llama-3.1-8b | disabled | minimal |
| fast/general/chat | chat | qwen2.5-14b | disabled | light |
| coding | coding | qwen2.5-14b | readonly | light |
| reasoning | analysis | qwen2.5-32b | disabled | full |
| tool_use/tool_fastpath | agent | qwen3.6-27b | agentic | full |
