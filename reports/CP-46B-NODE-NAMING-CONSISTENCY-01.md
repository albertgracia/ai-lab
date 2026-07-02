# CP-46B-NODE-NAMING-CONSISTENCY-01

**Resultado: PASS**

## Resumen

Corregir inconsistencia de nombres de nodo: `rx9070` → `rx9070-node` y `rx7900xt` → `rx7900xt-node` en el BACKENDS legacy del gateway.

## Estado inicial

- `BACKENDS` en `openai_gateway.py` usaba `"rx9070"` (short) y `"rx7900xt"` (short)
- `PRIMARY_BACKEND = "rx9070"` (short)
- El pool/node registry usa `"rx9070-node"` y `"rx7900xt-node"` (con sufijo)
- `_try_fallback()` grababa fallos con `current_backend.get("name")` = `"rx9070"` (short)
- `select()` grababa selecciones con `"rx9070-node"` (canónico)
- Resultado: `per_node` mostraba `rx9070` y `rx9070-node` como nodos separados

## Referencias encontradas (87)

| Contexto | Referencias | Acción |
|----------|-------------|--------|
| `runtime/gateway/openai_gateway.py` — BACKENDS | 2 short | **CORREGIDO** a canónico |
| `runtime/gateway/openai_gateway.py` — PRIMARY_BACKEND | 1 short | **CORREGIDO** a canónico |
| `runtime/observability/` — GPU identifiers | ~20 | No tocado (contexto GPU, no pool) |
| `runtime/validation/` — GPU assertions | ~15 | No tocado (contexto GPU) |
| `runtime/governance/` — SLO identifiers | ~8 | No tocado (contexto GPU) |
| `runtime/health/` — GPU state tracking | ~8 | No tocado (contexto GPU) |
| `runtime/gateway/tool_request_classifier.py` — keywords | ~4 | No tocado (keywords NLP, no pool) |
| `runtime/operator_intent/` — intent keywords | ~4 | No tocado (keywords) |
| `runtime/fastpath/` — intent keywords | ~1 | No tocado (keywords) |
| `runtime/llm/router_api.py` — fallback default | 1 | No tocado (router distinto, contexto diferente) |
| `runtime/llm/model_router.py` | 2 | Ya usaba `"rx9070-node"` — correcto |
| `runtime/observability/prometheus_audit.py` | 4 | No tocado (jobs Prometheus, no pool) |

## Cambios realizados

**Archivo:** `runtime/gateway/openai_gateway.py` (3 líneas)

| Línea | Antes | Después |
|-------|-------|---------|
| 625 | `"name": "rx9070"` | `"name": "rx9070-node"` |
| 627 | `"name": "rx7900xt"` | `"name": "rx7900xt-node"` |
| 630 | `PRIMARY_BACKEND = "rx9070"` | `PRIMARY_BACKEND = "rx9070-node"` |

## Validaciones ejecutadas

### 1. Health
```json
{"status": "ok", "pool": {"nodes_online": 3, "nodes_total": 3}}
```

### 2. Pool node IDs
```
['nas-n5', 'rx9070-node', 'rx7900xt-node']
```
✅ Solo canónicos

### 3. Metrics per_node keys (post-chat)
```
['rx9070-node']
```
✅ Solo canónico, sin `rx9070` legacy

### 4. Models
```
6 models
```

### 5. Chat non-stream
```
HTTP 200, "2 + 2 es igual a 4"
```

### 6. Chat stream
```
HTTP 200, 48 chunks, [DONE] termination
```

### 7. Observabilidad GPU no rota
- `runtime/observability/*.py` — sin referencias a BACKENDS/PRIMARY_BACKEND
- Cambio aislado al gateway

## Riesgos residuales

1. `runtime/llm/router_api.py:1042` aún usa `node.get("name", "rx9070")` como fallback default. No causa inconsistencia porque:
   - El fallback se activa solo si node no tiene "name"
   - El router usa su propia lógica de nodos, no BACKENDS del gateway
   - No afecta a las métricas del pool

2. Los contadores se resetearon al reiniciar el gateway (volátiles)

3. `nas-n5` ya era canónico — sin cambios

## Rollback

```bash
# Backup existe en .30
cp /opt/ai-lab/runtime/gateway/openai_gateway.py.cp46bbak.20260702_1650 \
   /opt/ai-lab/runtime/gateway/openai_gateway.py
# Restaurar BACKENDS legacy
# o desde git:
git checkout HEAD~1 -- runtime/gateway/openai_gateway.py
echo 19682507 | sudo -S systemctl restart ailab-gateway
```

## Próxima fase recomendada

**CP-47 — Pool Observability → Prometheus**
- Exportar contadores del pool como métricas Prometheus (`ailab_pool_*`)
- Dashboard Grafana para pool metrics
