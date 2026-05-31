---
title: "Operational Truth vs Discoverable Models"
date: "2026-05-23"
summary: "El error más común en runtimes locales: tratar discovery como operational. Cómo AI-LAB separa active/loaded/discoverable/disabled y evita ctx:0 como operational."
tags:
  - ai-lab
  - operational-truth
  - authority
  - governance
---


Que un modelo aparezca en `/v1/models` no significa que sea operativo.

## La separación que importa

- **active**: usado por el runtime.
- **loaded**: cargado en backend.
- **discoverable**: inventario.
- **disabled**: explícitamente fuera de routing.

## Pitfall: ctx:0

Algunos backends exponen artefactos o entradas de inventario. Si el runtime las trata como “operational”, los reportes mienten.

## La regla

Discovery es aditivo, no autoritativo.

La autoridad viene de evidencia (Prometheus + freshness). Si falta evidencia: `NO DISPONIBLE`.
