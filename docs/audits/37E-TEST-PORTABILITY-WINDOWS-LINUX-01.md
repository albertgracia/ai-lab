# 37E-TEST-PORTABILITY-WINDOWS-LINUX-01

**Estado:** PROPOSED
**Fecha:** 2026-06-11
**Objetivo:** Separar validacion funcional de asunciones de ruta Linux en la suite `DEV-36X` para que corra en Windows y Linux.

## Motivacion

Hallazgo abierto durante el cierre de 37D:

- `21 PASS`
- `10 FAIL`
- los 10 fallos dependen de `/opt/ai-lab/runtime`
- no hay evidencia de relacion con `_compute_score()`

## Evidencia

- `tests/test_codebase_memory_integration_dev36x.py:10` inserta `/opt/ai-lab` en `sys.path`
- `tests/test_codebase_memory_integration_dev36x.py:58-60` afirma que existe `/opt/ai-lab/runtime`
- varios tests posteriores dependen de ese root y fallan en Windows con `modules == {}`

## Alcance propuesto

1. Reemplazar paths hardcodeados por `RUNTIME_ROOT` o root derivado del repo.
2. Separar tests de contrato funcional de tests dependientes del entorno de despliegue.
3. Mantener compatibilidad Linux sin romper el caso productivo `/opt/ai-lab`.
4. Reejecutar la suite completa en Windows y Linux.

## Criterio de cierre propuesto

- misma suite funcional PASS en ambos entornos
- sin cambios en la semantica del scoring
- sin reabrir 37D salvo evidencia nueva
