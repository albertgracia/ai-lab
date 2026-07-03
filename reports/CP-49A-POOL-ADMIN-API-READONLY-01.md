# CP-49A — Pool Admin API (Read-Only)

**Fecha:** 2026-07-03
**Estado:** PASS ✅

---

## Endpoints implementados

| # | Endpoint | Método | Descripción | Fuente de datos |
|---|----------|--------|-------------|-----------------|
| 1 | `/runtime/admin/health` | GET | Health check del pool admin | `get_pool_summary()` |
| 2 | `/runtime/admin/pool` | GET | Estado agregado del pool | `get_pool_summary()` + `get_pool_metrics()` |
| 3 | `/runtime/admin/nodes` | GET | Lista detallada de nodos con métricas por nodo | `get_pool_status()` + `get_pool_metrics()` |
| 4 | `/runtime/admin/scoring` | GET | Factores de scoring + baseline scores por nodo | `get_pool().calculate_score()` |
| 5 | `/runtime/admin/contracts` | GET | Versiones de contrato y lista de endpoints | `get_pool_metrics()` |
| 6 | `/runtime/admin/models` | GET | Mapa modelo → nodos donde está disponible | `get_pool_status()` |

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `runtime/gateway/openai_gateway.py` | +181 líneas (6 handlers read-only) |

**No modificados:** `runtime/router/elastic_pool.py`, Prometheus, Grafana, Marketplace, Hermes, GitNexus.

## Condiciones cumplidas

- [x] Solo lectura — todos responden 200, sin POST/PUT/DELETE
- [x] Sin operaciones de escritura (no enable/disable/drain/restart/reload)
- [x] No modifica `elastic_pool.py`
- [x] No cambia algoritmo de selección ni scoring
- [x] No toca Prometheus, Grafana, Marketplace, Hermes, GitNexus
- [x] Formato error: `{"ok": false, "error": "...", "readonly": true}`
- [x] Reutiliza `get_summary()`, `get_status()`, `get_metrics()`, `calculate_score()`

## Validaciones

### Endpoints existentes (siguen funcionando)

| Endpoint | HTTP | Resultado |
|----------|------|-----------|
| `GET /health` | 200 | ✅ PASS |
| `GET /runtime/pool` | 200 | ✅ PASS |
| `GET /runtime/pool/metrics` | 200 | ✅ PASS |
| `GET /runtime/pool/prometheus` | 200 | ✅ PASS |

### Nuevos endpoints CP-49A

| Endpoint | HTTP | `ok` | `readonly` | Resultado |
|----------|------|------|------------|-----------|
| `GET /runtime/admin/health` | 200 | `true` | `true` | ✅ PASS |
| `GET /runtime/admin/pool` | 200 | `true` | `true` | ✅ PASS |
| `GET /runtime/admin/nodes` | 200 | `true` | `true` | ✅ PASS (3 nodos: rx9070, rx7900xt, nas-n5) |
| `GET /runtime/admin/scoring` | 200 | `true` | `true` | ✅ PASS (9 factores, baseline scores) |
| `GET /runtime/admin/contracts` | 200 | `true` | `true` | ✅ PASS (CP-47-NODE-SCORING-01) |
| `GET /runtime/admin/models` | 200 | `true` | `true` | ✅ PASS (0 modelos — backend offline) |

### Chat (backend LM Studio offline — condición pre-existente, no relacionada con CP-49A)

| Prueba | Resultado | Nota |
|--------|-----------|------|
| `GET /v1/models` | 502 | Backend offline — error esperado |
| Chat stream=false | Error | Backend offline — error esperado |
| Chat stream=true | No probado | Backend offline |

> **Nota:** LM Studio en 192.168.1.50 no está disponible (todos los nodos aparecen offline en el pool). Esta condición es pre-existente y no relacionada con CP-49A. Los 6 endpoints admin responden correctamente con datos del node registry incluso con backend offline.

## Backup

- `runtime/gateway/openai_gateway.py.cp49a-bak`

## Despliegue

1. Backup creado localmente y en servidor
2. `scp` al servidor: `/opt/ai-lab/runtime/gateway/openai_gateway.py`
3. `sudo systemctl restart ailab-gateway` → exit code 0
4. Gateway responde en `:8008` correctamente

## Resultado final

**PASS ✅** — CP-49A implementado y desplegado.
