---
title: "GitNexus como observabilidad estructural"
date: "2026-05-23"
summary: "Por qué GitNexus no es solo visualización: es verdad estructural grounded para detectar coupling, singularities, blast radius y drift arquitectónico."
tags:
  - ai-lab
  - gitnexus
  - codebase
  - observability
  - architecture
---

# GitNexus como observabilidad estructural

Prometheus te dice qué está pasando ahora.

GitNexus te dice **cómo está construido** el runtime.

## No es “un grafo bonito”

Usamos GitNexus para:

- analizar blast radius antes de tocar módulos sensibles,
- detectar hotspots y hubs (reverse coupling),
- identificar drift arquitectónico,
- y revisar singularities (puntos de fan-out peligrosos).

## Lección aprendida: backend URL remoto

Si abres la UI desde un PC remoto y ves “Waiting for server to start”, muchas veces la UI está usando `localhost:4747` como backend URL.

Fix: setear `localStorage['gitnexus-backend-url']` a `http://192.168.1.30:4747`.

## Governance

`.gitnexusignore` forma parte de la disciplina: nunca indexar `runtime/state/*`.
