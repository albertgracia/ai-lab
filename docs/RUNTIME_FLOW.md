---
title: "Runtime Flow — Flujo completo de una peticion"
summary: "Recorrido completo de una peticion desde Open WebUI hasta la GPU, pasando por Router API, Gateway y LM Studio."
order: 5
---

# Runtime Flow — Flujo Completo de una Peticion

## Diagrama de Flujo

```
Usuario
   │
   ▼
Open WebUI (:3000)
   │ POST /api/chat/completions
   │ model: ailab-router/auto
   ▼
ROUTER API (:8083)
   │
   ├── 1. Recibe peticion
   ├── 2. CORS check
   ├── 3. Extrae capability del modelo (auto/fast/coding/reasoning)
   ├── 4. build_system_state() → actualiza estado del cluster
   ├── 5. select_node(request_text, capability)
   │       ├── infer_task() → detecta tipo de tarea
   │       ├── select_best_node() → elige nodo optimo
   │       └── choose_model_for_node() → selecciona modelo
   ├── 6. build_selective_context() → contexto RAG
   ├── 7. Construye payload con system prompt + contexto
   └── 8. Envia a LM Studio
        │
        ▼
   GATEWAY (:8008)
   │
   ├── 1. Recibe peticion del Router API
   ├── 2. choose_model(task_type) → selecciona modelo
   ├── 3. inject_agent_context() → anyade prompt del agente
   ├── 4. Rate limit check
   ├── 5. Envia a LM Studio
   │       │ POST /v1/chat/completions
   │       │ model: qwen2.5-coder-14b-instruct
   │       ▼
   └── LM STUDIO (RX9070 :1234)
        │
        ├── 1. Carga/usa modelo en VRAM
        ├── 2. Procesa prompt
        ├── 3. Genera respuesta (streaming o completa)
        └── 4. Devuelve respuesta
             │
             ▼
   ROUTER API
   │
   ├── 1. Recibe respuesta de LM Studio
   ├── 2. Sanitiza stream (elimina reasoning_content)
   ├── 3. Aplica CORS headers
   └── 4. Devuelve streaming SSE a Open WebUI
        │
        ▼
   USUARIO
   │ Recibe respuesta en Open WebUI
```

## Flujo de Eventos (Fase 8)

Cada paso del flujo emite eventos al Event Bus:

```
1. request_started    → event_bus.emit()
2. routing_decision   → event_bus.emit()
3. model_selected     → event_bus.emit()
4. request_finished   → event_bus.emit()
5. session_created    → event_bus.emit()
                        │
                        ▼
                   Event Stream SSE
                        │
                   ┌────┴────┐
                   │         │
              Dashboard    Frontend
              Grafana      Astro
```

## Tiempos Tipicos

| Paso | Tiempo | Notas |
|---|---|---|
| Routing decision | <5ms | Capacidad-aware |
| Context loading | <10ms | RAG + archivos core |
| LM Studio prompt eval | 1-2 ms/token | Depende del modelo |
| LM Studio generation | 20-30 ms/token | Depende del modelo |
| Stream sanitization | <1ms | Inline en el stream |
| Total (50 tokens) | 1-2s | Con modelo 14B en RX9070 |

## Modelos y Rutas

| Ruta API | Modelo | Nodo | VRAM |
|---|---|---|---|
| `ailab-router/auto` | Seleccion automatica | — | — |
| `ailab-router/fast` | Llama 3.1 8B / Qwen 14B | RX9070 | 16 GB |
| `ailab-router/coding` | Qwen 2.5 Coder 14B / 32B | RX9070/RX7900XT | 16-20 GB |
| `ailab-router/reasoning` | Qwen 2.5 Coder 32B | RX7900XT | 20 GB |
