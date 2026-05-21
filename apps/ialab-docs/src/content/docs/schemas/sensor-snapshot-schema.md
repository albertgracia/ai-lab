---
title: "Sensor Snapshot Schema"
summary: "Esquema de sensor_snapshot con contrato 30I-D: topología, confidence, source_quality y summaries GPU compactos."
order: 31
---

## Campos

- `sensor_contract_version`
- `topology_mode`
- `observed_sources`
- `missing_sources`
- `stale_sources`
- `expected_offline_targets`
- `unexpected_down_targets`
- `domain_confidence`
- `source_quality`
- `context_size_bytes`
- `gpu_operational_summaries`

## Regla

El snapshot no debe convertirse en flood de métricas raw.
