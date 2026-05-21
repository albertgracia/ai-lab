---
title: "Sensor Domains"
summary: "Catálogo de dominios observados por sensor fusion: prioridad, confianza, evidence level y efecto operacional de cada dominio."
order: 23
---

## Dominios

### Críticos
- `gateway`
- `router`
- `gpu_nodes`

### Importantes
- `control_plane`
- `live_api`
- `containers`
- `docker`
- `system_node`
- `smartctl`
- `lmstudio_models`

### Auxiliares
- `windows_exporters`
- `unifi`
- `cloudflare_tunnel`

## Principio

Un fallo auxiliar no debe degradar una confianza crítica. Por eso 30I usa confidence per-domain.
