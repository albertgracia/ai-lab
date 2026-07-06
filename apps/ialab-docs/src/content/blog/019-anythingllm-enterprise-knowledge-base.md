---
title: "AnythingLLM Enterprise: Knowledge Base con RAG validado"
date: "2026-07-01"
summary: "AnythingLLM se despliega como Knowledge Base enterprise con 1304 vectores en 7 workspaces, embedder multilingual e5-small y validación RAG E2E al 100%."
tags:
  - ai-lab
  - anythingllm
  - rag
  - knowledge-base
  - enterprise
---

## De memoria documental a knowledge base enterprise

AnythingLLM comenzó como un experimento de memoria documental para AI-LAB. Tras varias fases de evolución, ahora es una Knowledge Base enterprise con RAG validado al 100%, capaz de responder preguntas sobre arquitectura, operaciones, runbooks, marketplace y governance con precisión verificable.

## Arquitectura

```text
Documentos canónicos (84 fuentes)
  → AnythingLLM Workspace Manager
    → Embedder: multilingual-e5-small (Q8_0, 384-dim)
      → Qdrant (1304 vectores)
        → RAG query → LM Studio → respuesta con contexto
```

## Workspaces activos

7 workspaces especializados, cada uno con documentos, system prompt y configuración específica:

| Workspace | Docs | Propósito |
|-----------|------|-----------|
| ai-lab-core-runtime | 12 | Documentación del runtime principal |
| ai-lab-architecture-governance | 10 | Arquitectura + governance |
| ai-lab-operations-runbooks | 8 | Runbooks operativos |
| ai-lab-marketplace-docs | 7 | Documentación del marketplace |
| ai-lab-enterprise-hermes | 5 | Hermes Enterprise Core |
| ai-lab-evidence-reports | 53 | Reportes de evidencia |
| ai-lab-stack-2026 | 8 | Stack tecnológico 2026 |

## Configuración

- Chunk size: 800 tokens
- Chunk overlap: 100 tokens
- Embedder: `text-embedding-multilingual-e5-small` (Q8_0, 384 dimensiones)
- Similarity threshold: 0.40 (por defecto en AnythingLLM)
- Top N: 4 documentos por consulta

## Validación

RAG E2E validation: 100% PASS. Cada workspace responde correctamente con el contexto de sus documentos canónicos, sin alucinaciones ni fugas entre workspaces.

## Baseline congelada

La configuración actual está congelada en el checkpoint `CP-ANYTHINGLLM-ENTERPRISE-04-COMPLETE`. Cualquier cambio futuro requerirá re-validación completa.

Documentación completa en [docs/architecture/anythingllm-enterprise/](/docs/architecture/anythingllm-enterprise/).
