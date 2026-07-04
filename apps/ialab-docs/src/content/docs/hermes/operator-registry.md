---
title: "Operator Registry"
summary: "5 operadores con execution modes, truth model y validación de contratos."
order: 5
---

## Estado: ✅ Implementado

## Operadores

| ID | Execution Mode | Authorization | Prioridad | Capabilities |
|----|---------------|---------------|-----------|-------------|
| `architectural-review` | readonly | no | 30 | gitnexus-analysis, ai-lab-runtime |
| `deployment-review` | advisory | yes | 80 | deployment-review, gitnexus-analysis, marketplace-operator |
| `runtime-observe` | readonly | no | 10 | ai-lab-runtime |
| `incident-observe` | readonly | no | 40 | incident-response, observability, ai-lab-runtime |
| `marketplace-observe` | readonly | no | 20 | marketplace-operator, gitnexus-analysis |

## Execution Modes

| Modo | Descripción | Authorization |
|------|-------------|---------------|
| `readonly` | Solo lectura, sin efectos secundarios | No requerida |
| `advisory` | Lectura + recomendaciones | Requerida |
| `execute` | Ejecución de acciones | Requerida |

**Estado actual:** ningún operador en modo `execute`.

## Truth Model

Cada operador declara:
- `min_confidence`: nivel mínimo de confianza para actuar
- `require_citations`: si debe citar fuentes en reportes
- `success_criteria`: condiciones de éxito
- `failure_conditions`: condiciones de fallo

## Validación

- 17 tests específicos en `test_hermes_operator_registry.py`
- IDs únicos, capabilities existen, execution modes válidos
- MCP referenciados existen
- Truth model completo (min_confidence, require_citations)
- Sin ejecución activa
