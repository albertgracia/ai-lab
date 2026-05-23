---
title: "Arquitectura AI-LAB"
summary: "Arquitectura real actual: nodos, servicios runtime, truth layers (authority/operational/structural) y dominios cognitivos."
order: 1
---

AI-LAB es un runtime local de inferencia con **gobernanza**, **observabilidad**, **capas de verdad** y **routing determinista**.

## Nodos

- Control plane (Linux): `ubuntu-ialab` (`192.168.1.30`)
- Backend inferencia GPU activo: RX9070 (`192.168.1.50:1234`)
- Backend inventariado/offline esperado: RX7900XT (`192.168.1.60:1234`) — **expected_offline / inventory**

## Servicios

- `ailab-gateway` (`:8008`) — único entrypoint OpenAI-compatible de chat.
- `ailab-router` (`:8083`) — API interna (status/perfiles/replay), no entrypoint de chat en producción.
- `ailab-live-api` (`:8084`) — estado vivo, embeddings y endpoints internos.
- `ailab-docs` (`:4322`) — documentación Astro (privado).
- `ailab-metrics` (`:3010`) — dashboard SSR (público).

Servicios de infraestructura (no core del runtime) como reverse proxy, UI externas o stacks docker pueden existir, pero no se consideran “arquitectura runtime” salvo que estén en el flujo de autoridad/evidencia.

## Capas de Verdad

- **Prometheus (Authority)**: métricas raw, targets, alertas.
- **OperationalTruth**: interpretación semántica (sensor fusion, topology/maturity, confidence).
- **GitNexus (Structural)**: verdad estructural grounded de la codebase (blast radius, coupling, drift).

## Objetivo

Construir una plataforma de inferencia local **stabilization-first** y **governance-first**, donde:

- el runtime no afirma lo que no observa,
- discovery no implica operational,
- la cognición estructural no reemplaza autoridad,
- y las decisiones son deterministas, visibles y verificables.
