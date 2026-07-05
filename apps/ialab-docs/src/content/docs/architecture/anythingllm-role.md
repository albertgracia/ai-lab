---
title: "AnythingLLM — Memoria Documental de AI-LAB"
summary: "Rol de AnythingLLM en AI-LAB: memoria documental, auditor RAG, consumidor de documentación canónica y gobierno del conocimiento."
order: 7
---

AnythingLLM es la **memoria documental** del ecosistema AI-LAB. No ejecuta inferencia, no orquesta servicios, no implementa cambios. Su función es exclusivamente documental: indexar, recuperar y auditar el conocimiento del laboratorio.

## Rol principal

**Memoria documental del laboratorio.**

AnythingLLM no es un LLM más ni un sustituto de documentación. Es un **consumidor oficial** de la documentación canónica de AI-LAB.

## Responsabilidades

- Recuperación documental vía RAG
- Indexación de documentación canónica
- Auditoría documental (consistencia, cobertura, frescura)
- Consulta de conocimiento estructurado
- Gobierno documental (jerarquía, prioridad, trazabilidad)
- Contextualización de respuestas basadas en documentación oficial

## No es responsable de

- Implementar cambios en runtime o infraestructura
- Desplegar servicios
- Modificar configuración del laboratorio
- Ejecutar fases operativas
- Inferencia de modelos

## Separación de roles en AI-LAB

| Componente | Rol |
|---|---|
| **OpenCode** | Implementa cambios, refactoriza, despliega, automatiza |
| **AnythingLLM** | Documenta, indexa, audita, recupera conocimiento |
| **LM Studio** | Ejecuta inferencia, hospeda modelos en VRAM |
| **Unsloth** | Entrena y optimiza modelos (fine-tuning, LoRA) |
| **AI-LAB Runtime** | Orquesta el ecosistema, aplica políticas, expone servicios |
| **Astro (ialab-docs)** | Publica documentación canónica |

## Flujo de ciclo documental

```
OpenCode implementa / modifica funcionalidad
  ↓
OpenCode actualiza documentación en Astro
  ↓
AnythingLLM reindexa documentación canónica
  ↓
AnythingLLM aprende / recupera nuevo conocimiento
```

## Regla de reindexación

Toda fase PASS debe evaluar impacto documental. Si la documentación canónica cambia:

1. AnythingLLM debe reindexar el workspace correspondiente
2. Debe verificarse la recuperación documental mediante preguntas representativas
3. La nueva documentación debe estar accesible vía RAG

El protocolo completo de cierre de fase está en `governance/phase-closure-protocol`. Allí se definen los pasos obligatorios (evaluación, actualización, build, reindexación, validación) y los criterios PASS/PARTIAL/FAIL.

## Regla de calidad

AnythingLLM se considera **consumidor oficial** de la documentación de AI-LAB. Por tanto:

- La calidad documental afecta directamente la calidad de las respuestas
- Documentación incompleta genera conocimiento incompleto
- Documentación incorrecta genera respuestas incorrectas
- La documentación forma parte del entregable de cada fase

## Estado actual

AnythingLLM opera como **Knowledge Base Enterprise** multi-workspace desde julio de 2026. Indexa documentación canónica de todo el ecosistema AI-LAB y expone recuperación RAG vía API.

## Estado actual (Julio 2026)

### Despliegue Enterprise

AnythingLLM se ejecuta en `192.168.1.50:3001`. Su API key está configurada en el runtime de AI-LAB y en OpenCode para consultas RAG automatizadas.

**ATENCIÓN:** `192.168.1.30:3001` NO es AnythingLLM. Ese puerto en `.30` corresponde a **Grafana v12.0.2**. No confundir las URLs.

### Arquitectura de workspaces

AnythingLLM aloja **12 workspaces**, de los cuales **9 contienen documentos** y **3 están vacíos (legacy):**

| Workspace | Documentos | Estado |
|---|---|---|
| `ai-lab-runtime` | Documentación del runtime AI-LAB (AGENTS.md, fases, configuraciones) | ✅ Activo |
| `hermes-enterprise` | Documentación completa de Hermes (SOUL, Capability, Operator, Hook, MCP, Governance) | ✅ Activo |
| `adrs` | Architecture Decision Records (ADR-001 a ADR-006 y posteriores) | ✅ Activo |
| `reports` | Reportes de fase, burn-ins, análisis operativos | ✅ Activo |
| `rioja-marketplace` | Documentación del Marketplace Rioja | ✅ Activo |
| `observabilidad` | Documentación de observabilidad (Prometheus, Grafana, métricas, alertas) | ✅ Activo |
| `runbooks` | Runbooks operativos y procedimientos de recuperación | ✅ Activo |
| `stack-2026` | Documentación del stack tecnológico 2026 | ✅ Activo |
| `mcp-y-a2a` | Documentación de servidores MCP y protocolo A2A | ✅ Activo |
| `mi-espacio-de-trabajo` | Legacy — sin documentos | Vacío |
| `assistant-chats` | Legacy — sin documentos | Vacío |
| `ids` | Legacy — sin documentos | Vacío |

**Total de vectores:** 1304

### Embedder definitivo

El modelo de embedding utilizado por AnythingLLM es **multilingual-e5-small** (Q8_0, 384 dimensiones), servido por LM Studio en `192.168.1.50:1234`.

Este embedder fue seleccionado tras una migración desde el embedder por defecto de AnythingLLM. Soporta multilingüismo (español e inglés), permitiendo consultas RAG en ambos idiomas con alta precisión semántica.

### Chat LLM

El modelo usado por AnythingLLM para responder consultas RAG es `qwen2.5-14b-instruct`, servido por LM Studio en `192.168.1.50:1234`.

### Configuración de workspaces

Cada workspace activo tiene configurado:

- **Similarity threshold:** 0.60 — 0.75 (según contexto del workspace)
- **Top N:** 4 — 8 fragmentos recuperados
- **Temperature:** 0.1 — 0.3 (baja, priorizando precisión documental)
- **Document limit:** 20 — 50 documentos por workspace
- **Chunk size:** 750 — 1500 caracteres (tuning por tipo de documento)
- **Chunk overlap:** 150 — 250 caracteres

### Validación RAG E2E

La recuperación documental fue validada extremo a extremo con preguntas representativas de cada dominio:

- **RAG E2E validation: 100% PASS**
- La cobertura documental permite responder preguntas sobre runtime, Hermes Enterprise, ADRs, reportes, marketplace, observabilidad, runbooks y MCP/A2A.

### Baseline congelada

El estado actual de AnythingLLM está congelado como baseline en el checkpoint:

```
CP-ANYTHINGLLM-ENTERPRISE-04-COMPLETE
```

Cualquier cambio posterior en workspaces, documentos o configuración debe partir de esta baseline y documentarse como fase nueva de AnythingLLM Enterprise.

### Clasificación documental

Clasificación: **CANÓNICO**
Prioridad: **ALTA**

AnythingLLM es el punto oficial de consulta RAG para agentes, operadores y documentación automatizada. Su contenido debe reflejar fielmente la documentación canónica publicada en Astro y los ADRs aprobados.
