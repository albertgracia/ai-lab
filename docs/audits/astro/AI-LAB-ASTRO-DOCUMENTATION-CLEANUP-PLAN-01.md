# AI-LAB-ASTRO-DOCUMENTATION-CLEANUP-PLAN-01

**Fecha:** 2026-05-31
**Modo:** READ ONLY â€” plan, no ejecuciÃ³n
**Fase de aplicaciÃ³n:** `AI-LAB-ASTRO-DOCUMENTATION-CLEANUP-APPLY-01`
**Resultado:** PASS

---

## 1. Resumen Ejecutivo

Basado en `AI-LAB-ASTRO-DOCUMENTATION-INVENTORY-01` (307 archivos inventariados), este plan define acciones concretas, seguras y reversibles para cada archivo problemÃ¡tico.

**FilosofÃ­a del plan:**
- NUNCA borrar directamente: mover a `archive/` o `quarantine/`
- NUNCA reemplazar sin verificaciÃ³n: revisiÃ³n manual obligatoria para MERGE
- Preservar siempre el contenido original hasta que la fase APPLY lo ejecute
- Cada acciÃ³n tiene riesgo documentado y comando futuro explÃ­cito

**Volumen de acciÃ³n:** 30 archivos (de 307 totales) requieren alguna intervenciÃ³n.

| AcciÃ³n propuesta | Archivos | % del total |
|-----------------|----------|-------------|
| NO_TOUCH | 277 | 90.2% |
| ARCHIVE_TO_PRE_CLEANUP | 7 | 2.3% |
| QUARANTINE_DELETE_CANDIDATE | 1 | 0.3% |
| MERGE_LATER | 18 | 5.9% |
| REVIEW_MANUAL | 4 | 1.3% |

---

## 2. Tabla Completa de Acciones

### 2.1 ARCHIVE_TO_PRE_CLEANUP (7 archivos)

Archivos que son duplicados exactos o contrapartes underscore de versiones hyphen. Se mueven a `docs/archive/pre-cleanup-20260531/`.

| # | Archivo | Ruta | TamaÃ±o | Estado Inventario | AcciÃ³n Propuesta | Motivo | Riesgo | Comando Futuro |
|---|---------|------|--------|-------------------|-----------------|--------|--------|----------------|
| 1 | gateway-graceful-shutdown.md | `docs/runtime/` | ? | ARCHIVE (exact duplicate) | ARCHIVE_TO_PRE_CLEANUP | Duplicado exacto de `src/content/docs/runtime/gateway-graceful-shutdown.md` | BAJO â€” archivar, no borrar. Si algÃºn enlace apunta a `docs/runtime/`, puede romperse | `mv docs/runtime/gateway-graceful-shutdown.md docs/archive/pre-cleanup-20260531/` |
| 2 | architecture_phase8.md | `docs/ARCHITECTURE_PHASE8.md` | 4,140B | ARCHIVE | ARCHIVE_TO_PRE_CLEANUP | Contenido IDÃ‰NTICO a `src/content/docs/architecture_phase8.md` (4,140B). La versiÃ³n Astro es la canÃ³nica | BAJO â€” mismo contenido | `mv docs/ARCHITECTURE_PHASE8.md docs/archive/pre-cleanup-20260531/` |
| 3 | event_bus.md | `docs/EVENT_BUS.md` | 2,370B | ARCHIVE | ARCHIVE_TO_PRE_CLEANUP | Contenido IDÃ‰NTICO a `src/content/docs/event_bus.md` (2,370B). La versiÃ³n Astro es la canÃ³nica | BAJO â€” mismo contenido | `mv docs/EVENT_BUS.md docs/archive/pre-cleanup-20260531/` |
| 4 | sse_runtime.md | `docs/SSE_RUNTIME.md` | 2,679B | ARCHIVE | ARCHIVE_TO_PRE_CLEANUP | Contenido IDÃ‰NTICO a `src/content/docs/sse_runtime.md` (2,679B). La versiÃ³n Astro es la canÃ³nica | BAJO â€” mismo contenido | `mv docs/SSE_RUNTIME.md docs/archive/pre-cleanup-20260531/` |
| 5 | topology_layer.md | `docs/TOPOLOGY_LAYER.md` | 2,693B | ARCHIVE | ARCHIVE_TO_PRE_CLEANUP | Contenido IDÃ‰NTICO a `src/content/docs/topology_layer.md` (2,693B). La versiÃ³n Astro es la canÃ³nica | BAJO â€” mismo contenido | `mv docs/TOPOLOGY_LAYER.md docs/archive/pre-cleanup-20260531/` |
| 6 | RUNTIME_FLOW.md | `docs/` | 3,338B | ARCHIVE | ARCHIVE_TO_PRE_CLEANUP | DIFERENTE de `src/content/docs/runtime_flow.md` (2,562B) â€” pero la versiÃ³n hyphen `RUNTIME-FLOW.md` (7,254B) es mÃ¡s completa. Esta underscore es probablemente un snapshot intermedio | MEDIO â€” contenido diferente al src. Revisar antes de archivar definitivamente | `mv docs/RUNTIME_FLOW.md docs/archive/pre-cleanup-20260531/` |
| 7 | SSE-RUNTIME.md | `docs/` | 2,587B | ARCHIVE | ARCHIVE_TO_PRE_CLEANUP | Similar a `SSE_RUNTIME.md` (2,679B, duplicado de src). La versiÃ³n hyphen es ligeramente mÃ¡s pequeÃ±a | BAJO â€” el contenido canÃ³nico estÃ¡ en Astro | `mv docs/SSE-RUNTIME.md docs/archive/pre-cleanup-20260531/` |

### 2.2 QUARANTINE_DELETE_CANDIDATE (1 archivo)

Archivo claramente residual. Se mueve a `docs/quarantine/pre-cleanup-20260531/`.

| # | Archivo | Ruta | TamaÃ±o | Estado Inventario | AcciÃ³n Propuesta | Motivo | Riesgo | Comando Futuro |
|---|---------|------|--------|-------------------|-----------------|--------|--------|----------------|
| 8 | Nuevo Documento de texto.md | `docs/` | 980B | DELETE_CANDIDATE | QUARANTINE_DELETE_CANDIDATE | Archivo creado por Windows Explorer. Sin relaciÃ³n con AI-LAB. Contenido irrelevante | NULO â€” mover a cuarentena para revisiÃ³n final | `mv "docs/Nuevo Documento de texto.md" "docs/quarantine/pre-cleanup-20260531/"` |

### 2.3 MERGE_LATER (18 archivos)

Archivos en `docs/` raÃ­z que son **Ãºnicos** (no existen en `src/content/docs/`) y contienen documentaciÃ³n legacy pre-Astro. Requieren migraciÃ³n manual a Astro.

| # | Archivo | TamaÃ±o | CategorÃ­a | AcciÃ³n Propuesta | Motivo | Riesgo | Comando Futuro |
|---|---------|--------|-----------|-----------------|--------|--------|----------------|
| 9 | ARCHITECTURE-PHASE8.md | 853B | Architecture | MERGE_LATER | Legacy pre-Astro. DIFERENTE de ARCHITECTURE_PHASE8.md (4,140B). VersiÃ³n corta | BAJO â€” contenido legacy, fase 8 | Evaluar si se migra a `src/content/docs/architecture/` |
| 10 | ARCHITECTURE.md | 688B | Architecture | MERGE_LATER | Muy pequeÃ±o (688B). Probablemente un Ã­ndice o resumen legacy | BAJO | Revisar si aporta valor nuevo vs contenido Astro existente |
| 11 | ARQUITECTURA_PUBLICO_PRIVADO.md | 3,230B | Architecture | MERGE_LATER | Documento legacy sobre arquitectura pÃºblico/privado. Ya existe `docs/architecture/ASTRO-DEPLOYMENT-GOVERNANCE.md` que cubre el mismo tema | MEDIO â€” posible solapamiento con ASTRO-DEPLOYMENT-GOVERNANCE.md | Revisar si el contenido es complementario o redundante |
| 12 | ASTRO_CLOUDFLARE_GITHUB.md | 6,291B | Architecture | MERGE_LATER | Legacy sobre despliegue Astro. Ya cubierto por ASTRO-DEPLOYMENT-GOVERNANCE.md | MEDIO â€” posible solapamiento | Revisar si tiene informaciÃ³n Ãºnica antes de migrar |
| 13 | AUTOMATIZACION_CI_CD.md | 5,329B | Operations | MERGE_LATER | CI/CD pipeline legacy. Posiblemente obsoleto | MEDIO â€” puede estar desactualizado | Revisar si el pipeline actual difiere |
| 14 | CLOUDFLARE_PAGES_REDIRECTS.md | 2,262B | Architecture | MERGE_LATER | Redirects de Cloudflare. Legacy | BAJO | Migrar a `src/content/docs/` si sigue vigente |
| 15 | COGNITIVE_ROUTER_PHASE5.md | 1,815B | Architecture | MERGE_LATER | Fase 5 del router cognitivo. Legacy histÃ³rico | BAJO | Contenido histÃ³rico, migrar o archivar |
| 16 | EVENT-BUS.md | 9,439B | Architecture | MERGE_LATER | DIFERENTE de `event_bus.md` (2,370B). VersiÃ³n mucho mÃ¡s extensa | ALTO â€” contenido Ãºnico de 9.4KB. Evaluar si debe migrarse como documento separado | RevisiÃ³n manual para determinar si es `event-bus.md` ampliado o documento diferente |
| 17 | IA-LAB Estado actual...md | 4,411B | Historical | MERGE_LATER | Snapshot de estado de infraestructura (fecha: 09/05/2026). Valor histÃ³rico | BAJO | Migrar a `src/content/incidents/` o `src/content/docs/` con nombre normalizado |
| 18 | INFRASTRUCTURE.md | 300B | Architecture | MERGE_LATER | Muy pequeÃ±o. Probablemente un placeholder | BAJO | Revisar si tiene utilidad |
| 19 | OPENCODE_AGENT_LAYER.md | 1,370B | Operations | MERGE_LATER | DocumentaciÃ³n de la capa de agente OpenCode | BAJO | Migrar a `src/content/docs/opencode/` o `docs/opencode/` |
| 20 | OPENWEBUI_CONEXION_ROUTER.md | 2,730B | Architecture | MERGE_LATER | ConexiÃ³n OpenWebUI-Router. Ya existe en `src/content/docs/openwebui-conexion-router.md` (verificar duplicado) | MEDIO â€” verificar si es duplicado de src | Comparar contenido con `src/content/docs/openwebui-conexion-router.md` |
| 21 | ROADMAP.md | 400B | Historical | MERGE_LATER | Muy pequeÃ±o. Roadmap legacy | BAJO | Migrar o archivar |
| 22 | RUNBOOK_CLOUDFLARE_PAGES.md | 5,374B | Runbook | MERGE_LATER | Runbook Cloudflare Pages. Ya existe `src/content/docs/runbook-cloudflare-pages.md` | MEDIO â€” verificar duplicado | Comparar con `src/content/docs/runbook-cloudflare-pages.md` |
| 23 | RUNTIME-FLOW.md | 7,254B | Architecture | MERGE_LATER | DIFERENTE de `runtime_flow.md` (2,562B src, 3,338B docs). VersiÃ³n mÃ¡s grande | ALTO â€” contenido Ãºnico de 7.2KB. Evaluar migraciÃ³n como documento separado | RevisiÃ³n manual para fusionar con contenido Astro existente |
| 24 | RUNTIME_ANALYTICS.md | 2,865B | Observability | MERGE_LATER | Legacy analytics. Ya existe en src | MEDIO â€” verificar duplicado con src | Comparar con `src/content/docs/runtime-analytics-engine.md` y `runtime-analytics-correccion.md` |
| 25 | RUNTIME_ANALYTICS_CORRECCION.md | 3,001B | Observability | MERGE_LATER | Legacy analytics correcciÃ³n | MEDIO | Verificar si es duplicado de src |
| 26 | TOPOLOGY-LAYER.md | 3,463B | Architecture | MERGE_LATER | DIFERENTE de `topology_layer.md` (2,693B). VersiÃ³n mÃ¡s grande | MEDIO | RevisiÃ³n manual para determinar si es complemento o versiÃ³n alternativa |
| 27 | blog-analytics-implementation.md | 2,484B | Operations | MERGE_LATER | ImplementaciÃ³n de analytics en blog. Legacy | BAJO | Migrar a `src/content/docs/` o archivar |

### 2.4 NO_TOUCH (277 archivos)

Incluye:
- 164 archivos de `src/content/docs/` (canÃ³nico Astro) â€” NO_TOUCH
- 25 archivos de `src/content/blog/` â€” NO_TOUCH
- 32 archivos de `src/content/runbooks/` â€” NO_TOUCH
- 2 archivos de `src/content/incidents/` â€” NO_TOUCH
- 21 archivos de `docs/audits/` â€” NO_TOUCH (auditorÃ­as activas)
- 1 archivo de `docs/architecture/` (ASTRO-DEPLOYMENT-GOVERNANCE.md) â€” NO_TOUCH
- 8 archivos de `docs/runtime/` (excepto el duplicado) â€” NO_TOUCH
- 23 archivos de `docs/opencode/` â€” NO_TOUCH
- 2 archivos de `docs/releases/` â€” NO_TOUCH

### 2.5 DEBUGGING.md â€” Caso Especial

| Archivo | Ruta | TamaÃ±o | Estado | AcciÃ³n | Motivo |
|---------|------|--------|--------|--------|--------|
| DEBUGGING.md | `docs/` | 238B | KEEP | NO_TOUCH | Contiene notas de debugging (Docker Pull Timeout). Aunque es legacy y pequeÃ±o, puede tener valor operativo inmediato. Se deja in situ hasta la fase APPLY |

---

## 3. Estructura Segura Propuesta

```
docs/
  archive/
    pre-cleanup-20260531/
      gateway-graceful-shutdown.md
      ARCHITECTURE_PHASE8.md
      EVENT_BUS.md
      SSE_RUNTIME.md
      TOPOLOGY_LAYER.md
      RUNTIME_FLOW.md
      SSE-RUNTIME.md
  quarantine/
    pre-cleanup-20260531/
      Nuevo Documento de texto.md
```

**Nota:** `archive/` y `quarantine/` deben crearse dentro de `docs/` (no en `src/content/docs/`), ya que los archivos afectados estÃ¡n en `docs/` raÃ­z y `docs/runtime/`.

---

## 4. Resumen por AcciÃ³n

| AcciÃ³n | Archivos | Destino |
|--------|----------|---------|
| ARCHIVE_TO_PRE_CLEANUP | 7 | `docs/archive/pre-cleanup-20260531/` |
| QUARANTINE_DELETE_CANDIDATE | 1 | `docs/quarantine/pre-cleanup-20260531/` |
| MERGE_LATER | 18 | In situ hasta revisiÃ³n manual |
| NO_TOUCH | 277 | In situ |
| REVIEW_MANUAL (dentro de MERGE) | 4 | `EVENT-BUS.md`, `RUNTIME-FLOW.md`, `ARQUITECTURA_PUBLICO_PRIVADO.md`, `ASTRO_CLOUDFLARE_GITHUB.md` |

---

## 5. Dependencias y Orden de EjecuciÃ³n

La fase `AI-LAB-ASTRO-DOCUMENTATION-CLEANUP-APPLY-01` debe ejecutar en este orden:

1. **PASO 0 â€” ValidaciÃ³n pre-apply**
   - Releer este plan
   - Verificar que `docs/archive/` y `docs/quarantine/` no existen (creaciÃ³n limpia)

2. **PASO 1 â€” QUARANTINE** (1 archivo, riesgo NULO)
   - Mover `Nuevo Documento de texto.md` a cuarentena

3. **PASO 2 â€” ARCHIVE duplicados exactos** (5 archivos, riesgo BAJO)
   - Archivar `gateway-graceful-shutdown.md`
   - Archivar `ARCHITECTURE_PHASE8.md`, `EVENT_BUS.md`, `SSE_RUNTIME.md`, `TOPOLOGY_LAYER.md`

4. **PASO 3 â€” ARCHIVE con precauciÃ³n** (2 archivos, riesgo MEDIO)
   - Archivar `RUNTIME_FLOW.md` (diferente del src)
   - Archivar `SSE-RUNTIME.md` (similar al underscore archivado)

5. **PASO 4 â€” REVISIÃ“N MANUAL** (4 archivos, riesgo ALTO)
   - `EVENT-BUS.md`: evaluar si es documento independiente o versiÃ³n extendida
   - `RUNTIME-FLOW.md`: evaluar fusiÃ³n con `src/content/docs/runtime_flow.md`
   - `ARQUITECTURA_PUBLICO_PRIVADO.md`: evaluar solapamiento con ASTRO-DEPLOYMENT-GOVERNANCE.md
   - `ASTRO_CLOUDFLARE_GITHUB.md`: evaluar solapamiento con ASTRO-DEPLOYMENT-GOVERNANCE.md

6. **PASO 5 â€” MERGE_LATER** (14 archivos restantes)
   - Migrar contenido valioso a `src/content/docs/`
   - Archivar el original tras migraciÃ³n confirmada

---

## 6. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | MitigaciÃ³n |
|--------|-------------|---------|------------|
| Archivar archivo con enlaces activos | Baja | Medio | Verificar referencias cruzadas antes de archivar. En fase APPLY, ejecutar `grep -r "enlace"` |
| Contenido diferente entre underscore y hyphen no detectado | Media | Medio | REVIEW_MANUAL explÃ­cito para los 4 archivos con contenido Ãºnico |
| MERGE_LATER pospuesto indefinidamente | Alta | Bajo | Los archivos legacy permanecen in situ hasta decisiÃ³n. No hay urgencia |
| ConfusiÃ³n entre `docs/` y `src/content/docs/` | Media | Alto | Este plan documenta claramente quÃ© archivos estÃ¡n en cada ubicaciÃ³n y quÃ© hacer |

---

## 7. Criterios para la Fase APPLY

La fase `AI-LAB-ASTRO-DOCUMENTATION-CLEANUP-APPLY-01` debe:
1. **SÃ** ejecutar los comandos `mv` documentados
2. **SÃ** crear las estructuras `archive/` y `quarantine/`
3. **SÃ** verificar que nada se rompe tras archivar (build de Astro)
4. **NO** borrar nada permanentemente (ni siquiera de cuarentena)
5. **NO** modificar contenido de ningÃºn archivo
6. **NO** migrar MERGE_LATER â€” eso requiere una fase separada

---

*Fin del informe AI-LAB-ASTRO-DOCUMENTATION-CLEANUP-PLAN-01*
