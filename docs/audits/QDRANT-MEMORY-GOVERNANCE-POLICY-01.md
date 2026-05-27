# QDRANT-MEMORY-GOVERNANCE-POLICY-01

## Objetivo
Establecer la politica formal de gobernanza de memoria de AI-LAB sobre Qdrant y memoria runtime, basada en la auditoria `QDRANT-MEMORY-GOVERNANCE-AUDIT-01` (PASS).

## Base de evidencia
- Auditoria completada: `/tmp/QDRANT-MEMORY-GOVERNANCE-AUDIT-01.md`
- Qdrant endpoint: `127.0.0.1:6333`
- 8 colecciones auditadas, 5 con datos, 3 vacias.
- Sin TTL/retention en ninguna coleccion.
- `incidents` con 1,962 puntos y `resolved=false`.
- 2,437 puntos en `routing_history` en 11 dias de operacion.
- Sin instrumentacion de `memory_injected`/`chars_injected` en `cognitive_history`.
- Latencia de shaping ~6s + inferencia ~14.5s promedio.

## Estado actual de Qdrant

| Coleccion | Points | Estado | Riesgo |
|-----------|--------|--------|--------|
| agent_knowledge | 152 | Operacional | MEDIUM |
| ai_lab_memory | 3 | Operacional | LOW |
| cognitive_history | 628 | Operacional | MEDIUM |
| incidents | 1,962 | Operacional | HIGH |
| optimizer_history | 0 | Vacia/Standby | LOW |
| routing_history | 2,437 | Operacional | HIGH |
| runtime_snapshots | 0 | Vacia/Standby | LOW |
| working_memory | 0 | Vacia/Standby | LOW |

## Clasificacion de colecciones

| Coleccion | Tipo | Uso |
|-----------|------|-----|
| agent_knowledge | KNOWLEDGE_BASE | Skills, documentacion operativa, conocimiento de agentes |
| ai_lab_memory | ACTIVE_MEMORY | Memoria persistente estrategica curada |
| cognitive_history | OPERATIONAL_HISTORY | Eventos cognitivos, context shaping, decisiones |
| incidents | INCIDENT_MEMORY | Historial de incidencias operacionales |
| optimizer_history | EMPTY_STANDBY | Sin uso actual; candidato a deprecacion |
| routing_history | OPERATIONAL_HISTORY | Decisiones de routing con latencia |
| runtime_snapshots | SNAPSHOT_STORE | Sin uso actual; pendiente de diseno |
| working_memory | WORKING_MEMORY | Sin uso actual; pendiente de activacion con TTL |

## Politica de retencion

### routing_history
- Retencion sugerida: 7 dias en detalle.
- Conservar agregados historicos por dia/modelo/ruta familia.
- No conservar eventos individuales infinitamente.
- Implementar TTL en Qdrant con `timestamp` como criterio.

### incidents
- Incidentes abiertos: conservar hasta resolucion.
- Incidentes resueltos: resumir y archivar (resumen en texto, no payload completo).
- Incidentes antiguos (>14d sin tocar): revisar y clasificar como `obsolete` o `archived`.
- No inyectar incidentes con severity < HIGH ni antiguedad > 7d.

### cognitive_history
- Retencion sugerida: 14 dias para eventos detallados.
- Conservar summaries agregados por dia/task_type/modelo.
- Anadir campos de correlacion antes de considerar retencion larga.

### agent_knowledge
- Retencion manual.
- Versionado por hash de contenido.
- Preferir referencia por path/version antes que texto completo en payload.

### ai_lab_memory
- Retencion curada/manual.
- Solo memoria validada y actualizada.
- Separar `HARD_FACTS`, `INFERIDO`, `UNKNOWNS` por punto.

### working_memory
- TTL recomendado: minutos a horas.
- Nunca persistencia indefinida.
- No activar sin limites estrictos de puntos y tamano.

### runtime_snapshots
- Maximo N snapshots (sugerido: 30).
- Compactacion automatica.
- Metadata-only: sin payloads LLM, sin prompts.

### optimizer_history
- No activar hasta definir caso de uso concreto.

## Politica de inyeccion contextual

### Reglas basicas

1. Nunca inyectar colecciones completas en prompt.
2. Nunca inyectar incidentes antiguos sin resumen y clasificacion.
3. Nunca inyectar payloads con prompts de usuario completos, respuestas completas, o datos sensibles.
4. Nunca inyectar secretos, tokens, credenciales, emails, o PII.
5. Toda inyeccion de memoria debe registrar campos de telemetria (ver seccion Instrumentacion).
6. La inyeccion debe ser bounded por coleccion, matches, chars, tokens, antiguedad y confianza.

### Limites sugeridos por operacion de inyeccion

| Parametro | Limite |
|-----------|--------|
| Max collections por recall | 2 |
| Max matches por coleccion | 5 |
| Max chars totales inyectados | 2000 |
| Max antiguedad | 30 dias |
| Min confidence | 0.6 |
| Max tokens de contexto total | 4096 |

### Separacion de contenido inyectable

Cada punto inyectable debe indicar si contiene:
- `HARD_FACTS`: factual verificado
- `INFERIDO`: inferencia del sistema
- `UNKNOWNS`: informacion no disponible

## Politica de resolucion de incidentes

### Problema detectado
`incidents` tiene 1,962 puntos con `resolved=false` — la mayoria probablemente ya no relevantes.

### Estados de incidente

| Estado | Significado |
|--------|-------------|
| open | Incidente nuevo, sin investigar |
| investigating | En analisis activo |
| mitigated | Medida temporal aplicada |
| resolved | Solucion confirmada |
| archived | Cerrado y archivado |
| false_positive | No era un incidente real |
| obsolete | Ya no aplica (componente cambiado) |

### Campos minimos obligatorios

| Campo | Tipo | Requerido |
|-------|------|-----------|
| incident_id | string | Si |
| timestamp | float | Si |
| severity | string | Si |
| source | string | Si |
| affected_component | string | Si |
| resolved | bool | Si |
| resolution_status | string | Si |
| summary | string | Si |
| evidence | string (truncado) | Si |
| confidence | float | Si |
| retention_class | string | Si |

### Inyectabilidad

- Solo inyectar incidentes con severity >= HIGH.
- Solo inyectar incidentes con antiguedad < 7d.
- Solo inyectar si relacionado con endpoint/modelo/ruta actual.
- Evidence suficiente y sin datos sensibles.

## Politica de trazabilidad de decisiones

### Campos minimos por evento de decision

| Campo | Descripcion |
|-------|-------------|
| decision_id | Identificador unico de decision |
| session_id | Sesion de usuario |
| trace_id | Trazabilidad distribuida |
| request_id | Request HTTP |
| timestamp | Unix timestamp |
| route_family | Familia de ruta |
| model | Modelo seleccionado |
| node | Nodo de inferencia |
| reason_codes | Codigos de razon de routing |
| authority_used | Fuente de autoridad |
| memory_used | Si se uso memoria |
| collections_used | Colecciones consultadas |
| prompt_tokens | Tokens de prompt |
| completion_tokens | Tokens generados |
| total_tokens | Suma |
| latency_ms | Latencia total |
| ttfb_ms | Time to first token |
| success | Booleano exitoso |
| error_type | Tipo de error si fallo |
| confidence | Confianza de la decision |
| hard_facts | Facts verificados usados |
| inferred | Inferencias usadas |
| unknowns | Lo que no se sabia |

## Seguridad y privacidad

### Niveles de riesgo

| Nivel | Descripcion | Ejemplos |
|-------|-------------|----------|
| LOW | Metadata tecnica sin contenido sensible | timestamps, scores, IDs internos |
| MEDIUM | Contenido parcial con contexto interno | prompts truncados, textos de skills, paths |
| HIGH | Datos operativos detallados | logs extensos, prompts completos, IPs con contexto |
| CRITICAL | Secretos activos | tokens, credenciales, API keys, PII |

### Reglas de seguridad

1. Nunca indexar ni almacenar secretos en Qdrant.
2. Truncar payloads textuales a 1024 caracteres como maximo.
3. Hash/versionar documentos largos; almacenar solo referencia.
4. Preferir path + hash antes que texto completo en payload.
5. No inyectar contenido de nivel HIGH o CRITICAL en prompts.
6. Auditoria periodica de payloads almacenados (recomendado: mensual).

## Riesgos actuales

| Riesgo | Severidad | Accion |
|--------|-----------|--------|
| Sin TTL en ninguna coleccion | HIGH | Implementar TTL en routing_history, incidents, cognitive_history |
| 1,962 incidentes sin resolver | HIGH | Revisar, clasificar y archivar incidentes |
| 3 colecciones vacias ocupando schema | MEDIUM | Evaluar si eliminar o mantener como standby |
| agent_knowledge con texto completo en payload | MEDIUM | Migrar a referencias path+hash |
| Sin instrumentacion de inyeccion de memoria | MEDIUM | Anadir memory_injected/chars_injected a cognitive_history |
| routing_history sin prompt_tokens | MEDIUM | Anadir prompt_tokens para correlacion con latencia |
| cognitive_history sin correlacion con latencia de inferencia | MEDIUM | Vincular con routing_history por timestamp/request_id |
| ai_lab_memory solo 3 puntos, posiblemente obsoleto | LOW | Revisar y actualizar contenido |

## Reglas de NO inyeccion

1. NO inyectar colecciones completas.
2. NO inyectar incidents sin filtrar por severity y antiguedad.
3. NO inyectar working_memory sin TTL.
4. NO inyectar cognitive_history en prompts (es historico, no memoria activa).
5. NO inyectar routing_history en prompts (es auditoria, no conocimiento).
6. NO inyectar payloads con contenido HIGH/CRITICAL.
7. NO inyectar agent_knowledge sin bounded matches y chars.
8. NO inyectar contenido sin clasificacion HARD_FACTS/INFERIDO/UNKNOWNS.

## Reglas de caducidad

| Coleccion | Accion | Timeline |
|-----------|--------|----------|
| routing_history | Borrar eventos detallados > 7d, conservar agregados | Proxima fase |
| incidents | Archivar incidentes > 30d sin cambios | Proxima fase |
| cognitive_history | Borrar eventos > 14d, conservar agregados | Proxima fase |
| agent_knowledge | Versionar y deduplicar por hash | Proxima fase |
| ai_lab_memory | Revision manual de vigencia | Proxima fase |
| working_memory | No activar sin TTL | Antes de activar |
| runtime_snapshots | No activar sin diseno de retencion | Antes de activar |
| optimizer_history | Evaluar deprecacion si no se usa en 60d | Proxima fase |

## Reglas de limpieza futura

1. INCIDENTS-RETENTION-CLEANUP-01: clasificar incidents, detectar duplicados, archivar resueltos/obsoletos.
2. ROUTING-HISTORY-RETENTION-01: implementar TTL, generar agregados diarios por modelo/ruta.
3. AGENT-KNOWLEDGE-DEDUP-01: reemplazar texto completo por referencias path+hash.
4. EMPTY-COLLECTIONS-EVALUATION-01: decidir destino de optimizer_history, runtime_snapshots, working_memory.

## Instrumentacion necesaria

### cognitive_history — campos a agregar

| Campo | Tipo | Proposito |
|-------|------|-----------|
| memory_injected | bool | Si se inyecto memoria en esta request |
| chars_injected | int | Caracteres inyectados |
| collections_used | list[str] | Colecciones consultadas |
| matches | int | Total de matches retornados por Qdrant |
| avg_score | float | Score promedio de matches |
| max_score | float | Score maximo |
| prompt_tokens_before | int | Tokens antes de inyeccion |
| prompt_tokens_after | int | Tokens despues de inyeccion |
| route_family | string | Familia de ruta |
| ttfb_ms | float | Time to first token de inferencia |
| latency_ms | float | Latencia total de inferencia |
| truncation | bool | Si hubo truncamiento |
| fallback | bool | Si se uso fallback |

### routing_history — campos a agregar

| Campo | Tipo | Proposito |
|-------|------|-----------|
| prompt_tokens | int | Tokens de prompt enviados |
| route_family | string | Familia de ruta asignada |
| time_to_first_token_ms | float | TTFB desde LM Studio |
| generation_time_ms | float | Tiempo de generacion |
| tokens_per_second | float | Velocidad de generacion |

## Fases recomendadas

| Fase | Prioridad | Descripcion |
|------|-----------|-------------|
| INCIDENTS-RETENTION-CLEANUP-01 | ALTA | Clasificar, archivar y resolver incidents |
| ROUTING-HISTORY-RETENTION-01 | ALTA | Implementar TTL y agregados en routing_history |
| MEMORY-INJECTION-TELEMETRY-01 | ALTA | Instrumentar memory_injected/chars_injected |
| AGENT-KNOWLEDGE-DEDUP-01 | MEDIA | Reemplazar texto completo por referencias |
| EMPTY-COLLECTIONS-EVALUATION-01 | MEDIA | Decidir destino de colecciones vacias |
| WORKING-MEMORY-ACTIVATION-01 | BAJA | Disenar working_memory con TTL |
| RUNTIME-SNAPSHOTS-PERSISTENCE-01 | BAJA | Disenar snapshots bounded |
| OPTIMIZER-HISTORY-DEPRECATE-01 | BAJA | Deprecar si no se usa en 60d |

## HARD_FACTS

- Qdrant operativo en `127.0.0.1:6333` con 8 colecciones.
- 5 colecciones con datos: agent_knowledge (152), ai_lab_memory (3), cognitive_history (628), incidents (1,962), routing_history (2,437).
- 3 colecciones vacias: optimizer_history (0), runtime_snapshots (0), working_memory (0).
- Sin TTL, sin replicacion, sin sharding en ninguna coleccion.
- 2,437 puntos en routing_history acumulados en 11 dias (~222 pts/dia).
- 1,962 puntos en incidents todos con `resolved=false`.
- Latencia de context_shaping ~6s en cognitive_history.
- Latencia de inferencia promedio ~14.5s en routing_history.
- agent_knowledge almacena texto completo de skills/agents en payload (vector 768).
- ai_lab_memory usa vector de 384 dimensiones (nomic-embed), diferente del resto.

## INFERIDO

- Las colecciones vacias son artifacts de fases anteriores que nunca se implementaron por completo.
- incidents funciona como log operacional, no como memoria de incidentes activos. El campo `resolved` nunca se actualiza.
- cognitive_history registra context shaping pero no la inyeccion real de memoria — falta telemetria.
- La latencia alta observada en RUNTIME-LATENCY-TRIAGE-01 no es causada directamente por Qdrant, pero no se puede descartar sin instrumentacion de `memory_injected`.
- agent_knowledge probablemente se cargo una vez y no se actualiza periodicamente (no hay timestamp por punto).
- routing_history contiene datos que duplican metricas Prometheus, pero con mayor granularidad por request.

## UNKNOWNS

- No se sabe si agent_knowledge o ai_lab_memory se consultan activamente durante `context_shaping` en requests actuales.
- No se sabe cuantas colecciones vacias deberian estar pobladas y no lo estan por bug vs diseno intencional.
- No se sabe si el watchdog de incidents sigue activo generando nuevos puntos o la coleccion esta estancada.
- No se sabe el volumen exacto de chars/tokens que inyectaria cada coleccion si se usara para recall.
- No se sabe si hay contenido de agent_knowledge desactualizado respecto al filesystem actual.

## Criterios de exito para futuras fases

| Fase | PASS si... |
|------|------------|
| INCIDENTS-RETENTION-CLEANUP-01 | Se clasifican todos los incidents, se resuelven/archivan los no relevantes, campo `resolved` se actualiza |
| ROUTING-HISTORY-RETENTION-01 | TTL implementado, agregados diarios generados, sin perdida de capacidad de auditoria |
| MEMORY-INJECTION-TELEMETRY-01 | `memory_injected`, `chars_injected`, `collections_used` aparecen en cognitive_history |
| AGENT-KNOWLEDGE-DEDUP-01 | agent_knowledge usa referencias path+hash, payload reducido, timestamp por punto |
| EMPTY-COLLECTIONS-EVALUATION-01 | Decision documentada para cada coleccion vacia (activar, deprecar, mantener standby) |

## Conclusion

La memoria Qdrant de AI-LAB tiene senal real en 5 de 8 colecciones pero carece de gobierno de retencion, instrumentacion de inyeccion, y trazabilidad de decisiones. Los riesgos principales son crecimiento sin limite (routing_history), acumulacion de incidentes no resueltos (incidents), y falta de visibilidad sobre cuanto contexto inyecta la memoria en los prompts. La politica aqui definida establece las bases para resolver estos problemas en fases sucesivas, priorizando retencion, telemetria y limpieza antes de nuevas funcionalidades de memoria.
