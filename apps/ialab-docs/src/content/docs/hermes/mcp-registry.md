---
title: "MCP Registry"
summary: "5 servidores MCP declarativos para acceso a herramientas del runtime."
order: 7
---

## Estado: ✅ Implementado

## Servidores

| ID | Estado | Tools | Auth | Prioridad |
|----|--------|-------|------|-----------|
| `gitnexus` | ✅ active | 11 | token | 100 |
| `ailab-runtime-mcp` | ✅ active | 8 | token | 90 |
| `filesystem` | ✅ active | 5 | none | 80 |
| `prometheus` | 📋 planned | 4 (planned) | planned_token | 70 |
| `marketplace-mcp` | 📋 planned | 0 | planned_token | 60 |

## Servidores activos

### GitNexus Code Intelligence

- **ID**: `gitnexus`
- **Protocolo**: MCP estándar
- **Herramientas**: 11 (query, context, impact, detect_changes, route_map, etc.)
- **Auth**: token

### AI-LAB Runtime MCP

- **ID**: `ailab-runtime-mcp`
- **Protocolo**: URL / MCP
- **Herramientas**: 9 (status, health, incidents, SLO, memory search, etc.)
- **Auth**: token

### Filesystem Access

- **ID**: `filesystem`
- **Protocolo**: URL
- **Herramientas**: 5 (lectura de archivos)
- **Auth**: none

## Servidores planificados

### Prometheus Metrics

- **ID**: `prometheus`
- **Estado**: 📋 planned
- **Herramientas**: 4 previstas (query_range, instant_query, series, labels)
- **Activación**: futura

### Marketplace MCP

- **ID**: `marketplace-mcp`
- **Estado**: 📋 planned
- **Activación**: futura

## Registry

El registry YAML en `mcp/registry.yaml` contiene metadatos:

```yaml
servers_total: 5
enabled_servers: 0
enforcement: disabled
activation_status: skeleton_only
mode: declarative_only
```
