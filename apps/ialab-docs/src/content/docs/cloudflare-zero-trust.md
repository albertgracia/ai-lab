---
title: "Cloudflare Zero Trust"
summary: "Publicación segura del AI-LAB mediante Cloudflare Access y Tunnel."
order: 13
---

# Cloudflare Zero Trust

## Objetivo

Publicar AI-LAB hacia Internet sin abrir puertos entrantes en el homelab.

## Arquitectura

```text
Usuario
↓
Cloudflare Access
↓
Cloudflare Tunnel
↓
Traefik
↓
Astro Portal / APIs / Servicios
