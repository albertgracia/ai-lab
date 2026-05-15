---
title: "SSE Runtime — Streaming de Eventos"
summary: "Implementacion del servidor SSE en la Live API, con ThreadingHTTPServer y conexiones persistentes."
order: 3
---

# SSE Runtime — Streaming de Eventos

## Servidor: `runtime/state/live_api.py`

La Live API sirve como punto de entrada para todos los datos en tiempo real.
Implementa un servidor HTTP multi-thread (`ThreadingHTTPServer`) que permite
multiples conexiones SSE simultaneas sin bloqueo.

### Endpoint SSE: `GET /api/events`

```
Formato: text/event-stream
Cache: no-cache
CORS: Access-Control-Allow-Origin: *

Secuencia:
1. Snapshot inicial (estado completo del cluster)
2. Heartbeats cada 3s con GPU + topologia
```

### Formato del Stream

```
data: {"event": "snapshot", "data": {"topology": {...}, "docker": {...}, "gpu": [...]}}

data: {"event": "heartbeat", "data": {"gpu": [...], "topology": {...}, "ts": 1778849000}}

data: {"event": "node_online", "data": {"host": "192.168.1.50", "latency_ms": 3}}
```

### Consumo desde el Frontend

```javascript
// Native EventSource API
const es = new EventSource("/api/events");

es.onmessage = (msg) => {
  const evt = JSON.parse(msg.data);
  switch (evt.event) {
    case "snapshot":
      renderInitialState(evt.data);
      break;
    case "heartbeat":
      updateMetrics(evt.data);
      break;
    case "node_online":
      markNodeOnline(evt.data.host);
      break;
    case "node_offline":
      markNodeOffline(evt.data.host);
      break;
  }
};

es.onerror = () => {
  showOfflineIndicator();
};
```

### Componentes Consumidores

| Componente | Archivo | Tipo | Fuente |
|---|---|---|---|
| ClusterHealth | `ClusterHealth.astro` | polling `/api/status.json` | Cada 5s |
| EventStream | `EventStream.astro` | SSE `/api/events` | Tiempo real |
| TopologyGraph | `TopologyGraph.astro` | polling `/api/topology` | Cada 5s |
| HomeLiveStats | `HomeLiveStats.astro` | polling `/api/status.json` | Cada 5s |

### ThreadingHTTPServer

El servidor usa `ThreadingHTTPServer` para evitar bloqueos. Cada conexion SSE
se mantiene en un hilo separado. El servidor puede manejar conexiones SSE
simultaneas mientras sigue sirviendo peticiones REST.

```python
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

class APIHandler(BaseHTTPRequestHandler):
    timeout = 10

    def _handle_sse(self):
        # Enviar snapshot inicial
        self.wfile.write(f"data: {json.dumps(snapshot)}\\n\\n".encode())
        self.wfile.flush()

        # Loop de heartbeat
        while True:
            data = {"event": "heartbeat", "data": get_gpu_data()}
            self.wfile.write(f"data: {json.dumps(data)}\\n\\n".encode())
            self.wfile.flush()
            time.sleep(3)
```
