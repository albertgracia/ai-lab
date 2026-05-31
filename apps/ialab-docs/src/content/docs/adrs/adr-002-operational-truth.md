---
title: "ADR-002 — Operational Truth"
summary: "Separar discovery/inventory de operational: active/loaded/discoverable/disabled y anti-promoción de ctx:0."
order: 42
---


## Contexto

La fuente `/v1/models` y discovery de modelos produce inventario, no necesariamente estado operativo.

## Problema

- Discovery tratado como operational produce reportes falsos.
- Modelos “ctx:0” o “disabled” pueden aparecer como disponibles.

## Decisión

- Mantener separación estricta entre active/loaded/discoverable/disabled.
- Reportes y fastpath deben declarar explícitamente lo discoverable como “not operational”.

## Consecuencias

- Menos alucinaciones operativas.
- Operación más confiable aunque “más conservadora”.

## Tradeoffs

- A veces se responde `NO DISPONIBLE` si falta authority/freshness.

## Riesgos evitados

- “Discoverable treated as operational”.
- Escalación implícita a modelos no operativos.
