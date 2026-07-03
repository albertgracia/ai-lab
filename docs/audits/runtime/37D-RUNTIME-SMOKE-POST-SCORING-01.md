# 37D-RUNTIME-SMOKE-POST-SCORING-01

**Estado:** PARTIAL
**Fecha:** 2026-06-11
**Modo:** smoke runtime controlado
**Objetivo:** Verificar en runtime real si el scoring grounded de 37D esta desplegado y si genera regresion operacional.

## Resultado ejecutivo

La smoke se ejecuto, pero el runtime activo debe tratarse como **NOT_DEPLOYED** respecto al cambio `15879d8`.

No se aplico rollout automatico.

Conclusion operativa:

- `37D` esta **commiteada localmente**
- el runtime activo **no tiene evidencia suficiente de estar usando ese commit**
- `Gateway` y `Router` estan `OK`
- `health_score` live se mantiene en `79.6`
- no hay evidencia de regresion operacional en el runtime activo
- el efecto del nuevo `codebase_health` no puede validarse live hasta hacer rollout controlado

## Preflight

### Git local

- `git status --short` -> limpio
- `git rev-parse HEAD` -> `15879d896fd46a3c9a34e0dc257ebc1b3530b6cc`
- `git log --oneline --decorate -5` -> `15879d8 (HEAD -> main) runtime(codebase): ground structural health scoring`
- `git branch -vv` -> `main` esta `[origin/main: ahead 1]`
- `git rev-list --left-right --count origin/main...HEAD` -> `0 1`

### Interpretacion de despliegue

Hecho verificable:

- el cambio 37D existe solo en el commit local `15879d8`
- `origin/main` sigue en `bc514a9`
- no se realizo push
- no se realizo deploy
- no se reinicio ningun servicio

Decision operacional:

- el runtime activo se clasifica como **NOT_DEPLOYED** para 37D

## Smoke del runtime activo

### Estado de servicios

Fuente: MCP runtime status / runtime health / SLO status.

- Gateway `OK` -> `http://127.0.0.1:8008/health` responde `200`
- Router `OK` -> `http://127.0.0.1:8083/health` responde `200`
- `runtime/health` -> `score = 79.6`, `status = warning`
- `runtime/slo/status` -> `overall_status = healthy`
- `runtime/slo/violations` -> `violations_total = 0`

### Scores observados

| Campo | Baseline conocido | Valor live observado | Estado |
|---|---:|---:|---|
| validation_score | 75.1 | NO DISPONIBLE | no verificable live desde este entorno |
| health_score | 79.6 | 79.6 | sin regresion |
| codebase_health | 20.0 (37C, scoring anterior) | NO DISPONIBLE | cambio no verificable live |

## Limitaciones observadas

Desde este entorno:

- el MCP puede verificar `Gateway`, `Router`, `runtime/health` y `SLO`
- los intentos directos a `/runtime/validation` y `/runtime/validation/score` desde PowerShell/WebFetch no devolvieron acceso util

Esto no invalida la decision de despliegue porque el estado `NOT_DEPLOYED` ya queda sustentado por la divergencia entre `HEAD` y `origin/main` y la ausencia total de rollout.

## Comparacion contra 37C / 37D

### 37C baseline documentado

- `codebase_health = 20.0`
- `validation_score = 75.1`
- `health_score = 79.6`

### 37D cambio local

- `wide_blast_radius` ya no penaliza
- `authority_dependency_spread` ya no penaliza
- `high_reverse_coupling` sigue penalizando
- `high_coupling` penaliza menos

### Estado actual del runtime real

- no hay evidencia de que el runtime activo este ejecutando `15879d8`
- por tanto, no procede afirmar un nuevo `codebase_health` live

## Evaluacion de regresion operacional

### Verificado

1. `Gateway` operativo
2. `Router` operativo
3. `health_score` no cae por debajo de `79.6`
4. `SLO` sigue `healthy`
5. `violations_total = 0`

### No verificable todavia

1. `validation_score >= 75.1` live
2. exposicion live de `codebase_health` grounded
3. exposicion live de `breakdown` / `risk_classification`

Motivo:

- el cambio no esta desplegado en el runtime activo

## Conclusion

**Resultado de fase: PARTIAL**

Justificacion:

1. la smoke runtime se ejecuto
2. el estado de despliegue quedo identificado con evidencia suficiente
3. el runtime activo esta sano a nivel operacional
4. el cambio de scoring 37D sigue local y no desplegado
5. no existe evidencia para declarar PASS post-scoring en runtime real sin rollout

## Siguiente fase propuesta

**37D-STRUCTURAL-HEALTH-ROLLOUT-01**

Objetivo:

- desplegar controladamente `15879d8` en el runtime real
- volver a ejecutar smoke sobre `/runtime/validation`, `/runtime/health` y la superficie donde aparezca `codebase_health`
- confirmar el nuevo valor grounded en produccion sin degradar `validation_score` ni `health_score`
