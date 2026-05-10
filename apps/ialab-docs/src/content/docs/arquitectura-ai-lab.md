---
title: "Arquitectura AI-LAB"
summary: "Topología actual del laboratorio, nodos, servicios y flujo de inferencia."
order: 1
---

# Arquitectura AI-LAB

AI-LAB es una infraestructura local de inferencia IA distribuida.

## Nodos

- Nodo principal Linux: `ubuntu-ialab`
- IP principal: `192.168.1.30`
- Nodo GPU RX9070XT: `192.168.1.50`
- Nodo GPU RX7900XT: `192.168.1.60`

## Servicios

- Traefik
- Qdrant
- Open WebUI
- Ollama
- Portainer

## Objetivo

Construir una plataforma cognitiva local con routing, grounding, documentación viva y orquestación de modelos.
