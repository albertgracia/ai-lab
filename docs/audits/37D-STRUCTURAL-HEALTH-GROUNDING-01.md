# 37D-STRUCTURAL-HEALTH-GROUNDING-01

**Estado:** PASS
**Fecha:** 2026-06-11
**Objetivo:** Regroundear `codebase_health` para reflejar riesgo operacional real y no ruido estructural.

## Alcance

Archivo modificado:

- `runtime/codebase/gitnexus_memory.py`

Cambio aplicado en `runtime/codebase/gitnexus_memory.py:281`:

- `wide_blast_radius` deja de penalizar el score
- `authority_dependency_spread` deja de penalizar el score
- `high_reverse_coupling` mantiene peso operacional
- `high_coupling` pasa a penalizacion reducida
- se anade desglose nuevo con `breakdown`, `risk_classification` y `total_findings`
- se preserva compatibilidad con `structural_health_score`, `level`, `high_risks`, `medium_risks`, `low_risks`

## Validacion de cierre

### Sanidad del modulo

- `C:\ProgramData\anaconda3\python.exe -m py_compile runtime\codebase\gitnexus_memory.py` -> PASS

### Regresion funcional focalizada en scoring

- `test_compute_score_returns_dict` -> PASS
- `test_compute_score_deterministic` -> PASS
- `test_build_codebase_score_returns_valid` -> PASS

Comando ejecutado:

```powershell
C:\ProgramData\anaconda3\python.exe -m pytest tests/test_codebase_memory_integration_dev36x.py -k "test_compute_score_returns_dict or test_compute_score_deterministic or test_build_codebase_score_returns_valid" -v
```

Resultado:

- `3 passed, 28 deselected`

## Suite disponible en este workspace

Ejecucion observada de `tests/test_codebase_memory_integration_dev36x.py`:

- `21 PASS`
- `10 FAIL`

Clasificacion de los 10 FAIL:

- no relacionados con el scoring implementado
- dependientes de rutas Linux hardcodeadas
- esperan `/opt/ai-lab/runtime`
- este workspace corre en `E:\opencode\ai-lab`

Evidencia principal en tests:

- `tests/test_codebase_memory_integration_dev36x.py:10` -> `sys.path.insert(0, "/opt/ai-lab")`
- `tests/test_codebase_memory_integration_dev36x.py:58-60` -> assert directo sobre `/opt/ai-lab/runtime`

## Evaluacion de regresion

No aparece evidencia de regresion funcional del scoring.

Razones:

1. El modulo compila correctamente.
2. Los tests que ejercitan el scoring pasan.
3. Los 10 fallos restantes no cubren la logica nueva de `_compute_score()`.
4. Los fallos restantes dependen del entorno y de portabilidad de rutas, no de la nueva formula.

## Hallazgo separado

Se clasifica como hallazgo independiente:

- **37E-TEST-PORTABILITY-WINDOWS-LINUX-01**

Descripcion:

- la suite `DEV-36X` mezcla validacion funcional con asunciones de despliegue Linux
- eso impide validar el modulo completo desde este workspace Windows aunque el scoring sea correcto

Decision:

- no bloquea el cierre de 37D
- debe tratarse en fase separada

## Decision final

**37D PASS**

Justificacion:

- scoring grounded implementado
- compatibilidad preservada
- validacion focalizada PASS
- sin evidencia de regresion funcional
- los fallos restantes son de portabilidad del harness de tests, no del scoring
