---
title: "Topología AI-LAB"
summary: "Diagrama real de alto nivel: clientes, gateway, truth layers, backend de inferencia, observabilidad y cognición estructural."
order: 2
---

```mermaid
flowchart LR
  U[Usuario / OpenCode / OpenWebUI] --> G[Gateway :8008]
  G --> LM[LM Studio :1234\nRX9070]
  G --> FP[FastPath 35D]
  G --> OI[Operator Intent 36C\n_operator_intent]

  subgraph AUTH[Authority]
    PROM[Prometheus :9090] --> GRAF[Grafana :3000]
  end

  PROM --> G

  subgraph OT[OperationalTruth]
    SF[Sensor fusion + topology + maturity]
  end
  PROM --> SF
  SF --> G

  subgraph SC[Structural Cognition]
    GN[GitNexus :4747]\n(codebase truth)
  end
  GN --> G

  Q[Qdrant :6333]\n(memory layer) --> G
  INV[RX7900XT :1234]\nexpected_offline (inventory):::inv
  classDef inv fill:#fff6f6,stroke:#d33,stroke-width:1px;
eof
