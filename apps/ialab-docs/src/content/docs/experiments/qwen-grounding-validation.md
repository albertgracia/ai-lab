---
title: "Qwen Grounding Validation"
summary: "Validación de grounding operacional de qwen sobre OBSERVED_RUNTIME y contratos 30I/30I-D, incluyendo rechazo de infraestructura no observada."
order: 28
---

## Casos principales

- estado GPU RX9070
- estado GPU RX7900XT
- detección correcta de `expected_offline`
- rechazo de NVIDIA A100 no observada

## Resultado

Qwen ya puede razonar sobre el runtime observacional, aunque aún pueden quedar ajustes de presentación compacta en respuestas cortas.
