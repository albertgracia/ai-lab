---
title: "Operator Intent Reasoning (36C)"
summary: "Clasificación determinista de intención operativa como metadata: evita sobreclasificación, no ejecuta acciones y no eleva verdad operacional sin autoridad."
order: 22
---

# Operator Intent Reasoning (36C)

36C introduce una capa ligera para identificar **qué tipo de respuesta operativa** es segura para una petición, sin ejecutar ni autorizar cambios.

## Contrato

- `contract_version`: `36C`
- Campo en payload (gateway): `_operator_intent`
- Categorías: `FAST_*`, `DIAGNOSTIC`, `FORENSIC_ANALYSIS`, `ARCHITECTURAL_REASONING`, `MIXED_INTENT`, `AMBIGUOUS`, `UNKNOWN`, etc.

## Pipeline

```mermaid
flowchart TD
  U[User text] --> N[Normalize + term matching]
  N --> S[Score intent categories]
  S --> C[Select category\n(ambiguous/mixed rules)]
  C --> SAF[Safety envelope\nNO_EXECUTION / NO_MUTATION]
  SAF --> OUT[_operator_intent dict]
  OUT --> G[Gateway inject_agent_context]
```

## Garantías de seguridad

- `can_execute=false`
- `execution_authority=none`
- `infrastructure_mutation_authority=none`
- `remediation_authority=discussion_only` (cuando aplica)

## Explainability

Incluye:

- `reason_codes`
- `matched_terms`
- `degraded` (metadata cuando faltan snapshots authority/precision)

## Anti-drift

- No eleva “discoverable” a “operational”.
- No infiere verdad operacional sin autoridad.
- No sintetiza remediation autónoma.
