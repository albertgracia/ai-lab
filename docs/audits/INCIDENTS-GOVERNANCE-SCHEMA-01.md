# INCIDENTS-GOVERNANCE-SCHEMA-01

## Objetivo
Formalizar schema de gobernanza para incidentes futuros en Qdrant, sin migrar historico.

## Relacion con fases previas
- INCIDENTS-RETENTION-CLEANUP-02: archivo 656 cluster_degraded historicos
- INCIDENTS-WATCHDOG-DEDUP-01: dedup para nuevos cluster_degraded
- Esta fase: schema builder + defaults para todos los nuevos incidentes watchdog

## Schema final (incidentes futuros)

| Campo | Tipo | Default | Descripcion |
|-------|------|---------|-------------|
| incident_id | string | WD-{uuid} | Identificador unico |
| schema_version | string | INCIDENTS-GOVERNANCE-SCHEMA-01 | Version del schema |
| event_type | string | (obligatorio) | cluster_degraded, service_down, etc. |
| timestamp | float | time.time() | Unix timestamp |
| severity | string | (obligatorio) | warning, info, critical |
| source | string | watchdog | Origen del incidente |
| message | string | (obligatorio) | Truncado a 500 chars |
| resolved | bool | false | Estado de resolucion |
| resolution_status | string | open | open/resolved/archived/etc. |
| retention_class | string | operational_signal | Clase de retencion |
| archived | bool | false | Archivado |
| duplicate_count | int | 0 | Contador de duplicados |
| first_seen_at | float | timestamp | Primera aparicion |
| last_seen_at | float | timestamp | Ultima aparicion |
| affected_component | string | service o node | Componente afectado |
| dedup_key | string | (opcional) | Clave SHA-256 de dedup |

## resolution_status
- open, investigating, mitigated, resolved, archived, archived_duplicate, false_positive, obsolete

## retention_class por event_type
| event_type | retention_class |
|------------|-----------------|
| cluster_degraded | degraded_signal |
| service_degraded | degraded_signal |
| service_down | down_signal |
| service_recovered | recovered_signal |
| routing_error | routing_error |
| cualquier critical | critical_keep |
| otro | operational_signal |

## Compatibilidad
- Payloads antiguos sin schema_version/governance siguen siendo validos
- watchdog_incident_hook usa schema builder si disponible, fallback a schema antiguo

## Seguridad
- No se guardan prompts completos
- No se guardan respuestas completas
- No se guardan datos sensibles
- Mensaje truncado a 500 chars maximo

## Archivos
- `runtime/incidents/incident_schema.py` (NUEVO) — schema builder
- `runtime/memory/watchdog_incident_hook.py` (modificado) — integra schema builder
- `runtime/memory/qdrant_collections.py` (modificado) — optional_fields actualizados
- `tests/test_incidents_governance_schema_01.py` (NUEVO) — 18 tests
