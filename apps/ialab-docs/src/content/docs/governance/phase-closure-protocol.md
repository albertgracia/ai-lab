---
title: "AI-LAB Phase Closure Protocol (01)"
summary: "Protocolo oficial de cierre de fase para AI-LAB. Toda fase debe evaluar impacto documental, actualizar documentación, reindexar AnythingLLM y validar recuperación documental antes de declararse PASS."
order: 5
---

## Versión del protocolo

`AI-LAB-PHASE-CLOSURE-PROTOCOL-01`

## Principio fundamental

La documentación forma parte del sistema. Una fase no está cerrada hasta que la documentación asociada está actualizada, indexada y verificable.

## Ámbito

Este protocolo aplica a toda fase que:

- Introduzca nueva funcionalidad, componente o servicio
- Modifique arquitectura, rutas o dependencias
- Cambie responsabilidades entre dominios
- Añada o modifique nodos de infraestructura
- Modifique procedimientos operativos
- Cambie políticas de governance o seguridad
- Modifique contratos o APIs expuestas
- Introduzca nuevos modelos o cambie el modelo set activo
- Modifique el stack de observabilidad

## No aplica a

- Fases exclusivamente READ-ONLY (auditorías, investigaciones)
- Fases de documentación pura sin cambios operacionales
- Correcciones de typos o erratas sin impacto semántico

En estos casos, el cierre puede ser PARTIAL (ver criterios abajo).

## Checklist de cierre obligatorio

### Paso 1: Evaluación de impacto documental

Antes de cerrar una fase, responder:

| Pregunta | Criterio |
|---|---|
| ¿La fase introduce nuevos conceptos? | Si → documentación nueva |
| ¿La fase modifica comportamiento existente? | Si → actualizar documentación afectada |
| ¿La fase añade/quita nodos o servicios? | Si → actualizar infraestructura y AGENTS.md |
| ¿La fase cambia APIs o endpoints? | Si → actualizar contratos |
| ¿La fase afecta a AnythingLLM? | Si → reindexar y validar |
| ¿La fase modifica documentación Astro? | Si → build Astro obligatorio |
| ¿La fase cambia el modelo set activo? | Si → actualizar modelo set en docs |
| ¿La fase introduce nuevas reglas de governance? | Si → documentar en governance/ |

Si **ninguna** respuesta es "Si", el cierre puede ser PARTIAL (solo actualizar fases list).

### Paso 2: Actualización documental

Ejecutar en orden:

1. **Documentación canónica**: crear o modificar documentos en `apps/ialab-docs/src/content/docs/`
2. **AGENTS.md**: actualizar lista de fases, próxima fase, roadmap y reglas si aplica
3. **OPENCODE.md**: actualizar si cambia el perfilado o las instrucciones del agente
4. **anythingllm-core/**: actualizar si cambia infraestructura o documentación canónica

### Paso 3: Astro build

Si se modificó `apps/ialab-docs/`:

```bash
cd /opt/ai-lab/apps/ialab-docs
npm run build
```

Criterio: build debe completar sin errores. Warnings de chunk size se permiten.

### Paso 4: Reindexación AnythingLLM

Si la fase tiene impacto documental:

1. Verificar qué documentos nuevos o modificados deben indexarse
2. Acceder al panel de AnythingLLM
3. Seleccionar el workspace AI-LAB
4. Ejecutar "Reindex" en el workspace
5. Esperar a que la indexación complete

Si no es posible reindexar (entorno no disponible, fase puramente documental en workspace SMB), el cierre puede ser PARTIAL documentando la razón.

### Paso 5: Validación de recuperación documental

Formular al menos 2 preguntas representativas sobre el contenido nuevo y verificar que AnythingLLM las responde correctamente usando la documentación indexada.

Ejemplos de preguntas según el cambio:

| Tipo de cambio | Pregunta de validación |
|---|---|
| Nuevo componente | "¿Qué hace [componente]?" |
| Nueva infraestructura | "¿Qué nodos forman parte de AI-LAB?" |
| Nuevo contrato | "¿Qué versión tiene el contrato [nombre]?" |
| Nueva política | "¿Cuándo debe reindexarse AnythingLLM?" |
| Nuevo protocolo | "¿Qué pasos tiene el protocolo de cierre de fase?" |

Criterio PASS: las respuestas son correctas y están basadas en la documentación indexada.

### Paso 6: Determinación del estado de cierre

| Estado | Condición |
|---|---|
| **PASS** | Todos los pasos 1-5 completados sin salvedades. Documentación actualizada, build OK, AnythingLLM reindexado y validado. |
| **PARTIAL** | Impacto documental identificado y documentación actualizada, pero reindexación AnythingLLM no posible (entorno no disponible, restricción de acceso). Debe documentarse la razón y planificar reindexación futura. |
| **FAIL** | Documentación no actualizada, build roto, o impacto documental no evaluado. |

### Paso 7: Registro de cierre

Cada fase cerrada debe incluir en su resumen (AGENTS.md, commit message, o documento de fase):

```
Documentación: [actualizada / no aplica]
Build Astro: [PASS / no aplica / FAIL]
AnythingLLM: [reindexado / no aplica / pendiente (razón)]
Validación: [PASS / no aplica / pendiente]
Estado cierre: [PASS / PARTIAL / FAIL]
```

## Excepciones

### Fases READ-ONLY

Las fases de auditoría, investigación o diagnóstico sin cambios en el sistema no requieren reindexación AnythingLLM. El cierre puede ser PASS si:

- El informe de auditoría está documentado
- No hay documentación canónica nueva que indexar
- No hay cambios en AGENTS.md más allá de añadir la fase a la lista

### Fases de documentación pura

Fases que solo crean o modifican documentación (sin cambios operacionales ni de infraestructura) requieren:

- Build Astro (si afecta a Astro)
- Reindexación AnythingLLM (si los documentos son canónicos)
- Validación de recuperación

### Emergencia o hotfix

Si una fase debe cerrarse rápido por emergencia operativa, se permite PARTIAL con documentación de la razón. La reindexación y validación deben completarse dentro de las siguientes 24h o en la siguiente fase programada.

## Relación con otros documentos

| Documento | Relación |
|---|---|
| `anythingllm-role.md` | Define el rol de AnythingLLM como consumidor oficial. Este protocolo concreta cuándo y cómo reindexar. |
| `AI-LAB-DOCUMENTATION-GOVERNANCE.md` | Define reglas generales de gobierno documental. Este protocolo las operacionaliza para cierre de fase. |
| `AGENTS.md` | Lista de fases, reglas de git y checkpoint integrity. Este protocolo añade la evaluación documental como requisito de cierre. |
| `AI-LAB-PHASE-METHODOLOGY.md` | Metodología de fases. Este protocolo es el checklist de cierre que complementa esa metodología. |
| `Git Discipline & Checkpoint Integrity Rule` (AGENTS.md) | Reglas de commit+tag. Este protocolo añade la capa documental antes del tag. |

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 01 | 2026-06-11 | Versión inicial del protocolo de cierre de fase |
