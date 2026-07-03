# GITNEXUS-FIRST-ACTIVATION-01 — Activación de Política GITNEXUS-FIRST

**Fecha:** 2026-07-03
**Estado:** PASS ✅

---

## Resumen

Se activa la política **GITNEXUS-FIRST** como doctrina oficial de consulta pre-cambio para AI-LAB. Esta política establece que antes de modificar cualquier componente crítico del runtime, es obligatorio consultar GitNexus para análisis de impacto, contexto y dependencias.

## Prerrequisitos cumplidos

| Fase | Estado | Resultado |
|------|--------|-----------|
| GITNEXUS-AILAB-INTEGRATION-01 | ✅ PASS | Auditoría completa del índice |
| GITNEXUS-AILAB-REINDEX-FIX-01 | ✅ PASS | Corrección de cobertura + reindex |
| `runtime/gateway/` cobertura | ✅ 100% | 7/7 archivos indexados |
| `runtime/router/` cobertura | ✅ 100% | Todos los archivos indexados |
| `openai_gateway.py` indexado | ✅ | `GatewayHandler` encontrado con 19 imports, 7 métodos |
| `ElasticComputePool` indexado | ✅ | Impact analysis detecta 12 referencias |
| Cross-file gateway→router | ✅ | `get_pool_status` → `GatewayHandler.do_GET` detectado |
| Backups excluidos | ✅ | `.bak`, `.backup` excluidos del índice |

## Documento actualizado

| Documento | Cambio |
|-----------|--------|
| `AGENTS.md` | Nueva sección **GITNEXUS-FIRST — Política Oficial de Consulta Pre-Cambio** insertada antes del bloque auto-generado de GitNexus |
| `AGENTS.md` | Estadísticas del índice actualizadas (27,124 nodes, 42,819 edges, 586 clusters) |

## Política añadida

### Título

**GITNEXUS-FIRST — Política Oficial de Consulta Pre-Cambio**

### Alcance

| Componente | Rutas |
|------------|-------|
| Router | `runtime/router/` |
| Gateway | `runtime/gateway/` |
| Runtime core | `runtime/*.py`, `runtime/**/*.py` |
| Scheduler | `runtime/nodes/scheduler.py` |
| Elastic Pool | `runtime/router/elastic_pool.py` |
| Marketplace Backend | `apps/marketplace/` (backend) |
| Marketplace Frontend | `apps/marketplace/` (frontend) |
| IDS | `runtime/intrusion/` |
| Hermes | `apps/hermes/` |

### Consultas obligatorias

1. `gitnexus_impact({target, direction: "upstream"})`
2. `gitnexus_impact({target, direction: "downstream"})`
3. `gitnexus_context({name})`
4. `gitnexus_detect_changes()` (pre-commit)
5. `gitnexus_route_map()` (si aplica a rutas API)
6. `gitnexus_shape_check()` (si aplica a rutas API)

### Flujo

```
1. Identificar componente/símbolo a modificar
2. Ejecutar impact() + context() obligatorios
3. Reportar blast radius al usuario
4. Si risk=HIGH/CRITICAL → aprobación explícita
5. Implementar cambio
6. Ejecutar detect_changes() pre-commit
7. Solo entonces commitear
```

### Excepciones

- Cambios puramente cosméticos (comentarios, whitespace, formatting)
- Archivos de configuración (`*.json`, `*.yaml`, `*.env`)
- Tests (`tests/`) — no requieren consulta pre-cambio
- Documentación (`docs/`, `reports/`, `*.md`) — no requieren consulta

### Incumplimiento

1. Reversión inmediata del cambio
2. Ejecución retrospectiva del análisis omitido
3. Documentación del incidente en `reports/`

## Riesgos

| Riesgo | Mitigación |
|--------|-----------|
| Falso sentido de seguridad si el índice está stale | La política exige verificar `gitnexus status` primero |
| Consultas costosas en tiempo para cambios pequeños | Excepciones para cambios cosméticos/config/docs/tests |
| Dependencia de disponibilidad del servidor GitNexus | La política aplica "best effort"; si GitNexus no responde, documentar la limitación |
| Fragmentación de comunidades (Gateway 13, Router 11) | No bloquea — la cohesión intra-comunidad es alta, el análisis de impacto cross-file funciona |

## Próximos pasos

1. Push a GitHub para sincronizar `AGENTS.md` actualizado
2. Pull en servidor para que `reports/` sea visible en el índice
3. Reindexar en servidor para incluir `reports/`
4. Comunicar la política al equipo/agentes

## Resultado final

**PASS ✅**

| Item | Valor |
|------|-------|
| Documento actualizado | `AGENTS.md` |
| Política añadida | GITNEXUS-FIRST — sección completa con alcance, consultas, flujo, excepciones |
| Commit | `docs(governance): activate GitNexus-first policy` |
| Ruta del informe | `reports/GITNEXUS-FIRST-ACTIVATION-01.md` |
| Componentes afectados | Router, Gateway, Runtime, Scheduler, Elastic Pool, Marketplace, IDS, Hermes (solo gobernanza) |
| Archivos modificados | 1 (`AGENTS.md`) |
| Archivos nuevos | 1 (`reports/GITNEXUS-FIRST-ACTIVATION-01.md`) |
