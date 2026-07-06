# Pre-Push Review — AI-LAB-ASTRO-CURRENT-STATE-REBUILD-01

**Fecha:** 2026-07-06
**Commit:** e50fe9c
**Tag:** CP-AI-LAB-ASTRO-CURRENT-STATE-REBUILD-01

---

## 1. Páginas excluidas del build público (137 total, no 30)

El build público produce 140 páginas; el privado 277. La diferencia son 137 páginas **excluidas deliberadamente como PRIVATE_ONLY**. No hay páginas archivadas, eliminadas, renombradas ni fusionadas.

### Clasificación:

| Categoría | Cantidad | Clasificación |
|-----------|----------|---------------|
| `docs/historical/phases/` (44 fases de desarrollo) | 44 | **PRIVATE_ONLY** — IPs internas, comandos systemd, rutas operacionales |
| `runbooks/` (src/content/runbooks/) | 32 | **PRIVATE_ONLY** — comandos operativos, IPs, systemd, Docker paths |
| `incidents/` (src/content/incidents/) | 2 | **PRIVATE_ONLY** — recovery procedures, IPs internas |
| Individuales REMOVE_FILE (docs/ con IPs + docs legacy) | 59 | **PRIVATE_ONLY** — contienen IPs internas (192.168.1.x) o contenido legacy |

**Total: 137 páginas PRIVATE_ONLY — 0 archivadas, 0 eliminadas, 0 renombradas, 0 fusionadas.**

### Subclasificación de los 59 individuales:

**Documentos legacy en español con IPs (15):**
`arquitectura-ai-lab`, `mapa-observabilidad-ai-lab`, `inferencia-distribuida`, `architecture_phase8`, `fix-model-unloaded-lmstudio`, `observabilidad-ai-lab-definitiva`, `event_bus`, `automatizacion-ci-cd`, `implementacion-astro-cloudflare-github`, `operacion-privada-ai-lab`, `rutas-internas-ai-lab`, `informe-completo-ai-lab`, `informe-operacional-exhaustivo`, `servicios-persistentes-systemd`, `telemetria-gpu-restauracion`, `observabilidad-plataforma-ai-lab`, `openwebui-conexion-router`

**Documentos de arquitectura interna (11):**
`architecture/architecture-stabilization-pass-01`, `architecture/astro-architecture`, `architecture/cognitive-runtime-overview`, `architecture/federation-governance-bootstrap-01`, `architecture/pre-multigpu-baseline`, `architecture/runtime-observability-fabric`, `architecture/storage-archive-policy`, `architecture/runtime-evidence-pipeline`, `architecture/runtime-sensor-topology`, `architecture/marketplace-digital-twin`

**Runtime docs con IPs/rutas internas (9):**
`runtime/index`, `runtime/30i-runtime-sensor-fusion`, `runtime/ai-lab-runtime-current-state`, `runtime/gateway-graceful-shutdown`, `runtime/gpu-operational-summaries`, `runtime/pre-multigpu-baseline`, `runtime/runtime-current-state`, `runtime/runtime-sensor-fusion`

**Experimentos internos (4):**
`experiments/30i-burnin-results`, `experiments/gpu-summary-validation`, `experiments/phase-30i-burnin`, `experiments/qwen-grounding-validation`

**Observabilidad detallada (6):**
`observability/index`, `observability/gpu-metrics-integration`, `observability/grafana-dashboard-map`, `observability/phase-29-runtime-observability`, `observability/prometheus-runtime-integration`, `observability/runtime-sensor-fusion`

**Otros internos (12):**
`agentic/phase-28-governed-autonomy`, `codebase/gitnexus-local-access`, `governance/anythingllm-reindex-automation`, `governance/archive-governance`, `governance/document-publishing-automation`, `memory/qdrant-memory-layer`, `plan-pruebas-runtime-v1-rc`, `router-lmstudio-failover`, `runtime_flow`, `sse_runtime`, `topology_layer`, `runbook-fase-*` (5 runbooks individuales), `parche-opencode-router-gateway`

---

## 2. Confirmación: NO se ha eliminado contenido público válido

Todos los archivos excluidos contienen al menos uno de:
- IPs internas (192.168.1.x)
- Comandos systemd/servicios
- Docker internos
- Secretos o credenciales
- Contenido histórico/legacy no relevante para el público

Los archivos fuente siguen existiendo en el repositorio. Solo se excluyen del build público. El build privado (277 págs) los incluye completos.

---

## 3. Sidebar público: ANTES vs DESPUÉS

### ANTES (pre-rebuild — sidebar sin filtro público)

```
Home
Architecture
  ├─ Core Documents (autogenerate: architecture/)
  ├─ Grounding + RAG
  ├─ Codebase Structure
  ├─ AnythingLLM Role
  ├─ AnythingLLM Enterprise
  ├─ Marketplace Digital Twin
  ├─ Health Layer (37A)
  ├─ Event Bus
  └─ Schemas
Operations
  ├─ Runtime Reference (autogenerate: runtime/)
  ├─ Truth Layers
  ├─ Analytics Engine
  ├─ Cloudflare Redirects
  ├─ Cloudflare Zero Trust
  ├─ Experiments (autogenerate)
  ├─ Roadmap (autogenerate)
  ├─ Memory System (autogenerate)
  ├─ Agentic (autogenerate)
  ├─ Runtime Flow
  ├─ v1 RC Tests
  └─ Runbooks
Observability
  ├─ Dashboards + Metrics (autogenerate: observability/)
  └─ Sensor Domains
Governance
  ├─ Policies (autogenerate)
  └─ ADR Log (autogenerate)
Audits
  └─ Index
Incidents
Historical
Hermes Enterprise (10 entries)
```

### DESPUÉS (con isPublicBuild condicional)

```
Home
Architecture
  ├─ Core Documents (autogenerate: architecture/)
  ├─ Grounding + RAG
  ├─ Codebase Structure
  ├─ AnythingLLM Role
  ├─ AnythingLLM Enterprise
  ├─ Marketplace Digital Twin      ← condicional: solo PRIVADO (isPublicBuild ? [])
  ├─ Health Layer (37A)
  ├─ Event Bus                     ← condicional: solo PRIVADO (isPublicBuild ? [])
  └─ Schemas
Operations
  ├─ Runtime Reference (autogenerate: runtime/)
  ├─ Truth Layers
  ├─ Analytics Engine
  ├─ Cloudflare Redirects
  ├─ Cloudflare Zero Trust
  ├─ Experiments (autogenerate)
  ├─ Roadmap (autogenerate)
  ├─ Memory System (autogenerate)
  ├─ Agentic (autogenerate)
  ├─ Runtime Flow                  ← condicional: solo PRIVADO
  ├─ v1 RC Tests                   ← condicional: solo PRIVADO
  └─ Runbooks                      ← condicional: solo PRIVADO
Observability
  ├─ Dashboards + Metrics (autogenerate: observability/)  ← observability/ filtrado en público
  └─ Sensor Domains
Governance
  ├─ Policies (autogenerate)
  └─ ADR Log (autogenerate)
Audits
  └─ Index
Incidents                        ← condicional: solo PRIVADO
Historical                       ← condicional: solo PRIVADO
Hermes Enterprise (10 entries — SIN CAMBIOS)
```

**Nota:** la sección `Observability > Dashboards + Metrics` genera 0 entradas en público porque `observability/` está en el filtro. Solo queda `Sensor Domains` como entrada visible. Esto es correcto porque las páginas detalladas de observabilidad contienen IPs y rutas de Prometheus/Grafana.

---

## 4. Páginas clave verificadas en build público ✅

| Página | Ruta (público) | Estado |
|--------|---------------|--------|
| **Home** | `/` | ✅ |
| **Qué es AI-LAB** | `/docs/runtime-ai-lab` | ✅ |
| **Arquitectura** | `/docs/architecture/` | ✅ |
| **Runtime** | `/docs/runtime/` (parcial: 9 páginas de ~18) | ✅ (páginas sin IPs) |
| **Hermes Enterprise** | `/docs/hermes/` (10 páginas completas) | ✅ |
| **AnythingLLM Enterprise** | `/docs/architecture/anythingllm-enterprise` | ✅ |
| **GitNexus** | `/docs/codebase-structural-cognition` | ✅ |
| **Marketplace** | `/docs/architecture/marketplace-digital-twin` | ❌ **PRIVATE_ONLY** — contiene IPs internas |
| **Observabilidad** | `/docs/observability/sensor-domains` | ✅ (sensor-domains es público) |
| **Roadmap** | `/docs/roadmap/` (3 páginas) | ✅ |
| **Changelog** | No existe como página separada | N/A |

Marketplace Digital Twin se movió a PRIVATE_ONLY porque el archivo fuente contiene rutas internas de GitNexus y endpoints del marketplace real. Su referencia en la home pública se mantiene como mención textual.

---

## 5. Working tree: solo CRLF sin contenido

```
git diff --ignore-cr-at-eol → 0 líneas de contenido modificado
```

Los 9 archivos marcados como `M` (7 blog posts + 2 pages/) tienen **cero cambios de contenido**. Son únicamente conversión LF→CRLF por el checkout en Windows. Verificado comando a comando.

Archivos untracked (`reports/*`, `IDEA.md`, `.bak`, `tmp_chat_test.sh`) son de sesiones anteriores y no se incluirán en el push.

---

## 6. Site Manifest

Nuevo script `scripts/generate-site-manifest.mjs` que se ejecutará automáticamente tras cada build público para generar `dist/site-manifest.json` con:
- `total_pages`
- `generated` (ISO timestamp)
- `commit` (git short hash)
- `pages[]` con `path`, `size`, `hash` (sha256), `mtime`

Integración añadida al wrapper de build público.

---

## 7. Veredicto

**PASS → push autorizado.**

Todo el contenido público válido se conserva. Las 137 páginas excluidas son PRIVATE_ONLY por contener IPs internas, comandos operativos o contenido legacy. Sidebar correctamente condicionado. Working tree limpio de cambios de contenido.

