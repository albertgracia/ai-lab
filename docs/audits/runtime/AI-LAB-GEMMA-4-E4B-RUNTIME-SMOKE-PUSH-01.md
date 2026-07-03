# AI-LAB-GEMMA-4-E4B-RUNTIME-SMOKE-PUSH-01

## Resultado: PASS

## HEAD inicial
- ebef7005 docs(audit): record lmstudio baseline push

## HEAD final
- 467bb63f merge: integrate remote public metrics before gemma smoke push

## Commit pusheado
- e19f81f4 docs(audit): smoke test gemma 4 e4b runtime

## Merge
- merge --no-ff
- commits remotos integrados: b642afa6 chore: update public metrics [skip ci]

## Confirmaciones
- Push principal realizado
- Branch sincronizada con origin/main
- Working tree limpio
- No tag en HEAD
- No runtime tocado
- No servicios tocados

## Smoke resumen
- Gateway avg: 10.23 tps
- Gateway min/max: 10.06 / 10.53 tps
- Router sample: 5.03 tps
- Gateway returned: qwen3-vl-8b-instruct
- Router returned: google/gemma-4-e4b
- Runtime health: 92.4
- nodes_online: 3
- routing_confidence: 0.91

## Nota operativa
- ailab-router/auto en OpenCode selecciona correctamente google/gemma-4-e4b.
- Gateway model preservation queda como pendiente no urgente.

## Riesgo residual
- Conviene abrir una fase de streaming vs non-streaming benchmark para separar tps internos de throughput end-to-end.

## Siguiente fase
- AI-LAB-LMSTUDIO-STREAMING-VS-NONSTREAMING-BENCHMARK-01
