# ANYTHINGLLM-ENTERPRISE-01: Workspace Design

**Estado:** ✅ PASS — Diseño completo
**Fecha:** 2026-07-04
**HEAD:** d92cc92 (CP-HERMES-DOCS-ASTRO-ENTERPRISE-01)

---

## 1. Rol de AnythingLLM en AI-LAB

AnythingLLM será la **memoria documental/RAG** del laboratorio. Su función es servir como repositorio semántico de conocimiento explícito, no como agente operativo ni runtime.

| Rol | Descripción | Prioridad |
|-----|-------------|-----------|
| **Documentalista técnico** | Almacenar y recuperar documentación arquitectónica, ADRs, runbooks | Alta |
| **Auditor documental** | Responder preguntas sobre decisiones pasadas, reports, fases cerradas | Alta |
| **Memoria RAG** | Proveer contexto semántico a OpenCode, Hermes y agentes vía embeddings | Media |
| **Apoyo a Hermes** | Resolver dudas de diseño enterprise, operators, capabilities, governance | Alta |
| **Apoyo a OpenCode** | Proveer contexto documental sin cargar AGENTS.md completo | Media |

### Lo que AnythingLLM NO es

- **No es un agente**: no ejecuta acciones, no modifica sistemas, no llama APIs
- **No es el runtime**: no reemplaza al gateway, router o live-api
- **No es la source of truth operacional**: Prometheus sigue siendo la autoridad para métricas; el runtime_state para estado vivo
- **No es un agente de código**: GitNexus sigue siendo la fuente de verdad estructural del código

---

## 2. Workspaces Recomendados

### 2.1 Hermes Enterprise

| Campo | Valor |
|-------|-------|
| **Propósito** | Documentación completa del sistema Hermes Enterprise: SOUL, Capabilities, Operators, Hooks, MCP, Governance, Status Endpoint |
| **Tipo de docs** | ADRs (ADR-001 a ADR-006), design docs, reports de fases, Astro docs hermes/, schemas JSON |
| **Fuentes** | `docs/hermes/*.md`, `runtime/hermes/**/*.json`, `runtime/hermes/**/*.yaml`, `reports/HERMES-ENTERPRISE-*.md`, `reports/HERMES-E*.md`, `reports/CP-HERMES-*.md`, `apps/ialab-docs/src/content/docs/hermes/*.md` |
| **Prioridad** | 🔴 Crítica (Fase A) |
| **Modelo** | `qwen2.5-coder-14b` (soporta contexto técnico y estructuras YAML/JSON) |
| **Confianza mínima** | 0.65 |
| **Reglas** | Citar ADR de origen cuando aplique. Distinguir diseño (ADR) de implementación (código). Admitir si una capability/operator solo existe como skeleton |

### 2.2 AI-LAB Runtime

| Campo | Valor |
|-------|-------|
| **Propósito** | Documentación del runtime: gateway, router, live-api, SLO, streaming, profiles, prompts, memory |
| **Tipo de docs** | Architecture docs, reports de estabilización, audits de runtime, runbooks operativos |
| **Fuentes** | `docs/architecture/*.md`, `docs/runtime/*.md`, `docs/audits/runtime/*.md`, `docs/governance/*.md`, `docs/ROADMAP-2026.md`, `docs/DOCUMENTATION-HIERARCHY.md`, `apps/ialab-docs/src/content/docs/*.md` (sin hermes/), `reports/AI-LAB-*.md`, `reports/CP-*.md` |
| **Prioridad** | 🔴 Crítica (Fase A) |
| **Modelo** | `qwen2.5-coder-14b` |
| **Confianza mínima** | 0.65 |
| **Reglas** | No inferir estado operativo — citar siempre la fuente documental. Distinguir entre lo diseñado, lo implementado y lo planeado |

### 2.3 Rioja Marketplace

| Campo | Valor |
|-------|-------|
| **Propósito** | Documentación del Marketplace Digital Twin: arquitectura, API, frontend, backend Go, PostgreSQL |
| **Tipo de docs** | Informes de marketplace, reports de integración, MCP specs, doc de operaciones |
| **Fuentes** | `docs/opencode/11-rioja-marketplace.md`, `reports/MARKETPLACE-*.md`, `reports/HERMES-MARKETPLACE-*.md`, `docs/integrations/HERMES-AI-LAB.md` |
| **Prioridad** | 🟡 Alta (Fase B) |
| **Modelo** | `qwen2.5-coder-14b` |
| **Confianza mínima** | 0.6 |
| **Reglas** | No confundir Marketplace (Windows Server .150) con AI-LAB runtime (.30). Citar fuente de integración |

### 2.4 Observabilidad

| Campo | Valor |
|-------|-------|
| **Propósito** | Documentación del stack de observabilidad: Prometheus, Grafana, Loki, Promtail, alertas, dashboards |
| **Tipo de docs** | MCP observability specs, runtime observability, alertas, dashboards |
| **Fuentes** | `docs/mcp/AI-LAB-MCP-OBSERVABILITY-*.md`, `docs/mcp/AI-LAB-MCP-PROMETHEUS-*.md`, `docs/observability/*.md`, `docs/opencode/09-observabilidad.md`, `reports/AI-LAB-GPU-OBSERVABILITY-*.md` |
| **Prioridad** | 🟡 Alta (Fase B) |
| **Modelo** | `llama-3.1-8b` (consultas factuales sobre config) |
| **Confianza mínima** | 0.7 |
| **Reglas** | Citar métrica exacta y endpoint Prometheus. No inferir estado actual de dashboards — solo documentación |

### 2.5 MCP y A2A

| Campo | Valor |
|-------|-------|
| **Propósito** | Documentación del ecosistema MCP: servidores, tools, resources, auth, protocolo |
| **Tipo de docs** | MCP specs, LAN endpoint docs, token auth, GitNexus MCP, runtime MCP |
| **Fuentes** | `docs/mcp/*.md` (todos), `docs/audits/mcp/*.md` |
| **Prioridad** | 🟢 Media (Fase C) |
| **Modelo** | `qwen2.5-coder-14b` |
| **Confianza mínima** | 0.6 |
| **Reglas** | Distinguir servidores implementados vs planificados. No documentar tools que no existen en código |

### 2.6 Stack-2026

| Campo | Valor |
|-------|-------|
| **Propósito** | Visión global del stack tecnológico: hardware, software, servicios, redes, dominios |
| **Tipo de docs** | Informes técnicos, inventario hardware, topología, modelo reference audit |
| **Fuentes** | `docs/opencode/06-hardware-infra.md`, `docs/opencode/01-arquitectura.md`, `docs/opencode/ai-lab-*.md`, `reports/AI-LAB-HARDWARE-*.md`, `reports/AI-LAB-MODEL-REFERENCE-*.md` |
| **Prioridad** | 🟢 Media (Fase C) |
| **Modelo** | `llama-3.1-8b` |
| **Confianza mínima** | 0.6 |
| **Reglas** | Citar IPs y servicios exactos. No inferir disponibilidad — marcar como DOCUMENTADO, no operativo |

### 2.7 IDS (Intrusion Detection)

| Campo | Valor |
|-------|-------|
| **Propósito** | Documentación del sistema IDS/IPS UniFi: syslog, promtail, Loki, dashboards Grafana |
| **Tipo de docs** | Docs de operaciones, observabilidad, informes de seguridad |
| **Fuentes** | `docs/opencode/03-operaciones.md`, `docs/opencode/09-observabilidad.md`, `docs/opencode/ai-lab-informe-tecnico.md` (secciones IDS/UniFi), `docs/opencode/CHANGELOG.md` |
| **Prioridad** | 🟢 Media (Fase C) |
| **Modelo** | `llama-3.1-8b` |
| **Confianza mínima** | 0.65 |
| **Reglas** | No inferir eventos de seguridad activos — solo documentación del pipeline. Citar puerto y protocolo exactos |

### 2.8 ADRs

| Campo | Valor |
|-------|-------|
| **Propósito** | Repositorio de Architectural Decision Records: decisiones pasadas, contexto, alternativas, consecuencias |
| **Tipo de docs** | ADRs de Hermes (ADR-001 a ADR-006), más ADRs futuros |
| **Fuentes** | `docs/hermes/ADR-*.md` |
| **Prioridad** | 🔴 Crítica (Fase A) |
| **Modelo** | `qwen2.5-coder-14b` |
| **Confianza mínima** | 0.7 |
| **Reglas** | Citar número de ADR y fecha. No reinterpretar decisiones — solo resumir y referenciar. Si dos ADRs parecen contradecirse, marcarlo explícitamente |

### 2.9 Reports

| Campo | Valor |
|-------|-------|
| **Propósito** | Archivo de reports de fases: qué se hizo, qué se validó, qué falló, qué sigue |
| **Tipo de docs** | Todos los reports en `reports/` |
| **Fuentes** | `reports/*.md` |
| **Prioridad** | 🟡 Alta (Fase B) |
| **Modelo** | `qwen2.5-coder-14b` |
| **Confianza mínima** | 0.6 |
| **Reglas** | Citar fase exacta y commit/tag si está disponible. Distinguir PASS, FAIL, PARTIAL. No inferir estado actual de una fase solo por su report |

### 2.10 Runbooks

| Campo | Valor |
|-------|-------|
| **Propósito** | Procedimientos operativos: reinicio de servicios, recovery, troubleshooting, verificación |
| **Tipo de docs** | Docs de operaciones, deployment procedures, recovery guides |
| **Fuentes** | `docs/opencode/03-operaciones.md`, `docs/opencode/05-desarrollo.md`, `docs/opencode/07-ecosistema-agent.md`, `apps/ialab-docs/src/content/docs/governance/*.md` |
| **Prioridad** | 🟡 Alta (Fase B) |
| **Modelo** | `llama-3.1-8b` |
| **Confianza mínima** | 0.7 |
| **Reglas** | Si un runbook menciona comandos, listarlos textualmente. No modificar procedimientos — solo documentar. Advertir si un runbook parece desactualizado |

---

## 3. Política Global de Respuesta

```
IDIOMA:       español (por defecto)
TONO:         técnico, factual, NOC-style
FORMATO:      markdown legible en CLI

REGLAS:
1. Citar siempre la fuente documental (archivo y sección)
2. Distinguir:
   - OBSERVADO:  extraído textualmente de un documento cargado
   - INFERIDO:   deducido de múltiples fuentes (explicar razonamiento)
   - SUPUESTO:   información no documentada, basada en heurística
3. Si la respuesta no está en los documentos cargados, decirlo explícitamente
4. No inventar facts, IPs, puertos, configuraciones, servicios
5. No ejecutar acciones, no modificar sistemas, no llamar APIs
6. Si hay conflicto entre fuentes, listar ambas y marcar la discrepancia
7. Para preguntas operativas ("cómo reinicio X"), redirigir a runbooks
8. Para preguntas de código, redirigir a GitNexus
```

---

## 4. Configuración Recomendada

| Parámetro | Valor | Razón |
|-----------|-------|-------|
| **Modelo chat** | `qwen2.5-coder-14b` | Mejor comprensión de documentación técnica, código, YAML/JSON. Soporta 32K contexto |
| **Modelo embeddings** | `nomic-embed-text-v1.5` | Ya desplegado en AI-LAB LM Studio. Embeddings 768d. Buen balance recall/precisión |
| **Vector DB** | LanceDB (local) | Integrado nativamente en AnythingLLM. Sin dependencias externas. Suficiente para ~10 workspaces |
| **Tamaño chunk** | 1024 tokens | Equilibrio entre granularidad y coherencia semántica para docs técnicos |
| **Overlap** | 128 tokens | Suficiente para evitar perder contexto entre chunks en documentación estructurada (YAML, JSON, ADRs) |
| **Top-K** | 5 | Contexto suficiente para responder sin saturar ventana del modelo |
| **Temperature** | 0.2 | Mínima creatividad — queremos respuestas literales y factuales |
| **Context window** | 4096 tokens | Suficiente para 5 chunks de 1024 con overlap + instrucciones de sistema |
| **Max response tokens** | 1024 | Respuestas concisas y documentales |

### Alternativa embeddings

Si `nomic-embed-text-v1.5` no está disponible en AnythingLLM (depende de compatibilidad con el provider LM Studio), usar:

| Alternativa | Provider | Dims | Nota |
|-------------|----------|------|------|
| `text-embedding-3-small` | OpenAI (local key) | 512-1536 | Si hay API key local, mejor consistencia |
| `all-MiniLM-L6-v2` | Built-in AnythingLLM | 384 | Fallbar local sin dependencias externas |

---

## 5. Orden de Carga Documental

### Fase A — Fundación documental

```
Orden: Hermes Enterprise → ADRs → AI-LAB Runtime → Reports recientes
Prioridad: 🔴 Crítica
Dependencias: ninguna
Volumen estimado: ~50-80 archivos
```

| Paso | Workspace | Docs | Archivos |
|------|-----------|------|----------|
| A1 | **Hermes Enterprise** | ADRs, design, Astro docs, schemas | `docs/hermes/ADR-*.md`, `docs/hermes/HERMES-ENTERPRISE-DESIGN-01.md`, `runtime/hermes/**/*.json`, `runtime/hermes/**/*.yaml`, `apps/ialab-docs/src/content/docs/hermes/*.md` |
| A2 | **ADRs** | Solo ADRs (puede ser subconjunto o workspace independiente) | `docs/hermes/ADR-*.md` |
| A3 | **AI-LAB Runtime** | Architecture, runtime audits, governance, roadmap | `docs/architecture/*.md`, `docs/runtime/*.md`, `docs/audits/runtime/*.md`, `docs/governance/*.md`, `docs/ROADMAP-2026.md`, `docs/DOCUMENTATION-HIERARCHY.md` |
| A4 | **Reports** | Reports de las últimas 10 fases (desde CP-45 en adelante) | `reports/CP-*.md`, `reports/HERMES-E*.md`, `reports/HERMES-ENTERPRISE-FOUNDATION-01.md`, `reports/HERMES-ENTERPRISE-CORE-01.md`, `reports/HERMES-DOCS-ASTRO-ENTERPRISE-UPDATE-01.md` |

### Fase B — Expansión

```
Orden: Marketplace → Observabilidad → Runbooks
Prioridad: 🟡 Alta
Dependencias: Fase A completa
Volumen estimado: ~30-50 archivos
```

| Paso | Workspace | Docs | Archivos |
|------|-----------|------|----------|
| B1 | **Rioja Marketplace** | Marketplace reports, integraciones MCP | `docs/opencode/11-rioja-marketplace.md`, `reports/MARKETPLACE-*.md`, `reports/HERMES-MARKETPLACE-*.md`, `docs/integrations/HERMES-AI-LAB.md` |
| B2 | **Observabilidad** | MCP observability specs, runtime observability | `docs/mcp/AI-LAB-MCP-OBSERVABILITY-*.md`, `docs/mcp/AI-LAB-MCP-PROMETHEUS-*.md`, `docs/observability/*.md`, `docs/opencode/09-observabilidad.md` |
| B3 | **Runbooks** | Operaciones, deployment, agent ecosystem | `docs/opencode/03-operaciones.md`, `docs/opencode/05-desarrollo.md`, `docs/opencode/07-ecosistema-agent.md`, `docs/opencode/08-despliegue.md` |

### Fase C — Cobertura total

```
Orden: IDS → Stack-2026 → MCP y A2A
Prioridad: 🟢 Media
Dependencias: Fase A + B
Volumen estimado: ~40-60 archivos
```

| Paso | Workspace | Docs | Archivos |
|------|-----------|------|----------|
| C1 | **IDS** | Seguridad, promtail, syslog, dashboards IDS | Secciones IDS en `docs/opencode/03-operaciones.md`, `docs/opencode/09-observabilidad.md`, `docs/opencode/CHANGELOG.md` |
| C2 | **Stack-2026** | Hardware, topología, modelos, arquitectura global | `docs/opencode/01-arquitectura.md`, `docs/opencode/06-hardware-infra.md`, `docs/opencode/ai-lab-*.md`, `reports/AI-LAB-HARDWARE-*.md`, `reports/AI-LAB-MODEL-REFERENCE-*.md`, `reports/AI-LAB-FAST-MODEL-*.md` |
| C3 | **MCP y A2A** | MCP specs, audits MCP, GitNexus, runtime MCP | `docs/mcp/*.md` (todos), `docs/audits/mcp/*.md` |

---

## 6. Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| **AnythingLLM no soporta LM Studio como provider de embeddings** | No podemos usar `nomic-embed-text-v1.5` nativamente | Usar built-in `all-MiniLM-L6-v2` como fallback, o configurar OpenAI-compatible endpoint apuntando a LM Studio |
| **Ventana de contexto insuficiente para consultas multi-workspace** | Respuestas incompletas si la pregunta cruza workspaces | Mantener queries por workspace. Si se necesita cruce, usar el workspace AI-LAB Runtime como contenedor general |
| **Documentación duplicada entre workspaces** | Confusión al preguntar sobre un tema que existe en 2+ workspaces | Política global: si el documento existe en un workspace específico, priorizar ese. Para docs generales, usar AI-LAB Runtime |
| **AnythingLLM no distingue OBSERVADO/INFERIDO/SUPUESTO por defecto** | Riesgo de alucinación | Configurar instrucciones de sistema por workspace. Verificar respuestas con preguntas conocidas post-carga |
| **Reports duplican información de ADRs** | Ruido documental | En Fase A, cargar primero ADRs, luego reports. Los reports deben referenciar ADRs, no reemplazarlos |
| **Carga inicial grande (~150 archivos)** | AnythingLLM lento al indexar | Cargar por fases (A→B→C). Dejar 5 min entre fases para que el vector DB indexe |

---

## 7. Siguiente Fase

**ANYTHINGLLM-ENTERPRISE-02-WORKSPACE-CREATE**: Crear los 10 workspaces en AnythingLLM con la configuración definida. No cargar documentos todavía — solo crear workspaces, configurar instruct de sistema, modelo y embeddings.

### Pre-requisitos

1. Verificar que AnythingLLM está accesible (URL y puerto)
2. Verificar que LM Studio está sirviendo `nomic-embed-text-v1.5` (o configurar fallback)
3. Verificar conectividad AnythingLLM → LM Studio
4. Confirmar capacidad de vector DB para ~150 archivos (~3-5M tokens total)

### Criterios de éxito

- 10 workspaces creados con nombre, descripción e instruct
- Sistema responde coherentemente a preguntas de prueba (ej: "¿qué es el SOUL según Hermes?")
- Embeddings funcionales con el provider configurado
- Sin errores de chunking en documentos de prueba (Fase A)
