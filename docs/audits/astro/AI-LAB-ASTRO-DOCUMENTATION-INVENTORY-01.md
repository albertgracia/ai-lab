# AI-LAB-ASTRO-DOCUMENTATION-INVENTORY-01

**Fecha:** 2026-05-31
**Modo:** READ ONLY ABSOLUTO
**Resultado:** PASS

---

## 1. Resumen Ejecutivo

Se inventariaron **307 archivos .md / .mdx** en todo el ecosistema documental de AI-LAB Astro. Se detectaron **1 duplicado exacto**, **5 pares de naming inconsistente (underscore vs hyphen)**, **1 archivo huÃ©rfano** (`Nuevo Documento de texto.md`), y **22 archivos en `docs/` raÃ­z que no tienen contraparte en `src/content/docs/`**.

| MÃ©trica | Valor |
|---------|-------|
| Total archivos | 307 |
| KEEP | 278 |
| MERGE | 20 |
| ARCHIVE | 6 |
| DELETE_CANDIDATE | 1 |
| UNKNOWN | 2 |

---

## 2. Inventario por Fuente

### src/content/docs/ â€” 164 archivos (canÃ³nico Astro)

| Subdirectorio | Archivos | CategorÃ­a | Notas |
|---------------|----------|-----------|-------|
| (root) | 88 | Mixto | Fases histÃ³ricas, runbooks sueltos, docs varios |
| runtime/ | 20 | Architecture | DocumentaciÃ³n del runtime |
| architecture/ | 18 | Architecture | Arquitectura general |
| adrs/ | 6 | ADR | Decisiones arquitectÃ³nicas (ADR-001 a 006) |
| observability/ | 6 | Observability | Observabilidad tÃ©cnica |
| governance/ | 5 | Governance | Gobernanza operativa |
| experiments/ | 5 | Historical | Experimentos pasados |
| schemas/ | 4 | Architecture | Schemas tÃ©cnicos |
| roadmap/ | 2 | Historical | Roadmaps |
| agentic/ | 1 | Governance | Phase 28 |
| codebase/ | 1 | Operations | GitNexus access |
| memory/ | 1 | Architecture | Qdrant memory layer |

**Total subdirectorios:** 11 (mÃ¡s root)
**Archivos index.md:** 11 (uno por subdirectorio)

### src/content/blog/ â€” 25 archivos

| PatrÃ³n | Archivos | Rango |
|--------|----------|-------|
| Numerados (001-016) | 16 | Blog formal |
| No numerados | 9 | Temas varios (evidence-bound, sensor-fusion, etc.) |

### src/content/runbooks/ â€” 32 archivos

Todos categorizados como Runbook. MayorÃ­a procedimental y operacional.

### src/content/incidents/ â€” 2 archivos

Incidentes post-reboot (2026-05-12, 2026-05-15).

### docs/ (raÃ­z) â€” 27 archivos

| Archivo | TamaÃ±o | CategorÃ­a | Marca |
|---------|--------|-----------|-------|
| ARCHITECTURE-PHASE8.md | 853B | Architecture | MERGE |
| ARCHITECTURE.md | 688B | Architecture | MERGE |
| ARCHITECTURE_PHASE8.md | 4,140B | Architecture | MERGE (contraparte hyphen) |
| ARQUITECTURA_PUBLICO_PRIVADO.md | 3,230B | Architecture | MERGE |
| ASTRO_CLOUDFLARE_GITHUB.md | 6,291B | Architecture | MERGE |
| AUTOMATIZACION_CI_CD.md | 5,329B | Operations | MERGE |
| CLOUDFLARE_PAGES_REDIRECTS.md | 2,262B | Architecture | MERGE |
| COGNITIVE_ROUTER_PHASE5.md | 1,815B | Architecture | MERGE |
| DEBUGGING.md | 238B | Operations | KEEP |
| EVENT-BUS.md | 9,439B | Architecture | MERGE |
| EVENT_BUS.md | 2,370B | Architecture | MERGE |
| IA-LAB Estado actual... | 4,411B | Historical | MERGE |
| INFRASTRUCTURE.md | 300B | Architecture | MERGE |
| Nuevo Documento de texto.md | 980B | Unknown | DELETE_CANDIDATE |
| OPENCODE_AGENT_LAYER.md | 1,370B | Operations | MERGE |
| OPENWEBUI_CONEXION_ROUTER.md | 2,730B | Architecture | MERGE |
| ROADMAP.md | 400B | Historical | MERGE |
| RUNBOOK_CLOUDFLARE_PAGES.md | 5,374B | Runbook | MERGE |
| RUNTIME-FLOW.md | 7,254B | Architecture | MERGE |
| RUNTIME_ANALYTICS.md | 2,865B | Observability | MERGE |
| RUNTIME_ANALYTICS_CORRECCION.md | 3,001B | Observability | MERGE |
| RUNTIME_FLOW.md | 3,338B | Architecture | MERGE |
| SSE-RUNTIME.md | 2,587B | Architecture | MERGE |
| SSE_RUNTIME.md | 2,679B | Architecture | MERGE |
| TOPOLOGY-LAYER.md | 3,463B | Architecture | MERGE |
| TOPOLOGY_LAYER.md | 2,693B | Architecture | MERGE |
| blog-analytics-implementation.md | 2,484B | Operations | MERGE |

### docs/architecture/ â€” 1 archivo

| Archivo | CategorÃ­a | Marca |
|---------|-----------|-------|
| ASTRO-DEPLOYMENT-GOVERNANCE.md | Architecture | KEEP |

### docs/audits/ â€” 21 archivos

Todos categorizados como **Audit**. Incluye informes de arquitectura runtime, estabilidad, health score, memoria Qdrant, etc. Todos KEEP.

### docs/runtime/ â€” 10 archivos

| Archivo | Marca | RazÃ³n |
|---------|-------|-------|
| gateway-graceful-shutdown.md | ARCHIVE (exact duplicate) | IdÃ©ntico en src/content/docs/runtime/ |
| auxiliary-storage-policy-01.md | KEEP | Solo aquÃ­ |
| cognitive-health-followup-39c.md | KEEP | Solo aquÃ­ |
| live-api-bind-localhost-hardening-02.md | KEEP | Solo aquÃ­ |
| live-api-systemd-hardening-01.md | KEEP | Solo aquÃ­ |
| live-state-duplicate-unit-cleanup-01.md | KEEP | Solo aquÃ­ |
| mcp-opencode-windows-connection-01.md | KEEP | Solo aquÃ­ |
| mcp-semantic-gateway-01.md | KEEP | Solo aquÃ­ |
| opencode-gateway-contract-39a.md | KEEP | Solo aquÃ­ |
| runtime-observability-alerts-39b.md | KEEP | Solo aquÃ­ |

### docs/opencode/ â€” 23 archivos

DocumentaciÃ³n del proyecto OpenCode. 11 mÃ³dulos numerados (01-11), 5 informes comerciales/tÃ©cnicos, 6 proyectos, CHANGELOG. Todos KEEP.

### docs/releases/ â€” 2 archivos

cp-21b-stable.md, cp-22b-stable.md. Ambos KEEP.

---

## 3. AnomalÃ­as Detectadas

### 3.1 Duplicado Exacto

| Archivo | Ruta A | Ruta B |
|---------|--------|--------|
| gateway-graceful-shutdown.md | `src/content/docs/runtime/` | `docs/runtime/` |

Contenido idÃ©ntico. Una de las dos copias debe archivarse.

### 3.2 Mismo Nombre, Diferente Ruta (Posible Contenido Diferente)

| Archivo | src/content/docs/ | docs/ |
|---------|-------------------|-------|
| architecture_phase8.md | `src/content/docs/` (3,100B aprox) | `docs/ARCHITECTURE_PHASE8.md` (4,140B) |
| event_bus.md | `src/content/docs/` | `docs/EVENT_BUS.md` |
| runtime_flow.md | `src/content/docs/` | `docs/RUNTIME_FLOW.md` |
| sse_runtime.md | `src/content/docs/` | `docs/SSE_RUNTIME.md` |
| topology_layer.md | `src/content/docs/` | `docs/TOPOLOGY_LAYER.md` |

Estos archivos existen en ambas ubicaciones. El contenido puede ser el mismo o no. Requieren revisiÃ³n manual.

### 3.3 Naming Inconsistente (Underscore vs Hyphen)

| Par | TamaÃ±o A | TamaÃ±o B | Diferencia |
|-----|----------|----------|------------|
| ARCHITECTURE_PHASE8.md / ARCHITECTURE-PHASE8.md | 4,140B | 853B | Contenido DIFERENTE |
| EVENT_BUS.md / EVENT-BUS.md | 2,370B | 9,439B | Contenido DIFERENTE |
| RUNTIME_FLOW.md / RUNTIME-FLOW.md | 3,338B | 7,254B | Contenido DIFERENTE |
| SSE_RUNTIME.md / SSE-RUNTIME.md | 2,679B | 2,587B | Similar |
| TOPOLOGY_LAYER.md / TOPOLOGY-LAYER.md | 2,693B | 3,463B | Contenido DIFERENTE |

**ConclusiÃ³n:** No son renombrados, son documentos diferentes con nombres casi iguales.

### 3.4 Archivo HuÃ©rfano

- `docs/Nuevo Documento de texto.md` (980B) â€” archivo creado por Windows Explorer, sin relaciÃ³n con AI-LAB.

### 3.5 Archivo con Caracteres Especiales

- `docs/IA-LAB â€” Estado actual de la infraestructura (09052026).md` â€” usa em dash (`â€”`) y parÃ©ntesis. Puede causar problemas en herramientas que no manejan UTF-8.

### 3.6 Archivos docs/ RaÃ­z Sin Contraparte en src/content/docs/

22 archivos en `docs/` que no existen en `src/content/docs/`. Algunos son legacy (pre-Astro), otros contienen informaciÃ³n no migrada. La mayorÃ­a marcados MERGE.

---

## 4. DistribuciÃ³n por CategorÃ­a

| CategorÃ­a | Archivos | % |
|-----------|----------|---|
| Architecture | 97 | 31.6% |
| Historical (fases) | 55 | 17.9% |
| Runbook | 38 | 12.4% |
| Operations | 30 | 9.8% |
| Blog | 25 | 8.1% |
| Audit | 23 | 7.5% |
| Observability | 16 | 5.2% |
| Governance | 8 | 2.6% |
| ADR | 7 | 2.3% |
| Unknown | 8 | 2.6% |

---

## 5. Lista de Candidatos a AcciÃ³n

### DELETE_CANDIDATE (1)

| Archivo | RazÃ³n |
|---------|-------|
| docs/Nuevo Documento de texto.md | Creado por Windows Explorer, sin contenido relevante |

### ARCHIVE (6)

| Archivo | RazÃ³n |
|---------|-------|
| docs/runtime/gateway-graceful-shutdown.md | Duplicado exacto de src/content/docs/runtime/ |
| docs/ARCHITECTURE_PHASE8.md | Contraparte con hyphen existe (puede archivar 1) |
| docs/EVENT_BUS.md | Contraparte con hyphen existe (puede archivar 1) |
| docs/RUNTIME_FLOW.md | Contraparte con hyphen existe (puede archivar 1) |
| docs/SSE_RUNTIME.md | Contraparte con hyphen existe (puede archivar 1) |
| docs/TOPOLOGY_LAYER.md | Contraparte con hyphen existe (puede archivar 1) |

### MERGE (20)

22 archivos de `docs/` raÃ­z necesitan revisiÃ³n para determinar si deben migrarse a `src/content/docs/`, fusionarse con contenido existente, o archivarse.

### UNKNOWN (2)

Dos archivos en `src/content/docs/` que no encajan claramente en ninguna categorÃ­a (requieren revisiÃ³n de contenido).

---

## 6. Recomendaciones

1. **Borrar** `docs/Nuevo Documento de texto.md` (DELETE_CANDIDATE)
2. **Archivar** `docs/runtime/gateway-graceful-shutdown.md` (duplicado exacto)
3. **Revisar pares underscore/hyphen**: determinar si son duplicados o versiones diferentes. Si son diferentes, renombrar para distinguirlos; si son iguales, archivar 1 por par
4. **Migrar gradualmente** contenido de `docs/` raÃ­z a `src/content/docs/` respetando la estructura de subdirectorios
5. **Normalizar nombres**: usar siempre hyphens (kebab-case) en lugar de underscores
6. **Revisar los 2 UNKNOWN** para clasificarlos correctamente

---

*Fin del informe AI-LAB-ASTRO-DOCUMENTATION-INVENTORY-01*
