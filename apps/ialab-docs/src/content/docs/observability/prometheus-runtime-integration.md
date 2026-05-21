---
title: "Prometheus Runtime Integration"
summary: "Integración de Prometheus como source of truth del runtime: query client, target discovery, GPU metrics, cache y freshness."
order: 15
---

## Visión

Prometheus es el sistema nervioso de AI-LAB. Todo lo que el runtime necesita saber sobre su propia infraestructura vive en Prometheus: targets up/down, métricas GPU, health de servicios, freshness de datos.

```
Prometheus 192.168.1.40:9090
├── 17 scrape targets
├── 100+ métricas ailab_*
├── 15 UP, 2 DOWN (expected)
└── 19 alert rules
```

## PrometheusQueryClient

`runtime/context/prometheus_client.py`

### API

```python
class PrometheusQueryClient:
    def query_instant(self, query: str) -> float | None
    def get_target_up(self, job: str, instance: str = "") -> dict
    def query_gpu_metrics(self, host: str) -> dict
    def get_freshness(self, source: str) -> float
```

### Timeout y resiliencia

- Timeout por query: 2s
- Fallback: None (nunca lanza excepción)
- Logging: warning si timeout, debug si éxito

### Cache TTL

- Cache por source: 5s
- Invalidate on write: no (read-only client)
- Freshness tracking: timestamp de último scrape exitoso

### GPU metric discovery

El cliente descubre métricas dinámicamente desde los targets de GPU:

```python
def query_gpu_metrics(self, host: str) -> dict:
    metrics = {}
    for metric in self.GPU_METRIC_QUERIES:
        value = self.query_instant(f"{metric}{{instance=~'{host}:.*'}}")
        if value is not None:
            key = self._deduplicate_key(metric)
            metrics[key] = value
    return metrics
```

Métricas descubiertas:

| Query Prometheus | Key | Unidad |
|-----------------|-----|--------|
| gpu_smalldata | gpu_smalldata | - |
| gpu_load_percent | gpu_load_percent | % |
| gpu_temperature_celsius | gpu_temperature_celsius | °C |
| gpu_power_watts | gpu_power_watts | W |
| gpu_fan_speed_rpm | gpu_fan_speed_rpm | RPM |
| gpu_clock_mhz | gpu_clock_mhz | MHz |
| gpu_voltage | gpu_voltage | V |

### Prefix deduplication

Los nombres de métricas en Prometheus que comienzan con "GPU" ya incluyen el prefijo `gpu_`. Para evitar `gpu_gpu_memory_used`, el cliente detecta y remueve el prefijo duplicado:

```python
GPU_PREFIX = "gpu_"

def _deduplicate_key(self, metric_name: str) -> str:
    if metric_name.startswith(GPU_PREFIX):
        return metric_name
    return f"{GPU_PREFIX}{metric_name}"
```

## Scrape targets

### Configuración actual

```yaml
scrape_configs:
  - job_name: 'ai-lab-gateway'
    static_configs: [{targets: ['192.168.1.30:8008']}]
  - job_name: 'ai-lab-router'
    static_configs: [{targets: ['192.168.1.30:8083']}]
  - job_name: 'ai-lab-live-api'
    static_configs: [{targets: ['192.168.1.30:8084']}]
  - job_name: 'ai-lab-cadvisor'
    static_configs: [{targets: ['192.168.1.30:8081']}]
  - job_name: 'ai-lab-node'
    static_configs: [{targets: ['192.168.1.30:9100']}]
  - job_name: 'ai-lab-gpu-rx9070'
    static_configs: [{targets: ['192.168.1.50:9182']}]
  - job_name: 'ai-lab-gpu-metrics'
    static_configs: [{targets: ['192.168.1.50:9183']}]
  - job_name: 'cloudflare-tunnel'
    static_configs: [{targets: ['cloudflare-tunnel:2000']}]
```

### Targets DOWN (expected)

```yaml
  - job_name: 'ai-lab-gpu-rx7900xt'
    static_configs: [{targets: ['192.168.1.60:9182']}]
  - job_name: 'ai-lab-gpu-metrics'
    static_configs: [{targets: ['192.168.1.60:9183']}]
```

Estos targets están DOWN porque el nodo 192.168.1.60 está apagado. Son `expected_offline`.

## Freshness model

Cada fuente de datos tiene un timestamp del último scrape exitoso. El sensor fusion expone estos valores como freshness labels:

| Freshness | Significado |
|-----------|-------------|
| < 5s | Datos recién adquiridos |
| 5-30s | Datos stale (cache no renovado) |
| > 30s | Datos potentially expired |
| None | Nunca se obtuvo dato |

## Métricas de integración

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `ailab_prometheus_query_duration_ms` | Histogram | Duración de queries a Prometheus |
| `ailab_prometheus_query_errors_total` | Counter | Errores de query a Prometheus |
| `ailab_prometheus_cache_hit_total` | Counter | Cache hits en PrometheusQueryClient |

## Troubleshooting

### Prometheus no responde

Síntoma: `ailab_sensor_fusion_missing_source_total` se incrementa.
Causa: timeout 2s excedido.
Efecto: el source aparece como missing, no como error. El LLM ve "NO DISPONIBLE".

### GPU metrics vacías

Síntoma: `gpu_summary` no muestra métricas.
Causa: target GPU metrics (9183) no responde.
Diagnóstico: `curl http://192.168.1.50:9183/metrics | grep gpu_load`

### Cache stale

Síntoma: freshness labels > 5s.
Causa: Prometheus no scrapea o el query client no puede renovar cache.
Diagnóstico: `curl http://192.168.1.40:9090/api/v1/targets | jq '.data.activeTargets[] | select(.health != "up")'`

## Ver también

- [FASE 30I — Runtime Sensor Fusion](/docs/runtime/30i-runtime-sensor-fusion/)
- [Runtime Sensor Fusion — Observability](/docs/observability/runtime-sensor-fusion/)
- [Runtime Observability Fabric](/docs/architecture/runtime-observability-fabric/)
- [Runtime Evidence Pipeline](/docs/architecture/runtime-evidence-pipeline/)
