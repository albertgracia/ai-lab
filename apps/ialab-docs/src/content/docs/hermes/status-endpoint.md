---
title: "Runtime Status Endpoint"
summary: "GET /hermes/status — fuente oficial de observabilidad de Hermes Enterprise."
order: 9
---

## Estado: ✅ Implementado

## Ruta

```
GET /hermes/status
Host: 127.0.0.1:8095
Content-Type: application/json
```

## Descripción

Endpoint HTTP read-only que expone el estado completo de Hermes Enterprise. Reutiliza `runtime.hermes.status` como única fuente de verdad.

## Ejemplo de uso

```bash
python -m runtime.hermes.endpoint 127.0.0.1 8095

# En otra terminal:
curl -s http://127.0.0.1:8095/hermes/status | jq .
```

## Campos de la respuesta

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `service` | string | `"Hermes Enterprise"` |
| `version` | string | Schema version (`"1.0"`) |
| `build` | string | Core checkpoint tag |
| `git` | object | `{head, branch, dirty}` |
| `enterprise` | object | `{core_version, foundation_complete, schema_version, registries_loaded, initialized}` |
| `soul` | object | `{loaded, version, truth_model}` |
| `capabilities` | object | `{total, valid, dependency_graph_ok}` |
| `operators` | object | `{total, valid}` |
| `hooks` | object | `{total, enabled, enforcement}` |
| `mcp` | object | `{total, configured, connected, servers[]}` |
| `governance` | object | `{mode, enforcement_active, anti_flapping, modes[]}` |
| `architecture` | object | `{enterprise_phase, next_phase, readiness, compatibility}` |
| `tests` | object | `{passed, failed}` |
| `status` | object | `{healthy, warnings[], errors[]}` |

## Ejemplo de respuesta real

```json
{
  "service": "Hermes Enterprise",
  "version": "1.0",
  "build": "CP-HERMES-ENTERPRISE-CORE-01",
  "git": {
    "head": "df84882fe26bc7edb668bbc7e8b096f845e50545e",
    "branch": "main",
    "dirty": false
  },
  "enterprise": {
    "core_version": "CP-HERMES-ENTERPRISE-CORE-01",
    "foundation_complete": true,
    "schema_version": "1.0",
    "registries_loaded": true,
    "initialized": true
  },
  "soul": {
    "loaded": true,
    "version": "1.0.0",
    "truth_model": { "truth_levels": { "OBSERVADO": "...", "INFERIDO": "...", "SUPUESTO": "..." } }
  },
  "capabilities": { "total": 6, "valid": true, "dependency_graph_ok": true },
  "operators": { "total": 5, "valid": true },
  "hooks": { "total": 9, "enabled": 0, "enforcement": false },
  "mcp": {
    "total": 5,
    "configured": 5,
    "connected": 3,
    "servers": [
      { "id": "gitnexus", "status": "active", "tools": 11 },
      { "id": "ailab-runtime-mcp", "status": "active", "tools": 8 },
      { "id": "filesystem", "status": "active", "tools": 5 },
      { "id": "prometheus", "status": "planned", "tools": 4 },
      { "id": "marketplace-mcp", "status": "planned", "tools": 0 }
    ]
  },
  "governance": {
    "mode": "NORMAL",
    "enforcement_active": false,
    "anti_flapping": true,
    "modes": ["NORMAL", "ELEVATED", "DEGRADED", "LOCKDOWN"]
  },
  "architecture": {
    "enterprise_phase": "CORE",
    "next_phase": "E08",
    "readiness": "READY",
    "compatibility": {
      "astro": true,
      "marketplace": true,
      "gitnexus": true,
      "mcp": true
    }
  },
  "tests": { "passed": 185, "failed": 0 },
  "status": { "healthy": true, "warnings": [], "errors": [] }
}
```

## Errores posibles

| Código | Condición |
|--------|-----------|
| 200 | Éxito |
| 404 | Ruta no encontrada |

## Health check

```
GET /health
→ {"status": "ok", "service": "hermes-enterprise-status"}
```
