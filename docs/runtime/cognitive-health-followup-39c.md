# FASE 39C — Cognitive Health Follow-up

Fecha: 2026-05-25

## Objetivo

Auditar consistencia operativa de `runtime/health/cognitive_health_layer.py` y aplicar solo fix minimo en caso de inconsistencia real.

## Hallazgo principal

- Inconsistencia detectada en `/runtime/health`: podia aparecer un nodo `rx9070` como `online=false` aunque el backend real `192.168.1.50` estuviera online.
- Causa: `stats_by_node()` usa claves de routing (p.ej. `rx9070`) y `get_control_nodes()` usa claves IP (p.ej. `192.168.1.50`), sin reconciliacion de alias.

## Cambio aplicado (minimo y acotado)

Archivo: `runtime/health/cognitive_health_layer.py`

- Se agrego normalizacion de claves (`_normalize_node_key`).
- Se agrego reconciliacion host->alias backend (`_build_backend_host_aliases`) leyendo `BACKENDS` en modo best-effort/fail-safe.
- `build_node_scores()` ahora:
  - enlaza stats de routing a nodos del control plane por aliases (IP, host y nombre backend),
  - marca claves de historial consumidas,
  - evita duplicar como "unknown" nodos ya reconciliados.

Resultado esperado: no duplicar `rx9070` como nodo desconocido cuando ya representa `192.168.1.50`.

## Validacion

Comando ejecutado:

```bash
/opt/ai-lab/.venv/bin/python -m pytest -q tests/test_cognitive_health_layer_37a.py tests/test_cognitive_slo_01.py tests/test_federation_cognitive_guards_01.py
```

Resultado:

- `37 passed`
- `1 warning` (deprecacion existente en `runtime/state/runtime_state.py`, fuera de alcance 39C)

Checks funcionales directos:

- `build_cognitive_health_snapshot()` pasa de 4 nodos (incluyendo `rx9070` unknown) a 3 nodos consistentes con control plane.
- `192.168.1.50` conserva estado online y ahora absorbe `success_rate` desde routing history.

## Tests nuevos/agregados

Archivo: `tests/test_cognitive_health_layer_37a.py`

- `test_build_node_scores_reconciles_history_with_control_plane_aliases`
- `test_build_node_scores_reconciles_history_with_backend_aliases`

Cobertura nueva: reconciliacion de aliases entre control plane, routing history y backend names.

## Impacto

- Sin cambios de routing ni decisiones de inferencia.
- Solo mejora de coherencia observacional en endpoints `/runtime/health*`.
- Contrato `37A-COGNITIVE-HEALTH-LAYER-01` preservado.

## FIX01 (runtime vivo)

Se detecto un gap adicional en proceso vivo: `routing_history.host` llega frecuentemente como URL completa (por ejemplo `http://192.168.1.50:1234/v1`), no solo IP/host plano.

Para cubrir ese caso real:

- Se agrego extraccion robusta de host (`_extract_host_key`) para normalizar URL -> hostname.
- Se agrego reconciliacion por aliases derivados de historial reciente (`_build_routing_host_aliases`), enlazando `node=rx9070` con `host=192.168.1.50`.

Efecto esperado en runtime:

- `rx9070` deja de aparecer como nodo independiente `unknown/offline`.
- Sus stats se absorben en `192.168.1.50`.
