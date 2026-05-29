---
title: "Operacion diaria AI-LAB"
summary: "Checklist basico para comprobar que el laboratorio esta operativo."
severity: "info"
---

Checklist basico para validar el estado del laboratorio.

## 1. Comprobar servicios systemd

```bash
systemctl status ailab-router.service --no-pager
systemctl status ailab-docs.service --no-pager
```

> **Nota:** `ialab-router-api` y `ialab-docs` fueron eliminados como unidades duplicadas/remanentes.
> `ialab-live-state` nunca fue instalado como unidad systemd; el proceso `live_api.py` (puerto 8084)
> esta actualmente detectado sin unit instalado, pendiente de fase propia.

## 2. Tabla de puertos

| Servicio | Puerto | Notas |
|----------|--------|-------|
| Gateway | 8008 | ailab-gateway.service |
| Router | 8083 | ailab-router.service |
| MCP | 8091 | ailab-mcp-semantic-gateway.service |
| Metrics | 3010 | ailab-metrics.service |
| Docs | 4322 | ailab-docs.service (astro preview) |
| Live API | 8084 | live_api.py - proceso actualmente detectado sin unit instalado, pendiente de fase propia |

## 3. Health check

```bash
curl -s http://127.0.0.1:8008/health
curl -s http://127.0.0.1:8083/health
```
