---
title: "AI-LAB v1 RC - Native Tool Calls + Tool Fastpath Stable"
summary: "Runbook de control para validar que tool calls nativas y fastpath tool-aware están estables."
status: stable
category: milestone
date: "2026-05-17"
---

# Control de versión

## Validación

1. `GET /health` en `router`, `gateway` y `docs` devuelve `200`.
2. `tool_use` devuelve `tool_calls` estructurado.
3. `qwen/qwen3.6-27b` queda seleccionado para `tool_use` en `rx9070`.
4. La latencia se mantiene en torno a `~3s`.

## Resultado

Hito alcanzado.
