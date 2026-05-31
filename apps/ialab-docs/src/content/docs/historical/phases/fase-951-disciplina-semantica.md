---
title: "FASE 9.5.1 — Disciplina Semántica en HARD FACTS"
summary: "Reglas estrictas de categorización para evitar que el modelo confunda servicios systemd, contenedores Docker, colecciones Qdrant y nodos GPU. Etiquetado obligatorio [HARD_FACTS], [INFERIDO], [NO DISPONIBLE]."
order: 21
---

## Problema

El modelo (qwen2.5-coder-14b-instruct) mezclaba categorías en sus respuestas:

- **Colecciones Qdrant** confundidas con **servicios systemd** (ej: "colecciones cognitivas como ailab-docs, ailab-gateway")
- **context_size del modelo** (32768) reportado como si fuera el contexto usado por HARD FACTS
- **working_memory activa** afirmada sin dato verificable en el JSON
- Valores inferidos dentro de la sección [HARD_FACTS] sin etiquetar como [INFERIDO]

## Causa Raíz

El `BASE_SYSTEM_CONTEXT` en `router_api.py` tenía directrices genéricas pero no reglas taxativas:

```
DIRECTRICES:
4. Distingue siempre entre:
   - [HARD_FACTS] → dato verificado del runtime
   - [INFERIDO] → deducción lógica propia
   - [PENDIENTE] → funcionalidad no implementada aún
```

Esto permitía que el modelo interpretara libremente en lugar de citar textualmente.

## Solución

### 1. Reglas de citas textuales

`[HARD_FACTS]` solo puede contener datos que aparezcan **explícitamente** en el bloque JSON. No resumir, no interpretar, no extender.

### 2. Mapa de categorías

Cada sección del JSON tiene su propósito declarado en el prompt:

| Sección JSON | Categoría real | No confundir con |
|---|---|---|
| `gpu_nodes` | Nodos GPU físicos con modelos LM Studio | Servicios systemd |
| `services` | Servicios systemd (ailab-router, ailab-docs...) | Contenedores Docker |
| `docker.main` | Contenedores Docker (traefik, qdrant, open-webui...) | Colecciones Qdrant |
| `routing.model_performance` | Rendimiento de modelos de inferencia | Nodos GPU |
| `pending_implementations` | Funcionalidades no implementadas | Servicios activos |
| *(no aparece en JSON)* | Colecciones Qdrant | → [NO DISPONIBLE] |

### 3. Valores prohibidos de inferencia

El modelo tiene prohibido inferir:

- `context_size` — solo existe `ctx` por modelo (ventana del modelo, no contexto usado)
- `health_score` numérico
- `working_memory` activa
- `watchdog` score detallado por servicio
- `routing_confidence`
- Latencia por request individual

### 4. Etiquetas obligatorias

| Etiqueta | Cuándo usarla |
|---|---|
| `[HARD_FACTS]` | Copia literal o resumen fiel de datos del JSON |
| `[INFERIDO]` | Deducción lógica propia ("probablemente...") |
| `[PENDIENTE]` | Funcionalidad listada en `pending_implementations` |
| `[NO DISPONIBLE]` | Dato que no aparece en HARD FACTS ni PENDING |

### 5. Prohibiciones explícitas

- No usar `thinking` ni `reasoning_content`
- No inventar valores numéricos
- No confundir servicios con colecciones con contenedores
- No decir que algo funciona si no aparece en HARD FACTS
- No mover infraestructura sin permiso explícito

## Implementación

**Archivo:** `runtime/llm/router_api.py` (líneas 82-108 y 377-384)

Dos cambios:

1. **`BASE_SYSTEM_CONTEXT`** (línea 82): Reemplazadas las DIRECTRICES genéricas por REGLAS ESTRICTAS con 6 secciones (citas textuales, categorías, datos no disponibles, etiquetas obligatorias, ejemplo correcto, prohibiciones).

2. **`final_instruction`** (línea 377): Añadido refuerzo: *"No infieras valores ni confundas categorías: services != collections != containers != models"*.

## Resultado

Test de validación con la pregunta "Describe el estado actual del AI-LAB. ¿Qué colecciones Qdrant existen? ¿Qué servicios systemd?":

| Antes | Después |
|---|---|
| "colecciones cognitivas como ailab-docs, ailab-gateway" ❌ | "Colecciones Qdrant: [NO DISPONIBLE en HARD FACTS]" ✅ |
| Servicios systemd mezclados con colecciones | 7 servicios systemd listados correctamente |
| Sin etiquetas [HARD_FACTS] | Etiquetas [HARD_FACTS] en cada afirmación |
| GPU NVIDIA inventadas | Solo nodos reales del JSON |

## Archivos modificados

- `runtime/llm/router_api.py` — BASE_SYSTEM_CONTEXT + final_instruction

## Commits

Este cambio es posterior al commit `052c2db` (FASE 9.5) y `1bfa064` (FASE 10 JSON HARD FACTS). No tiene commit propio — aplicado directamente sobre main.
