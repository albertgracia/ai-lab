---
title: "Cómo construimos un runtime contextualmente consciente de su propia infraestructura"
description: "Sensor fusion con Prometheus para que un LLM local sepa exactamente qué GPUs, modelos y servicios tiene disponibles — sin alucinar."
summary: "Integramos Prometheus directamente en el contexto del LLM: 13 dominios observados, GPU metrics en vivo, confidence per-domain y un evidence guard que impide alucinaciones."
date: "2026-05-21"
tags:
  - ai-lab
  - prometheus
  - llm
  - context
  - architecture
  - engineering
---

# Cómo construimos un runtime contextualmente consciente de su propia infraestructura

## El problema de la conciencia contextual

Los LLMs son excelentes generando texto. Pésimos sabiendo lo que realmente tienen delante.

Cuando integras un LLM en un runtime, necesitas que sepa:

- ¿Qué GPU está disponible ahora?
- ¿Qué temperatura tiene?
- ¿Hay algún nodo caído?
- ¿Qué modelo está cargado?

Sin un mecanismo explícito de contexto, el LLM adivina. Y adivinar en infraestructura produce alucinaciones costosas.

## Nuestra solución: Prometheus como contexto

La idea es simple: todo lo que el runtime necesita saber sobre sí mismo está en Prometheus. Targets UP/DOWN, métricas, health checks. ¿Por qué no usar Prometheus directamente como fuente de contexto para el LLM?

### La arquitectura

```
Prometheus API → Query Client (timeout 2s, cache 5s)
  → Sensor Fusion Engine (13 dominios)
    → Runtime Snapshot (observed + derived)
      → OBSERVED_RUNTIME JSON (≤16KB)
        → Inyectado en system prompt del LLM
          → Evidence Guard (post-hoc sanitization)
```

### El PrometheusQueryClient

El cliente tiene que ser resiliente. Prometheus puede fallar, tardar, o devolver datos inconsistentes. Nuestro cliente:

- Timeout a 2s (no bloquea el gateway)
- Cache TTL 5s (reduce latencia)
- Fallback a None (nunca lanza excepción)
- Freshness tracking (cada dato sabe su edad)

```python
class PrometheusQueryClient:
    def query_instant(self, query):
        # timeout 2s, cache 5s, fallback None
        ...

    def query_gpu_metrics(self, host):
        # descubre dinámicamente 7 métricas
        ...
```

### El Sensor Fusion Engine

No basta con traer datos de Prometheus. Hay que fusionarlos, clasificarlos y darles significado:

1. **13 dominios** observados, cada uno con source_of_truth
2. **observed vs derived**: los datos crudos separados de las inferencias
3. **Domain confidence**: per-domain, no global
4. **Topología dinámica**: derivada de targets UP/DOWN
5. **Evidence catalog**: qué se observó realmente

### La inyección de contexto

El OBSERVED_RUNTIME se inyecta como JSON en el system prompt:

```
You are AI-LAB's runtime assistant.
Here is the current observed state of the runtime:

{
  "observed_data": {...},
  "derived_state": {...},
  "domain_confidence": {...},
  "runtime_topology": {...},
  "operational_summary": "..."
}

Rules:
- Never invent GPUs, models, hosts, or platforms not in OBSERVED_RUNTIME
- If a metric is "N/A", say so
- RX7900XT is expected to be offline
```

## Lecciones aprendidas

### 1. Los LLMs no leen tu código

Parece obvio, pero es fácil olvidarlo. El LLM solo ve `messages[]`. Si quieres que sepa algo, tienes que ponerlo explícitamente en el prompt. No puede leer archivos, variables de entorno, ni APIs internas.

### 2. El training data es enemigo de la precisión

Cuando un LLM no tiene contexto, completa con lo más probable. "GPU" + "informe" = "NVIDIA A100". "Modelo" + "descripción" = "GPT-4". Tienes que overrule ese comportamiento con contexto explícito.

### 3. Cache con límite de daño

TTL 5s, timeout 2s. Si Prometheus no responde, el runtime usa el último dato conocido y lo marca como stale. Nunca bloquea una request. Preferimos datos ligeramente desactualizados que una request fallida.

### 4. Confidence per-domain es crítico

Un fallo en un sensor de red WiFi (Unifi, AUXILIARY) no debe hacer que el LLM dude de la temperatura de la GPU. La confianza debe ser granular.

### 5. La topología dinámica evita configs muertas

Antes teníamos un archivo JSON de topología que había que mantener a mano. Ahora la topología se deriva de Prometheus. Si añades un nodo, aparece solo. Si se cae, se refleja solo.

## Resultados

- 29 tests, todos PASS
- Endpoint /runtime/sensors → 200 con 13 dominios
- GPU metrics en vivo: 32°C, 0% load, 49W
- OBSERVED_RUNTIME: 4043 bytes (bajo límite 16KB)
- 0 alucinaciones en burn-in
- 4 nuevas métricas Prometheus

## Lo que haríamos diferente

- **Lazy loading de dominios**: algunos dominios AUXILIARY no necesitan consultarse en cada request
- **Caché predictiva**: si un dominio siempre responde igual, reducir frecuencia de scrape
- **Freshness adaptativa**: dominios CRITICAL con TTL más corto que AUXILIARY

## Código relevante

- `runtime/context/prometheus_client.py` — PrometheusQueryClient (136 líneas)
- `runtime/context/sensor_fusion.py` — SensorFusionEngine (384 líneas)
- `runtime/context/summary_builder.py` — OperationalSummaryBuilder (121 líneas)
- `runtime/context/report_runtime_context.py` — integración OBSERVED_RUNTIME

## Conclusión

Prometheus no es solo para dashboards. Es el sistema nervioso de tu runtime. Úsalo como fuente de contexto para tu LLM y dejará de adivinar qué infraestructura tiene delante.
