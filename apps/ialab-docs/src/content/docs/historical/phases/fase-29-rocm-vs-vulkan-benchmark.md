---
title: "FASE 29.0 — ROCm vs Vulkan Benchmark"
summary: "Comparativa de rendimiento entre los backends Vulkan y ROCm de llama.cpp v2.14.0 en RX9070 con qwen2.5-coder-14b-instruct. 20 requests por backend, midiendo latencia, tokens/sec y consistencia."
order: 67
---

## Contexto

FASE 29.0 introduce hardening del gateway y establece una baseline de inferencia. AI-LAB usa llama.cpp v2.14.0 (Windows) como backend en el nodo GPU RX9070 (192.168.1.50:1234). El runtime soporta dos backends de aceleración: Vulkan y ROCm.

**Objetivo:** Comparar el rendimiento de ambos backends con carga idéntica para determinar cuál ofrece mejor latencia, throughput y consistencia.

## Metodología

| Parámetro | Valor |
|-----------|-------|
| Modelo | `qwen2.5-coder-14b-instruct` |
| Backend A | llama.cpp Vulkan v2.14.0 |
| Backend B | llama.cpp ROCm v2.14.0 |
| GPU | AMD RX9070 16GB |
| Requests por backend | 20 |
| Prompt | "explica docker en 3 lineas" |
| max_tokens | 64 |
| temperature | 0 |
| Métricas | Latencia total, tokens/sec, finish_reason |

## Resultados

### Latencia (ms)

| Percentil | Vulkan | ROCm | Delta |
|-----------|--------|------|-------|
| **p50** | 10,062 | 9,998 | **-64** |
| **avg** | 10,101 | 10,039 | **-62** |
| p95 | 10,676 | 10,563 | -113 |
| p99 | 10,676 | 10,563 | -113 |
| min | 9,959 | 9,900 | -59 |
| max | 10,676 | 10,563 | -113 |
| **spread (max-min)** | 717 | 663 | -54 |

### Throughput

| Métrica | Vulkan | ROCm |
|---------|--------|------|
| Tokens/sec (avg) | 6.3 | 6.4 |
| Total tokens generados | 1,280 | 1,280 |
| Finish length | 20/20 | 20/20 |

### Comparativa visual

```
Latencia p50 (ms):
Vulkan  ████████████████████████████████████████████████████ 10062
ROCm    ██████████████████████████████████████████████████   9998

Spread max-min (ms):
Vulkan  ███████████████████████████████████  717
ROCm    █████████████████████████████████    663

Tokens/sec:
Vulkan  ██████████████████████████████████   6.3
ROCm    ██████████████████████████████████   6.4
```

## Análisis

### Consistencia

Ambos backends muestran una consistencia **excepcional**. El spread entre min y max es inferior a 1 segundo en 20 requests — comparado con el viejo LM Studio que tenía spreads de 15-30 segundos.

### Diferencia Vulkan vs ROCm

ROCm es marginalmente más rápido (~0.6% en p50) con un spread ligeramente más ajustado (54ms menos). La diferencia no es estadísticamente significativa para este modelo y carga de trabajo.

### Dónde se espera mayor diferencia

La ventaja de ROCm se manifestaría con:
- **Modelos más grandes**: qwen3.6-27b o qwen2.5-coder-32b, donde el acceso a memoria de ROCm es más eficiente
- **Concurrencia**: múltiples requests simultáneos donde ROCm maneja mejor los compute queues
- **Prompt processing**: prompts largos donde ROCm acelera el prefill

## Comparativa con LM Studio anterior

| Métrica | LM Studio (viejo) | llama.cpp Vulkan | llama.cpp ROCm |
|---------|-------------------|-----------------|----------------|
| p50 (ms) | ~11,900 | 10,062 | 9,998 |
| Spread | 15-30s | 0.7s | 0.6s |
| Consistencia | Muy variable | Plana | Plana |
| Tokens/sec | ~5.4 | 6.3 | 6.4 |

**Mejora:** llama.cpp reduce la latencia p50 en ~16% y elimina prácticamente la varianza entre requests.

## Veredicto

**Ganador: ROCm** por margen mínimo (0.6%). Ambos backends son perfectamente viables para producción. La elección entre Vulkan y ROCm debe basarse en:

- **Vulkan**: Mejor compatibilidad, menos dependencias, más estable en Windows
- **ROCm**: Ligera ventaja en latencia, mejor para modelos grandes y concurrencia

Para el caso de uso actual de AI-LAB (qwen2.5-14b como modelo principal, baja concurrencia), la diferencia es negligible. Se recomienda mantener el backend que ofrezca mejor estabilidad operativa.

## Datos completos

- [Vulkan benchmark JSON](/api/fase29-vulkan-benchmark.json)
- [ROCm benchmark JSON](/api/fase29-rocm-benchmark.json)
- [Comparativa combinada JSON](/api/fase29-rocm-vs-vulkan.json)
