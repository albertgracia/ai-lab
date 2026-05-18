---
title: "Runbook — FASE 19.4 Route Family Observability"
summary: "Runbook para revisar metricas por route family, detectar regresiones de contexto y validar el baseline del runtime AI-LAB."
order: 37
---

# Runbook — FASE 19.4 Route Family Observability

## Objetivo

Verificar rapidamente si el runtime sigue enroutando bien y si `minimal` / `observe` siguen siendo ligeras.

## Flujo de lectura

1. Mirar la distribucion por family.
2. Revisar latencia por family.
3. Revisar tokens por family.
4. Revisar errores y bloqueos por family.
5. Confirmar que `minimal` y `observe` no crecen en coste semantico.

## Que significa cada family

| Family | Lectura operativa |
|---|---|
| `minimal` | Debe ser corta, barata y sin contexto pesado |
| `observe` | Debe usar solo informacion observable |
| `tool_fastpath` | Debe resolver herramientas sin inflar el prompt |
| `cognitive` | Puede usar contexto y recall, pero controlado |
| `learning` | Solo para endpoints internos de aprendizaje |

## Queries rapidas

### Distribucion

```text
sum by (family) (ailab_route_family_total)
```

### Latencia promedio

```text
sum by (family) (rate(ailab_route_family_latency_ms_sum[5m])) / sum by (family) (rate(ailab_route_family_latency_ms_count[5m]))
```

```text
histogram_quantile(0.95, sum by (le, family) (rate(ailab_route_family_latency_ms_bucket[5m])))
```

### Tokens

```text
sum by (family) (rate(ailab_route_family_prompt_tokens_total[5m]))
```

```text
sum by (family) (rate(ailab_route_family_completion_tokens_total[5m]))
```

### Errores y bloqueos

```text
sum by (family) (rate(ailab_route_family_errors_total[5m]))
```

```text
sum by (family) (rate(ailab_route_family_blocked_total[5m]))
```

## Grafana

Dashboard: `AI-LAB Route Family Observability Baseline`

URL: `http://192.168.1.40:3000`

## Paneles Grafana

| Panel | Objetivo |
|---|---|
| Route Family Distribution | Ver que family domina el trafico |
| Latency by Route Family | Detectar rutas simples lentas con promedio real |
| Prompt Tokens by Family | Ver inflacion de contexto |
| Completion Tokens by Family | Ver salida real por family |
| Errors by Family | Ver fallos por familia |
| Blocked by Family | Ver bloqueo de policy por familia |

## Como detectar regresiones

### Regresion de contexto

Señal:

- `minimal` sube en prompt tokens
- `observe` sube en prompt tokens
- `minimal` sube en latencia

Interpretacion:

- se esta inyectando contexto innecesario
- se esta reintroduciendo recall pesado
- se esta perdiendo la ruta minima

### Regresion tool fastpath

Señal:

- `tool_fastpath` sube en errores o bloqueos
- `tool_fastpath` baja en throughput y sube en latencia

Interpretacion:

- parser de tools roto
- fastpath no se esta activando bien
- demasiada carga en la ruta de tools

### Regresion cognitive

Señal:

- `cognitive` domina el trafico trivial
- `cognitive` absorbe saludos o reportes simples

Interpretacion:

- el clasificador esta siendo demasiado permisivo
- el runtime dejo de respetar la segmentacion

## Checklist de validacion

- `minimal` responde con latencia y tokens bajos.
- `observe` no usa HARD_FACTS pesados.
- `tool_fastpath` no arrastra contexto completo.
- `cognitive` sigue siendo la ruta pesada, no la predeterminada.
- `learning` solo aparece en endpoints internos.
- `ailab_embedding_truncations_total` no sube en usos normales.

## Baseline esperado

- `minimal` y `observe` deben quedarse por debajo de `cognitive` en tokens y latencia.
- Si suben, hay regresion de contexto.
- Si `learning` crece sin motivo, hay ruido de observabilidad o jobs mal encaminados.
