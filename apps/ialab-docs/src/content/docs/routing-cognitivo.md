---
title: "Routing Cognitivo"
summary: "Routing determinista del runtime AI-LAB: route families, perfiles, fastpath, autoridad/precisión y reglas de escalación."
order: 6
---

El routing del runtime AI-LAB es **determinista**: el LLM no decide qué ruta o modelo se usa.

Su función es seleccionar **route family** y aplicar perfiles/guards para:

- elegir modelo (según intención y políticas)
- decidir si aplica fastpath
- aplicar profiles (tokens/temp/tools/memory)
- aplicar evidence/grounding y governance
- mantener separación active/loaded/discoverable/disabled

---

# Objetivos

## Optimización de inferencia

Seleccionar automáticamente:

- nodo menos cargado
- GPU óptima
- modelo adecuado
- tamaño de contexto correcto

---

# Flujo (real)

```mermaid
flowchart TD
  U[Usuario] --> G[Gateway :8008]
  G --> C[Classifier\n(route family + reasons)]

  C -->|saludos / lightweight| MIN[minimal/observe\nllama-3.1-8b]
  C -->|coding / architecture / report| HEAVY[report/coding\nqwen2.5-coder-14b]
  C -->|operational intent + tools| FP[tool_fastpath\noperational]

  MIN --> LM[LM Studio :1234]
  HEAVY --> LM
  FP --> OT[OperationalTruth\n(sensor fusion)]
  OT --> G
  LM --> G
  G --> U
```

## Reglas clave

- **Fastpath primero**: preguntas operacionales (runtime/GPUs/observabilidad) se responden compacto y evidence-bound.
- **Escalación controlada**: qwen se reserva para intentos con razones explícitas (p.ej. coding/architecture/diagnostic).
- **Authority y precision**: si falta evidencia, se responde `NO DISPONIBLE` o se marca degradación; nunca se inventa infraestructura.
- **Operator intent (36C)**: se adjunta como metadata (`_operator_intent`) para guiar formato/seguridad, sin ejecución.
