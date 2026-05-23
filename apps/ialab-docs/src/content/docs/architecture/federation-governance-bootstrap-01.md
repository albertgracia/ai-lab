---
title: "Federation Governance Bootstrap (01)"
summary: "Transición de runtime monolítico a federación cognitiva operacional basada en bounded contexts: registry + contracts + aislamiento de agentes."
order: 9
---

# Federation Governance Bootstrap (01)

Objetivo: preparar federación sin romper runtime actual.

## Core rule

- Runtime core orquesta.
- Runtime core **no** razona globalmente.

## Componentes nuevos (metadata-only)

- `runtime/domain_registry/` — dominios oficiales + allowed/forbidden deps.
- `runtime/contracts/` — contracts-first governance (IO expectations).
- `runtime/federation/` — capa de aislamiento para futura federación multiagente.

## Anti-singularity doctrine

```mermaid
flowchart TD
  CORE[Gateway/Core Orchestrator] -->|contracts| D1[Domain: authority]
  CORE -->|contracts| D2[Domain: observability]
  CORE -->|contracts| D3[Domain: precision]
  CORE -->|contracts| D4[Domain: incidents]
  CORE -->|contracts| D5[Domain: codebase (GitNexus)]
  CORE -->|contracts| D6[Domain: operator_intent]

  D1 -. forbidden .-> R[routing]
  D2 -. forbidden .-> OT[operational truth override]
  D6 -. forbidden .-> EX[execution/remediation]
```

## Agent isolation

La capa `.agent/agents/*.md` define restricciones por dominio:

- propósito
- ownership
- imports permitidos
- coupling prohibido
- evidence policy

Esto reduce carga cognitiva y evita “god agents” en el core.
