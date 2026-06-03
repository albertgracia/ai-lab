# AI-LAB MCP — Spec de Resources y Prompts

| Propiedad | Valor |
|---|---|
| Fase | `AI-LAB-MCP-TOOLS-RESOURCES-PROMPTS-SPEC-01` |
| Fecha | 2026-06-03 |
| HEAD de referencia | `96da556f` |
| Autor | Operador `albert@192.168.1.30` |
| Estado | Spec — solo documentación |
| Implementación | Futura — `AI-LAB-MCP-TOOLS-RESOURCES-PROMPTS-IMPLEMENTATION-01` |

---

## 1. Estado actual

| Servicio | Puerto | Modo | Active | Enabled | Tools |
|---|---|---|---|---|---|
| Semantic Gateway | `127.0.0.1:8091` | Local, read-only, sin token | active | enabled | 8 tools |
| LAN Gateway | `0.0.0.0:8092` | LAN, read-only, token-auth | active | enabled | 8 tools |

**UFW:** inactive.
**Snapshot:** `mcp/runtime-mcp/` — 0 drift, tests 5/5 PASS.
**Tools:** 8 (5 bajo riesgo, 3 medio, 0 alto/prohibidas).
**Resources actuales:** 0.
**Prompts actuales:** 0 (solo `ListPromptsRequest` recibe `ResourceTemplatePrompt` por defecto MCP).

---

## 2. Motivación

| Razón | Detalle |
|---|---|
| Estandarizar acceso read-only a datos MCP | URIs estables evitan que cada cliente invente paths |
| Separar datos (resources) de acciones (tools) | Semántica MCP clara: resources = datos, tools = acciones |
| Reducir alucinación en modelos | Resources devuelven datos reales sin paso de inferencia |
| Facilitar herramientas GUI MCP | Algunos clientes prefieren navegar resources en UI |
| Preparar prompts guiados | Prompts estructurados reducen placeholders y `TASK_COMPLETED` vacío |

---

## 3. Resources propuestos

### 3.1 Esquema de URIs

```
ai-lab://<categoria>/<recurso>
```

Todas las URIs son estables, read-only y sin parámetros dinámicos salvo `ai-lab://memory/search-policy`.

### 3.2 Tabla completa

#### Bajo riesgo

##### `ai-lab://status/current`

| Propiedad | Valor |
|---|---|
| Descripción | Health básico de Gateway y Router |
| Fuente MCP | `ailab_status` |
| Riesgo | Bajo |
| Clientes | Todos |
| Formato | JSON: `{ "gateway": {...}, "router": {...}, "timestamp": "..." }` |
| Campos permitidos | `gateway`, `router`, `timestamp` |
| Campos prohibidos | Token, env, rutas filesystem |
| Caché recomendada | 30s |
| Motivo | Primer diagnóstico rápido sin llamar a tool |

##### `ai-lab://runtime/health`

| Propiedad | Valor |
|---|---|
| Descripción | Health score, nodes online, routing confidence |
| Fuente MCP | `ailab_runtime_health` |
| Riesgo | Bajo |
| Clientes | Todos |
| Formato | JSON: `{ "health_score": ..., "nodes_online": ..., "routing_confidence": ... }` |
| Caché recomendada | 30s |
| Motivo | Diagnóstico operativo del runtime |

##### `ai-lab://runtime/latency`

| Propiedad | Valor |
|---|---|
| Descripción | Latencias p50/p95/max |
| Fuente MCP | `ailab_health_latency` |
| Riesgo | Bajo |
| Clientes | Todos |
| Formato | JSON: `{ "health_status": "...", "p50_ms": ..., "p95_ms": ..., "max_ms": ... }` |
| Caché recomendada | 30s |
| Motivo | Rendimiento y latencia |

##### `ai-lab://slo/current`

| Propiedad | Valor |
|---|---|
| Descripción | Estado SLO, degradación, violaciones recientes |
| Fuente MCP | `ailab_slo_status` |
| Riesgo | Bajo |
| Clientes | Todos |
| Formato | JSON: `{ "health": "...", "degradation_level": "...", "recent_violations": [...] }` |
| Caché recomendada | 60s |
| Motivo | NOC rápido |

##### `ai-lab://tools/catalog`

| Propiedad | Valor |
|---|---|
| Descripción | Catálogo oficial de tools MCP con descripción, riesgo y clientes |
| Fuente MCP | Documentación: `docs/mcp/AI-LAB-MCP-TOOLS-CATALOG-FINAL-01.md` |
| Riesgo | Bajo |
| Clientes | Todos |
| Formato | Markdown o JSON |
| Caché recomendada | 1h |
| Motivo | Clientes pueden consultar el catálogo sin buscar en repo |

##### `ai-lab://clients/config-guide`

| Propiedad | Valor |
|---|---|
| Descripción | Guía de configuración de clientes OpenCode y LM Studio |
| Fuente MCP | Documentación: `docs/mcp/AI-LAB-MCP-CLIENT-CONFIG-DOCS-01.md` |
| Riesgo | Bajo |
| Clientes | Todos |
| Formato | Markdown |
| Caché recomendada | 1h |
| Motivo | Clientes pueden consultar configuración sin buscar en repo |

##### `ai-lab://mcp/security-policy`

| Propiedad | Valor |
|---|---|
| Descripción | Reglas de seguridad, prohibiciones y contrato para tools |
| Fuente MCP | Catálogo tools (sección 7-8) |
| Riesgo | Bajo |
| Clientes | Todos |
| Formato | Markdown |
| Caché recomendada | 1h |
| Motivo | Recordatorio de reglas incrustado en el MCP |

#### Medio riesgo — con cautela

##### `ai-lab://incidents/active`

| Propiedad | Valor |
|---|---|
| Descripción | Incidentes activos, degradaciones, correlaciones |
| Fuente MCP | `ailab_incidents_active` |
| Riesgo | Medio |
| Clientes | OpenCode preferente, LM Studio con cautela |
| Formato | JSON: `[ { "severity": "...", "description": "...", "timestamp": "..." } ]` |
| Caché recomendada | 30s |
| Motivo | Puede contener información operativa interna |

##### `ai-lab://operator/summary`

| Propiedad | Valor |
|---|---|
| Descripción | Resumen NOC: servicios, nodos, GPU, watchdog |
| Fuente MCP | `ailab_operator_summary` |
| Riesgo | Medio |
| Clientes | OpenCode preferente, LM Studio con cautela |
| Formato | JSON: `{ "services": {...}, "nodes": {...}, "gpu": {...}, "watchdog": {...} }` |
| Caché recomendada | 60s |
| Motivo | Contexto amplio de sistema que puede confundir modelos |

##### `ai-lab://memory/search-policy`

| Propiedad | Valor |
|---|---|
| Descripción | Política de búsqueda semántica en Qdrant, colecciones disponibles, límites |
| Fuente MCP | `ailab_memory_search` (documentación) |
| Riesgo | Medio |
| Clientes | OpenCode preferente, LM Studio con cautela |
| Formato | Markdown o JSON |
| Caché recomendada | 1h |
| Motivo | Define qué se puede buscar y qué no antes de ejecutar `ailab_memory_search` |

#### Alto riesgo — prohibido por ahora

| URI | Razón |
|---|---|
| `ai-lab://runtime/logs` | Logs completos expuestos |
| `ai-lab://config/env` | Token y variables de entorno |
| `ai-lab://systemd/status` | Control de systemd |
| `ai-lab://runtime/state-raw` | Estado interno del runtime |
| `ai-lab://memory/qdrant-raw` | Dump completo de Qdrant |
| `ai-lab://clients/<host>/config-real` | Configuraciones reales de OpenCode/LM Studio |

### 3.3 Reglas generales para resources

1. **Read-only:** Ningún resource permite crear, modificar ni eliminar datos.
2. **Sin token:** Ningún resource expone ni requiere token.
3. **Sin secretos:** No incluir paths sensibles, env, logs completos ni dumps.
4. **Sin datos masivos:** No exponer colecciones Qdrant completas sin query explícita.
5. **Timestamp obligatorio:** Todo resource con estado dinámico debe incluir `updated_at` o `timestamp`.
6. **Cache etiquetada:** Cada resource documenta su caché recomendada. El cliente no debe cachear más del doble.
7. **Sin side effects:** Leer un resource no modifica estado del sistema.

---

## 4. Prompts propuestos

### 4.1 Esquema de nombres

```
ai-lab-<accion>-<contexto>
```

Todos los prompts son read-only. No generan mutaciones.

### 4.2 Tabla completa

#### `ai-lab-diagnostico-rapido`

| Propiedad | Valor |
|---|---|
| Objetivo | Primer diagnóstico rápido del MCP |
| Tools que puede usar | `ailab_status`, `ailab_runtime_health` |
| Resources | `ai-lab://status/current`, `ai-lab://runtime/health` |
| Inputs | Ninguno |
| Output esperado | Resumen en español: estado Gateway, Router, health_score, nodes_online |
| Reglas | No inventar valores. Si un campo no existe, escribir `no disponible`. Citar cada tool/resource usado |
| Riesgo | Bajo |
| Clientes | Todos |

#### `ai-lab-resumen-noc`

| Propiedad | Valor |
|---|---|
| Objetivo | Resumen NOC del runtime |
| Tools que puede usar | `ailab_runtime_health`, `ailab_slo_status`, `ailab_operator_summary` (solo OpenCode) |
| Resources | `ai-lab://runtime/health`, `ai-lab://slo/current` |
| Inputs | Ninguno |
| Output esperado | Health score, nodes, SLO, degradación, estado watchdog |
| Reglas | `ailab_operator_summary` solo si el cliente es OpenCode. Para LM Studio, omitir y marcar `no disponible` |
| Riesgo | Bajo-Medio |
| Clientes | OpenCode preferente, LM Studio con limitaciones |

#### `ai-lab-revisar-incidentes`

| Propiedad | Valor |
|---|---|
| Objetivo | Revisar incidentes activos |
| Tools que puede usar | `ailab_incidents_active` |
| Resources | `ai-lab://incidents/active` |
| Inputs | Ninguno |
| Output esperado | Lista de incidentes con severidad, descripción y timestamp |
| Reglas | Si no hay incidentes, escribir `sin incidentes activos`. No inventar placeholders. No delegar a agente secundario |
| Riesgo | Medio |
| Clientes | OpenCode preferente, LM Studio con cautela |

#### `ai-lab-validar-routing`

| Propiedad | Valor |
|---|---|
| Objetivo | Validar routing esperado para un prompt antes de inferencia |
| Tools que puede usar | `ailab_route_preview` |
| Inputs | `prompt: string` (obligatorio) |
| Output esperado | Ruta sugerida, confianza, familia de routing |
| Reglas | Si no se proporciona prompt, devolver error: `prompt es obligatorio`. No inventar métricas de routing |
| Riesgo | Bajo |
| Clientes | Todos |

#### `ai-lab-health-latency-review`

| Propiedad | Valor |
|---|---|
| Objetivo | Revisar latencias del MCP |
| Tools que puede usar | `ailab_health_latency` |
| Resources | `ai-lab://runtime/latency` |
| Inputs | Ninguno |
| Output esperado | p50, p95, max, health_status |
| Reglas | Si no hay datos de latencia, escribir `sin datos`. No sugerir restart |
| Riesgo | Bajo |
| Clientes | Todos |

#### `ai-lab-mcp-client-troubleshooting`

| Propiedad | Valor |
|---|---|
| Objetivo | Diagnóstico de conectividad de clientes (`.50`, `.250`) |
| Resources | `ai-lab://clients/config-guide`, `ai-lab://mcp/security-policy` |
| Inputs | Host del cliente (opcional) |
| Output esperado | Checklist de conectividad: puerto, token, red, UFW, enable state |
| Reglas | No leer token. No mostrar comandos que expongan token. No acceder a hosts remotos |
| Riesgo | Bajo |
| Clientes | Todos |

#### `ai-lab-no-placeholder-report`

| Propiedad | Valor |
|---|---|
| Objetivo | Generar informe operativo garantizando que no se usan placeholders |
| Tools que puede usar | Cualquiera de bajo riesgo |
| Inputs | Prompt del usuario |
| Output esperado | Informe con valores reales. Si una tool no devuelve un campo, escribir `no disponible` |
| Reglas | Prohibido usar `[Valor]`. Prohibido devolver `TASK_COMPLETED` sin contenido. Cada bloque debe citar la tool que lo produjo. No mezclar datos históricos con actuales sin marcarlo. No sugerir restart/deploy/sync |
| Riesgo | Bajo |
| Clientes | Todos |

### 4.3 Reglas anti-alucinación para prompts

1. **No inventar valores:** Si una tool/resource no devuelve un campo, escribir `no disponible`.
2. **No placeholders:** Prohibido usar `[Valor]`, `[campo]` o similar.
3. **No `TASK_COMPLETED` vacío:** Siempre incluir el contenido real devuelto por la tool o resource.
4. **Citar fuente:** Cada bloque del informe debe indicar qué tool o resource lo produjo.
5. **No delegación operativa:** No delegar a agente secundario si se pide evidencia operativa directa.
6. **No mezclar historial:** Separar datos históricos de estado actual, marcando la diferencia.
7. **No restart/deploy/sync:** Prohibido sugerir acciones mutables salvo fase explícita.
8. **Verificar cliente:** `ailab_operator_summary` y `ailab_incidents_active` solo se usan si el cliente es OpenCode. LM Studio debe recibir `no disponible` en su lugar.

---

## 5. Clasificación de riesgo

### Bajo — uso diario

| Resource | Prompt |
|---|---|
| `ai-lab://status/current` | `ai-lab-diagnostico-rapido` |
| `ai-lab://runtime/health` | `ai-lab-resumen-noc` |
| `ai-lab://runtime/latency` | `ai-lab-health-latency-review` |
| `ai-lab://slo/current` | `ai-lab-validar-routing` |
| `ai-lab://tools/catalog` | `ai-lab-mcp-client-troubleshooting` |
| `ai-lab://clients/config-guide` | `ai-lab-no-placeholder-report` |
| `ai-lab://mcp/security-policy` | |

### Medio — con cautela

| Resource | Prompt |
|---|---|
| `ai-lab://incidents/active` | `ai-lab-revisar-incidentes` |
| `ai-lab://operator/summary` | `ai-lab-resumen-noc` (solo OpenCode) |
| `ai-lab://memory/search-policy` | |

### Alto — prohibido por ahora

Ninguno de los resources o prompts propuestos es alto riesgo. La lista de prohibiciones (logs, env, systemd, qdrant raw) queda documentada como no implementable sin spec adicional.

---

## 6. Contrato de implementación futura

**Fase:** `AI-LAB-MCP-TOOLS-RESOURCES-PROMPTS-IMPLEMENTATION-01`

### Condiciones

1. Modificar solo `mcp/runtime-mcp/`.
2. No tocar `/mnt/mcp_server`.
3. No cambiar systemd.
4. No reiniciar servicios.
5. Tests de contrato obligatorios antes del deploy.
6. Secret scan obligatorio.
7. Dry-run sync antes de tocar `/mnt/mcp_server`.
8. Implementación repo primero, sync controlado después (fase APPLY separada).
9. Documentación actualizada antes del sync.
10. Rollback plan antes del sync.

### Archivos a modificar (estimado)

| Archivo | Cambio |
|---|---|
| `mcp/runtime-mcp/server.py` | Registrar resources y prompts |
| `mcp/runtime-mcp/tools/` (nuevo subdirectorio `resources/`) | Handlers de resources |
| `mcp/runtime-mcp/tools/` (nuevo subdirectorio `prompts/`) | Handlers de prompts |
| `tests/` (nuevo archivo) | Tests de contrato resources y prompts |

---

## 7. Tests futuros obligatorios

### Tests de contrato

```python
test_resources_registered        # resources/list no devuelve vacío
test_prompts_registered          # prompts/list no devuelve vacío
test_resource_uris_stable        # URIs siguen esquema ai-lab://
test_no_secret_resources         # Ningún resource expone token/env
test_no_mutable_prompts          # Ningún prompt modifica estado
test_prompt_outputs_require_real_values  # No placeholders en output
test_tools_resources_prompts_list # Listar tools+resources+prompts
test_lan_auth_still_required     # 8092 sin token = 401
```

### Smoke MCP futuro

1. `initialize` — handshake MCP
2. `tools/list` — lista de tools
3. `resources/list` — lista de resources
4. `prompts/list` — lista de prompts
5. `resources/read` — leer resource bajo riesgo
6. `prompts/get` — obtener prompt bajo riesgo
7. Auth `8092` sin token → `401`
8. Auth `8092` con token → `200`

---

## 8. No-go list

| Prohibición | Razón |
|---|---|
| Resources con logs completos | Exposición de información interna |
| Resources con token/env | Riesgo de seguridad crítico |
| Resources con systemd control | Mutabilidad no permitida |
| Resources con runtime/state raw | Estado interno sin filtrar |
| Resources con Qdrant raw dump | Datos masivos sin query explícita |
| Prompts que ejecuten restart/deploy/sync | Solo fases explícitas |
| Prompts que accedan a hosts remotos | No hay cliente MCP para SSH |
| Resources que requieran auth diferente a Bearer token | Mantener esquema actual |
| Resources mutables (POST/PUT/DELETE) | Solo read-only phase actual |

---

## 9. Siguientes fases recomendadas

| Fase | Descripción |
|---|---|
| `AI-LAB-MCP-TOOLS-RESOURCES-PROMPTS-SPEC-PUSH-01` | Publicar esta spec |
| `AI-LAB-MCP-TOOLS-RESOURCES-PROMPTS-IMPLEMENTATION-01` | Implementar resources y prompts en `mcp/runtime-mcp/` |
| `AI-LAB-MCP-OBSERVABILITY-METRICS-SPEC-01` | Spec de métricas de observabilidad |
| `AI-LAB-MCP-CONTRACT-TESTS-01` | Tests de contrato MCP (read-only) |
