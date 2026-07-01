# AI-LAB-ASTRO-INFORMATION-ARCHITECTURE-01

**Fecha:** 2026-05-31
**Modo:** READ ONLY ABSOLUTO
**Precondiciones:** Governance PASS, Inventory PASS, Cleanup Plan PASS, Cleanup Apply PASS
**Resultado:** PASS

---

## FASE 0 â€” MAPA ACTUAL

### Estructura del sitio AI-LAB Astro

El sitio tiene **dos sistemas de pÃ¡ginas** que coexisten:

#### 1. Starlight Docs (`src/content/docs/`)

Auto-genera la barra lateral. OrganizaciÃ³n por subdirectorios:

```
docs/                    (11 subdirectorios + 88 flat files en root)
  adrs/                  6 ADRs + index
  agentic/               1 doc + index
  architecture/          18 docs + index
  codebase/              1 doc + index
  experiments/           5 docs + index
  governance/            5 docs + index
  memory/                1 doc + index
  observability/         6 docs + index
  roadmap/               2 docs + index
  runtime/               20 docs + index
  schemas/               4 docs + index
```

#### 2. PÃ¡ginas personalizadas (`src/pages/`)

PÃ¡ginas fuera del sistema Starlight, enrutadas manualmente:

```
/                       Homepage (index.astro)
/architecture/          Portal de arquitectura
/architecture/security/
/blog/                  Blog index + [...slug]
/docs/                  Docs index + [...slug] (tambiÃ©n Starlight)
/experiments/
/hardware-lab/
/incidents/
/infra/
/knowledge/
/models/
/observability/
/ops/                   commands, learning, memory
/portal/
/projects/
/research/
/runbooks/              index + [...slug]
/services/
/skills/
/status/                gpus, history, live, models, topology
```

### Problemas del mapa actual

| Problema | Impacto |
|----------|---------|
| 88 flat files en `src/content/docs/` root | Sin categorizaciÃ³n, mezclan fases histÃ³ricas, runbooks, arquitectura |
| 3 ubicaciones para runbooks: `src/content/runbooks/` (32), `src/content/docs/runbook-*` (4), `src/pages/runbooks/` (5) | FragmentaciÃ³n total de runbooks |
| 2 ubicaciones para incidents: `src/content/incidents/` (2) + `src/pages/incidents/` | DuplicaciÃ³n de entrada |
| NavegaciÃ³n Starlight sin sidebar personalizada | Orden alfabÃ©tico por defecto, sin jerarquÃ­a semÃ¡ntica |
| 55 documentos de fase histÃ³rica mezclados con contenido activo | Ruido documental |
| 23 archivos `docs/` raÃ­z legacy no migrados a Astro | Contenido invisible para el sitio |
| `architecture_phase8.md` como flat file vs `architecture/` como directorio | ConfusiÃ³n semÃ¡ntica |
| docs en EspaÃ±ol + InglÃ©s sin separaciÃ³n | Mezcla de idiomas |

---

## FASE 1 â€” DOMINIOS DOCUMENTALES

### Dominios identificados (12 dominios)

| # | Dominio | PropÃ³sito | Audiencia | Propietario | Volumen |
|---|---------|-----------|-----------|-------------|---------|
| 1 | **Architecture** | DiseÃ±o del sistema, bounded contexts, truth layers, federaciÃ³n | Ingenieros, operadores | Runtime owner | 38 docs |
| 2 | **Runtime** | Estado vivo del runtime, madurez, sensor fusion, precisiÃ³n | Operadores, agentes | Runtime owner | 20 docs |
| 3 | **Operations** | OperaciÃ³n diaria, recuperaciÃ³n, troubleshooting | Operadores | Sysadmin | 12 docs |
| 4 | **Runbooks** | Procedimientos paso a paso para tareas operativas | Operadores, agentes | Sysadmin | 36 docs |
| 5 | **Observability** | Prometheus, mÃ©tricas, dashboards, SLOs, alerts | Operadores | Observability owner | 16 docs |
| 6 | **Governance** | Trust boundaries, operational truth, ADRs, polÃ­ticas | Agentes, operadores | Governance owner | 8 docs |
| 7 | **Audits** | Informes forenses, anÃ¡lisis de codebase, health score | Operador, agentes | Auditor | 25 docs |
| 8 | **ADRs** | Decisiones arquitectÃ³nicas registradas | Ingenieros | Architecture owner | 7 docs |
| 9 | **MCP / OpenCode** | IntegraciÃ³n con OpenCode, MCP servers | Agentes | Agent owner | 4 docs |
| 10 | **Infrastructure / Storage** | Servidores, GPUs, almacenamiento, redes | Sysadmin | Sysadmin | 8 docs |
| 11 | **Blog** | ArtÃ­culos pÃºblicos, divulgaciÃ³n tÃ©cnica | PÃºblico externo | Operator | 25 docs |
| 12 | **Historical (Fases)** | Registro de fases del proyecto (FASE-11 a 36+) | Archivo | Archiver | 55 docs |

### Problemas con la clasificaciÃ³n actual

1. **No hay separaciÃ³n** entre "activo" e "histÃ³rico" â€” fases antiguas coexisten con documentaciÃ³n operativa vigente
2. **No hay separaciÃ³n** entre pÃºblico y privado â€” contenido operacional sensible (runbooks, IPs) estÃ¡ mezclado con blog pÃºblico
3. **Runbooks fragmentados** en 3 ubicaciones
4. **Audits** estÃ¡n solo en `docs/` (fuera de Astro), invisibles para el navegador

---

## FASE 2 â€” NAVEGACIÃ“N OBJETIVO

### Propuesta de sidebar Starlight

Basada en 6 secciones principales (colapsando las 12 categorÃ­as en agrupaciones lÃ³gicas).

```
ðŸ“‹ AI-LAB Docs
â”œâ”€â”€ ðŸ—ï¸ Architecture
â”‚   â”œâ”€â”€ Overview
â”‚   â”œâ”€â”€ Core Runtime Architecture
â”‚   â”œâ”€â”€ Cognitive Layer
â”‚   â”œâ”€â”€ Routing & Federation
â”‚   â”œâ”€â”€ Memory & Knowledge
â”‚   â”œâ”€â”€ Infrastructure & Storage
â”‚   â””â”€â”€ Architecture Decisions (ADRs)
â”‚
â”œâ”€â”€ âš™ï¸ Operations
â”‚   â”œâ”€â”€ Runbooks (Ã­ndice maestro)
â”‚   â”‚   â”œâ”€â”€ Gateway
â”‚   â”‚   â”œâ”€â”€ Router
â”‚   â”‚   â”œâ”€â”€ Docs / Astro
â”‚   â”‚   â”œâ”€â”€ GPU / LM Studio
â”‚   â”‚   â”œâ”€â”€ GitNexus
â”‚   â”‚   â”œâ”€â”€ Recovery
â”‚   â”‚   â””â”€â”€ Maintenance
â”‚   â”œâ”€â”€ Daily Operations
â”‚   â”œâ”€â”€ Incident Response
â”‚   â””â”€â”€ Troubleshooting
â”‚
â”œâ”€â”€ ðŸ“Š Observability
â”‚   â”œâ”€â”€ Metrics & Prometheus
â”‚   â”œâ”€â”€ Dashboards & Grafana
â”‚   â”œâ”€â”€ SLOs & Alerts
â”‚   â”œâ”€â”€ Sensor Fusion
â”‚   â””â”€â”€ Health Score
â”‚
â”œâ”€â”€ ðŸ›¡ï¸ Governance
â”‚   â”œâ”€â”€ Operational Truth
â”‚   â”œâ”€â”€ Trust Boundaries
â”‚   â”œâ”€â”€ Evidence Enforcement
â”‚   â”œâ”€â”€ Worktree Governance
â”‚   â””â”€â”€ Agent Constitution
â”‚
â”œâ”€â”€ ðŸ“ Audits & Forensics
â”‚   â”œâ”€â”€ Architecture Audits
â”‚   â”œâ”€â”€ Health Score Audits
â”‚   â”œâ”€â”€ Observability Recovery
â”‚   â””â”€â”€ Runtime Stability
â”‚
â””â”€â”€ ðŸ—„ï¸ Historical
    â”œâ”€â”€ Phase Index
    â”œâ”€â”€ Completed Phases (Fase-11 a Fase-36)
    â””â”€â”€ Legacy Docs Archive
```

### PÃ¡ginas personalizadas (fuera de Starlight)

| Ruta | PropÃ³sito | Se mantiene |
|------|-----------|-------------|
| `/` | Homepage | SI |
| `/blog/` | Blog pÃºblico | SI |
| `/status/` | Estado vivo (snapshots) | SI |
| `/api/*` | Endpoints JSON | SI |
| `/ops/` | Comandos rÃ¡pidos | SI (mover a Operations) |
| `/infra/` | Estado infraestructura | SI |
| `/models/` | CatÃ¡logo modelos | SI |
| `/services/` | CatÃ¡logo servicios | SI |

### Rutas a eliminar o consolidar

| Ruta actual | AcciÃ³n | RazÃ³n |
|-------------|--------|-------|
| `/experiments/` | Mover a Historical | Los experiments son histÃ³ricos |
| `/incidents/` | Fusionar con Operations | Incidentes son parte de operaciones |
| `/portal/` | Revisar | Â¿Sigue activo? |
| `/skills.bak-before-observability-links/` | Archivar | Backup evidente |
| `/research/` | Fusionar con Architecture/Blog | Sin contenido independiente |

---

## FASE 3 â€” AUDITORÃAS

### docs/audits/ â€” 21 archivos

#### AuditorÃ­as permanentes (deben permanecer accesibles)

| Archivo | Motivo |
|---------|--------|
| ASTRO-DEPLOYMENT-GOVERNANCE.md | Governance activo, referencia obligatoria |
| ASTRO-DOCUMENTATION-INVENTORY-01.md | Base del plan de limpieza |
| ASTRO-DOCUMENTATION-CLEANUP-PLAN-01.md | Plan vigente |
| ASTRO-DOCUMENTATION-CLEANUP-APPLY-01.md | EjecuciÃ³n realizada |
| OBSERVABILITY-RECOVERY-SUMMARY-01.md | Resumen de recuperaciÃ³n reciente |
| HEALTH-SCORE-SOURCE-OF-TRUTH-01.md | Contrato canÃ³nico de health score |

#### AuditorÃ­as histÃ³ricas (valor de referencia, pueden archivarse)

| Archivo | Motivo |
|---------|--------|
| ARCHITECTURE-FORENSICS-01 | Codebase audit inicial |
| HEALTH-SCORE-CONTRACT-SPEC-01 | Superado por SOURCE-OF-TRUTH |
| HEALTH-SCORE-METRICS-ALIGNMENT-01 | Superado por implementaciÃ³n |
| HEALTH-SCORE-DASHBOARD-ALIGNMENT-SPEC-01 | Superado por implementaciÃ³n |
| HEALTH-SCORE-DASHBOARD-ALIGNMENT-01 | ImplementaciÃ³n completada |
| GRAFANA-PROVISIONING-VALIDATION-01 | Tarea puntual completada |
| DASHBOARD-DRIFT-AUDIT-01 | Tarea puntual completada |
| PROMETHEUS-RUNTIME-HEALTH-RECORDING-RULE-01 | Tarea puntual |
| PROMETHEUS-RUNTIME-HEALTH-RECORDING-RULE-FIX-01 | Tarea puntual |
| HEALTH-SCORE-DRIFT-RULE-01 | Tarea puntual |

### PolÃ­tica propuesta para auditorÃ­as

1. **Permanentes** (6): se integran a la navegaciÃ³n Starlight bajo "Audits & Forensics"
2. **HistÃ³ricas** (10): se mueven a `docs/archive/audits/` con Ã­ndice
3. **Fechadas**: todas las auditorÃ­as deben incluir fecha en el filename (formato YYYY-MM-DD)
4. **MÃ¡ximo 10 auditorÃ­as activas**: cuando se supera, archivar las mÃ¡s antiguas

---

## FASE 4 â€” FASES HISTÃ“RICAS

### DiagnÃ³stico

55 documentos histÃ³ricos de fase, numerados FASE-11 a FASE-36, mÃ¡s algunos sin numerar.

**Problemas:**
- Ocupan el root de `src/content/docs/` sin subdirectorio
- No hay separaciÃ³n entre fase completada y fase activa
- Una fase puede tener 1 a 5 documentos sin agrupaciÃ³n
- Nombres inconsistentes: `fase-29.4.1-` vs `fase-2941-` vs `fase-26.2-`

### Estrategia propuesta

1. **Crear `src/content/docs/historical/phases/`**
2. **Mover todas las fases** a ese subdirectorio
3. **Crear `index.md`** con tabla de fases (nÃºmero, tÃ­tulo, fecha, estado)
4. **Marcar fases completadas** con frontmatter `status: completed`
5. **Consolidar sub-fases**: `fase-29.4.1`, `fase-29.4.2`, etc. bajo `fase-29/` o mantener planas

### Volumen estimado

| Grupo | Archivos | AcciÃ³n |
|-------|----------|--------|
| FASE-11 a FASE-20 | 12 | Mover a historical/phases/ |
| FASE-21 a FASE-29 | 25 | Mover a historical/phases/ |
| FASE-94, 95, 951 | 3 | Mover a historical/phases/ |
| roadmap-legacy, ai-lab-v1-rc, snapshots-historicos | 3 | Mover a historical/ |
| research-qdrant-cognitive-layer, retrospectiva-fase18 | 2 | Evaluar si van a historical o se mantienen activos |

---

## FASE 5 â€” DOCUMENTOS CRÃTICOS

### Top 20 documentos mÃ¡s importantes de AI-LAB

| # | Documento | Dominio | Por quÃ© es crÃ­tico |
|---|-----------|---------|---------------------|
| 1 | ASTRO-DEPLOYMENT-GOVERNANCE.md | Governance | Source of truth de despliegue web. Obligatorio para cualquier agente |
| 2 | cognitive-health-layer.py | Runtime | CÃ³digo fuente del health score canÃ³nico |
| 3 | AI-LAB-HEALTH-SCORE-SOURCE-OF-TRUTH-01.md | Audit | Contrato canÃ³nico de health score (5 sistemas identificados) |
| 4 | Federated Runtime Agent Constitution (AGENTS.md) | Governance | Doctrina operacional de runtime governance |
| 5 | AI-LAB-ARCHITECTURE-FORENSICS-01.md | Audit | Inventario completo del codebase (104K LOC, circulares, super-mÃ³dulos) |
| 6 | runtime/30i-runtime-sensor-fusion.md | Runtime | Sensor fusion â€” columna vertebral de observabilidad |
| 7 | runtime/runtime-current-state.md | Runtime | Estado actual del runtime (living document) |
| 8 | architecture/runtime-observability-fabric.md | Architecture | Tejido de observabilidad del runtime |
| 9 | architecture/runtime-domains.md | Architecture | Bounded contexts del runtime |
| 10 | architecture/federation-governance-bootstrap-01.md | Architecture | FederaciÃ³n y governance multi-nodo |
| 11 | runtime/cognitive-health-layer.md | Runtime | DocumentaciÃ³n de la capa cognitiva de salud |
| 12 | runtime/cognitive-slo-governance.md | Runtime | SLO governance del runtime cognitivo |
| 13 | governance/operational-truth.md | Governance | Verdad operacional frente a datos descubribles |
| 14 | governance/runtime-trust-boundaries.md | Governance | LÃ­mites de confianza entre dominios |
| 15 | runtime/authority-backed-cognition-35c.md | Runtime | Authority-backed cognition |
| 16 | runtime/precision-semantics-36b.md | Runtime | PrecisiÃ³n semÃ¡ntica |
| 17 | observability/prometheus-runtime-integration.md | Observability | IntegraciÃ³n Prometheus con el runtime |
| 18 | observability/sensor-domains.md | Observability | Dominios de sensores de observabilidad |
| 19 | runtime/observed-runtime-contract.md | Runtime | Contrato de runtime observado |
| 20 | architecture/pre-multigpu-baseline.md | Architecture | Baseline pre-Multi-GPU (decisiÃ³n arquitectÃ³nica crÃ­tica) |

### Criterios de selecciÃ³n

- **Valor operativo**: documentos necesarios para operar el sistema (runbooks, governance)
- **Valor arquitectÃ³nico**: decisiones de diseÃ±o que definen la estructura del sistema
- **Valor contractual**: contratos, interfaces, APIs, source of truth
- **Valor histÃ³rico-cultural**: decisiones que explican por quÃ© el sistema es como es
- **Valor para agentes**: documentaciÃ³n que un agente AI debe leer antes de modificar algo

---

## FASE 6 â€” ROADMAP DOCUMENTAL

### Fase 1: Consolidation (EstimaciÃ³n: BAJO)

**AcciÃ³n:** Mover las fases histÃ³ricas a `historical/phases/`.

| Paso | Archivos | Dependencia |
|------|----------|-------------|
| Mover fase-11 a fase-36 | ~45 | Ninguna |
| Mover roadmap-legacy, snapshots-historicos | ~3 | Ninguna |
| Actualizar sidebar Starlight | 1 archivo | Movimientos completados |
| Verificar build | â€” | Post-movimiento |

**Tiempo estimado:** 30 minutos.

### Fase 2: Navigation (EstimaciÃ³n: MEDIO)

**AcciÃ³n:** Implementar sidebar personalizada Starlight con la jerarquÃ­a propuesta en Fase 2.

| Paso | Dependencia |
|------|-------------|
| Definir sidebar en `astro.config.mjs` | ConsolidaciÃ³n completada |
| Agrupar 88 flat files en subdirectorios | ConsolidaciÃ³n completada |
| Crear Ã­ndices para cada grupo | Sidebar definida |
| Verificar que ningÃºn enlace se rompe | Todo lo anterior |

**Tiempo estimado:** 2-3 horas.

### Fase 3: Audit Organization (EstimaciÃ³n: BAJO)

**AcciÃ³n:** Clasificar auditorÃ­as en permanentes e histÃ³ricas.

| Paso | Archivos | Dependencia |
|------|----------|-------------|
| Mover 10 auditorÃ­as histÃ³ricas a `docs/archive/audits/` | 10 | Ninguna |
| Integrar 6 auditorÃ­as permanentes a navegaciÃ³n Astro | 6 | Navigation completada |
| Crear Ã­ndice de auditorÃ­as | â€” | Movimientos completados |

**Tiempo estimado:** 30 minutos.

### Fase 4: Historical Archive (EstimaciÃ³n: MEDIO)

**AcciÃ³n:** Archivar definitivamente documentos legacy de `docs/` raÃ­z.

| Paso | Archivos | Dependencia |
|------|----------|-------------|
| Revisar 18 MERGE_LATER | 18 | Cleanup completado |
| Migrar contenido valioso a `src/content/docs/` | Variable | RevisiÃ³n completada |
| Archivar el resto | Variable | MigraciÃ³n completada |

**Tiempo estimado:** 3-4 horas (depende de revisiÃ³n manual).

### Fase 5: ADR Governance (EstimaciÃ³n: ALTO)

**AcciÃ³n:** Establecer proceso formal de ADRs.

| Paso | Dependencia |
|------|-------------|
| Template de ADR (ADR-007+) | Navigation completada |
| Integrar ADRs en proceso de desarrollo | Cultural |
| Backfill de decisiones faltantes | Conocimiento del operador |

**Tiempo estimado:** Continuo.

### Diagrama de dependencias

```
Consolidation â”€â”€> Navigation â”€â”€> Audit Organization
                                      â”‚
                                      v
                              Historical Archive
                                      â”‚
                                      v
                              ADR Governance
```

---

## SALIDA EJECUTIVA

### 1. Â¿CuÃ¡l deberÃ­a ser la estructura documental definitiva?

Un sistema de **6 secciones Starlight** (Architecture, Operations, Observability, Governance, Audits, Historical) + pÃ¡ginas especiales independientes (Home, Blog, Status, API). El directorio `src/content/docs/` debe tener **subdirectorios semÃ¡nticos**, no 88 flat files sueltos. Los runbooks deben unificarse en una sola ubicaciÃ³n.

```
src/content/docs/
  architecture/     (38 docs â€” actuales runtime/ + architecture/ + schemas/)
  operations/       (48 docs â€” runbooks + incidentes + troubleshooting)
  observability/    (16 docs â€” actuales)
  governance/       (8 docs â€” actuales + AGENTS.md como referencia)
  audits/           (6 docs â€” solo permanentes)
  historical/       (55 docs â€” fases + experiments + legacy)
```

### 2. Â¿QuÃ© estÃ¡ peor organizado actualmente?

**Los 88 flat files en root de `src/content/docs/`.** Mezclan:
- Fases histÃ³ricas (`fase-11-cognitive-recall.md`)
- Runbooks (`runbook-cloudflare-pages.md`)
- Arquitectura (`almacenamiento-ai-lab.md`, `automatizacion-ci-cd.md`)
- Operaciones (`plan-pruebas-runtime-v1-rc.md`)
- Documentos huÃ©rfanos (`fix-model-unloaded-lmstudio.md`)

Esto hace que la navegaciÃ³n automÃ¡tica de Starlight muestre una lista alfabÃ©tica inmanejable.

### 3. Â¿QuÃ© aporta mÃ¡s valor reorganizar primero?

**La ConsolidaciÃ³n de fases histÃ³ricas (Fase 1 del roadmap).** Porque:
- Elimina el 64% del ruido del root de docs/ (55 de 88 flat files)
- Coste mÃ­nimo (solo mover archivos, actualizar sidebar)
- Impacto inmediato en la navegaciÃ³n
- No requiere decisiones arquitectÃ³nicas complejas

### 4. Â¿QuÃ© NO deberÃ­a tocarse?

| Elemento | RazÃ³n |
|----------|-------|
| `src/pages/` pages activas (/, /blog/, /status/, /api/) | Funcionan bien, tienen audiencia definida |
| `src/content/runbooks/` (32 docs) | Ya estÃ¡n correctamente aislados |
| `src/content/blog/` (25 docs) | SeparaciÃ³n pÃºblico/privado clara |
| `docs/opencode/` (23 docs) | DocumentaciÃ³n de otro proyecto, no tocar |
| `docs/archive/` | Ya organizado por el cleanup |
| Las 6 auditorÃ­as permanentes | Mantener accesibles |
| `astro.config.mjs` sidebar hasta Fase 2 | No tocar sidebar sin tener los docs organizados |

### 5. Â¿CuÃ¡l es el riesgo de seguir creciendo sin reorganizar?

| Riesgo | Probabilidad | Impacto |
|--------|-------------|---------|
| **Colapso de navegaciÃ³n**: 88+ flat files se vuelven imposibles de explorar | Alta (prÃ³ximas 50 fases) | Alto â€” el sitio pierde utilidad como referencia |
| **DuplicaciÃ³n**: nuevos documentos se crean sin saber que ya existen | Alta | Medio â€” contenido contradictorio |
| **FragmentaciÃ³n de runbooks**: crecen en 3 ubicaciones sin coordinaciÃ³n | Alta | Medio â€” operadores no encuentran procedimientos |
| **PÃ©rdida de auditorÃ­as**: al no estar en Astro, quedan invisibles | Media | Medio â€” decisiones no documentadas se pierden |
| **Onboarding imposible para agentes**: sin jerarquÃ­a clara, los agentes no saben quÃ© leer | Alta | Alto â€” agents pierden contexto |

El riesgo inmediato es **navegaciÃ³n inutilizable** si se aÃ±aden 20-30 documentos mÃ¡s al root. La mitigaciÃ³n es la Fase 1 (Consolidation) que cuesta ~30 minutos y resuelve el 80% del problema.

---

*Fin del informe AI-LAB-ASTRO-INFORMATION-ARCHITECTURE-01*
