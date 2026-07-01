# AI-LAB-LMSTUDIO-RUNTIME-PERFORMANCE-BASELINE-PUSH-01

## Resultado: PASS

## HEAD inicial
- eeefb720 docs(audit): record grafana health score labeling push

## HEAD final
- febfce3c docs(audit): record lmstudio runtime performance baseline

## Commit pusheado
- febfce3c docs(audit): record lmstudio runtime performance baseline

## Merge
- No hubo merge adicional

## Publicado
- docs/audits/AI-LAB-LMSTUDIO-RUNTIME-PERFORMANCE-BASELINE-01.md

## Validaciones
- Push principal realizado
- Branch sincronizada con origin/main
- Working tree limpio
- No tag en HEAD
- No runtime tocado
- No servicios tocados

## Baseline resumen
- Gateway avg: 10.40 tps
- Gateway min/max: 10.03 / 10.78 tps
- Router sample: 2.79 tps
- Gateway runtime: 89.6
- nodes_online: 2
- routing_confidence: 0.89
- Prometheus cognitive health: 86.8
- Prometheus nodes_online: 3
- Prometheus routing_confidence: 0.87

## Riesgo residual
- La medicion formal quedo por debajo de la observacion informal de 30-50 tps.
- Conviene separar streaming vs non-streaming y tps internos vs end-to-end en el siguiente paso.

## Siguiente fase
- AI-LAB-LMSTUDIO-STREAMING-VS-NONSTREAMING-BENCHMARK-01
