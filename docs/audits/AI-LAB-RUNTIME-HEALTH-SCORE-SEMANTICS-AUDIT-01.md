# AI-LAB-RUNTIME-HEALTH-SCORE-SEMANTICS-AUDIT-01

## Resultado: PASS

---

## Resumen ejecutivo

La evidencia actual confirma que `ai_lab:runtime_health_score` y `ailab_cognitive_health_score` no expresan lo mismo.

- `ai_lab:runtime_health_score` es un cross-check SLO binario en Prometheus, en rango 0-1.
- `ailab_cognitive_health_score` es la salud cognitiva/runtime canonica, en rango 0-100.
- `no_nodes_online` es un trigger de watchdog, no el estado actual; hoy no esta activo porque hay nodos online.

## Inventario

| Componente | Artefacto | Semantica | Rango |
|---|---|---|---|
| Recording rule | `monitorizacion/prometheus/rules/ai-lab-cognitive-alerts.yml` | Cross-check SLO de infraestructura | `0-1` |
| Cognitive layer | `runtime/health/cognitive_health_layer.py` | Salud cognitiva/runtime canonica | `0-100` |
| Gateway endpoint | `runtime/gateway/runtime_api_routes.py` | Sirve `/runtime/health*` desde la capa cognitiva | N/A |
| Gateway metrics | `runtime/gateway/openai_gateway.py` | Exporta `ailab_cognitive_health_score` | N/A |

## Evidencia de codigo

### Recording rule

`monitorizacion/prometheus/rules/ai-lab-cognitive-alerts.yml:306`

```yaml
- record: ai_lab:runtime_health_score
  expr: |
    (
      ailab_slo_gateway_health
      + ailab_slo_lmstudio_health
      + ailab_slo_registry_consistency
      + (ailab_registry_routable_models_total > bool(1))
      + (ailab_federation_guard_state < bool(2))
    ) / 5
```

Esto confirma que la regla mide cinco senales binarias de SLO y no la salud cognitiva completa.

### Cognitive health layer

`runtime/health/cognitive_health_layer.py:237`

```python
if nodes_online <= 0:
    return {"confidence": 0.0, "nodes_online": 0, "reasons": ["no_nodes_online"]}
```

`runtime/health/cognitive_health_layer.py:291`

```python
if nodes_online == 0:
    triggers.append({"id": "no_nodes_online", "severity": "critical"})
```

`runtime/health/cognitive_health_layer.py:528`

```python
f"ailab_cognitive_health_score {score}\n"
```

`runtime/gateway/openai_gateway.py:1352`

```python
# HELP ailab_cognitive_health_score Cognitive health score (0-100, metadata-only)
```

### Runtime endpoints

`runtime/gateway/runtime_api_routes.py:275-281`

- `/runtime/health`
- `/runtime/health/score`
- `/runtime/health/summary`
- `/runtime/health/nodes`
- `/runtime/health/routing-confidence`
- `/runtime/health/watchdog`

## Observed values

### Prometheus

- `ai_lab:runtime_health_score` = `1`
- `ailab_cognitive_health_score` = `93.8`
- `ailab_cognitive_health_nodes_online` = `2`
- `ailab_cognitive_health_routing_confidence` = `0.92`

### Runtime

- `/health` = `ok`
- `/runtime/health` = `healthy`, `score=93.8`
- `/runtime/grounding` = `ok`, `grounded=false`, `confidence=low`
- router `/health` = `ok`

### Watchdog

- `watchdog_state` = `enabled`
- `triggers` = `[]`
- `no_nodes_online` = not active

## Conclusion

No score conflict exists.

- Use `ailab_cognitive_health_score` as the primary runtime health signal.
- Use `/runtime/health` and `/runtime/health/summary` for NOC/runtime status.
- Use `ai_lab:runtime_health_score` only as a Prometheus cross-check signal.
- Treat `no_nodes_online` as an alert trigger, not a current-state metric.

## Recommendation

Keep the existing split:

- canonical runtime/cognitive health: `ailab_cognitive_health_score`
- infrastructure SLO cross-check: `ai_lab:runtime_health_score`
- watchdog semantics: `no_nodes_online`

That matches both the code and the live runtime behavior.
