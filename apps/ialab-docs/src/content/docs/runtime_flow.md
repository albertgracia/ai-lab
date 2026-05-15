 cat /opt/ai-lab/apps/ialab-docs/src/content/docs/topology_layer.md
[?2004l
]3008;start=51fa343f-1d42-4401-b386-794e9a2d665d;machineid=20aaf5bfa7584e8fb6c0264046eebecd;user=albert;hostname=ubuntu-ialab;bootid=1fc818c4-677f-4c57-b21b-3a4b2a5c6134;pid=00000000000000061390;type=command;cwd=/home/albert\---
title: "Topology Layer — Mapa Vivo del Cluster"
summary: "Capa de topologia interactiva del AI-LAB: nodos, conexiones, estados en tiempo real."
order: 4
---



## Descripcion

La capa de topologia proporciona un mapa vivo del cluster AI-LAB mostrando
todos los nodos (GPU, servicios, componentes) y sus conexiones, con estado
online/offline en tiempo real.

## Fuente de Datos: `GET /api/topology`

### Formato de Respuesta

```json
{
  "nodes": [
    {
      "id": "rx9070-node",
      "title": "RX9070",
      "subtitle": "192.168.1.50",
      "mainstat": "3ms",
      "secondarystat": "5 models",
      "arc__online": 1,
      "arc__offline": 0
    },
    {
      "id": "gateway",
      "title": "Gateway AI-LAB",
      "subtitle": ":8008 | OpenAI API",
      "mainstat": "OK",
      "secondarystat": "1.30",
      "arc__online": 1,
      "arc__offline": 0
    }
  ],
  "edges": [
    {
      "id": "gateway-rx9070-node",
      "source": "gateway",
      "target": "rx9070-node",
      "mainstat": "3ms",
      "secondarystat": "RTT"
    }
  ]
}
```

### Nodos Virtuales

| Nodo | Descripcion | Subtitulo |
|---|---|---|
| `gateway` | Gateway AI-LAB | :8008 \| OpenAI API |
| `event-bus` | Event Bus | Cognitivo |
| `episodic-memory` | Episodic Memory | JSONL Store |

### Nodos Dinamicos (desde cluster_state.json)

Se generan automaticamente a partir del estado actual del cluster,
incluyendo latencia, modelos disponibles y estado online/offline.

## Componente: `TopologyGraph.astro`

Renderiza la topologia como texto estructurado con colores:

```
     AI-LAB CLUSTER TOPOLOGY
     ======================

  ● RX9070 (3ms)
  ○ RX7900XT (OFFLINE)
  ● Gateway AI-LAB (OK)
  ● Event Bus (OK)
  ● Episodic Memory (OK)

  gateway -> RX9070: 3ms
  gateway -> RX7900XT: OFFLINE
  gateway -> event-bus: active
  event-bus -> episodic-memory: recording
```

### Cytoscape.js

Cytoscape.js esta instalado en el proyecto Astro para una futura migracion
a un grafo interactivo con las siguientes capacidades:

- Nodos coloreados por estado (verde online, rojo offline)
- Aristas con etiquetas de latencia
- Layout breadfirst (jerarquico)
- Tooltips con metricas al hacer hover
- Actualizacion en tiempo real via SSE

## Paginas

| Pagina | Ruta | Componente |
|---|---|---|
| Topologia Publica | `/status/topology` | TopologyGraph |
| Estado Vivo | `/status/live` | ClusterHealth + EventStream |

## Plan de Migracion a Cytoscape

1. Implementar renderizado Cytoscape en TopologyGraph.tsx
2. Conectar a SSE para actualizacion en vivo
3. Anadir colores degradados (amarillo = degraded)
4. Anadir tooltips con metricas al hover
5. Pagina privada `/ops/topology` con detalle ampliado
]3008;end=51fa343f-1d42-4401-b386-794e9a2d665d;exit=success\]3008;start=da4295b8-58a2-4b7b-beb8-e909d3b51b99;machineid=20aaf5bfa7584e8fb6c0264046eebecd;user=albert;hostname=ubuntu-ialab;bootid=1fc818c4-677f-4c57-b21b-3a4b2a5c6134;pid=00000000000000061390;type=shell;cwd=/home/albert\[?2004h]0;albert@ubuntu-ialab: ~[01;32malbert@ubuntu-ialab[00m:[01;34m~[00m