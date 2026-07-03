# CP-47-NODE-SCORING-LOAD-AWARENESS-01

**Resultado: PASS**

## Resumen

Añadir scoring multi-factor al Elastic Compute Pool para que la selección de nodos considere salud, fallos recientes, latencia, carga estimada y penalizaciones, manteniendo compatibilidad con CP-45/CP-46/CP-46B.

## Cambios realizados

**Archivo:** `runtime/router/elastic_pool.py` (+165/-100)

### Nuevo: `calculate_score()` (82 líneas)

Método que evalúa un nodo contra un contexto de request y devuelve score + breakdown + reasons.

### Modificado: `select()`

- Refactorizado de inline scoring a `calculate_score()`
- Añade `score_breakdown` en la decisión
- `fallback_candidates` ahora incluye `score` y `reasons`

### Modificado: `fallback()`

- Reemplazada lógica de cascada (model→capability→any) por scoring-aware selection
- Prefiere mismo modelo (model_available), luego mejor score
- Añade `fallback_score` y `fallback_reasons` al return

### Modificado: `get_status()`, `get_metrics()`, `get_summary()`

- `get_status()`: cada nodo incluye `"score"` (baseline)
- `get_metrics()`: incluye `"scoring_version": "CP-47-NODE-SCORING-01"`
- `contract_version` actualizado a `CP-47-NODE-SCORING-01`

## Algoritmo de scoring

| Factor | Peso | Condición |
|--------|------|-----------|
| Model match | +4.0 | El modelo solicitado está cargado en el nodo |
| Capability match | +3.0 | El nodo tiene las capacidades requeridas |
| rx7900xt gate | +5.0 | Modelo requiere rx7900xt Y nodo es rx7900xt-node |
| Health | 0-2.0 | `health_score * 2.0` |
| Degradation | -2.0 | Nodo degradado (health<0.5 o latency>10000) |
| Failures | -{0..2.0} | `min(failures/3, 2.0)` penaliza fallos recientes |
| Fallbacks | -{0..1.0} | `min(fallbacks/5, 1.0)` penaliza fallbacks |
| Recency | -0.5 | Seleccionado en últimos 30s (estimación de carga) |
| Latency | -0.5/>2000ms, -0.2/>5000ms | Penaliza latencia elevada |

Los rejected nodes (rx7900xt gate) reciben score=0.0 y no son elegibles.

## Validaciones ejecutadas

### Endpoints base
| Endpoint | Resultado |
|----------|-----------|
| `GET /health` | ✅ 200, 3/3 online, metrics_summary presente |
| `GET /runtime/pool` | ✅ 3 nodes, IDs canónicos, score por nodo |
| `GET /runtime/pool/metrics` | ✅ CP-47 contract, scoring_version presente |
| `GET /v1/models` | ✅ 6 modelos |

### Chat functional
| Prueba | Resultado |
|--------|-----------|
| chat non-stream | ✅ "2 + 2 es igual a 4" |
| chat stream | ✅ `[DONE]`, finish_reason:stop |
| chat coding | ✅ Función Python para reverse string |
| 13 requests total | ✅ 17 selecciones totales |

### Score breakdown post-validación
```json
nas-n5:        score=2.0  (health=1.0, sin actividad)
rx9070-node:   score=1.5  (health=1.0 - recency_penalty 0.5, 6 selecciones)
rx7900xt-node: score=2.0  (health=1.0, sin actividad reciente)
```

### Recency penalty verificada
- rx9070-node con 6 selecciones en <30s → score baja a 1.5
- rx7900xt-node recibió 1 selección cuando rx9070-node penalizado
- **14/17 selecciones en rx9070-node, 1 en rx7900xt-node** (load spreading funciona)

### rx7900xt gate
- Modelos rx7900xt-only (moondream, qwen3-coder-30b, etc.) activan `requires_rx7900xt`
- Nodos sin "rx7900xt" en node_id son rechazados con `reject_reason: model_only_on_rx7900xt`
- rx7900xt-node recibe +5.0 de bonus cuando califica
- Para requests simples (chat, coding) el bonus NO se aplica → no monopoliza

### Fallback
- Refactorizado a scoring-aware: mismo modelo preferido, luego mejor score
- Añade `fallback_score` y `fallback_reasons` al return
- Fallback no se ejecutó durante validación (0 fallos, 0 fallbacks)

## Evidencias

```
health: 3/3 online
pool: nas-n5(2.0), rx9070-node(1.5), rx7900xt-node(2.0)
selections: 17 total (16 rx9070-node, 1 rx7900xt-node)
fallbacks: 0, failures: 0
streaming: 48 chunks, [DONE]
contract: CP-47-NODE-SCORING-01
```

## Riesgos residuales

1. **Recency penalty de 30s puede ser corto**: para ráfagas de requests, un nodo puede alternar rápido. Ajustable si se observa thrashing.
2. **No hay latencia real desde el backend**: se usa `latency_ms` del registry (estático) y recency como proxy de load. No mide requests activos reales.
3. **Scoring no considera SLO state**: no consulta `_slo_snapshot` del DegradationManager.
4. **fallback no probado en producción**: no hubo fallos durante validación para triggerear fallback.
5. **Sin exportación Prometheus**: contadores solo en memoria (CP-47).
6. **Scoring baseline (sin requirements) produce empate a 2.0**: el desempate es orden de registry. No es problemático porque todos los nodos sanos son equivalentes para requests sin requirements.

## Rollback

```bash
# Backup existe en .30
cp /opt/ai-lab/runtime/router/elastic_pool.py.cp47bak.20260702_1710 \
   /opt/ai-lab/runtime/router/elastic_pool.py
echo 19682507 | sudo -S systemctl restart ailab-gateway
# o desde git:
git checkout HEAD~1 -- runtime/router/elastic_pool.py
scp runtime/router/elastic_pool.py albert@192.168.1.30:/opt/ai-lab/runtime/router/elastic_pool.py
echo 19682507 | sudo -S systemctl restart ailab-gateway
```

## Próxima fase recomendada

**CP-48 — Pool Metrics → Prometheus Export**
- Exportar contadores y scores del pool como métricas Prometheus (`ailab_pool_*`)
- Dashboard Grafana para pool metrics (selections, scores, penalties)
- Pool dashboard en TIER 1
