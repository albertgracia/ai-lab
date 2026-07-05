---
title: "AnythingLLM Enterprise"
summary: "Knowledge Base Enterprise de AI-LAB sobre AnythingLLM Desktop: 1304 vectores, 7 workspaces activos, RAG 100%."
order: 8
---

## Stack de despliegue

| Componente | Host | Puerto | Detalle |
|------------|------|--------|---------|
| AnythingLLM Desktop | Red privada | 3001 | v1.x — API REST + UI |
| LM Studio | Red privada | 1234 | Backend de inferencia y embeddings |
| Embedder | multilingual-e5-small (Q8_0) | — | 384 dimensiones |
| Chat LLM | qwen2.5-14b-instruct (Q4_K_M) | — | Modelo de respuesta RAG |
| Vector DB | LanceDB | — | Integrado en AnythingLLM

## Workspaces

AnythingLLM aloja **12 workspaces**, de los cuales **9 contienen documentos** y **3 legacy vacíos** (`mi-espacio-de-trabajo`, `assistant-chats`, `ids`).

### Workspaces activos con documentos

| Workspace | Vectores | Documentos | Contenido |
|-----------|----------|------------|-----------|
| `hermes-enterprise` | 190 | ~35 | Python/YAML/JSON de Hermes Enterprise Core |
| `reports` | 456 | 53 | Reportes canónicos de fase y burn-in |
| `adrs` | 50 | ~10 | ADR-001 a ADR-006 y posteriores |
| `ai-lab-runtime` | 100 | ~20 | AGENTS.md, fases, configuraciones del runtime |
| `rioja-marketplace` | 99 | 7 | Documentación del Marketplace Rioja |
| `observabilidad` | 27 | 2 | Prometheus, Grafana, métricas, alertas |
| `runbooks` | 40 | 4 | Runbooks operativos y procedimientos de recuperación |
| `stack-2026` | 55 | 4 | Documentación del stack tecnológico 2026 |
| `mcp-y-a2a` | 160 | 19 | Servidores MCP y protocolo A2A |

**Total:** ~136 documentos importados, **1304 vectores**.

### Canon de conocimiento

Los documentos provienen de:

- **Hermes Enterprise:** Código Python, schemas YAML/JSON de SOUL, Capability, Operator, Hook, MCP, Governance
- **ADRs:** Architecture Decision Records completos
- **AI-LAB Runtime:** Documentación operativa del runtime
- **Reports:** 53 reportes canónicos de fase (FASE 28 — FASE 39)
- **Marketplace:** 7 documentos del Marketplace Rioja
- **Observabilidad + IDS:** 2 documentos de monitoreo
- **Runbooks + Stack-2026:** 8 documentos operativos
- **MCP + A2A:** 19 documentos de servidores MCP y protocolo A2A

### Limpieza de ruido

Se eliminaron **40 archivos YAML/JSON** del workspace `hermes-enterprise` que producían chunks sintácticos de ~108 caracteres (schemas planos sin contexto semántico). Estos chunks contaminaban los rankings de recuperación con fragmentos sin significado documental.

## Decisión de embedder

| Embedder | Recall español | Recall inglés | Decisión |
|----------|---------------|---------------|----------|
| `nomic-embed-text-v1.5` | 2/4 | — | ❌ Rechazado |
| `multilingual-e5-small` (Q8_0) | **4/4** | Alto | ✅ **Elegido** |

**Criterio:** `multilingual-e5-small` fue seleccionado por recall superior en español (4/4 vs 2/4 de `nomic-embed-text-v1.5`). Migración completa ejecutada en **subfase 04A2**, con regeneración total de vectores.

**Congelado:** No cambiar embedder sin fase nueva explícita.

## Validación RAG E2E

El sistema fue validado extremo a extremo con cobertura de todos los workspaces activos:

| Dimensión | Resultado |
|-----------|-----------|
| Vector search | 21/21 PASS |
| Chat API | 14/14 PASS |
| Contaminación entre workspaces | 0% |
| **Score global** | **100%** |

### Limitación conocida: sin fuentes en chat API

AnythingLLM Desktop no reporta `sources[]` en las respuestas del endpoint de chat (`/api/v1/workspace/:slug/chat`). El array `sources` siempre aparece vacío, incluso cuando la recuperación RAG es correcta.

**Mitigación:** para trazabilidad, usar el endpoint de vector search (`POST /api/v1/workspace/:slug/vector-search`) combinado con prompt manual que inyecte los fragmentos recuperados. Esto permite verificar qué documentos soportan cada respuesta.

## Riesgos

| ID | Severidad | Descripción |
|----|-----------|-------------|
| **R-01** | 🔴 CRITICAL | Sin citas de fuentes en chat API — no hay trazabilidad automática de respuestas |
| **R-02** | 🟡 MEDIUM | Respuestas genéricas en contextos ambiguos (ej. MCP interpretado como "Middleware Configuration Platform" en lugar de Model Context Protocol) |
| **R-03** | 🟢 LOW | Chunks cortos persistentes en documentos mayores a 10 KB que generan fragmentos sin contexto suficiente |
| **R-04** | 🟢 LOW | A2A sin documentación independiente — todo el conocimiento depende de una sola fuente |

## Baseline congelada

```
Checkpoint:  CP-ANYTHINGLLM-ENTERPRISE-04-COMPLETE
Commit:      7b50e67
Fecha:       2026-07-05
```

La baseline **no debe modificarse**. Está prohibido:

- Importar nuevos documentos
- Cambiar el embedder
- Modificar chunk size, overlap o similarity threshold
- Cambiar prompts del sistema
- Alterar configuración de workspaces existentes

Cualquier cambio futuro debe iniciar una **fase ANYTHINGLLM-ENTERPRISE-05** con necesidad funcional real validada previamente.

## Próxima fase

| Fase | Estado | Requisito |
|------|--------|-----------|
| ANYTHINGLLM-ENTERPRISE-05 | ⏸️ Bloqueada | Necesidad funcional real |

No abrir nueva fase sin un caso de uso documentado que justifique modificar la baseline congelada.

## Referencias

- Rol documental de AnythingLLM: `architecture/anythingllm-role`
- Reporte diseño workspaces: `reports/ANYTHINGLLM-ENTERPRISE-01-WORKSPACE-DESIGN.md`
- Reporte creación workspaces: `reports/ANYTHINGLLM-ENTERPRISE-03-WORKSPACE-CREATE.md`
- Reporte KB Enterprise completo: `reports/ANYTHINGLLM-ENTERPRISE-04-COMPLETE.md`
