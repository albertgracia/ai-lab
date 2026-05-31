---
title: "Event Bus — Sistema de Eventos Cognitivos"
summary: "Arquitectura del bus de eventos SSE del AI-LAB para streaming de metricas y eventos del runtime."
order: 2
---


## Descripcion

El Event Bus es el sistema de eventos en tiempo real del AI-LAB. Permite que
los componentes del runtime emitan eventos estructurados y que los visualizadores
los consuman via Server-Sent Events (SSE).

## Modulo: `runtime/event_bus.py`

### Tipos de Eventos

| Evento | Descripcion | Datos asociados |
|---|---|---|
| `node_online` | Nodo GPU conectado | host, modelo, latencia |
| `node_offline` | Nodo GPU desconectado | host, error |
| `model_selected` | Modelo elegido para tarea | modelo, nodo, tarea, latencia |
| `request_started` | Peticion entrante al gateway | modelo, tarea, timestamp |
| `request_finished` | Peticion completada | modelo, tokens, latencia |
| `agent_invoked` | Agente del Antigravity Kit llamado | agente, tarea, modo |
| `session_created` | Nueva sesion de inferencia | session_id, modelo, nodo |
| `routing_decision` | Decision de ruteo | tarea, nodo origen, nodo destino |
| `gpu_overheat` | Temperatura GPU critica | gpu, temp_actual, umbral |
| `snapshot` | Estado completo del cluster (inicial SSE) | topologia, docker, gpu |
| `heartbeat` | Latido cada 3s | gpu, topologia, timestamp |

### API

```python
from runtime.event_bus import emit, get_history, get_stats

emit("node_online", {"host": "192.168.1.50", "latency_ms": 3})

# Obtener historial
events = get_history(limit=50)

# Estadisticas
stats = get_stats()
# {"total_events": 150, "active_listeners": 2, "event_types": {...}}
```

### Arquitectura

```
Componentes del Runtime
    │
    ├── Gateway → emit("request_started", data)
    ├── Router  → emit("routing_decision", data)
    ├── Event Bus (buffer 200 eventos)
    │       │
    │       ├── SSE endpoint → clientes web
    │       └── Historia → GET /api/events/history
    │
    └── Listeners (callbacks suscritos)
```

### Endpoints

| Endpoint | Metodo | Formato | Descripcion |
|---|---|---|---|
| `/api/events` | GET | SSE | Stream continuo de eventos |
| `/api/events/history` | GET | JSON | Ultimos 100 eventos + stats |
| `/api/status.json` | GET | JSON | Snapshot completo del cluster |
| `/api/topology` | GET | JSON | Nodos y aristas de la topologia |
