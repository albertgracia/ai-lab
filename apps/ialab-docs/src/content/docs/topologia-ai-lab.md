---
title: "Topología AI-LAB"
summary: "Diagrama de alto nivel del flujo OpenCode, router y nodos GPU."
order: 2
---

# Topología AI-LAB

```mermaid
flowchart LR
    User[Usuario / OpenCode] --> Router[AI-LAB Router API]

    Router --> RX9070[Gaming PC RX9070XT]
    Router --> RX7900[Gaming PC RX7900XT]

    RX9070 --> LM1[LM Studio]
    RX7900 --> LM2[LM Studio]

    Router --> Docker[Docker Stack]

    Docker --> Traefik[Traefik]
    Docker --> Qdrant[Qdrant]
    Docker --> WebUI[Open WebUI]
eof
