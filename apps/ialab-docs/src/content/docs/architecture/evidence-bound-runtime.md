---
title: "Evidence-Bound Runtime"
summary: "Cómo 30H y 30I convierten AI-LAB en un runtime evidence-bound: prevención, observación, contratos y sanitización post-respuesta."
order: 17
---

## Idea central

Un runtime evidence-bound no permite que el LLM defina su infraestructura por plausibilidad estadística.

## Capas

1. **Prompt discipline**
2. **OBSERVED_RUNTIME**
3. **Sensor semantics**
4. **Evidence catalog**
5. **Evidence guard**

## Flujo

```mermaid
flowchart LR
    RS[runtime state] --> EC[evidence catalog]
    EC --> PI[prompt injection]
    PI --> M[model]
    M --> PG[post-response guard]
    PG --> GA[grounded answer]
```

## Qué evita

- GPUs inexistentes
- plataformas cloud no desplegadas
- modelos no activos
- hosts no observados
- confundir inventario con runtime vivo
