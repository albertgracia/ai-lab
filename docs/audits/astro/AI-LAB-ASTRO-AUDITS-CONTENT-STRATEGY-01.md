# AI-LAB-ASTRO-AUDITS-CONTENT-STRATEGY-01

**Fecha:** 2026-05-31
**Modo:** READ ONLY / PLAN
**Basado en:** AI-LAB-ASTRO-SIDEBAR-REALIGNMENT-01 (commit feb19169)
**Resultado:** PASS

---

## 1. Resumen

Fase READ-ONLY de análisis y estrategia para integrar los 28 informes de auditoría en `docs/audits/` dentro de la documentación Starlight, sin mover ni copiar documentos. Se completó inventario, clasificación, comparativa de estrategias y recomendación.

## 2. Estado base

| Item | Valor |
|------|-------|
| Repo | /opt/ai-lab |
| Rama | main |
| HEAD | feb19169 |
| Sidebar actual | 5 secciones (sin Audits) |
| Riesgo documentado | Sección Audits no implementada |

## 3. Inventario completo — 28 auditorías

### Astro Documentation (7 informes)

| Archivo | Tamaño | Líneas | Tracked | Temática |
|---------|--------|--------|---------|----------|
| AI-LAB-ASTRO-CONSOLIDATION-PHASES-01-MANIFEST.md | 3.7K | 60 | Sí | Manifiesto de consolidación de fases |
| AI-LAB-ASTRO-CONSOLIDATION-PHASES-01.md | 2.5K | 66 | Sí | Reporte de consolidación de fases |
| AI-LAB-ASTRO-DOCUMENTATION-CLEANUP-APPLY-01.md | 2.4K | 60 | No | Ejecución de limpieza documental |
| AI-LAB-ASTRO-DOCUMENTATION-CLEANUP-PLAN-01.md | 14K | 191 | No | Plan de limpieza (30 acciones) |
| AI-LAB-ASTRO-DOCUMENTATION-INVENTORY-01.md | 9.2K | 233 | No | Inventario de 307 archivos |
| AI-LAB-ASTRO-INFORMATION-ARCHITECTURE-01.md | 20K | 433 | No | Diseño de arquitectura de información |
| AI-LAB-ASTRO-SIDEBAR-REALIGNMENT-01.md | 4.1K | 90 | Sí | Realineamiento de sidebar |

### Observabilidad / Monitoring (8 informes)

| Archivo | Tamaño | Líneas | Tracked | Temática |
|---------|--------|--------|---------|----------|
| AI-LAB-DASHBOARD-DRIFT-AUDIT-01.md | 13K | 276 | No | Drift en dashboards Grafana (156 paneles) |
| AI-LAB-GRAFANA-PROVISIONING-VALIDATION-01.md | 2.4K | 73 | No | Validación de provisioning |
| AI-LAB-HEALTH-SCORE-DASHBOARD-ALIGNMENT-01.md | 5.9K | 143 | Sí | Alineación de health score |
| AI-LAB-HEALTH-SCORE-DRIFT-RULE-01.md | 6.4K | 224 | Sí | Regla de drift |
| AI-LAB-HEALTH-SCORE-SOURCE-OF-TRUTH-01.md | 13K | 322 | No | Source of truth de health score |
| AI-LAB-OBSERVABILITY-RECOVERY-SUMMARY-01.md | 9.8K | 258 | No | Recuperación de observabilidad |
| AI-LAB-PROMETHEUS-RUNTIME-HEALTH-RECORDING-RULE-01.md | 6.0K | 144 | Sí | Recording rules Prometheus |
| AI-LAB-PROMETHEUS-RUNTIME-HEALTH-RECORDING-RULE-FIX-01.md | 5.8K | 191 | Sí | Fix de recording rules |

### GitNexus / Codebase (2 informes)

| Archivo | Tamaño | Líneas | Tracked | Temática |
|---------|--------|--------|---------|----------|
| GITNEXUS-EXECSTARTPRE-NAPI-ERROR-TRIAGE-01.md | 4.0K | 78 | Sí | Triage de error NAPI |
| GITNEXUS-GOVERNED-RUNTIME-CHANGE-POLICY-01.md | 5.5K | 184 | Sí | Política de cambios en runtime |

### Incidentes (2 informes)

| Archivo | Tamaño | Líneas | Tracked | Temática |
|---------|--------|--------|---------|----------|
| INCIDENTS-GOVERNANCE-SCHEMA-01.md | 2.6K | 60 | Sí | Schema de governance de incidentes |
| INCIDENTS-WATCHDOG-DEDUP-01.md | 2.0K | 52 | Sí | Dedup de watchdog |

### Memoria / Qdrant (3 informes)

| Archivo | Tamaño | Líneas | Tracked | Temática |
|---------|--------|--------|---------|----------|
| MEMORY-INJECTION-QDRANT-PERSISTENCE-FIX-01.md | 1.3K | 46 | Sí | Fix de persistencia Qdrant |
| MEMORY-INJECTION-TELEMETRY-01.md | 4.6K | 110 | Sí | Telemetría de inyección |
| QDRANT-MEMORY-GOVERNANCE-POLICY-01.md | 15K | 332 | Sí | Política de governance Qdrant |

### Release / Runtime (6 informes)

| Archivo | Tamaño | Líneas | Tracked | Temática |
|---------|--------|--------|---------|----------|
| POST-RELEASE-SLO-DRIFT-WATCH-40A.md | 4.3K | 190 | Sí | Monitoreo post-release SLO |
| RELEASE-CLOSE-39E.md | 1.6K | 45 | Sí | Cierre de release |
| RUNTIME-DEEP-AUDIT-01-SUMMARY.md | 1.2K | 69 | Sí | Resumen de auditoría runtime |
| RUNTIME-DEEP-AUDIT-01.md | 5.3K | 140 | Sí | Auditoría profunda de runtime |
| RUNTIME-STABILITY-SNAPSHOT-01.md | 3.6K | 80 | Sí | Snapshot de estabilidad |
| RUNTIME-STABILITY-SNAPSHOT-38D.md | 2.2K | 113 | Sí | Snapshot de estabilidad (fase 38D) |

## 4. Análisis de sensibilidad

| Categoría | Hallazgo | Riesgo |
|-----------|----------|--------|
| IPs internas | Presentes en 15/28 archivos (192.168.1.x, 10.x) | Bajo — IPs privadas no enrutables |
| Secretos/passwords | 0 ocurrencias reales de credenciales | Ninguno |
| Rutas internas (/opt/, /etc/) | Presentes en 8 archivos | Bajo — paths de infra estándar |
| Hostnames internos | labrazahome.com, ai-lab.labrazahome.com | Bajo — ya expuestos en site URL |
| Datos operativos detallados | PromQL queries, panel IDs, recording rules | Bajo — útiles para operadores |
| Logs de error | Presentes en informes de triage | Bajo — sin datos de usuario |

**Conclusión:** Ningún informe contiene secretos, tokens, claves API, contraseñas ni datos personales. Toda la información es técnica-operativa. El sitio ya es privado (acceso vía tunnel Cloudflare).

## 5. Clasificación por tipo (A/B/C/D)

### Categoría A — Publicables en Starlight como resumen
Informes de documentación/documentación estructural, útiles para navegación permanente.

| # | Archivo | Justificación |
|---|---------|---------------|
| 1 | AI-LAB-ASTRO-CONSOLIDATION-PHASES-01-MANIFEST.md | Registro permanente de consolidación |
| 2 | AI-LAB-ASTRO-CONSOLIDATION-PHASES-01.md | Reporte de fase completada |
| 3 | AI-LAB-ASTRO-DOCUMENTATION-CLEANUP-APPLY-01.md | Historial de limpieza |
| 4 | AI-LAB-ASTRO-DOCUMENTATION-CLEANUP-PLAN-01.md | Plan de reorganización |
| 5 | AI-LAB-ASTRO-DOCUMENTATION-INVENTORY-01.md | Inventario base de documentación |
| 6 | AI-LAB-ASTRO-INFORMATION-ARCHITECTURE-01.md | Blueprint de arquitectura IA |
| 7 | AI-LAB-ASTRO-SIDEBAR-REALIGNMENT-01.md | Reporte de sidebar final |
| 8 | AI-LAB-OBSERVABILITY-RECOVERY-SUMMARY-01.md | Resumen multi-fase de observabilidad |
| 9 | RUNTIME-DEEP-AUDIT-01-SUMMARY.md | Resumen ejecutivo de auditoría runtime |

**Total: 9 informes** — todos estables, permanentes, sin sensibilidad.

### Categoría B — Enlazables internamente, no copiables
Informes operativos detallados, útiles como referencia desde índices.

| # | Archivo | Justificación |
|---|---------|---------------|
| 10 | AI-LAB-DASHBOARD-DRIFT-AUDIT-01.md | Análisis panel-por-panel (13K) |
| 11 | AI-LAB-GRAFANA-PROVISIONING-VALIDATION-01.md | Validación técnica de provisioning |
| 12 | AI-LAB-HEALTH-SCORE-DASHBOARD-ALIGNMENT-01.md | Alineación de dashboards |
| 13 | AI-LAB-HEALTH-SCORE-DRIFT-RULE-01.md | Regla específica de drift |
| 14 | AI-LAB-HEALTH-SCORE-SOURCE-OF-TRUTH-01.md | Fuente de verdad de health score (13K) |
| 15 | AI-LAB-PROMETHEUS-RUNTIME-HEALTH-RECORDING-RULE-01.md | Recording rules operativas |
| 16 | AI-LAB-PROMETHEUS-RUNTIME-HEALTH-RECORDING-RULE-FIX-01.md | Fix de reglas Prometheus |

**Total: 7 informes** — detallados, operativos, referencia útil.

### Categoría C — Solo archivo técnico interno
Informes demasiado específicos, temporales, o con ruido operativo para exposición en Starlight.

| # | Archivo | Justificación |
|---|---------|---------------|
| 17 | GITNEXUS-EXECSTARTPRE-NAPI-ERROR-TRIAGE-01.md | Triage de error puntual, temporal |
| 18 | GITNEXUS-GOVERNED-RUNTIME-CHANGE-POLICY-01.md | Política interna, cambia con el tiempo |
| 19 | INCIDENTS-GOVERNANCE-SCHEMA-01.md | Schema de incidentes, detalle operativo |
| 20 | INCIDENTS-WATCHDOG-DEDUP-01.md | Fix de dedup temporal |
| 21 | MEMORY-INJECTION-QDRANT-PERSISTENCE-FIX-01.md | Fix específico de Qdrant |
| 22 | MEMORY-INJECTION-TELEMETRY-01.md | Telemetría de inyección |
| 23 | QDRANT-MEMORY-GOVERNANCE-POLICY-01.md | Política extensa de Qdrant (15K) |
| 24 | POST-RELEASE-SLO-DRIFT-WATCH-40A.md | Watch post-release temporal |
| 25 | RELEASE-CLOSE-39E.md | Cierre de release, temporal |
| 26 | RUNTIME-DEEP-AUDIT-01.md | Auditoría detallada (5.3K) |
| 27 | RUNTIME-STABILITY-SNAPSHOT-01.md | Snapshot de estabilidad |
| 28 | RUNTIME-STABILITY-SNAPSHOT-38D.md | Snapshot de estabilidad |

**Total: 12 informes** — operativos/temporales, mantener en docs/audits/.

### Categoría D — Candidatos a resumen sanitizado
Ninguno identificado. Todos los informes Categoría A son directamente publicables.

## 6. Comparativa de estrategias

### Estrategia 1 — Mantener docs/audits/ fuera de Starlight

| Aspecto | Evaluación |
|---------|------------|
| Pros | Riesgo cero, duplicación cero, esfuerzo cero |
| Contras | Sección Audits invisible en sidebar, informes solo accesibles vía repo |
| Riesgos | Navegación documental incompleta, blueprint IA con sección faltante |
| Cuándo usarla | Si el costo de implementar supera el beneficio de navegabilidad |

### Estrategia 2 — Crear src/content/docs/audits/index.md con resúmenes

| Aspecto | Evaluación |
|---------|------------|
| Pros | Muy bajo esfuerzo (1 página), sin copia de contenido, sidebar funcional |
| Contras | No enlaza a informes completos (fuera de content collection), mantenimiento manual |
| Riesgos | Mínimos — solo crear un index.md y añadirlo al sidebar |
| Cuándo usarla | AHORA — para habilitar sección Audits sin mover contenido |

### Estrategia 3 — Copiar auditorías seleccionadas a src/content/docs/audits/

| Aspecto | Evaluación |
|---------|------------|
| Pros | Documentos completos bajo Starlight, navegación rica |
| Contras | Duplicación, divergencia de versiones, sidebar crece, esfuerzo medio |
| Riesgos | Medio — archivos duplicados pueden quedar desincronizados |
| Cuándo usarla | Solo para informes estables y definitivos (ninguno cumple aún) |

### Estrategia 4 — Crear páginas sanitizadas por categoría

| Aspecto | Evaluación |
|---------|------------|
| Pros | Contenido curado, UX profesional, sin datos operativos crudos |
| Contras | Esfuerzo alto (categorizar + resumir + mantener), sobreingeniería para v1 |
| Riesgos | Bajo — pero esfuerzo no justificado para el volumen actual |
| Cuándo usarla | En una fase futura si la sección Audits crece significativamente |

## 7. Recomendación

### Estrategia principal: Estrategia 2 — Índice de auditorías en Starlight

Crear `src/content/docs/audits/index.md` con tabla resumen de los 28 informes, clasificados por categoría (A/B/C). Cada entrada incluye nombre, breve descripción y categoría.

Modificar `astro.config.mjs` para añadir sección "Audits" en sidebar:
```js
{
  label: "Audits",
  collapsed: false,
  items: [
    { label: "Audit Index", link: "/audits/" },
    { label: "Documentation", autogenerate: { directory: "audits" } },
  ],
}
```

**Justificación:**
- Riesgo mínimo (1 página nueva + 1 entrada en sidebar)
- Sin duplicación de contenido
- Sin exponer datos operativos crudos
- Navegación profesional con sección Audits completa
- Esfuerzo: ~1 hora (redactar índice + configurar sidebar + build + commit)

### Estrategia secundaria: Estrategia 1 — Status quo

Mantener `docs/audits/` fuera de Starlight si:
- La prioridad de implementar Audits es baja
- El equipo prefiere navegar auditorías directamente en el repo
- El blueprint de 6 secciones no es vinculante

## 8. Propuesta de siguiente fase

### AI-LAB-ASTRO-AUDITS-INDEX-01

**Alcance exacto:**
1. Crear `src/content/docs/audits/index.md` con tabla resumen de los 28 informes clasificados (A/B/C), cada uno con nombre, descripción 1-línea y categoría.
2. Modificar `apps/ialab-docs/astro.config.mjs` para añadir sección "Audits" al sidebar apuntando a `/audits/`.
3. `npm run build` para validar.
4. Commit local.

**Archivos que tocaría:**
- `apps/ialab-docs/astro.config.mjs` (añadir sección Audits al sidebar)
- `src/content/docs/audits/index.md` (nuevo)

**Archivos que NO tocaría:**
- Ningún archivo en `docs/audits/` (origen)
- Ningún archivo en `runtime/`
- Ningún archivo de configuración de servicios
- Ningún dashboard, Prometheus, Grafana

**Criterio PASS:**
- Build pasa
- Sidebar muestra sección "Audits" con índice
- Índice lista los 28 informes con clasificación
- No se movieron/copiaron documentos
- No se tocó runtime
- Commit local creado

**Riesgo residual:**
- El índice debe mantenerse manualmente si se añaden nuevas auditorías (bajo)
- Los enlaces en el índice apuntan a `docs/audits/` (relativos, no Starlight) — pueden quedar obsoletos si se mueven (bajo)
- Sin enlaces directos funcionales desde Starlight a informes fuera del content collection (medio — UX)

## 9. Validación

| Item | Resultado |
|------|-----------|
| No se movieron documentos | ✅ Confirmado |
| No se modificó sidebar | ✅ Confirmado |
| No se tocó runtime/servicios | ✅ Confirmado |
| git diff --stat | Solo el informe de esta fase |
| git status | Dirty preexistente fuera de alcance |

---

*Fin del informe AI-LAB-ASTRO-AUDITS-CONTENT-STRATEGY-01*
