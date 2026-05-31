---
title: "Qdrant Memory Layer"
summary: "Colecciones reales en Qdrant y su rol en AI-LAB: operational recall, incident recall, knowledge, snapshots y governance."
order: 7
---


Qdrant es la capa de memoria persistente del runtime. Se usa para retrieval semántico y para retener señales operacionales a través de reinicios.

## Colecciones reales (observadas)

Colecciones detectadas en `GET http://127.0.0.1:6333/collections`:

- `agent_knowledge`
- `ai_lab_memory`
- `cognitive_history`
- `incidents`
- `optimizer_history`
- `routing_history`
- `runtime_snapshots`
- `working_memory`

## Roles

- **Operational recall**: `routing_history`, `runtime_snapshots`, `working_memory`.
- **Cognitive history**: `cognitive_history`.
- **Incidents**: `incidents`.
- **Optimizer**: `optimizer_history`.
- **Knowledge**: `agent_knowledge`.
- **General memory bucket**: `ai_lab_memory`.

## Integración (pipeline)

```mermaid
flowchart TD
  E[Runtime events\n(routing/incidents/snapshots)] --> EM[nomic-embed embeddings\nLM Studio]
  EM --> Q[Qdrant :6333\ncollections]
  Q --> RECALL[Controlled recall\n(policy: minimal/light/full)]
  RECALL --> G[Gateway response\n(evidence-bound)]
```

## Governance

- La memoria no eleva inventario a operational.
- La memoria no reemplaza Prometheus como autoridad.
- La memoria puede estar deshabilitada por perfil o por política.

## Estado: implemented vs experimental vs planned

- Implemented: colecciones operacionales (`routing_history`, `cognitive_history`, `incidents`, `optimizer_history`, `runtime_snapshots`, `working_memory`).
- Implemented (knowledge): `agent_knowledge`.
- Experimental/legacy bucket: `ai_lab_memory` (útil como contenedor general, pero debe gobernarse para evitar contaminación).
- Planned: “remediation memory” (no implementado como autoridad de ejecución).
