# CP-45-ELASTIC-COMPUTE-POOL-01

**Resultado: PASS**

## Resumen

Elastic Compute Pool implementado como capa unificada sobre Dynamic Node Registry. Proporciona selección determinística de nodos por capacidad, estados online/offline/degraded, fallback automático a nodo sano, y API de observabilidad.

## Arquitectura

```
        ┌─────────────────────────────────────────┐
        │          ElasticComputePool             │
        │  select() | fallback() | get_status()  │
        ├─────────────────────────────────────────┤
        │  Dynamic Node Registry (source of truth)│
        │  Capability Scheduler (scoring)         │
        │  Multi-Node Routing (URLs, normalization)│
        │  Fallback Engine (legacy fallback)      │
        └─────────────────────────────────────────┘
```

## Pool API

### `GET /runtime/pool`
Endpoint always-on 200. Devuelve:
- pool, contract_version, timestamp
- nodes_total, nodes_online, nodes_offline, nodes_degraded
- required_offline_critical
- nodes_by_role
- nodes[] con estado, capacidades, health_score, degraded flag

### `GET /health` (extendido)
Incluye `pool` key con summary.

## Scoring

Cada nodo online recibe un score basado en:
| Factor | Peso | Descripción |
|--------|------|-------------|
| Model match | +4.0 | El modelo solicitado existe en el nodo |
| Capability match | +3.0 | El nodo cumple requisitos de capacidad |
| rx7900xt required | +5.0 | Modelo solo disponible en .60 |
| Health | ×2.0 | health_score del registry (0.0-1.0) |

Gates: rx7900xt-only models → rechazados si no es .60.

## Estados de nodo

| Estado | Criterio | Routing |
|--------|----------|---------|
| online | LM Studio responde + routing_eligible=True | ✅ Seleccionable |
| offline | No responde o routing_eligible=False | ❌ Excluido |
| degraded | health_score < 0.5 o latency > 10s | ✅ Seleccionable (penalizado) |

## Fallback

`ElasticComputePool.fallback()`:
1. Same model en otro nodo online → usa ese modelo
2. Visión fallback → nodo con capability vision
3. Large-context fallback → nodo con capability large-context
4. Último recurso: cualquier nodo online
5. Si fallback pool → None → legacy IFE

## Archivos

| Archivo | Rol |
|---------|-----|
| `runtime/router/elastic_pool.py` (NUEVO) | ElasticComputePool class + singleton |
| `runtime/gateway/openai_gateway.py` (MOD) | Integración gateway: pool.select() + pool.fallback() + endpoint |

## Validaciones

| Test | Resultado |
|------|-----------|
| Gateway health + pool | ✅ 3/3 online |
| /runtime/pool 200 | ✅ 3 nodos, caps correctas |
| /v1/models | ✅ 6 modelos |
| Chat simple stream=false | ✅ finish_reason=length |
| Chat simple stream=true | ✅ 2 chunks + [DONE] |
| Stream multi-chunk | ✅ 5 chunks + [DONE] |
| Router health | ✅ ok |
| .50 LM Studio | ✅ 6 modelos |
| .60 LM Studio | ✅ 11 modelos |
| .250 LM Studio | ✅ 3 modelos |
| Vision route → .60 | ✅ moondream2-20250414 |

## Riesgos residuales

1. Pool sin tests unitarios — solo validación funcional
2. No hay burn-in multi-nodo automatizado
3. Si registry TTL (30s) no se respeta, decisiones pueden basarse en datos stale
4. Degraded state detectado solo por health_score/latency, no por SLO

## Rollback

```bash
# Restaurar openai_gateway.py
cp /opt/ai-lab/runtime/gateway/openai_gateway.py.cp45bak.20260702_161225 \
   /opt/ai-lab/runtime/gateway/openai_gateway.py
# Eliminar elastic_pool.py
rm /opt/ai-lab/runtime/router/elastic_pool.py
# Reiniciar
sudo systemctl restart ailab-gateway
```
