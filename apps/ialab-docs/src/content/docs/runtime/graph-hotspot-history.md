---
title: "Graph Hotspot History (37D)"
summary: "Histórico bounded de hotspots/chokepoints y drift_score determinista para detectar evolución topológica del runtime."
order: 61
---

## Qué es

**Graph Hotspot History (37D)** añade una memoria topológica **bounded** (por ventana), **determinista** y **metadata-only** sobre:

- Hotspots y chokepoints recurrentes.
- Cambios en score/severity y expansión de blast radius.
- Detección de drift arquitectónico mediante `drift_score` (0–1, fórmula fija).

No hace remediation, no muta routing y no introduce loops/daemons.

## Relación con 37B y 37C

- **37C Critical Path**: aporta `top_files`, `chokepoints`, `blast-radius` y señales por módulo.
- **37B Correlation**: aporta señales de degradación runtime correlacionadas con hotspots topológicos.

37D no recalcula la topología desde cero: **recuerda la evolución** de lo que ya exponen 37B/37C.

## Endpoints (Gateway :8008)

- `GET /runtime/hotspot-history`
- `GET /runtime/hotspot-history/summary`
- `GET /runtime/hotspot-history/latest`
- `GET /runtime/hotspot-history/trends`
- `GET /runtime/hotspot-history/recurring`
- `GET /runtime/hotspot-history/drift`
- `GET /runtime/hotspot-history/blast-radius`
- `GET /runtime/hotspot-history/recommendations`

Todos responden **HTTP 200** y payload bounded/fail-safe.

## drift_score

`drift_score` es un score determinista 0–1 basado en:

- Delta de `critical_path_score`.
- Máximo delta de score por módulo.
- Escalaciones de severity y blast radius.
- Degradación de `routing_confidence` y `health_score`.
- Incremento de unknowns.

No usa ML y no tiene pesos adaptativos.

## Bounded History

Por defecto 37D opera en **in-memory only** y mantiene un máximo acotado de snapshots.

Si solo hay 1 snapshot, 37D no inventa tendencias: devuelve `trend: "unknown"` y `unknowns: ["insufficient_history"]`.

## Qué NO hace

- No escribe en `runtime/state/*`.
- No ejecuta polling agresivo ni daemons.
- No persiste datos sin límites.
- No incluye user data, prompts ni payloads de LLM.
