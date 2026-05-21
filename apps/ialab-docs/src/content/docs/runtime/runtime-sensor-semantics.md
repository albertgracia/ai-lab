---
title: "Runtime Sensor Semantics"
summary: "FASE 30I-D: normalización semántica de sensores para alinear /runtime/sensors, OBSERVED_RUNTIME y respuestas LLM sobre un único contrato operacional."
order: 13
---

## Objetivo

30I-D normaliza cómo se expone el estado de sensores para que endpoint, contexto y respuesta cognitiva usen el mismo contrato.

## Contrato 30I-D

Cada summary operacional puede exponer:

- `inventory_state`
- `observed_state`
- `operational_state`
- `source_of_truth`
- `freshness`
- `confidence`
- `last_seen`
- `missing_metrics`
- `derived_state`
- `observed_metrics`
- `evidence_level`

## Reglas

- Todo dato observado se separa del derivado.
- `source_of_truth` aparece en cada summary operacional.
- `freshness` usa `fresh | stale | expired | unavailable`.
- `confidence` se calcula por dominio.
- RX7900XT `expected_offline` no degrada la confianza crítica de `gpu_nodes`.
- No se envían raw metrics masivas al LLM.

## Ejemplo

```json
{
  "gpu_id": "RX9070",
  "inventory_state": "known",
  "observed_state": "online",
  "operational_state": "active",
  "source_of_truth": ["gpu_exporter", "lmstudio_api", "prometheus"],
  "freshness": {"status": "fresh"},
  "confidence": "high",
  "evidence_level": "observed"
}
```

## Alias temporal

`gpu_summary` se mantiene como alias backward compatible, pero el contrato preferido es:

```text
gpu_operational_summaries
```

con:

```json
{
  "deprecated_alias": true,
  "alias_for": "gpu_operational_summaries"
}
```
