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

AnythingLLM opera con un workspace AI-LAB dedicado. Indexa documentación canónica desde `anythingllm-core/` y documentación Astro publicada.

Clasificación documental: **CANÓNICO**
Prioridad: **ALTA**
