---
title: "Open WebUI — Conexion al AI-LAB Router"
summary: "Configuracion de Open WebUI para usar el Router API del AI-LAB con enrutamiento declarativo por perfiles cognitivos y politicas de herramientas."
order: 14
---

## Descripcion

Open WebUI es el frontend unificado del AI-LAB. Esta conectado al Router API (`ailab-router`) para enrutar las peticiones de los usuarios al perfil y modelo optimo segun el tipo de tarea.

## Configuracion de Conexion

### OpenAI Connection

En Open WebUI (Ajustes -> Conexiones), anadir una nueva conexion OpenAI:

| Campo | Valor |
|---|---|
| URL | `http://192.168.1.30:8083/v1` |
| API Key | (dejar vacio) |
| Prefijo de modelos | (dejar vacio) |

### Modelos disponibles

Una vez configurada la conexion, los siguientes modelos apareceran en el selector de Open WebUI:

| Modelo | Perfil | Modelo real | Nodo GPU | Uso recomendado |
|---|---|---|---|---|
| `ailab-router/auto` | Routing automatico | Segun ruta | RX9070 (.50) | Chat general |
| `ailab-router/fast` | chat | qwen2.5-coder-14b | RX9070 (.50) | Respuestas rapidas |
| `ailab-router/coding` | coding | qwen2.5-coder-14b | RX9070 (.50) | Codigo, debugging |
| `ailab-router/reasoning` | analysis | qwen2.5-coder-32b | RX9070 (.50) | Arquitectura, analisis |
| `ailab-router/auto` + tools | agent | qwen3.6-27b | RX9070 (.50) | Herramientas, tool_use |

### Rutas adicionales (gestion interna del router)

| Ruta | Perfil | Modelo | Uso |
|------|--------|--------|-----|
| minimal/casual/greeting | observe | llama-3.1-8b | Saludos, preguntas simples |
| observe | observe | llama-3.1-8b | Observacion ligera |
| general | chat | qwen2.5-14b | Conversacion general |

## Routing Interno

Cuando Open WebUI envia una peticion al Router API, este:

1. Clasifica la intencion (greeting, casual, report, observe, tool, general)
2. Asigna un perfil cognitivo via `manifest_profiles.json`
3. Aplica politica de herramientas via `manifest_tools.json` (disabled/readonly/agentic)
4. Aplica politica de memoria via `manifest_memory.json` (minimal/light/full)
5. Selecciona el modelo segun el perfil
6. Sanitiza la respuesta y mantiene compatibilidad con el formato OpenAI/SSE

## Arquitectura

```text
Open WebUI (:3000)
    |
    | POST /v1/chat/completions
    v
Router API (:8083)
    |
    | perfil cognitivo + politica de herramientas + politica de memoria
    v
Gateway (:8008)
    |
    | seleccion de modelo + confirmation gate (428)
    v
LM Studio (:1234)
    |
    | GPU Node
    v
RX9070 (llama-3.1-8b / qwen2.5-14b / qwen2.5-32b / qwen3.6-27b)
```

## Comportamiento de herramientas

- Rutas sin tools (minimal/casual/greeting/observe/chat/coding): tools eliminadas por politica `disabled`
- Coding con tools: `readonly_policy` — solo read, glob, grep, list, webfetch
- Tool_use: `agent_policy` — tools completas con confirmation gate 428 para write

## Troubleshooting

### Error: "Fallo al conectar al servidor de herramientas"

Configurar como **Conexion OpenAI** normal, no como Servidor de Herramientas.

### Respuestas con HARD_FACTS inesperado

Usar `ailab-router/fast` o `ailab-router/coding`. Las rutas ligeras no usan HARD_FACTS.

### Tool calls no funcionan

Asegurar que el modelo `ailab-router/auto` con `tool_choice=auto` y `tools` en el payload activa el perfil `agent`.

### No aparecen los modelos en el selector

1. Verificar que el Router API esta activo: `curl http://localhost:8083/health`
2. Verificar CORS: `curl -I -X OPTIONS -H 'Origin: http://192.168.1.30:3000' http://localhost:8083/v1/models`
3. Refrescar Open WebUI (F5 o limpiar cache del navegador)
