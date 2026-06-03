# AI-LAB MCP — Catálogo Oficial de Tools

| Propiedad | Valor |
|---|---|
| Fase | `AI-LAB-MCP-TOOLS-CATALOG-FINAL-01` |
| Fecha | 2026-06-03 |
| HEAD de referencia | `3eb0cb14` |
| Autor | Operador `albert@192.168.1.30` |
| Estado | Documentación / Gobernanza |

---

## 1. Estado actual del MCP

| Servicio | Puerto | Modo | Active | Enabled | PID | Origen |
|---|---|---|---|---|---|---|
| Semantic Gateway | `127.0.0.1:8091` | Local, read-only, sin token | active | enabled | 1522 | `/mnt/mcp_server/server.py` |
| LAN Gateway | `0.0.0.0:8092` | LAN, read-only, token-auth | active | enabled | 1518 | `/mnt/mcp_server/lan_server.py` |

**UFW:** inactive por decisión operativa, compensado con token + LAN interna `192.168.1.0/24`.

**Snapshot versionado:** `mcp/runtime-mcp/` — 13 archivos, 0 drift respecto a `/mnt/mcp_server`.

---

## 2. Tabla oficial de tools

| Tool | Descripción | Entrada | Salida esperada | Riesgo | Clientes recomendados | Uso recomendado |
|---|---|---|---|---|---|---|
| `ailab_status` | Health básico de Gateway y Router | Ninguna | JSON `gateway`, `router` y `timestamp` | Bajo | Todos | Primer diagnóstico rápido |
| `ailab_runtime_health` | Health score, nodes online, routing confidence | Ninguna | JSON con `health_score`, `nodes_online`, `routing_confidence` | Bajo | Todos | Diagnóstico operativo del runtime |
| `ailab_route_preview` | Clasificación heurística de prompt sin inferencia pesada | `prompt: string` | JSON con clasificación, ruta sugerida, confianza | Bajo | Todos | Validar routing esperado antes de pedir inferencia |
| `ailab_slo_status` | Estado SLO, degradación y violaciones recientes | Ninguna | JSON con `health`, `degradation_level`, `recent_violations` | Bajo | Todos | NOC rápido y validación de degradación |
| `ailab_health_latency` | Health y latencias p50/p95/max | Ninguna | JSON con `health_status`, `p50_ms`, `p95_ms`, `max_ms` | Bajo | Todos | Revisar rendimiento y latencia |
| `ailab_operator_summary` | Resumen NOC amplio: servicios, nodos, GPU, watchdog | Ninguna | JSON con estado de servicios, nodos, GPU, watchdog | Medio | OpenCode preferente, LM Studio con cautela | Diagnóstico operativo amplio |
| `ailab_incidents_active` | Incidentes activos, degradaciones, correlaciones | Ninguna | JSON con lista de incidentes, severidad, timestamp | Medio | OpenCode preferente, LM Studio con cautela | Revisión de incidentes |
| `ailab_memory_search` | Búsqueda semántica en Qdrant | `query: string`, `limit: int=5` | JSON con resultados de búsqueda y scores de similitud | Medio | OpenCode preferente, LM Studio con cautela | Buscar memoria operacional histórica |

---

## 3. Clasificación por riesgo

### Bajo riesgo — uso diario (todos los clientes)

```
ailab_status
ailab_runtime_health
ailab_route_preview
ailab_slo_status
ailab_health_latency
```

### Medio riesgo — con cautela

```
ailab_operator_summary
ailab_incidents_active
ailab_memory_search
```

**Razones del riesgo medio:**
- `ailab_operator_summary` puede mezclar contexto amplio de sistema
- `ailab_incidents_active` puede exponer información operativa interna
- `ailab_memory_search` recupera contexto histórico que requiere validación contra estado actual

### Alto riesgo — prohibidas actualmente

Ninguna mutable permitida.

Queda prohibido por ahora:
- Shell remota
- Escritura a filesystem
- Control de systemd
- Restart
- Deploy
- Sync repo → `/mnt/mcp_server`
- Acceso a token
- Exposición a Internet
- Cloudflare / NPM

---

## 4. Política de uso por cliente

### OpenCode Ubuntu local (`127.0.0.1:8091`)

- Puede usar todas las tools read-only.
- Cliente preferente para diagnóstico técnico, operador summary, incidentes y búsqueda semántica.

### OpenCode Desktop `.50` / `.250` (`192.168.1.30:8092`)

- Puede usar las 5 de bajo riesgo libremente.
- Usar con cautela `ailab_operator_summary`, `ailab_incidents_active`, `ailab_memory_search`.

### LM Studio `.50` / `.250` (`192.168.1.30:8092`)

- Usar preferentemente las 5 de bajo riesgo.
- Evitar `ailab_operator_summary`, `ailab_incidents_active`, `ailab_memory_search` salvo validación expresa.
- Verificar que LM Studio retorna datos reales, no placeholders.

---

## 5. Prompts recomendados de validación

```text
Usa ailab_status y resume el resultado en español. No inventes valores.
```

```text
Usa ailab_runtime_health y dime health_score, nodes_online y routing_confidence. Si un campo no existe, escribe "no disponible".
```

```text
Usa ailab_route_preview con este prompt: "Necesito diagnosticar Gateway y Router de AI-LAB".
```

```text
Usa ailab_health_latency y dime p50, p95 y max. Si no hay datos, escribe "sin datos".
```

```text
Usa ailab_slo_status y dime si hay degradación activa.
```

---

## 6. Errores de uso detectados

| Error | Problema | Solución |
|---|---|---|
| Informes con placeholders `[Valor]` | El modelo generó datos no reales | Pedir siempre datos reales, no plantillas. Verificar que la tool retornó valores concretos |
| `TASK_COMPLETED` como evidencia | Respuesta vacía sin contenido real | Exigir el contenido de la tool. `TASK_COMPLETED` no es evidencia suficiente |
| Fingerprint usado como token | Error de autenticación | Usar siempre `AILAB_MCP_TOKEN` completo (`ff4f2df5ea199879...`) |
| Olvidar `Bearer` en header | `401 Unauthorized` | Formato correcto: `Authorization: Bearer <token>` |
| `127.0.0.1:8092` desde Windows `.50` | No puede conectar porque 8092 escucha en todas las interfaces | Usar `192.168.1.30:8092` desde cualquier cliente |
| WSL usado para configurar OpenCode Desktop | WSL no tiene acceso directo al escritorio Windows | Configurar OpenCode Desktop desde Windows nativo, no desde WSL |

---

## 7. Reglas de seguridad

1. **No token access:** Ninguna tool MCP actual expone ni accede al token `AILAB_MCP_TOKEN`.
2. **No mutables:** Todas las tools actuales son read-only. No se permite crear, modificar ni eliminar recursos.
3. **No restart/deploy/sync:** Prohibido reiniciar servicios, desplegar cambios o sincronizar snapshot contra `/mnt/mcp_server` vía MCP.
4. **No Internet exposure:** MCP LAN Gateway está limitado a `192.168.1.0/24`.
5. **No Cloudflare/NPM:** Sin túnel, proxy reverso ni exposición pública.
6. **Token-only en LAN:** La autenticación via `Bearer` token es el único control de acceso en LAN.
7. **UFW inactive:** Decisión operativa compensada por token + segmento LAN privado.
8. **Cualquier tool mutable futura** requiere spec, aprobación, tests y rollback plan.

---

## 8. Contrato para nuevas tools MCP

Toda nueva tool debe tener:

- `nombre`: identificación única (prefijo `ailab_`)
- `descripción`: qué hace y para qué sirve
- `entrada`: parámetros, tipos, obligatoriedad, defaults
- `salida`: estructura JSON o tipo esperado
- `riesgo`: bajo / medio / alto
- `cliente permitido`: qué clientes pueden usarla
- `tests`: cobertura mínima antes de producción
- `rollback`: plan de reversión si aplica
- `prohibición de secretos`: no leer, mostrar ni almacenar tokens, passwords ni API keys
- `validación de no side effects`: confirmar que la tool no modifica estado operativo
- `documentación`: aprobada antes de pasar a producción

---

## 9. Siguientes fases recomendadas

| Fase | Descripción |
|---|---|
| `AI-LAB-MCP-TOOLS-CATALOG-FINAL-PUSH-01` | Publicar este catálogo en el repo |
| `AI-LAB-MCP-TOOLS-RESOURCES-PROMPTS-SPEC-01` | Spec de resources y prompts |
| `AI-LAB-MCP-OBSERVABILITY-METRICS-SPEC-01` | Spec de métricas de observabilidad |
| `AI-LAB-MCP-CONTRACT-TESTS-01` | Tests de contrato MCP (read-only) |
