---
title: "AI-LAB v1 RC - Native Tool Calls + Tool Fastpath Stable"
summary: "Punto de control del runtime: native tool calls y fastpath tool-aware estabilizados en router y gateway."
order: 32
---

## Estado

Hito alcanzado.

## Evidencia

- `qwen/qwen3.6-27b` detectado en `rx9070`
- `tool_use` priorizado por routing
- `tool_calls` estructurado en router y gateway
- latencia estable alrededor de `~3s` en produccion local
- saludos triviales respondidos sin `HARD_FACTS`
- comandos peligrosos bloqueados por policy
- saludos triviales dominan aun con `tools` implicitas
- bloques `<system-reminder>` sanitizados en entrada y salida

## Comparacion

| Modo | Latencia |
|---|---:|
| `tool_use` test | `~3.0s` |
| `tool_use` produccion local | `~3.0s` |
| `normal` produccion local | `~22-38s` |

## Conclusión

El fastpath de herramientas ya es estable y el control de version puede considerarse cerrado.
