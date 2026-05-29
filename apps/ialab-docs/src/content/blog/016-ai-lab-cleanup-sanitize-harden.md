---
title: "AI-LAB operaciones - limpieza de servicios, saneamiento de secretos y hardening del Live API"
date: "2026-05-29"
summary: "AI-LAB completa una ronda operativa mayor - eliminacion de servicios systemd, saneamiento de secretos, formalizacion del Live API y storage auxiliar."
tags:
  - ai-lab
  - systemd
  - security
  - operations
  - hardening
  - live-api
---
# Content placeholder - full body will be completed later
# AI-LAB operaciones - limpieza de servicios, saneamiento de secretos y hardening del Live API

## Introduccion

Esta entrada documenta la ronda operativa mas reciente del AI-LAB, centrada en higiene de sistema, saneamiento de seguridad y formalizacion de servicios.

## Hallazgo critico: contrasena sudo expuesta

La contrasena sudo del usuario albert estaba incrustada en comandos de rollback en 6 archivos del repositorio, incluyendo runbooks publicados en Astro. La correccion reemplazo los comandos inseguros por sudo directo y se sano el commit via amend.

## Duplicados systemd eliminados

Dos servicios zombies fueron eliminados: ialab-router-api.service (crash loop en puerto 8008) e ialab-docs.service (modo dev duplicado). Ambos con backup en almacenamiento auxiliar.

## Live API formalizado

El Live API en puerto 8084 ya estaba gestionado por systemd desde el arranque. Se validaron sus endpoints, se creo backup y documentacion.

## Storage auxiliar

Se creo /mnt/ai-models/ai-lab con estructura de directorios para logs, backups, snapshots, staging y cache, con politicas de retencion y ownership definidos.

## Estado de servicios

Gateway 8008, Router 8083, MCP 8091, Live API 8084, Docs 4322, Metrics 3010 - todos activos. 0 failed units.

## Known issues

- Live API bind en 0.0.0.0 (pendiente de refactor Traefik)
- /api/history devuelve 404
- openai_gateway.py monolitico (~5700 lineas)
- LM Studio apagado voluntariamente
