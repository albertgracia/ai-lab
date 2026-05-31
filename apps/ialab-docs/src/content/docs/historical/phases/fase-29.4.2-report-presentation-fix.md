---
title: "FASE 29.4.2 — Report Grounding Presentation Fix"
summary: "Convierte los reportes AI-LAB de chatbot genérico a informes operacionales NOC con clasificación precisa de modelos (active/disabled/discovered), nodos (active/inventory), servicios (core/support/observability), calidad de datos (observed/inferred/missing), estructura fija de 12 secciones, tono técnico y metadatos de reporte."
order: 80
---

## Objetivo

FASE 29.4.1 resolvió el grounding — los reportes ya usan OBSERVED_RUNTIME real y no responden "no tengo información". Pero la presentación seguía siendo genérica, sin clasificación técnica:

- qwen3.6-27b aparecía como nodo disponible en lugar de DESACTIVADO
- RX7900XT aparecía como nodo offline ambiguo en lugar de INVENTARIADO
- El informe mezclaba datos observados, inferidos y no disponibles
- El tono era demasiado chatbot genérico

## Cambios

### Modificado: `runtime/context/report_runtime_context.py`

Reestructuración completa del contexto OBSERVED_RUNTIME:

- **Modelos** separados en tres categorías:
  - `models.active`: llama-3.1-8b, qwen2.5-coder-14b, nomic-embed
  - `models.disabled`: qwen/qwen3.6-27b con `disabled_reason`
  - `models.discovered`: lmstudio-community/qwen2.5-coder-14b
- **Nodos** separados en dos categorías:
  - `inference_nodes.active`: RX9070 (online, primary runtime)
  - `inference_nodes.inventory`: RX7900XT (offline, future backend, `active_runtime: false`)
- **Servicios** separados en tres categorías:
  - `services.core`: gateway, router, live-api
  - `services.support`: docs, heartbeat, metrics, runner
  - `services.observability`: prometheus, grafana
- **Data quality**: nueva sección `data_quality` con `observed_fields`, `inferred_fields`, `missing_fields`
- **Report metadata**: `_report_type`, `_runtime_generation`, `_grounded_runtime`, `_grounding_confidence`

### Modificado: `runtime/prompts/report_prompt.md`

Reescritura completa del system prompt para reportes:

- Tono: TÉCNICO / OPERACIONAL / PRECISO / OBSERVACIONAL
- Estructura obligatoria de 12 secciones fijas
- Clasificación explícita: OBSERVADO / INFERIDO / NO DISPONIBLE
- Reglas: qwen3.6 es DESACTIVADO, RX7900XT es INVENTARIADO
- Prohibido: secciones dinámicas, texto redundante, HARD_FACTS, inventar datos

### Modificado: `runtime/telemetry/prometheus_metrics.py`

+3 métricas Prometheus:

- `ailab_report_model_classification_total` (labels: status)
- `ailab_report_node_classification_total` (labels: status)
- `ailab_report_data_quality_total` (labels: quality)

### Nuevo: `tests/test_report_presentation_29_4_2.py`

35+ assertions cubriendo:

- Clasificación correcta de modelos (active/disabled/discovered)
- qwen3.6 nunca en active
- Nodos activos vs inventario
- Servicios por categoría
- Data quality fields
- Report metadata
- Legacy `gpu_nodes` eliminado
- `report_prompt.md` con 12 secciones, tono correcto
- `extract_target_ip` regression

## Validación

```bash
# Tests
python3 tests/test_report_presentation_29_4_2.py

# Build Astro
cd /opt/ai-lab/apps/ialab-docs && npx astro build --log-level=info
```

## Checkpoint

`CP-29.4.2-REPORT-PRESENTATION-STABLE`
