---
title: "AI-LAB: por qué consolidamos la madurez del runtime antes de Multi-GPU"
description: "Antes de orquestar múltiples GPUs, necesitábamos que el runtime supiera qué modelos tiene, qué nodos están vivos y qué puede afirmar sin alucinar."
summary: "Antes de Multi-GPU, AI-LAB necesitaba madurez semántica: model state awareness, degraded mode, governance visibility, route semantics y evidence enforcement."
date: "2026-05-21"
tags:
  - ai-lab
  - runtime
  - multigpu
  - maturity
  - architecture
---


## El espejismo del segundo nodo

Teníamos una RX7900XT apagada en 192.168.1.60. Teníamos un modelo de 32b esperando. La tentación era conectar el segundo nodo y lanzar el scheduler.

Pero el runtime no sabía responder preguntas básicas:

- ¿Qué modelo está realmente cargado?
- ¿El nodo RX9070 está degradado?
- ¿Por qué se bloqueó una ruta cognitiva?
- ¿Qué GPU existe de verdad en el laboratorio?

Sin ese conocimiento, intentar Multi-GPU habría sido construir una casa sobre arena.

## El problema: sin semántica operacional

### active vs loaded vs discoverable

Antes de FASE 30B, un modelo "cargado" era lo mismo que un modelo "activo". Si LM Studio reportaba que `qwen2.5-coder-14b` estaba cargado, el runtime asumía que estaba disponible para inferencia.

Pero `loaded != active`: un modelo puede estar cargado en memoria pero no listo para responder (ej: en medio de una descarga, o con contexto parcial).

FASE 30B introdujo `ModelStatusTracker` con 5 estados explícitos:

```
active → loaded, ready para inferencia
loaded → en memoria, no necesariamente listo
discoverable → existe en el endpoint, no cargado
disabled → explícitamente desactivado (ej: qwen3.6-27b)
unknown → no se sabe nada
```

Con reglas como RULE-30B-1: "Un modelo DISABLED prevalece sobre cualquier otro estado".

### El nodo que no sabía que estaba mal

Sin degraded mode explícito (FASE 30C), el runtime no podía distinguir entre "funcionando" y "funcionando mal". Si el TTFB subía de 800ms a 12s, el gateway seguía enrutando igual.

Ahora el runtime tiene 3 colores semáforo:

- GREEN: operación normal
- YELLOW: degradación parcial
- RED: degradación crítica

Y un `DegradationManager` con 4 niveles que activa countermeasures: forzar llama-3.1-8b, proteger qwen, reducir concurrencia.

### La gobernanza que no se veía

FASE 30E hizo visible lo que antes era invisible: cada decisión de governance ahora tiene por qué, qué regla se aplicó y quién la solicitó.

### El enrutamiento sin razón aparente

FASE 30F dio semántica a las rutas. route family existence != active. Un perfil puede existir sin estar activo. Una ruta puede estar registrada sin ser enrutable.

## La decisión de posponer

Cuando evaluamos el estado del runtime frente a los requisitos de Multi-GPU, la lista de carencias era larga:

| Requisito para Multi-GPU | Estado pre-30 | Estado actual |
|-------------------------|---------------|---------------|
| Saber qué modelo está activo | loaded = active | 5 estados con TTL |
| Detectar degradación | No | 4 niveles con anti-flapping |
| Gobernanza visible | No | endpoint explícito |
| Semántica de rutas | No | route-family semantics |
| Reportes sin alucinaciones | No | evidence guard |
| Catálogo de evidencia | No | 6 categorías observadas |

Decidimos cerrar las 8 fases de madurez (30A-30H) antes de tocar un solo cable del RX7900XT.

## El evidence guard: no inventar lo que no se ve

FASE 30H fue la culminación: si el runtime no observa una GPU, no puede afirmar que existe. Si no tiene una métrica, no puede dar un porcentaje. Si no carga un modelo, no puede mencionarlo.

Regla simple: **NO DISPONIBLE si falta evidencia.**

Esto parece obvio, pero los LLMs son expertos en completar información faltante con "lo más probable". Para un informe operacional, eso es inaceptable.

El evidence guard escanea 6 categorías: modelos, GPUs, security tools, plataformas externas, hosts y denylists. Si algo no está en el catálogo, se marca como no verificado. Con 5+ afirmaciones no verificadas, el hallucination_risk es HIGH.

## El resultado

38 tags git desde CP-21B-STABLE. 157 maturity tests PASS. 8 endpoints always-on 200. 100+ métricas Prometheus. 15 dashboards Grafana.

El runtime sabe qué tiene, qué no tiene y qué no debe inventar.

Ahora sí, podemos hablar de Multi-GPU.

## Lo que viene

- FASE 31A — RX7900XT Bring-up
- Scheduler contracts
- Warm pool
- Cognitive route placement
- gpt-oss-20b-derestricted en Q4_K_M como modelo destino del RX7900XT

Pero esa es otra historia.
