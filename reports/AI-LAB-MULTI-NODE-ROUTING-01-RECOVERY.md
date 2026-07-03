# AI-LAB-MULTI-NODE-ROUTING-01-RECOVERY

**Resultado: PASS**

## Estado inicial
- Dynamic Node Registry ✅ funcional, 3 nodos definidos
- Multi-Node Routing ✅ funcional, `resolve_node_for_model()` + `resolve_backend_for_model()` operativos
- Capability Scheduler ✅ funcional, `build_scheduler_decision()` operativo
- Intelligent Fallback Engine ✅ funcional, `classify_backend_failure()` + `build_fallback_candidates()` + `select_fallback_candidate()` operativos
- Gateway integr: scheduler → multi-node → IFE en flujo lineal ✅
- Nodos: .50 ON, .60 ON, .250 ON (los 3 con LM Studio)

## Cambios realizados

### 1. `runtime/router/elastic_pool.py` (NUEVO)
Clase `ElasticComputePool` que unifica en una sola capa observable:
- Carga de nodos desde Dynamic Node Registry
- Estados: online/offline/degraded
- Selección por capacidad con scoring
- Fallback a nodo sano
- Pool status API via `get_status()` / `get_summary()`
- Módulo singleton: `get_pool()`, `select_node()`, `get_pool_status()`

### 2. `runtime/gateway/openai_gateway.py` (MODIFICADO)
- `_try_fallback()` → prioriza `ElasticComputePool.fallback()`, fallback legacy IFE
- `do_POST` → pool.select_node() reemplaza capability_scheduler como selector primario
- `/health` → incluye pool summary
- `/runtime/pool` → nuevo endpoint (200 siempre)
- `Connection: keep-alive` → `close` en SSE headers (fix streaming Hermes)

## Archivos tocados
| Archivo | Acción | Líneas |
|---------|--------|--------|
| `runtime/router/elastic_pool.py` | CREATE | 444 |
| `runtime/gateway/openai_gateway.py` | MODIFY | ~60 líneas cambiadas |

## Módulos NO tocados
- Dynamic Node Registry (`runtime/state/dynamic_node_registry.py`) ✅ intacto
- Multi-Node Routing (`runtime/router/multi_node_routing.py`) ✅ intacto
- Capability Scheduler (`runtime/router/capability_scheduler.py`) ✅ intacto
- Fallback Engine (`runtime/router/fallback_engine.py`) ✅ intacto
- Marketplace ✅ no tocado
- Hermes ✅ no tocado
- GitNexus ✅ solo consulta read-only

## Evidencias

### Pool status
```
nodes_total: 3, nodes_online: 3, nodes_offline: 0
[online] nas-n5        role=baseline   caps=['chat', 'embeddings', 'fast']
[online] rx9070-node   role=on_demand  caps=['chat', 'coding', 'embeddings', 'fast', 'reasoning']
[online] rx7900xt-node role=on_demand  caps=['chat', 'coding', 'embeddings', 'fast', 'large-context', 'multimodal', 'reasoning', 'vision']
```

### Gateway health with pool
```json
{"status": "ok", "pool": {"pool": "elastic-compute-pool-01", "nodes_online": 3, "nodes_total": 3}}
```

### Chat simple
```
model: qwen2.5-14b-instruct | finish_reason: length
```

### Streaming
```
chunks: 2, finish_reason: stop, [DONE]: PRESENT
```

### Vision routing
```
model: moondream2-20250414 (correctly routed to .60)
```

### Non-streaming response
```
finish_reason: length, content: OK
```

## Riesgos residuales
1. Streaming en Hermes Desktop puede requerir test manual adicional (el fix `Connection: close` está desplegado pero no validado con Hermes Desktop)
2. Elastic Compute Pool no tiene tests unitarios aún (solo validación funcional)
3. Si se añaden nodos nuevos, hay que actualizar `NODE_DEFINITIONS` en `dynamic_node_registry.py`

## Rollback exacto
```bash
# Restaurar openai_gateway.py desde backup
cp /opt/ai-lab/runtime/gateway/openai_gateway.py.cp45bak.20260702_161225 \
   /opt/ai-lab/runtime/gateway/openai_gateway.py
# Eliminar elastic_pool.py
rm /opt/ai-lab/runtime/router/elastic_pool.py
# Reiniciar gateway
sudo systemctl restart ailab-gateway
```

## Próximos pasos
1. Tests unitarios para ElasticComputePool
2. Validación Hermes Desktop streaming (post-deploy manual)
3. Burn-in corto multi-nodo (10 requests rotando modelos)
4. Documentar pool en Astro docs
