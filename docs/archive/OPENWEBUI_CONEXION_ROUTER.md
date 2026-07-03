---
title: "Open WebUI — Conexion al AI-LAB Router"
summary: "Configuracion de Open WebUI para usar el Router API del AI-LAB con enrutamiento capability-aware."
order: 14
---

## Descripcion

Open WebUI es el frontend unificado del AI-LAB. Esta conectado al Router API
(`ailab-router`) para enrutar las peticiones de los usuarios al modelo optimo
segun el tipo de tarea.

## Configuracion de Conexion

### OpenAI Connection

En Open WebUI (Ajustes -> Conexiones), anadir una nueva conexion OpenAI:

| Campo | Valor |
|---|---|
| URL | `http://192.168.1.30:8083/v1` |
| API Key | (dejar vacio) |
| Prefijo de modelos | (dejar vacio) |

### Modelos disponibles

Una vez configurada la conexion, los siguientes modelos apareceran en el
selector de Open WebUI:

| Modelo | Tipo | Nodo GPU | VRAM | Uso recomendado |
|---|---|---|---|---|
| `ailab-router/auto` | Routing automatico | — | — | Seleccion por keyword |
| `ailab-router/fast` | Respuesta rapida | RX9070 (1.50) | 16 GB | Mantenimiento, consultas simples |
| `ailab-router/coding` | Programacion | RX7900XT (1.60) | 20 GB | Codigo, debugging, refactor |
| `ailab-router/reasoning` | Razonamiento | RX7900XT (1.60) | 20 GB | Arquitectura, problemas complejos |

## Routing Interno

Cuando Open WebUI envia una peticion al Router API, este:

1. Analiza la tarea (keyword detection)
2. Selecciona el nodo GPU optimo (capability-aware)
3. Elige el modelo adecuado segun disponibilidad
4. Envia la peticion a LM Studio en el nodo correspondiente
5. Sanitiza la respuesta (elimina `reasoning_content`)
6. Devuelve el streaming SSE a Open WebUI

## Arquitectura

```text
Open WebUI (:3000)
    |
    | POST /v1/chat/completions
    v
Router API (:8083)
    |
    | capability-aware routing
    v
Gateway (:8008)
    |
    | seleccion de modelo
    v
LM Studio (:1234)
    |
    | GPU Node
    v
RX9070 / RX7900XT
```

## Troubleshooting

### Error: "Fallo al conectar al servidor de herramientas"

Este error aparece en Open WebUI al configurar la conexion como "Servidor de
Herramientas". **No es necesario** configurarlo como tal. Solo hay que
configurarlo como **Conexion OpenAI** normal.

### Error: "Error en la respuesta previa"

Ocurre cuando el modelo genera contenido en `reasoning_content` en lugar de
`content`. El Router API sanitiza el stream para evitar este problema.
Si persiste, usar `ailab-router/fast` que utiliza Llama 3.1 8B (modelo sin
razonamiento interno).

### No aparecen los modelos en el selector

1. Verificar que el Router API esta activo: `curl http://localhost:8083/health`
2. Verificar CORS: `curl -I -X OPTIONS -H 'Origin: http://192.168.1.30:3000' http://localhost:8083/v1/models`
3. Refrescar Open WebUI (F5 o limpiar cache del navegador)
