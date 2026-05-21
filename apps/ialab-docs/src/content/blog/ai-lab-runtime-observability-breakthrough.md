---
title: "AI-LAB Runtime Observability Breakthrough: cuando el LLM dejó de inventar su infraestructura"
description: "La FASE 30I de AI-LAB marca un hito epistemológico: el runtime dejó de usar contexto sintético y comenzó a alimentarse de Prometheus. El LLM ya no adivina qué GPU tienes."
summary: "FASE 30I convierte Prometheus en el sistema nervioso del runtime: 13 dominios observados, GPU metrics en vivo y un LLM que responde con datos reales, no con training data."
date: "2026-05-21"
tags:
  - ai-lab
  - observability
  - prometheus
  - sensor-fusion
  - runtime
  - architecture
---

# AI-LAB Runtime Observability Breakthrough

## El hito epistemológico

Hasta hoy, cuando preguntabas a AI-LAB "¿qué GPU tienes?", el LLM hacía dos cosas:

1. Leía un archivo JSON con la configuración del laboratorio
2. Respondía con lo que decía el archivo

Si alguien cambiaba una GPU y olvidaba actualizar el archivo, el LLM respondía con información incorrecta. Y si el LLM decidía ser "creativo", podía mencionar una NVIDIA A100 que nunca existió.

**Eso se acabó.**

La FASE 30I (Runtime Sensor Fusion) marca el momento en que AI-LAB dejó de depender de contexto sintético y comenzó a alimentarse directamente de Prometheus.

## El cambio

### Antes: el runtime adivinaba

```
OBSERVED_RUNTIME = {
  "gpus": ["RX9070"],           # del archivo de configuración
  "temperature": "unknown",     # no había métricas en vivo
  "load": "unknown",
  "power": "unknown"
}
```

El LLM recibía un snapshot estático. Podía estar desactualizado. Podía estar incompleto. Y el LLM no tenía forma de saberlo.

### Ahora: el runtime observa

```
OBSERVED_RUNTIME = {
  "observed_data": {
    "gpu_nodes": {
      "source_of_truth": "prometheus",
      "rx9070": {"temp": 32.0, "load": 0.0, "power": 49.0},
      "rx7900xt": {"up": false, "expected_offline": true}
    }
  },
  "domain_confidence": {
    "gpu_nodes": "high",
    "gateway": "high"
  },
  "topology": {
    "mode": "degraded_single_gpu"
  }
}
```

El LLM recibe datos verificados contra Prometheus. Sabe qué es observado y qué es inferido. Sabe qué GPUs están vivas y cuáles están apagadas intencionalmente.

## La prueba

Hicimos una pregunta directa: "What is the current GPU temperature and which GPUs are available?"

### Antes de 30I (respuesta típica):

> "El laboratorio cuenta con una GPU AMD RX9070 para inferencia y una RX7900XT para carga pesada. La temperatura actual es de aproximadamente 45°C bajo carga normal."

Sin métricas en vivo, el LLM inventaba la temperatura. Inventaba la carga. A veces inventaba GPUs.

### Después de 30I (respuesta real):

> **RX9070:**
> - Temperature: 32°C
> - VRAM: 16GB
> - Status: Online
> - Load: 0%
> - Power usage: 49W
> - Fan speed: 949 RPM
>
> **RX7900XT:**
> - Temperature: N/A (offline)
> - VRAM: 20GB
> - Status: Offline (expected to be offline)

Temperatura real: 32°C (promedio idle de RX9070). Load real: 0%. RX7900XT correctamente clasificada como expected_offline. Sin alucinaciones.

## La arquitectura

### 13 dominios observados

Cada dominio tiene su propia fuente de verdad y su propio nivel de confianza:

- **CRITICAL**: gateway, router, gpu_nodes — si fallan, el runtime está degradado
- **IMPORTANT**: control_plane, live_api, system, smartctl, lmstudio_models — si fallan, hay warning
- **AUXILIARY**: containers, docker, windows_exporters, unifi, cloudflare_tunnel — si fallan, se registra pero no afecta nada

### Confidence per-domain (no global)

Esta es probablemente la decisión arquitectónica más importante. Un fallo en Unifi (AUXILIARY) no reduce la confianza del gateway (CRITICAL). En sistemas anteriores, un solo sensor caído podía teñir todo el estado del sistema.

### Topología derivada de sensores

La topología ya no es un archivo JSON. Se deriva de los targets de Prometheus:

- 1 GPU UP + 1 expected_offline = `degraded_single_gpu`
- 2 GPUs UP = `multi_gpu` (futuro)
- 0 GPUs UP = `inventory_only`

## Las GPU metrics en vivo

El `PrometheusQueryClient` descubre dinámicamente 7 métricas desde el endpoint de GPU (9183):

- `gpu_load_percent` — nada que adivinar
- `gpu_temperature_celsius` — temperatura real del chip
- `gpu_power_watts` — consumo en vatios
- `gpu_fan_speed_rpm` — RPM del ventilador
- `gpu_clock_mhz` — frecuencia del core

Sin defaults. Sin estimaciones. Datos directos de Prometheus.

## Por qué esto es un hito

### 1. El runtime conoce su propio estado

AI-LAB pasó de "tener un archivo de configuración" a "observar su propia infraestructura". Es la diferencia entre leer tu currículum y hacerte un chequeo médico.

### 2. El LLM dejó de adivinar

El training data de los LLMs está lleno de NVIDIA A100, H100, clústeres Kubernetes y clouds AWS. Cuando un LLM responde sobre infraestructura sin contexto, responde con training data. Ahora responde con datos observados.

### 3. La confianza es granular

No es una nota global de "confianza: 0.8". Es 13 confidence scores independientes. Un problema en el router no hace que el LLM dude de la temperatura de la GPU.

### 4. Es preparación para Multi-GPU

Sin sensor fusion, un scheduler multi-GPU sería ciego. Con sensor fusion, el scheduler sabe qué nodos están UP, cuáles tienen capacidad, y cuáles están en inventario.

## Lo que viene

- **Multi-GPU (FASE 31A)**: scheduler que lee topología de Prometheus
- **Warm pool basado en métricas**: no asumir, medir
- **Routing con confidence scores**: rutas que evitan nodos con confianza baja

## La lección

El salto cualitativo de AI-LAB en FASE 30I no es técnico. Es epistemológico: el runtime dejó de creer lo que le dicen y empezó a observar lo que tiene.

El LLM sigue siendo un generador estadístico. Pero ahora, cuando habla de infraestructura, no habla desde el training data. Habla desde Prometheus.
