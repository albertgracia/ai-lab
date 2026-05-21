---
title: "Phase 30I Burn-in"
summary: "Burn-in de 30I/30I-B: validación de sensor fusion con datos reales, dominio GPU, expected_offline y comportamiento del endpoint /runtime/sensors."
order: 27
---

## Qué se validó

- endpoint `/runtime/sensors`
- RX9070 online
- RX7900XT expected_offline
- separación observed/derived
- confidence per-domain
- tests ampliados en 30I-B

## Resultado

El burn-in confirmó que el runtime ya podía usar observabilidad como base de contexto cognitivo, no solo como telemetría externa.
