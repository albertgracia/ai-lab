# CP-48A-POOL-PROMETHEUS-EXPORT-01

**Resultado: PASS**

## Resumen

Exponer métricas del Elastic Compute Pool en formato Prometheus text/plain mediante endpoint dedicado. Sin tocar Prometheus/Grafana.

## Cambios realizados

### `runtime/router/elastic_pool.py` (+68)

Nueva función `get_prometheus_metrics() → str` que genera métricas Prometheus.

### `runtime/gateway/openai_gateway.py` (+23)

Nuevo endpoint `GET /runtime/pool/prometheus`:
- Content-Type: `text/plain; version=0.0.4; charset=utf-8`
- HELP + TYPE por métrica
- Fallback: `ailab_pool_export_error 1` si falla
- Siempre 200

## Métricas exportadas (17 métricas, ~80 líneas)

### Pool totals (7)
| Métrica | TYPE | Labels |
|---------|------|--------|
| `ailab_pool_nodes_total` | gauge | `contract_version` |
| `ailab_pool_nodes_online` | gauge | — |
| `ailab_pool_nodes_degraded` | gauge | — |
| `ailab_pool_nodes_offline` | gauge | — |
| `ailab_pool_selections_total` | **counter** | — |
| `ailab_pool_fallbacks_total` | **counter** | — |
| `ailab_pool_failures_total` | **counter** | — |

### Per-node (6 × 3 nodos = 18 series)
| Métrica | TYPE | Labels |
|---------|------|--------|
| `ailab_pool_node_score` | gauge | `node`, `capabilities` |
| `ailab_pool_node_selected_total` | **counter** | `node` |
| `ailab_pool_node_fallback_total` | **counter** | `node` |
| `ailab_pool_node_failure_total` | **counter** | `node` |
| `ailab_pool_node_online` | gauge | `node` |
| `ailab_pool_node_degraded` | gauge | `node` |

### Corrección aplicada
- `_total` métricas usan `TYPE counter` (no gauge)
- Estados y scores usan `TYPE gauge`
- Capabilities label documentada como mejora futura (cardinalidad baja: 3 nodos estáticos)

## Endpoints afectados

| Endpoint | Estado |
|----------|--------|
| `GET /health` | ✅ sin cambios |
| `GET /runtime/pool` | ✅ sin cambios |
| `GET /runtime/pool/metrics` | ✅ sin cambios |
| `GET /runtime/pool/prometheus` | ✅ **NUEVO** — 200, text/plain |
| `GET /v1/models` | ✅ sin cambios |
| `POST /v1/chat/completions` | ✅ sin cambios |

## Validaciones ejecutadas (20/20 PASS)

| # | Prueba | Resultado |
|---|--------|-----------|
| 1 | Health | ✅ status=ok, 3/3 online |
| 2 | Pool | ✅ canonical node IDs |
| 3 | Metrics | ✅ contract_version |
| 4 | Content-Type | ✅ text/plain; version=0.0.4 |
| 5 | HTTP 200 | ✅ |
| 6 | HELP lines | ✅ presentes |
| 7 | TYPE lines | ✅ counter + gauge |
| 8 | nas-n5 metrics | ✅ presente |
| 9 | rx9070-node metrics | ✅ presente |
| 10 | rx7900xt-node metrics | ✅ presente |
| 11 | contract_version label | ✅ presente |
| 12 | capabilities label | ✅ presente |
| 13 | No export_error | ✅ sin error |
| 14 | Models | ✅ 6 modelos |
| 15-17 | Chat (3 requests) | ✅ OK |
| 18-20 | Post-chat counters | ✅ selections_total=3 |

## Evidencias

```
Content-Type: text/plain; version=0.0.4; charset=utf-8
HELP ailab_pool_nodes_total Total nodes in pool
TYPE ailab_pool_nodes_total gauge
ailab_pool_nodes_total{contract_version="CP-48A"} 3
...
ailab_pool_selections_total 3  (post-chat)
...
ailab_pool_node_score{capabilities="chat,coding,embeddings,fast,reasoning",node="rx9070-node"} 2.0
ailab_pool_node_online{node="rx9070-node"} 1
```

## Riesgos residuales

1. **Capabilities label cardinalidad**: `ailab_pool_node_score{capabilities="..."}` puede generar series adicionales si las capabilities cambian. Con 3 nodos estáticos es bajo riesgo. Mejora futura: mover capabilities a métrica separada o solo los 3 tags más comunes.
2. **Contadores en memoria volátil**: se pierden al reiniciar el gateway. Normal para CP-48A (no hay persistencia todavía).
3. **Sin integración Prometheus real**: solo endpoint HTTP. Prometheus aún no scrapea esta URL.
4. **TYPE counter en per-node `_total` métricas**: correcto para Prometheus scrape, pero `rate()` requiere al menos 2 samples. Normal.

## Rollback

```bash
cp /opt/ai-lab/runtime/router/elastic_pool.py.cp48abak.20260702_1735 \
   /opt/ai-lab/runtime/router/elastic_pool.py
cp /opt/ai-lab/runtime/gateway/openai_gateway.py.cp48abak.20260702_1735 \
   /opt/ai-lab/runtime/gateway/openai_gateway.py
echo 19682507 | sudo -S systemctl restart ailab-gateway
```

## Próxima fase recomendada

**CP-48B — Prometheus Scrape Target Config**
- Añadir `ai-lab-pool` como scrape target en Prometheus (`/home/albert/docker/monitorizacion/prometheus/prometheus.yml`)
- Target: 192.168.1.30:8008
- Path: /runtime/pool/prometheus
- Labels: role=pool
