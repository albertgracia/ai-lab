# INCIDENTS-WATCHDOG-DEDUP-01

## Problema detectado
El watchdog generaba incidentes `cluster_degraded` duplicados cada vez que el estado del cluster era "degraded", sin comprobar si ya existia un incidente equivalente no archivado. Esto produjo 656 puntos duplicados, limpiados en INCIDENTS-RETENTION-CLEANUP-02.

## Solucion
Implementar deduplicacion bounded por dedup_key (SHA-256 de event_type + source + severity + service + mensaje normalizado) con ventana configurable:
- `cluster_degraded`: 24h
- `service_degraded`: 1h

## Archivos creados
- `runtime/incidents/incident_dedup.py` — helper de dedup (build_dedup_key, check_and_tag, normalize_message)

## Archivos modificados
- `runtime/memory/watchdog_incident_hook.py` — integracion de dedup en cluster_degraded
- `runtime/memory/qdrant_collections.py` — schema incidents con nuevos optional_fields
- `runtime/telemetry/prometheus_metrics.py` — 3 metricas dedup (skipped, new, errors)
- `tests/test_incidents_watchdog_dedup_01.py` — 12 tests

## Dedup_key
```
sha256(event_type | source | severity | service | normalize(message))
```

## Ventanas de dedup
| Evento | Ventana |
|--------|---------|
| cluster_degraded | 24h |
| service_degraded | 1h |

## Eventos NO deduplicados
- service_down
- routing_error
- critical severity (cualquier evento)
- service_recovered

## Metricas Prometheus
- `ailab_incident_dedup_skipped_total{event_type="cluster_degraded"}`
- `ailab_incident_dedup_new_total{event_type="cluster_degraded"}`
- `ailab_incident_dedup_errors_total`

## Riesgos
- Qdrant failure: fail-safe, escribe incidente sin dedup
- False positive dedup: ventana de 24h asegura que no se pierdan eventos relevantes
- service_down no deduplicado: intencional, son eventos de servicio individuales

## Rollback
1. Revertir cambios en watchdog_incident_hook.py: eliminar bloque dedup.
2. Revertir incident_dedup.py: eliminar archivo.
3. Revertir metricas en prometheus_metrics.py.
4. Revertir qdrant_collections.py.
5. Reiniciar gateway.
