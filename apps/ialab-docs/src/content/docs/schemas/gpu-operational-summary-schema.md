---
title: "GPU Operational Summary Schema"
summary: "Contrato semántico de un summary GPU en 30I-D: inventory, observed, operational, metrics, freshness, confidence y evidence level."
order: 32
---

## Campos

- `gpu_id`
- `host`
- `inventory_state`
- `observed_state`
- `operational_state`
- `topology_role`
- `observed_metrics`
- `derived_state`
- `missing_metrics`
- `source_of_truth`
- `freshness`
- `confidence`
- `evidence_level`

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
