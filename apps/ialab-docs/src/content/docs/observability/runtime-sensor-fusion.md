---
title: "Runtime Sensor Fusion — Observabilidad"
summary: "Observabilidad del sensor fusion runtime: métricas, dashboards, endpoints y troubleshooting para FASE 30I."
order: 16
---

## Resumen

La sensor fusion runtime añade una nueva capa de observabilidad: el runtime ahora puede observarse a sí mismo a través de Prometheus y reportar su propio estado con precisión.

## Endpoints

### GET /runtime/sensors

Always-on 200. Devuelve el snapshot completo del sensor fusion:

- Topología derivada de targets Prometheus
- 13 dominios con confidence scoring
- GPU metrics en vivo
- Freshness labels por source
- Catálogo de evidencia

Ver [FASE 30I — Runtime Sensor Fusion](/docs/runtime/30i-runtime-sensor-fusion/) para schema detallado.

## Métricas

### Sensor fusion metrics (4 nuevas)

| Métrica | Tipo | Labels | Descripción |
|---------|------|--------|-------------|
| `ailab_sensor_fusion_total` | Counter | source, status | Colecciones de sensor fusion ejecutadas |
| `ailab_sensor_fusion_duration_ms` | Histogram | source | Duración de la colección por source |
| `ailab_sensor_fusion_missing_source_total` | Counter | source | Sources que fallaron en la colección |
| `ailab_observed_runtime_context_size_bytes` | Gauge | - | Tamaño del snapshot OBSERVED_RUNTIME |

### Labels disponibles

| Label | Valores | Descripción |
|-------|---------|-------------|
| source | "all" o nombre del dominio | Fuente de datos |
| status | "ok", "timeout", "missing" | Estado de la colección |

### Ejemplos PromQL

```promql
# Sensor fusion rate (últimos 5 min)
rate(ailab_sensor_fusion_total{status="ok"}[5m])

# Duración promedio de sensor fusion
rate(ailab_sensor_fusion_duration_ms_sum[5m]) / rate(ailab_sensor_fusion_duration_ms_count[5m])

# Sources missing (deben ser 0 en operación normal)
ailab_sensor_fusion_missing_source_total

# Tamaño del OBSERVED_RUNTIME (debe ser <16000)
ailab_observed_runtime_context_size_bytes
```

## Dashboards

### Nuevos paneles recomendados para Grafana

| Panel | Query | Tipo |
|-------|-------|------|
| Sensor Fusion Rate | `rate(ailab_sensor_fusion_total[5m])` | Stat |
| Fusion Duration | `histogram_quantile(0.95, rate(ailab_sensor_fusion_duration_ms_bucket[5m]))` | Gauge |
| Missing Sources | `ailab_sensor_fusion_missing_source_total` | Stat (alarma si >0) |
| OBSERVED_RUNTIME Size | `ailab_observed_runtime_context_size_bytes` | Time series |
| Domain Confidence | `count(ailab_sensor_fusion_total{status="ok"}) by (source)` | Table |

## Alertas recomendadas

### Sensor Fusion Degradation

```yaml
alert: SensorFusionDegradation
expr: rate(ailab_sensor_fusion_total{status="timeout"}[5m]) > 0
for: 2m
labels:
  severity: warning
annotations:
  summary: "Sensor fusion está perdiendo sources"
```

### Missing Sources Persistentes

```yaml
alert: SensorFusionMissingSources
expr: ailab_sensor_fusion_missing_source_total > 0
for: 5m
labels:
  severity: critical
annotations:
  summary: "Sources missing en sensor fusion"
```

## Troubleshooting

### El endpoint /runtime/sensors devuelve 200 pero faltan sources

Posibles causas:

1. Prometheus no responde (timeout 2s)
2. Target específico está DOWN
3. Cache TTL no renovado

Diagnóstico:

```bash
curl http://192.168.1.30:8008/runtime/sensors | jq '.missing_sources'
curl http://192.168.1.40:9090/api/v1/targets | jq '.data.activeTargets[] | select(.health != "up")'
```

### GPU metrics no aparecen

1. Verificar que el target 9183 responde:

```bash
curl http://192.168.1.50:9183/metrics | grep gpu_load
```

2. Verificar que Prometheus scrapea el target:

```bash
curl http://192.168.1.40:9090/api/v1/query?query=up{job="ai-lab-gpu-metrics"}
```

### OBSERVED_RUNTIME excede 16KB

Si `ailab_observed_runtime_context_size_bytes` supera 16000, el contexto se trunca. Posibles causas:

- Demasiados targets GPU activos
- Evidence catalog demasiado grande
- Operational summary inflado

Solución: revisar `REPORT_MAX_CHARS` en `runtime/context/report_runtime_context.py`.

## Relación con FASE 29 observability

| Aspecto | FASE 29 | FASE 30I |
|---------|---------|----------|
| Enfoque | Rendimiento y SLO | Estado y topología |
| Métricas | Latencia, timeouts, GPU pressure | Sensor health, confidence, freshness |
| Endpoints | /slo/health | /runtime/sensors |
| Fuente | Código runtime + LM Studio | Prometheus + LM Studio |
| Consumidor | Operadores humanos | LLM (OBSERVED_RUNTIME) |

## Ver también

- [FASE 30I — Runtime Sensor Fusion](/docs/runtime/30i-runtime-sensor-fusion/)
- [Prometheus Runtime Integration](/docs/observability/prometheus-runtime-integration/)
- [FASE 29 — Runtime Observability](/docs/observability/phase-29-runtime-observability/)
- [Runtime Observability Fabric](/docs/architecture/runtime-observability-fabric/)
