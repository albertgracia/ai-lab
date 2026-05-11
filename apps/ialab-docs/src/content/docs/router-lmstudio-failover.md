---
title: "Router LM Studio Failover"
summary: "Tarea pendiente para mejorar el failover inteligente entre nodos LM Studio."
order: 12
---

# Router LM Studio Failover

## Objetivo

OpenCode no debe depender de un nodo LM Studio fijo.

Debe llamar siempre al AI-LAB Router:

```text
http://192.168.1.30:8008/v1/chat/completions
