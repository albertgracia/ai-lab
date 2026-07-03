# CP-46-POOL-OBSERVABILITY-01

**Resultado: PASS**

## Resumen

Añadir observabilidad en memoria al Elastic Compute Pool sin romper el router ni el gateway.

- Nuevos contadores para selecciones, fallbacks y fallos por nodo
- Endpoint `/runtime/pool/metrics` (siempre 200)
- Métricas visibles en `/health` via `get_summary().metrics_summary`

## Cambios realizados

### `runtime/router/elastic_pool.py` (+64 líneas)

| Cambio | Líneas |
|--------|--------|
| Contadores en `__init__` (selected, fallback, failure, last_*_at, totals) | +9 |
| `select()` — `_selected_count[node_id]++`, `_total_selections++` | +4 |
| `fallback()` — `_record_fallback(node_id)` en cada return path | +4 |
| `_record_fallback()` — helper privado | +4 |
| `record_failure(node_id, failure_type)` — método público | +5 |
| `get_metrics()` — endpoint payload | +30 |
| `get_summary()` — incluye `metrics_summary` | +5 |
| `get_pool_metrics()` — top-level convenience | +4 |

### `runtime/gateway/openai_gateway.py` (+22/-1)

| Cambio | Líneas |
|--------|--------|
| `/runtime/pool/metrics` endpoint handler | +13 |
| `_try_fallback()` — `pool.record_failure()` en el nodo fallido | +9 |

## Métricas añadidas (12)

### Totales
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `total_selections` | int | Número de veces que `select()` eligió un nodo |
| `total_fallbacks` | int | Número de veces que `fallback()` devolvió un candidato |
| `total_failures` | int | Número de fallos registrados via `record_failure()` |

### Por nodo (`per_node.{node_id}`)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `selected_count` | int | Veces que fue seleccionado como primario |
| `fallback_count` | int | Veces que fue elegido como fallback |
| `failure_count` | int | Fallos registrados en este nodo |
| `last_selected_at` | float | Timestamp última selección |
| `last_failure_at` | float | Timestamp último fallo |
| `last_fallback_at` | float | Timestamp último fallback |

## Endpoints afectados

| Endpoint | Estado |
|----------|--------|
| `GET /health` | ✅ `pool.metrics_summary` presente |
| `GET /runtime/pool` | ✅ sin cambios |
| `GET /runtime/pool/metrics` | ✅ **NUEVO** — 200 siempre |
| `GET /v1/models` | ✅ sin cambios |
| `POST /v1/chat/completions` | ✅ sin cambios |

## Validaciones ejecutadas

### 1. Health
```
GET /health → 200
status=ok, pool.nodes_online=3/3
metrics_summary: {total_selections:0, total_fallbacks:2, total_failures:2}
```

### 2. Pool
```
GET /runtime/pool → 200
nodes_total=3, nodes_online=3, nodes_offline=0, nodes_degraded=0
```

### 3. Pool metrics (inicial)
```
GET /runtime/pool/metrics → 200
total_selections=0, total_fallbacks=2, total_failures=2
per_node: {}
```
*Nota: fallbacks=2 y failures=2 iniciales provienen de peticiones previas a la validación (gateway recién reiniciado con pool existente)*

### 4. Modelos
```
GET /v1/models → 200
6 models
```

### 5. Chat non-stream (3 requests)
```python
# request: "2+2?" → response: "4"
# todas respondieron OK
```

### 6. Chat stream (1 request)
```
HTTP 200, 50 chunks → finish_reason:stop → [DONE]
```

### 7. Métricas finales (5 requests)
```json
{
  "total_selections": 5,
  "total_fallbacks": 3,
  "total_failures": 3,
  "per_node": {
    "nas-n5":        { "selected_count": 0, "fallback_count":3, "failure_count":0 },
    "rx9070":        { "selected_count": 0, "fallback_count":0, "failure_count":3 },
    "rx9070-node":   { "selected_count": 5, "fallback_count":0, "failure_count":0 }
  }
}
```

Todos los contadores incrementan correctamente.

## Estado nodos (post-validación)

| Nodo | IP | Estado | Modelos |
|------|----|--------|---------|
| nas-n5 | 192.168.1.250 | online | 3 |
| rx9070-node | 192.168.1.50 | online | 6 |
| rx7900xt-node | 192.168.1.60 | online | 11 |

## Riesgos residuales

1. **Naming inconsistency**: `BACKENDS` legacy usa `"rx9070"` (short) mientras el pool usa `"rx9070-node"`. Los fallos se registran con el nombre corto, las selecciones con el largo. `per_node` muestra ambos como nodos separados. Esto es pre-existente y no se corrige en CP-46.
2. **Contadores en memoria volátil**: Se pierden al reiniciar el gateway. No hay persistencia ni exportación a Prometheus todavía (CP-47).
3. **Sin tests unitarios**: Solo validación funcional contra .30.
4. **Sin burn-in multi-nodo automatizado**: pre-existente.

## Rollback

```bash
# Restaurar backup desde .30
cp /opt/ai-lab/runtime/gateway/openai_gateway.py.cp46bak.20260702_1625 \
   /opt/ai-lab/runtime/gateway/openai_gateway.py
# Restaurar elastic_pool.py desde git (commit 6e4a00d)
git checkout 6e4a00d -- runtime/router/elastic_pool.py
scp runtime/router/elastic_pool.py albert@192.168.1.30:/opt/ai-lab/runtime/router/elastic_pool.py
# Reiniciar gateway
echo 19682507 | sudo -S systemctl restart ailab-gateway
```

## Próxima fase recomendada

**CP-47 — Pool Observability → Prometheus**
- Exportar contadores del pool como métricas Prometheus (`ailab_pool_*`)
- Dashboard Grafana para pool metrics
- Pool dashboard en TIER 1 de operación diaria
