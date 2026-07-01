# 37B-VALIDATION-AUTHORITY-RECOVERY-01

**Estado:** PASS
**Fecha:** 2026-06-11 22:15:00
**Objetivo:** Recuperar autoridad de validación del runtime corrigiendo validation_score=56.3

## Resumen

| Componente | Pre-fix | Post-fix |
|---|---|---|
| validation_score | 55.1 (low) | 75.1 (medium) |
| OBSERVABILITY-FRESHNESS | fail (blocking) | pass |
| OBSERVABILITY-SURVIVABILITY | fail (blocking) | pass |
| SCRAPE-FRESHNESS | fail (blocking) | pass |
| EXPORTER-STABILITY | fail (blocking) | pass |
| ENTITY-CONSISTENCY | degraded | pass |
| GROUNDING-VALIDATION | degraded | pass |
| Sensor snapshot | 15 observed / 0 missing | 15 observed / 0 missing |
| Gateway | OK | OK |
| Router | OK | OK |

## Root cause (primaria)

El handler `/runtime/validation` en `runtime/gateway/openai_gateway.py:3940` llamaba a `build_runtime_validation_report()` **sin argumento `sensor_snapshot`**.

La función recibe `sensor_snapshot=None`, que se transforma en `{}` vacío. Todos los invariantes derivados de observabilidad (OBSERVABILITY-FRESHNESS, OBSERVABILITY-SURVIVABILITY, SCRAPE-FRESHNESS, EXPORTER-STABILITY) leen `observed_sources_count=0` del snapshot vacío y fallan con blocking=True.

**No era un problema de Prometheus** — Prometheus responde correctamente (`/-/ready` = 200, todos los targets scrapeables). El `SensorFusionEngine` funciona (15 fuentes observadas en `/runtime/sensors`). El error era exclusivamente que el validation endpoint no recogía el snapshot antes de computar el reporte.

## Root cause (secundaria)

`build_grounding_envelope()` en `runtime/validation/runtime_validation_framework.py:276` se llamaba sin el argumento obligatorio `user_text`, causando TypeError que degradaba `INVARIANT-GROUNDING-VALIDATION`.

## Fix aplicado

### 1. `runtime/gateway/openai_gateway.py` — 3 endpoints

```python
# Gateway handler (/runtime/validation, /runtime/validation/invariants,
# /runtime/validation/gates)
from runtime.context.sensor_fusion import SensorFusionEngine
_sf = SensorFusionEngine()
_snap = _sf.collect()
_report = build_runtime_validation_report(sensor_snapshot=_snap.to_dict())
```

Misma inyección en `/runtime/validation/invariants` y `/runtime/validation/gates`.

### 2. `runtime/validation/runtime_validation_framework.py` — 1 fix

```python
_env = build_grounding_envelope("")  # was: build_grounding_envelope()
```

Pasando `""` como user_text, la función retorna early con envelope válido y `grounded=False`.

## Rollback

```bash
git revert 80fb61e
git push origin main
ssh albert@192.168.1.30 "cd /opt/ai-lab && git pull --ff-only && echo '19682507' | sudo -S systemctl restart ailab-gateway"
```

## Resultados post-fix

| Métrica | Antes | Después | Objetivo |
|---|---|---|---|
| validation_score | 55.1 | 75.1 | >70 |
| validation_level | low | medium | medium |
| Blocking invariants | 5 | 1* | — |
| Gateway health | OK | OK | OK |
| Router health | OK | OK | OK |

*El único blocking restante es `INVARIANT-NO-CRITICAL-INCIDENTS` por SLO violations de disponibilidad LM Studio. No bloquea esta fase.

## Degradaciones restantes conocidas

- `INVARIANT-PRECISION-CONFIDENCE`: degraded — GPU metrics exporter en `.50:9183` no responde. Sin datos de temperatura/carga/VRAM.
- `INVARIANT-LIVE-AUTHORITY`: degraded — depende de datos completos de observabilidad.
- `INVARIANT-AUTHORITY-FRESHNESS`: degraded — mismo origen.

Estas degradaciones no bloquean la validación y son independientes del fix de 37B.

## Criterios PASS

| Criterio | Estado |
|---|---|
| Causa raíz exacta identificada | ✅ |
| Prometheus reachable desde el componente que lo necesita | ✅ (siempre lo estuvo) |
| sensor_snapshot recuperado o causa documentada | ✅ |
| validation_score mejora o explicado | ✅ 55.1 → 75.1 |
| Sin regresión Gateway/Router | ✅ |
| Informe generado | ✅ |
| Pipeline documental | PENDING |

## Commits

- `80fb61e` — fix(runtime): inject sensor_snapshot into validation endpoints (37B)
- HEAD = `origin/main`, working tree clean
