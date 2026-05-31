---
title: "Precision Semantics (36B)"
summary: "Semántica de precisión operacional: partial evidence, conflicts, stale evidence, degradación segura y señales de precisión expuestas por el runtime."
order: 21
---


La precisión operacional no es “exactitud del texto”, sino **integridad de evidencia**.

36B define:

- cómo el runtime marca `partial_state_total`, `authority_conflicts_total`, `stale_evidence_total`
- cuándo una respuesta debe degradarse o limitarse
- cómo evitar “operational drift” cuando falta autoridad

## Flujo de precisión

```mermaid
flowchart TD
  P[Prometheus authority] --> SF[Sensor fusion contract]
  SF --> PR[Precision scoring 36B]
  PR -->|scores + markers| G[Gateway :8008]
  G -->|if partial/conflict| EG[Evidence/Precision guard]
  EG --> R[Respuesta: compacta, con límites\n(NO DISPONIBLE si aplica)]
```

## Señales

- Endpoint: `GET /runtime/precision/score`.
- Indicadores:
  - `operational_precision_score`
  - `partial_state_total`
  - `authority_conflicts_total`
  - `stale_evidence_total`

## Principios

- “Precisión” se degrada de forma **visible**, nunca silenciosa.
- Un marcador de precisión no autoriza remediation ni ejecución.
- La degradación no convierte discovery en operational.
